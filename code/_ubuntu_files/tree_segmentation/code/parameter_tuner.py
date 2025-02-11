import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from tqdm import tqdm

# Constants
RADIUS_VALUES = [250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]  # Example radii
VERTICAL_RES_VALUES = [10, 50, 100, 200]  # Example vertical resolutions
MIN_POINTS_VALUES = [3]  # Minimum points per cluster 5 and 10 yield 0
OUTPUT_DIR = "whm_01/results"
INPUT_FILE = "whm_01/whm_01_filtered.xyz"
LOG_FILE = "tuning.log"
NUM_CORES = 16

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def log_message(message):
    """Log a message to the log file."""
    with open(LOG_FILE, "a") as log:
        log.write(f"{message}\n")

def run_segment_trees(params):
    """Run the segment_trees executable with given parameters."""
    radius, vertical_res, min_points = params
    output_file = f"{OUTPUT_DIR}/whm_01_r_{radius}_vres_{vertical_res}_minp_{min_points}.xyz"

    if os.path.isfile(output_file):
        log_message(f"Skipping: {output_file} already exists.")
        return

    try:
        subprocess.run(
            ["./segment_trees", INPUT_FILE, output_file, str(radius), str(vertical_res), str(min_points)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        file_size = os.path.getsize(output_file) if os.path.isfile(output_file) else "N/A"
        log_message(f"Completed: R={radius}, VER_RES={vertical_res}, MIN_P={min_points}")
        log_message(f"Size: {file_size} bytes")
    except subprocess.CalledProcessError:
        log_message(f"Error: segment_trees failed for R={radius}, VER_RES={vertical_res}, MIN_P={min_points}")

def main():
    """Main function to execute parameter tuning and diagnostics."""
    combinations = list(product(RADIUS_VALUES, VERTICAL_RES_VALUES, MIN_POINTS_VALUES))
    print(f"Starting parallel execution with {NUM_CORES} cores...")

    with ThreadPoolExecutor(max_workers=NUM_CORES) as executor:
        list(tqdm(executor.map(run_segment_trees, combinations), total=len(combinations), desc="Processing"))

    print(f"All tasks completed. Check the log file: {LOG_FILE}")

    diagnostics_script = os.path.join(os.path.dirname(__file__), "diagnostics.py")
    try:
        subprocess.run(["python", diagnostics_script], check=True)
        print("Diagnostics script completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error running diagnostics script: {e}")

if __name__ == "__main__":
    main()
