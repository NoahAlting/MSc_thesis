# main.py
import os
import sys
import time
import logging
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import set_start_method

from luna import send_email_notification
from filter_vegetation import process_tile as vegetation_filter
from segmentation_tiles import segment_tile_fixed
from shared_logging import setup_logging

# Read number of workers from command line
if len(sys.argv) < 2:
    print("Usage: python main.py <num_workers>")
    sys.exit(1)

num_workers = int(sys.argv[1])

# --- Setup logging ---
setup_logging("logs/main.log")  # High-level logs
logger = logging.getLogger("main")

# --- Paths ---
case_dir = "delft"
tiles_dir = os.path.join(case_dir, "tiles")

# --- Parameters ---
segmentation_exe = "./segmentation_code/build/segmentation"
segmentation_params_dict = {
    'radius': 2.5,
    'vres': 4.0,
    'min_pts': 5
}

def process_tile(tile_name: str):
    setup_logging("logs/pipeline.log")  # Logs from all workers go here
    logger = logging.getLogger("pipeline")

    start_time = time.time()
    tile_path = os.path.join(tiles_dir, tile_name)

    clipped_las = os.path.join(tile_path, "clipped.LAZ")
    vegetation_las = os.path.join(tile_path, "vegetation.LAZ")
    vegetation_xyz = os.path.join(tile_path, "vegetation.XYZ")
    segmentation_xyz = os.path.join(tile_path, "segmentation.XYZ")
    tree_hulls_geojson = os.path.join(tile_path, "segmentation_hulls.geojson")

    logger.info(f"[{tile_name}] START tile processing")

    # Step 1: Vegetation Filtering
    if not (os.path.exists(vegetation_las) and os.path.exists(vegetation_xyz)):
        logger.info(f"[{tile_name}] START vegetation filter")
        vegetation_filter(
            input_las=clipped_las,
            output_las=vegetation_las,
            output_xyz=vegetation_xyz
        )
        logger.info(f"[{tile_name}] DONE vegetation filter")
    else:
        logger.info(f"[{tile_name}] SKIP vegetation filter (already exists)")

    # Step 2: Segmentation
    if not (os.path.exists(segmentation_xyz) and os.path.exists(tree_hulls_geojson)):
        logger.info(f"[{tile_name}] START segmentation")
        segment_tile_fixed(
            input_xyz_path=vegetation_xyz,
            output_xyz_path=segmentation_xyz,
            output_geojson_path=tree_hulls_geojson,
            exe_path=segmentation_exe,
            segmentation_params=segmentation_params_dict
        )
        logger.info(f"[{tile_name}] DONE segmentation")
    else:
        logger.info(f"[{tile_name}] SKIP segmentation (already exists)")

    total_time = time.time() - start_time
    logger.info(f"[{tile_name}] FINISHED in {total_time:.2f}s\n")

# --- Tile processing ---
if __name__ == "__main__":
    set_start_method("spawn")

    tile_folders = [f for f in os.listdir(tiles_dir)
                    if os.path.isdir(os.path.join(tiles_dir, f))]

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        executor.map(process_tile, tile_folders)


    send_email_notification()