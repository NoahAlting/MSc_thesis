import os
import subprocess
import logging
import pandas as pd
import time
from itertools import product
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from shared_logging import setup_logging

logger = logging.getLogger(__name__)

# ------------------------------- helpers -----------------------------------

def next_index(csv_path):
    """Return the next index based on existing rows in the CSV (used for naming output files)."""
    if os.path.exists(csv_path):
        return len(pd.read_csv(csv_path))
    return 0

def count_xyz_file_stats(path):
    """Count total number of points and number of unique trees in an output .xyz file."""
    df = pd.read_csv(path, sep=r"\s+", header=None, names=["tree_id", "x", "y", "z"])
    return len(df), df["tree_id"].nunique()

def create_or_update_csv(csv_path, new_rows):
    """Append new segmentation results to the summary CSV."""
    cols = ["File Name", "Radius", "Vertical Res", "Min Points", "Num Points", "Num Trees", "Runtime (s)"]
    df = pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame(columns=cols)
    for row in new_rows:
        df.loc[len(df)] = row
    df.to_csv(csv_path, index=False)
    logger.info("CSV updated → %s  (rows=%d)", csv_path, len(df))

def is_duplicate_combo(csv_path, radius, vres, min_pts):
    """Check if the given parameter combination has already been processed and logged."""
    if not os.path.exists(csv_path):
        return False
    df = pd.read_csv(csv_path)
    return ((df["Radius"] == radius) &
            (df["Vertical Res"] == vres) &
            (df["Min Points"] == min_pts)).any()

# ------------------------------ runner -------------------------------------

def run_cpp_segmenter(exe, input_path, output_path, radius, vres, min_pts):
    """Run the C++ segmentation executable with given parameters."""
    cmd = [exe, input_path, output_path, str(radius), str(vres), str(min_pts)]
    logger.info("Running: %s", " ".join(cmd))
    try:
        start = time.time()
        subprocess.run(cmd, check=True, text=True,
                       stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
        runtime = time.time() - start
        return True, runtime
    except subprocess.CalledProcessError as e:
        logger.error("C++ segmentation failed with return code %d", e.returncode)
        return False, 0.0

# --------------------------- public API ------------------------------------

def run_segmentation(data_dir, exe, input_xyz, output_dir,
                     radius, vres, min_pts, overwrite=False):
    """
    Run a single segmentation using one parameter set.
    Results are saved to a file and logged in a CSV.
    """
    log_path = os.path.join(data_dir, "segmentation.log")
    setup_logging(log_path)
    logger.info("[run_segmentation] Segmenter function called")

    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, "segmentation_stats.csv")

    if not overwrite and is_duplicate_combo(csv_path, radius, vres, min_pts):
        logger.info("Skipping duplicate combination: r=%d, vres=%d, min=%d", radius, vres, min_pts)
        return

    idx = next_index(csv_path)
    out_file = os.path.join(output_dir, f"segmentation_{idx:04d}.xyz")

    success, runtime = run_cpp_segmenter(exe, os.path.join(data_dir, input_xyz), out_file, radius, vres, min_pts)
    if success:
        num_pts, num_trees = count_xyz_file_stats(out_file)
        create_or_update_csv(csv_path, [{
            "File Name": os.path.basename(out_file),
            "Radius": radius,
            "Vertical Res": vres,
            "Min Points": min_pts,
            "Num Points": num_pts,
            "Num Trees": num_trees,
            "Runtime (s)": round(runtime, 2)
        }])

def run_segmentation_sweep(data_dir, exe, input_xyz, output_dir,
                           radius_vals, vres_vals, min_pts_vals, cores,
                           overwrite=False, save_per_iteration=False):
    """
    Run segmentation for a sweep of parameter combinations in parallel.
    Skips combinations already in the CSV unless overwrite=True.
    If save_per_iteration=True, updates the CSV after every task.
    """
    log_path = os.path.join(data_dir, "segmentation.log")
    setup_logging(log_path)
    logger.info("[run_segmentation_sweep] Segmenter sweep function called")

    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, "segmentation_stats.csv")
    combos = list(product(radius_vals, vres_vals, min_pts_vals))
    start_idx = next_index(csv_path)
    tasks = []

    for i, (r, v, m) in enumerate(combos):
        if not overwrite and is_duplicate_combo(csv_path, r, v, m):
            logger.info("Skipping duplicate combination: r=%d, vres=%d, min=%d", r, v, m)
            continue
        out_file = os.path.join(output_dir, f"segmentation_{start_idx + len(tasks):04d}.xyz")
        tasks.append(((r, v, m), out_file))

    def process_task(args):
        (r, v, m), out_file = args
        success, runtime = run_cpp_segmenter(
            exe, os.path.join(data_dir, input_xyz), out_file, r, v, m
        )
        if success:
            num_pts, num_trees = count_xyz_file_stats(out_file)
            return {
                "File Name": os.path.basename(out_file),
                "Radius": r,
                "Vertical Res": v,
                "Min Points": m,
                "Num Points": num_pts,
                "Num Trees": num_trees,
                "Runtime (s)": round(runtime, 2)
            }
        return None

    if save_per_iteration:
        with ThreadPoolExecutor(max_workers=cores) as pool:
            for row in tqdm(pool.map(process_task, tasks), total=len(tasks), desc="Segmenting"):
                if row:
                    create_or_update_csv(csv_path, [row])
    else:
        new_rows = []
        with ThreadPoolExecutor(max_workers=cores) as pool:
            for row in tqdm(pool.map(process_task, tasks), total=len(tasks), desc="Segmenting"):
                if row:
                    new_rows.append(row)
        if new_rows:
            create_or_update_csv(csv_path, new_rows)


# --------------------------- standalone CLI --------------------------------

if __name__ == "__main__":
    # Example single run
    run_segmentation(
        data_dir="whm_100",
        exe="./segmentation_code/build/segmentation",
        input_xyz="forest.xyz",
        output_dir="whm_100/segmentation_results",
        radius=10,
        vres=2,
        min_pts=1,
        overwrite=False
    )

    # Example sweep run
    run_segmentation_sweep(
        data_dir="whm_100",
        exe="./segmentation_code/build/segmentation",
        input_xyz="forest.xyz",
        output_dir="whm_100/segmentation_results",
        radius_vals=[10, 15],
        vres_vals=[1, 2],
        min_pts_vals=[1, 3],
        cores=4,
        overwrite=False,
        save_per_iteration=True
    )
