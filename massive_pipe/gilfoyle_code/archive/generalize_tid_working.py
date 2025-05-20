import os
import sys
import pandas as pd
import geopandas as gpd
import numpy as np
import laspy
import logging
from shapely.geometry import Point
from multiprocessing import Pool
from tqdm import tqdm

# === CONFIGURATION ===
CASE_DIR = "delft"
TILE_ROOT = os.path.join(CASE_DIR, "tiles")
TILE_GRID_PATH = os.path.join(CASE_DIR, "tile_grid_core.geojson")
OUTPUT_HULLS = os.path.join(CASE_DIR, "filtered_renumbered_hulls.geojson")
OUTPUT_REJECTED = os.path.join(CASE_DIR, "rejected_hulls.geojson")
LOG_PATH = os.path.join(CASE_DIR, "gtid.log")

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)

# === GLOBAL STORAGE ===
gtid_map = {}  # (tile_id, tid) -> gtid
gtid_counter = 0
accepted_features = []
rejected_features = []

# === PHASE 1: BUILD GTID MAP FROM HULLS ===
def build_gtid_map():
    global gtid_counter

    if not os.path.exists(TILE_GRID_PATH):
        logging.error(f"Tile grid not found: {TILE_GRID_PATH}")
        return

    tile_grid = gpd.read_file(TILE_GRID_PATH).set_index("tile_id").to_crs("EPSG:28992")

    for tile_id in tqdm(os.listdir(TILE_ROOT), desc="Building gtid map"):
        tile_path = os.path.join(TILE_ROOT, tile_id)
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
        accepted.to_file(OUTPUT_HULLS, driver="GeoJSON")
        logging.info(f"Saved {len(accepted)} accepted trees to {OUTPUT_HULLS}")

    if rejected_features:
        rejected = gpd.GeoDataFrame(pd.concat(rejected_features, ignore_index=True), crs="EPSG:28992")
        rejected.to_file(OUTPUT_REJECTED, driver="GeoJSON")
        logging.info(f"Saved {len(rejected)} rejected trees to {OUTPUT_REJECTED}")

# === PHASE 2: PROCESS POINT CLOUDS IN PARALLEL ===
def process_tile(tile_id):
    tile_path = os.path.join(TILE_ROOT, tile_id)
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

# === MAIN ===
if __name__ == "__main__":
    # Parse number of workers from command-line argument
    if len(sys.argv) < 2:
        logging.error("Usage: python generalize_tree_ids.py <num_workers>")
        sys.exit(1)

    try:
        num_workers = int(sys.argv[1])
        if num_workers < 1:
            raise ValueError
    except ValueError:
        logging.error("Invalid number of workers provided. Must be a positive integer.")
        sys.exit(1)

    build_gtid_map()
    logging.info(f"Assigned {gtid_counter} global tree IDs")

    tiles = list(gtid_map.keys())
    unique_tiles = sorted(set(tile for tile, _ in tiles))

    with Pool(processes=num_workers) as pool:
        list(tqdm(pool.imap_unordered(process_tile, unique_tiles), total=len(unique_tiles), desc="Writing forest.laz"))

    logging.info("[DONE] All tiles processed.")
