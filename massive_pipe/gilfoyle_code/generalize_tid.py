import os
import pandas as pd
import geopandas as gpd
import numpy as np
import laspy
import logging
from shapely.geometry import Point
from multiprocessing import Pool
from tqdm import tqdm

def build_gtid_map(data_dir):
    tile_root = os.path.join(data_dir, "tiles")
    tile_grid_path = os.path.join(data_dir, "tile_grid_core.geojson")
    output_hulls = os.path.join(data_dir, "filtered_renumbered_hulls.geojson")
    output_rejected = os.path.join(data_dir, "rejected_hulls.geojson")

    gtid_map = {}
    gtid_counter = 0
    accepted_features = []
    rejected_features = []

    if not os.path.exists(tile_grid_path):
        logging.error(f"Tile grid not found: {tile_grid_path}")
        return {}, 0

    tile_grid = gpd.read_file(tile_grid_path).set_index("tile_id").to_crs("EPSG:28992")

    for tile_id in tqdm(os.listdir(tile_root), desc="Building gtid map"):
        tile_path = os.path.join(tile_root, tile_id)
        hull_path = os.path.join(tile_path, "segmentation_hulls.geojson")

        if not os.path.exists(hull_path):
            logging.warning(f"SKIP {tile_id}: Missing segmentation_hulls.geojson")
            continue

        if tile_id not in tile_grid.index:
            logging.warning(f"SKIP {tile_id}: Not found in tile_grid_core.geojson")
            continue

        try:
            core_poly = tile_grid.loc[tile_id].geometry
            gdf = gpd.read_file(hull_path).to_crs("EPSG:28992")

            if "tid" not in gdf.columns:
                logging.error(f"SKIP {tile_id}: 'tid' column not found")
                continue

            gdf["centroid"] = gdf.geometry.centroid
            inside = gdf[gdf["centroid"].within(core_poly)].copy()
            outside = gdf[~gdf["centroid"].within(core_poly)].copy()

            inside["gtid"] = range(gtid_counter, gtid_counter + len(inside))
            inside["tile"] = tile_id
            accepted_features.append(inside.drop(columns=["centroid"]))

            for _, row in inside.iterrows():
                gtid_map[(tile_id, row["tid"])] = row["gtid"]

            gtid_counter += len(inside)

            if not outside.empty:
                outside["tile"] = tile_id
                rejected_features.append(outside.drop(columns=["centroid"]))

        except Exception as e:
            logging.error(f"Failed processing {tile_id}: {e}")

    if accepted_features:
        accepted = gpd.GeoDataFrame(pd.concat(accepted_features, ignore_index=True), crs="EPSG:28992")
        accepted.to_file(output_hulls, driver="GeoJSON")
        logging.info(f"Saved {len(accepted)} accepted trees to {output_hulls}")

    if rejected_features:
        rejected = gpd.GeoDataFrame(pd.concat(rejected_features, ignore_index=True), crs="EPSG:28992")
        rejected.to_file(output_rejected, driver="GeoJSON")
        logging.info(f"Saved {len(rejected)} rejected trees to {output_rejected}")

    return gtid_map, gtid_counter

def process_tile(tile_id, data_dir, gtid_map):
    tile_path = os.path.join(data_dir, "tiles", tile_id)
    seg_path = os.path.join(tile_path, "segmentation.XYZ")
    laz_path = os.path.join(tile_path, "vegetation.LAZ")
    out_path = os.path.join(tile_path, "forest.laz")

    if not os.path.exists(seg_path):
        logging.warning(f"SKIP {tile_id}: Missing segmentation.XYZ")
        return
    if not os.path.exists(laz_path):
        logging.warning(f"SKIP {tile_id}: Missing vegetation.LAZ")
        return

    try:
        df = pd.read_csv(seg_path, delim_whitespace=True, header=None, names=["tid", "x", "y", "z"])
        df["tid"] = df["tid"].astype(int)
        df["gtid"] = df["tid"].apply(lambda tid: gtid_map.get((tile_id, tid), -1))
        valid_points = df[df["gtid"] != -1].copy()
        coord_to_gtid = {tuple(row[1:4]): row[4] for row in valid_points.itertuples(index=False)}

        las = laspy.read(laz_path)
        coords = np.vstack((las.x, las.y, las.z)).T
        matched_gtid = np.array([coord_to_gtid.get(tuple(c), -1) for c in coords], dtype=np.int32)
        mask = matched_gtid != -1

        if "gtid" not in las.point_format.extra_dimension_names:
            las.add_extra_dim(laspy.ExtraBytesParams(name="gtid", type=np.int32))
        las["gtid"] = matched_gtid
        las.points = las.points[mask]
        las.write(out_path)
        logging.info(f"Written forest.laz for {tile_id} with {mask.sum()} points")

    except Exception as e:
        logging.error(f"Error processing {tile_id}: {e}")

def process_all_tiles(data_dir, gtid_map, num_cores):
    tiles = sorted(set(tile for tile, _ in gtid_map.keys()))
    args = [(tile, data_dir, gtid_map) for tile in tiles]
    with Pool(processes=num_cores) as pool:
        list(tqdm(pool.starmap(process_tile, args), total=len(args), desc="Writing forest.laz"))

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python generalize_tid.py <data_dir> <num_cores>")
        sys.exit(1)

    data_dir = sys.argv[1]
    num_cores = int(sys.argv[2])

    log_dir = os.path.join(data_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "gtid.log")

    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )

    gtid_map, gtid_count = build_gtid_map(data_dir)
    logging.info(f"Assigned {gtid_count} global tree IDs")
    process_all_tiles(data_dir, gtid_map, num_cores)
    logging.info("[DONE] All tiles processed.")