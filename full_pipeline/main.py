import logging
import os
import sys

from shared_logging import setup_logging
from preprocess_pointcloud import process_point_cloud
from segmentation import run_segmentation, run_segmentation_sweep
from merge_tree_ids import merge_tree_ids_into_las


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
log_path = os.path.join(data_dir, "main.log")
setup_logging(log_path)
logger = logging.getLogger(__name__)
logger.info("[main.py] Pipeline started")

#===========================================================================
# Preprocessing
#===========================================================================
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

process_point_cloud(
    data_dir=data_dir,
    input_filename=original_las,
    output_filename_xyz=vegetation_xyz,
    output_filename_laz=vegetation_las,
    thinning_factor=filters['thinning_factor'],
    nb_neighbors=filters['nb_neighbors'],
    std_ratio=filters['std_ratio']
)
logger.info("✓ Preprocessing completed")

#===========================================================================
# Segmentation
#===========================================================================
segmentation_dir = os.path.join(data_dir, "segmentation_results")

segmentation_exe = os.path.join(".", "segmentation_code", "build", "segmentation")

run_sweep = False  # Set to False to run single segmentation instead

segmentation_sweep = {
    'radius': [10, 15],
    'vres': [1, 2, 3, 5],
    'min_pts': [1, 3, 5]
}

single_segmentation = {
    'radius': 10,
    'vres': 2,
    'min_pts': 1
}

if run_sweep:
    logger.info("=== Segmentation SWEEP started ===")
    logger.info("Running sweep using:")
    logger.info("  Radii:         %s", segmentation_sweep['radius'])
    logger.info("  VRes options:  %s", segmentation_sweep['vres'])
    logger.info("  MinPts values: %s", segmentation_sweep['min_pts'])

    logger.info("Segmentation sweep config: %s", segmentation_sweep)
    run_segmentation_sweep(        
        data_dir=data_dir,
        exe=segmentation_exe,
        input_xyz=vegetation_xyz,
        output_dir=segmentation_dir,
        radius_vals=segmentation_sweep['radius'],
        vres_vals=segmentation_sweep['vres'],
        min_pts_vals=segmentation_sweep['min_pts'],
        cores=4,
        overwrite=False,
        save_per_iteration=True
    )
    logger.info("✓ Segmentation SWEEP completed")
else:
    logger.info("=== Single segmentation started ===")
    run_segmentation(
        data_dir=data_dir,
        exe=segmentation_exe,
        input_xyz=vegetation_xyz,
        output_dir=segmentation_dir,
        radius=single_segmentation['radius'],
        vres=single_segmentation['vres'],
        min_pts=single_segmentation['min_pts'],
        overwrite=False
    )
    logger.info("✓ Single segmentation completed")

#===========================================================================
# Merge tree IDs into LAS
#===========================================================================
logger.info("=== Merging tree IDs into LAS ===")

merged_las = "forest_tid.laz"
segmentation_to_use = "segmentation_0000.xyz"  # ← manually picked best result
logger.info("Using segmentation file: %s", segmentation_to_use)

merge_tree_ids_into_las(
    data_dir=data_dir,
    forest_las_name=vegetation_las,
    segmentation_xyz=segmentation_to_use,
    output_las_name=merged_las
)
logger.info("✓ Merging completed")

logger.info("[main.py] Pipeline finished")
