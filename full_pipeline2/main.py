import logging
import os
import sys

from shared_logging import setup_logging
from preprocess_pointcloud import process_point_cloud
from segmentation_analysis import run_segmentation_and_analyze


# Handle data_dir and check for right starting structure
if len(sys.argv) < 2:
    raise ValueError("Usage: python main.py <data_dir>")

data_dir = sys.argv[1]
original_las_path = os.path.join(data_dir, "original.laz")

if not os.path.isdir(data_dir):
    raise FileNotFoundError(f"Directory '{data_dir}' does not exist.")

if not os.path.isfile(original_las_path):
    raise FileNotFoundError(f"Required file '{original_las_path}' not found in '{data_dir}'.")


# Set up high-level logging for main pipeline
log_dir = os.path.join(data_dir, "logs")
os.makedirs(log_dir, exist_ok=True)

log_path = os.path.join(log_dir, "0_main.log")
setup_logging(log_path)

logger = logging.getLogger("pipeline")
logger.info("=" * 60 + "Pipeline")
logger.info("Parameters → data_dir: %s", data_dir)
logger.info("[main.py] Pipeline started")


#===========================================================================
# Preprocessing
#===========================================================================
logger.info("=" * 60)
logger.info("=== Preprocessing started ===")


original_las = "original.laz"
vegetation_xyz = "forest.xyz"
vegetation_las = "forest.laz"

# filtering parameters
filters = {
    'thinning_factor': 1.0,  # Set to 1.0 to keep all points
    'nb_neighbors': 20,
    'std_ratio': 2.0
}
logger.info("Filtering parameters: %s", filters)
logger.info("Running preprocessing for '%s' with params: %s", data_dir, filters)

process_point_cloud(
    data_dir=data_dir,
    input_filename=original_las,
    output_filename_xyz=vegetation_xyz,
    output_filename_laz=vegetation_las,
    thinning_factor=filters['thinning_factor'],
    nb_neighbors=filters['nb_neighbors'],
    std_ratio=filters['std_ratio']
)
logger.info("✓ Preprocessing completed (details in preprocess.log)")

#===========================================================================
# Segmentation
#===========================================================================
logger.info("=" * 60)
logger.info("=== Segmentation started ===")

segmentation_exe = "./segmentation_code/build/segmentation"
municipality_geojson = "Bomen_in_beheer_door_gemeente_Delft.geojson"
output_dir = os.path.join(data_dir, "segmentation_results")
csv_name = "segmentation_stats.csv"

radius_vals = [2.5, 5, 7.5]
vres_vals = [1, 2, 3]
min_pts_vals = [1]

logger.info("Running Segmentation for parameters: radius_vals=%s, vres_vals=%s, min_pts_vals=%s",
            radius_vals, vres_vals, min_pts_vals)

run_segmentation_and_analyze(
    data_dir=data_dir,
    exe=segmentation_exe,
    input_xyz=vegetation_xyz,
    output_dir=output_dir,
    radius_vals=radius_vals,
    vres_vals=vres_vals,
    min_pts_vals=min_pts_vals,
    municipality_geojson=municipality_geojson,
    forest_las_name=vegetation_las,
    csv_name=csv_name,
    cores=4,
    overwrite=False,
    delete_segmentation_after_processing=True
)
logger.info("Segmentation results saved to: %s", os.path.join(output_dir, csv_name))
logger.info("✓ Segmentation completed (details in segmentation.log)")
#===========================================================================

