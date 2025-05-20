import logging
import os
import sys

from shared_logging import setup_logging
from preprocess_pointcloud import process_point_cloud
from hull_segment import run_hull_analysis


# Handle data_dir and check for right starting structure
if len(sys.argv) < 3:
    raise ValueError("Usage: python main.py <data_dir> <cores>")

data_dir = sys.argv[1]

try:
    available_cores = int(sys.argv[2])
except ValueError:
    raise ValueError("Cores should be an integer.")

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

radius_vals= [2.5] #[1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6.5]
vres_vals=[4] #[1, 1.25, 1,5, 1.75, 2, 2.25, 2.5, 2.75, 3, 3.25, 3.5, 3.75, 4]
min_pts_vals=[5] #[1, 2, 3, 4, 5]

logger.info("Running Segmentation for parameters: \nradius_vals=%s \nvres_vals=%s \nmin_pts_vals=%s",
            radius_vals, vres_vals, min_pts_vals)
logger.info('-' * 60)
logger.info("Running parallel using %s cores", available_cores)
cores = available_cores #depends on machine
# Noahs windows laptop has 6 max so 5 reserves one for other tasks
# Gilfoyle has many, but check availability with htop

# ----------------------------------------------------------------
# if ran from scratch:
# overwrite existing combos doesnt work so                  FALSE
# delete segm after processing creates too many files so    TRUE
# use existing geojsons doesnt work so                      FALSE
# ----------------------------------------------------------------

run_hull_analysis(
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
    cores=available_cores,
    overwrite_existing_combos=False,
    delete_segmentation_after_processing=False,
    save_geojsons=True,
    use_existing_geojsons=False,
    add_attr_to_geojson=True
)
logger.info("Segmentation results (geojsons) saved to: %s", output_dir)
logger.info("✓ Preprocessing completed (details in hull_analysis.log)")
#===========================================================================

