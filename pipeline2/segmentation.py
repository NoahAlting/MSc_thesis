import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)


def run_segment_trees(segmenter_cpp_exe: str, params, input_file, output_dir):
    radius, vertical_res, min_points = params
    output_file = f"{output_dir}/segmentation_r_{radius}_vres_{vertical_res}_minp_{min_points}.xyz"

    if os.path.isfile(output_file):
        logger.info(f"Skipping: {output_file} already exists.")
        return

    cmd = [segmenter_cpp_exe, input_file, output_file, str(radius), str(vertical_res), str(min_points)]
    logger.info(f"Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # decode bytes to strings
            check=True
        )
        file_size = os.path.getsize(output_file) if os.path.isfile(output_file) else "N/A"
        logger.info(f"Completed: R={radius}, ver_res={vertical_res}, min_p={min_points}")
        logger.info(f"Size: {file_size} bytes")
        if result.stdout.strip():
            logger.info(f"stdout:\n{result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        logger.error(f"segment_trees failed for R={radius}, ver_res={vertical_res}, min_p={min_points}")
        logger.error(f"Return code: {e.returncode}")
        if e.stdout:
            logger.error(f"stdout:\n{e.stdout.strip()}")
        if e.stderr:
            logger.error(f"stderr:\n{e.stderr.strip()}")


def run_parallel_segmentation(data_dir, segmenter_cpp_exe, input_file_name, output_dir, num_cores, radius_values, vertical_res_values, min_points_values):
    os.makedirs(output_dir, exist_ok=True)
    combinations = list(product(radius_values, vertical_res_values, min_points_values))
    input_file = os.path.join(data_dir, input_file_name)

    logger.info(f"Starting parallel tuning with {len(combinations)} parameter sets using {num_cores} cores...")

    with ThreadPoolExecutor(max_workers=num_cores) as executor:
        list(tqdm(executor.map(lambda p: run_segment_trees(segmenter_cpp_exe, p, input_file, output_dir),
                               combinations),
                  total=len(combinations),
                  desc="Processing",
                  file=open(os.devnull, "w")))

    logger.info(f"Tuning completed. Results saved in {output_dir}.")

    diagnostics_script = os.path.join(os.path.dirname(__file__), "2_tuning_diagnostics.py")
    try:
        subprocess.run(["python", diagnostics_script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info("Diagnostics script completed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running diagnostics script: {e}")
        logger.error(f"segment_trees failed with return code {e.returncode}")



def run_single_segmentation(data_dir, segmenter_cpp_exe, input_file_name, output_dir, radius, vertical_res, min_points):
    os.makedirs(output_dir, exist_ok=True)
    input_file = os.path.join(data_dir, input_file_name)
    logger.info("Running single segmentation:")
    logger.info(f"  R={radius}, ver_res={vertical_res}, min_p={min_points}")
    run_segment_trees(segmenter_cpp_exe, (radius, vertical_res, min_points), input_file, output_dir)
    logger.info("Single segmentation completed.")


if __name__ == "__main__":
    from shared_logging import setup_logging

    data_dir = 'delft_100'
    log_file = os.path.join(data_dir, "segmentation.log")
    setup_logging(log_file)
    logger.info("Segmentation script started separately.")


    # Configuration variables (adjust as needed)
    radius_values = [4500] #, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000], 
    vertical_res_values = [150] #, 50, 100, 200]
    min_points_values = [3] # , 5, 10] 

    segmentation_results_folder = os.path.join(data_dir, "segmentation_results")
    filtered_vegetation_xyz_name = "forest.xyz"
    num_cores = 4

    if len(radius_values) == 1 and len(vertical_res_values) == 1 and len(min_points_values) == 1:
        run_single_segmentation(
            data_dir=data_dir,
            segmenter_cpp_exe="./segment_trees",
            input_file_name=filtered_vegetation_xyz_name,
            output_dir=segmentation_results_folder,
            radius=radius_values[0],
            vertical_res=vertical_res_values[0],
            min_points=min_points_values[0]
        )
    else:
        run_parallel_segmentation(
            data_dir=data_dir,
            segmenter_cpp_exe="./segment_trees",
            input_file_name=filtered_vegetation_xyz_name,
            output_dir=segmentation_results_folder,
            num_cores=num_cores,
            radius_values=radius_values,
            vertical_res_values=vertical_res_values,
            min_points_values=min_points_values
        )


    logger.info("Preprocessing script finished.")
