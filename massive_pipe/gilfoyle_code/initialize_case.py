import os
import sys
import subprocess
import logging

from shared_logging import setup_logging


def check_case_structure(case_dir):
    tiles_path = os.path.join(case_dir, "tiles")
    if not os.path.exists(tiles_path):
        logging.error(f"[ERROR] Missing 'tiles' directory in {case_dir}")
        return False

    tile_folders = [f for f in os.listdir(tiles_path)
                    if os.path.isdir(os.path.join(tiles_path, f))]
    if not tile_folders:
        logging.error(f"[ERROR] No subfolders found in {tiles_path}")
        return False

    for folder in tile_folders:
        raw_path = os.path.join(tiles_path, folder, "raw.LAZ")
        if not os.path.exists(raw_path):
            logging.error(f"[ERROR] Missing raw.LAZ in tile {folder}")
            return False

    bomen_path = os.path.join(case_dir, "Bomen_in_beheer_door_gemeente_Delft.geojson")
    if not os.path.exists(bomen_path):
        logging.error(f"[ERROR] Missing Bomen_in_beheer_door_gemeente_Delft.geojson in {case_dir}")
        return False

    return True


def run_preprocessing(case_dir, cores):
    logging.info("[INFO] Running preprocess_municipality_trees.py")
    result = subprocess.run(["python3", "preprocess_municipality_trees.py", case_dir])
    if result.returncode != 0:
        logging.error("[ERROR] preprocess_municipality_trees.py failed")
        return False

    logging.info("[INFO] Running clip_tiles_to_muni.sh")
    result = subprocess.run(["./clip_tiles_to_muni.sh", case_dir, str(cores)])
    if result.returncode != 0:
        logging.error("[ERROR] clip_tiles_to_muni.sh failed")
        return False

    logging.info("[INFO] Running create_core_tile_grid.py")
    result = subprocess.run(["python3", "create_core_tile_grid.py", case_dir, str(cores)])
    if result.returncode != 0:
        logging.error("[ERROR] create_core_tile_grid.py failed")
        return False

    logging.info("[DONE] Case initialized successfully")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python initialize_case.py <case_dir> <cores>")
        sys.exit(1)

    case_dir = sys.argv[1]
    cores = int(sys.argv[2])

    log_dir = os.path.join(case_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(os.path.join(log_dir, "init.log"))

    logging.info(f"[START] Initializing case {case_dir} with {cores} cores")

    if check_case_structure(case_dir):
        run_preprocessing(case_dir, cores)
    else:
        logging.error("[ABORT] Case structure validation failed")
