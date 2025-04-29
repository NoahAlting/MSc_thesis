import os
import sys
import subprocess
import laspy
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box, Polygon
from shapely.ops import unary_union
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from tqdm import tqdm
import time

from shared_logging import setup_module_logger

logger = None

def load_municipality_geojson(filename):
    gdf = gpd.read_file(filename)
    assert all(gdf.geometry.type == "Point"), "GeoJSON must contain Point geometries"
    gdf = gdf[["OBJECTID", "BOOMSORTIMENT", "geometry"]]
    gdf["BOOMSORTIMENT"] = gdf["BOOMSORTIMENT"].astype(pd.StringDtype())
    return gdf.to_crs("EPSG:28992")


def load_forest_gdf(laz_file_path):
    with laspy.open(laz_file_path) as las:
        points = las.read()
        scale = las.header.scales
        offset = las.header.offsets

        X = points.X * scale[0] + offset[0]
        Y = points.Y * scale[1] + offset[1]
        Z = points.Z * scale[2] + offset[2]

        attributes = {dim.name: np.array(getattr(points, dim.name)) for dim in points.point_format}
        df = pd.DataFrame(attributes)
        df['X'] = X
        df['Y'] = Y
        df['Z'] = Z

        # df = df[['tree_id', 'X', 'Y', 'Z', 'red', 'green', 'blue', 'nir', 'ndvi', 'norm_g', 'mtvi2']]
        df['geometry'] = df.apply(lambda row: Point(row['X'], row['Y'], row['Z']), axis=1)
        df.drop(columns=['X', 'Y', 'Z'], inplace=True)

        return gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:28992")


def get_bbox_from_las(las_path):
    with laspy.open(las_path) as las_file:
        bbox_min = las_file.header.min  # [min_x, min_y, min_z]
        bbox_max = las_file.header.max  # [max_x, max_y, max_z]
    return box(bbox_min[0], bbox_min[1], bbox_max[0], bbox_max[1])


def compute_tree_convex_hulls(gdf):
    gdf = gdf[gdf["tree_id"] != -1]
    hull_gdf = gdf.groupby("tree_id")["geometry"].apply(
        lambda geom: Polygon(unary_union(geom).convex_hull.exterior)
    ).reset_index()
    return gpd.GeoDataFrame(hull_gdf, geometry="geometry", crs=gdf.crs)


