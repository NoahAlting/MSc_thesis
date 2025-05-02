import os
import sys
import subprocess
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box, Polygon
from shapely.ops import unary_union
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from concurrent.futures import as_completed
from tqdm import tqdm
import time

from shared_logging import setup_module_logger
from segmentation_analysis import load_municipality_geojson, get_bbox_from_las

logger = None

def compute_tree_convex_hulls(gdf, idx=None):
    """
    Compute convex hulls per tree_id.
    Only create a hull if enough points are available.
    """
    hulls = []

    for tree_id, group in gdf.groupby("tree_id"):
        if group.empty or len(group) < 3:
            logger.warning(f"Iteration {idx}: Tree ID {tree_id} has less than 3 points, skipping hull computation.")
            continue  # Skip if less than 3 points

        union = unary_union(group.geometry)

        hull = union.convex_hull  # Should be a Polygon

        hulls.append({
            "tree_id": tree_id,
            "geometry": hull
        })

    hulls_gdf = gpd.GeoDataFrame(hulls, crs=gdf.crs)
    return hulls_gdf



def run_segmentation_public_matching(data_dir, exe, input_xyz, output_dir,
                                      radius_vals, vres_vals, min_pts_vals,
                                      municipality_geojson, forest_las_name,
                                      csv_name,
                                      cores=4,
                                      overwrite_existing_combos=False,
                                      delete_segmentation_after_processing=False):
    global logger
    if logger is None:
        logger = setup_module_logger("segmentation_public_match", data_dir)

    logger.info("[segmentation_public_match] Starting public tree matching sweep")

    segmentation_dir = output_dir
    os.makedirs(segmentation_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, csv_name)

    # Load and prepare public trees
    logger.info("Loading municipality public tree dataset")
    muni_gdf = load_municipality_geojson(municipality_geojson)
    muni_gdf = muni_gdf.to_crs("EPSG:28992")

    forest_bbox = get_bbox_from_las(os.path.join(data_dir, forest_las_name))
    public_trees_gdf = muni_gdf[muni_gdf.within(forest_bbox)].copy()

    logger.info("Clipped public trees to forest bbox, remaining: %d trees", len(public_trees_gdf))

    public_trees_gdf = public_trees_gdf.reset_index(drop=True)
    public_trees_gdf["public_tree_id"] = public_trees_gdf.index

    combos = list(product(radius_vals, vres_vals, min_pts_vals))

    existing_combos = set()
    if os.path.exists(csv_path):
        df_existing = pd.read_csv(csv_path)
        existing_combos = set(zip(df_existing["Radius"], df_existing["Vertical Res"], df_existing["Min Points"]))

    def run_segmentation_task(args):
        (r, v, m), idx = args
        out_file = os.path.join(segmentation_dir, f"segmentation_{idx:04d}.xyz")

        if not overwrite_existing_combos and (r, v, m) in existing_combos:
            logger.info("Skipping existing combination: Radius=%.2f, VRes=%.2f, MinPts=%d", r, v, m)
            return None

        logger.info("Running segmentation for iteration %d: Radius=%.2f, VRes=%.2f, MinPts=%d", idx, r, v, m)

        cmd = [exe, os.path.join(data_dir, input_xyz), out_file, str(r), str(v), str(m)]

        try:
            start = time.time()
            subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            runtime = time.time() - start
            logger.info("✓ Segmentation finished for iteration %d (%.2fs)", idx, runtime)
        except subprocess.CalledProcessError as e:
            logger.error("Segmentation failed for iteration %d: %s", idx, str(e))
            return None

        # Analyze segmentation result
        try:
            seg_df = pd.read_csv(out_file, sep=r"\s+", header=None, names=["tree_id", "x", "y", "z"])
            N_points = len(seg_df)

            seg_gdf = gpd.GeoDataFrame(seg_df, geometry=gpd.points_from_xy(seg_df.x, seg_df.y), crs="EPSG:28992")

            hulls_gdf = compute_tree_convex_hulls(seg_gdf, idx)
            N_hulls = len(hulls_gdf)


            if hulls_gdf.empty:
                logger.warning("No hulls generated for iteration %d", idx)
                return None

            # For each public tree, count how many hulls contain it
            counts = []
            for pt in public_trees_gdf.geometry:
                num_enclosed = hulls_gdf.geometry.contains(pt).sum()
                counts.append(num_enclosed)

            counts_series = pd.Series(counts)

            total = len(public_trees_gdf)
            zero_hulls = (counts_series == 0).sum() / total * 100
            one_hull = (counts_series == 1).sum() / total * 100
            two_hull = (counts_series == 2).sum() / total * 100
            three_hull = (counts_series == 3).sum() / total * 100
            fourplus_hull = (counts_series >= 4).sum() / total * 100

            logger.info("Iteration %d results: N_trees= %d,0hulls=%.2f%%, 1hull=%.2f%%, 2hull=%.2f%%, 3hull=%.2f%%, 4+hull=%.2f%%",
                        idx, total, zero_hulls, one_hull, two_hull, three_hull, fourplus_hull)

            result_row = {
                "iteration_id": idx,
                "Radius": r,
                "Vertical Res": v,
                "Min Points": m,
                "Runtime (s)": runtime,
                "N_points": N_points,
                "N_hulls": N_hulls,
                "N_trees_public": total,
                "0_hulls (%)": zero_hulls,
                "1_hull (%)": one_hull,
                "2_hull (%)": two_hull,
                "3_hull (%)": three_hull,
                "4+_hull (%)": fourplus_hull
            }

            # Delete the .xyz if requested
            if delete_segmentation_after_processing:
                try:
                    os.remove(out_file)
                    logger.info("Deleted segmentation file: %s", out_file)
                except Exception as e:
                    logger.error("Failed to delete file %s: %s", out_file, str(e))

            return result_row

        except Exception as e:
            logger.exception("Failed to process segmentation for iteration %d: %s", idx, str(e))
            return None

    # Prepare tasks
    tasks = [((r, v, m), idx) for idx, (r, v, m) in enumerate(combos)]

    # Prepare CSV if it does not exist
    if not os.path.exists(csv_path):
        header = ["iteration_id", "Runtime (s)", "Radius", "Vertical Res", "Min Points", "N_points", "N_hulls", "N_trees_public", "0_hulls (%)", "1_hull (%)", "2_hull (%)", "3_hull (%)", "4+_hull (%)"]
        pd.DataFrame(columns=header).to_csv(csv_path, index=False)

    results = []
    with ThreadPoolExecutor(max_workers=cores) as pool:
        futures = [pool.submit(run_segmentation_task, task) for task in tasks]
        for future in tqdm(as_completed(futures), total=len(tasks), desc="Public Matching Sweep", disable=not sys.stdout.isatty()):
            result = future.result()
            if result:
                result_key = (result["Radius"], result["Vertical Res"], result["Min Points"])

                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    df = df[~((df["Radius"] == result_key[0]) &
                            (df["Vertical Res"] == result_key[1]) &
                            (df["Min Points"] == result_key[2]))]
                else:
                    df = pd.DataFrame()

                df = pd.concat([df, pd.DataFrame([result])], ignore_index=True)
                df.to_csv(csv_path, index=False)
                existing_combos.add(result_key)



    logger.info("[segmentation_public_match] Sweep finished!")

if __name__ == "__main__":
    data_dir = "whm_100"
    segmentation_exe = "./segmentation_code/build/segmentation"
    municipality_geojson = "Bomen_in_beheer_door_gemeente_Delft.geojson"
    forest_las_name = "forest.laz"
    csv_name = "segmentation_stats_public.csv"

    run_segmentation_public_matching(
        data_dir=data_dir,
        exe=segmentation_exe,
        input_xyz="forest.xyz",
        output_dir=os.path.join(data_dir, "segmentation_results"),
        radius_vals=[1, 2, 3, 4, 5],
        vres_vals=[.5],#, 1, 2, 2.5, 3],
        min_pts_vals=[1],#],
        municipality_geojson=municipality_geojson,
        forest_las_name=forest_las_name,
        csv_name=csv_name,
        cores=4,
        overwrite_existing_combos=True,
        delete_segmentation_after_processing=True
    )