def run_cpp_segmenter_local(exe, input_path, output_path, radius, vres, min_pts):
    cmd = [exe, input_path, output_path, str(radius), str(vres), str(min_pts)]
    try:
        start = time.time()
        subprocess.run(cmd, check=True, text=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        runtime = time.time() - start
        return True, runtime
    except subprocess.CalledProcessError:
        return False, 0.0


def run_segmentation_and_analyze(data_dir, exe, input_xyz, output_dir,
                                  radius_vals, vres_vals, min_pts_vals,
                                  municipality_geojson, forest_las_name,
                                  csv_name,
                                  cores=4, overwrite=False,
                                  delete_segmentation_after_processing=False):
    global logger
    if logger is None:
        logger = setup_module_logger("segmentation_analysis", data_dir)

    logger.info("[sweep_segment_analyze] Sweep + Analysis started")

    segmentation_dir = output_dir
    os.makedirs(segmentation_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, csv_name)

    logger.info("Loading and clipping municipality public trees")
    muni_gdf = load_municipality_geojson(municipality_geojson)
    forest_bbox = get_bbox_from_las(os.path.join(data_dir, forest_las_name))
    muni_gdf = muni_gdf[muni_gdf.within(forest_bbox)].copy()
    logger.info("Clipped municipality points, remaining: %d", len(muni_gdf))

    combos = list(product(radius_vals, vres_vals, min_pts_vals))

    existing_combos = set()
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
        existing_combos = set(zip(df_existing["Radius"], df_existing["Vertical Res"], df_existing["Min Points"]))

    def process_task(args):
        (r, v, m), idx = args
        out_file = os.path.join(segmentation_dir, f"segmentation_{idx:04d}.xyz")

        if not overwrite and (r, v, m) in existing_combos:
            logger.info("Skipping existing combination: Radius=%.2f, VRes=%.2f, MinPts=%d", r, v, m)
            return None

        logger.info("Processing new combination: Radius=%.2f, VRes=%.2f, MinPts=%d", r, v, m)

        success, runtime = run_cpp_segmenter_local(
            exe, os.path.join(data_dir, input_xyz), out_file, r, v, m
        )

        if not success:
            return None

        try:
            seg_df = pd.read_csv(out_file, sep=r"\s+", header=None, names=["tree_id", "x", "y", "z"])
            seg_gdf = gpd.GeoDataFrame(seg_df, geometry=gpd.points_from_xy(seg_df.x, seg_df.y), crs="EPSG:28992")
            hulls_gdf = compute_tree_convex_hulls(seg_gdf)

            if hulls_gdf.empty:
                logger.warning("No hulls generated for %s", out_file)
                return None

            counts = []
            for hull in hulls_gdf.geometry:
                inside = muni_gdf[muni_gdf.within(hull)]
                counts.append(len(inside))

            counts_series = pd.Series(counts)
            hulls_0 = (counts_series == 0).sum()
            hulls_1 = (counts_series == 1).sum()
            hulls_2 = (counts_series == 2).sum()
            hulls_3 = (counts_series == 3).sum()
            hulls_4plus = (counts_series > 3).sum()

            all_hulls_union = hulls_gdf.geometry.union_all()
            unmatched = muni_gdf[~muni_gdf.within(all_hulls_union)]

            return {
                "File Name": os.path.basename(out_file),
                "Radius": r,
                "Vertical Res": v,
                "Min Points": m,
                "Num Points": len(seg_df),
                "Num Trees": seg_df["tree_id"].nunique(),
                "Runtime (s)": round(runtime, 2),
                "Hulls with 0": hulls_0,
                "Hulls with 1": hulls_1,
                "Hulls with 2": hulls_2,
                "Hulls with 3": hulls_3,
                "Hulls with 4+": hulls_4plus,
                "Public trees unmatched": len(unmatched)
            }

        except Exception as e:
            logger.exception("Failed to process %s: %s", out_file, str(e))
            return None

    start_idx = 0
    if os.path.exists(csv_path):
        start_idx = len(pd.read_csv(csv_path))

    tasks = [((r, v, m), start_idx + i) for i, (r, v, m) in enumerate(combos)]

    with ThreadPoolExecutor(max_workers=cores) as pool:
        for (result, args) in tqdm(zip(pool.map(process_task, tasks), tasks), total=len(tasks), desc="Sweep+Analyze", disable=not sys.stdout.isatty()):
            if result:
                append_result_to_csv(csv_path, result, overwrite)

                if delete_segmentation_after_processing:
                    (_, idx) = args
                    out_file = os.path.join(segmentation_dir, f"segmentation_{idx:04d}.xyz")
                    try:
                        os.remove(out_file)
                        logger.info("Deleted segmentation file after processing: %s", out_file)
                    except Exception as e:
                        logger.error("Failed to delete segmentation file %s: %s", out_file, str(e))


    logger.info("[sweep_segment_analyze] Sweep + Analysis finished")

def append_result_to_csv(csv_path, row_dict, overwrite=False):
    cols = ["File Name", "Radius", "Vertical Res", "Min Points", "Num Points", "Num Trees", "Runtime (s)",
            "Hulls with 0", "Hulls with 1", "Hulls with 2", "Hulls with 3", "Hulls with 4+", "Public trees unmatched"]
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if overwrite:
            df = df[~((df["Radius"] == row_dict["Radius"]) &
                     (df["Vertical Res"] == row_dict["Vertical Res"]) &
                     (df["Min Points"] == row_dict["Min Points"]))]
    else:
        df = pd.DataFrame(columns=cols)
    df.loc[len(df)] = row_dict
    df.to_csv(csv_path, index=False)

if __name__ == "__main__":
    data_dir = "whm_100"
    segmentation_exe = os.path.join(".", "segmentation_code", "build", "segmentation")
    municipality_geojson = "Bomen_in_beheer_door_gemeente_Delft.geojson"
    forest_las_name = "forest.laz"
    csv_name = "segmentation_stats.csv"

    run_segmentation_and_analyze(
        data_dir=data_dir,
        exe=segmentation_exe,
        input_xyz="forest.xyz",
        output_dir=os.path.join(data_dir, "segmentation_results"),
        radius_vals=[1, 2.5, 5, 7.5],
        vres_vals=[1, 2],
        min_pts_vals=[1],
        municipality_geojson=municipality_geojson,
        forest_las_name=forest_las_name,
        csv_name=csv_name,
        cores=4,
        overwrite=False,
        delete_segmentation_after_processing=False
    )