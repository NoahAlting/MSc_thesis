
import os
import logging
from shared_logging import setup_logging

from preprocessing import process_point_cloud
from segmentation import run_parallel_segmentation, run_single_segmentation
from tuning_diagnostics import create_tuning_csv
from link_xyz_laz import process_forest_data


# Configuration variables (adjust as needed)
data_dir = 'whm_100'
original_pointcloud = 'whm_100_original.laz'

# Paths to log files
log_files = {
    "preprocessing": os.path.join(data_dir, "preprocess.log"),
    "segmentation": os.path.join(data_dir, "segmentation.log"),
    "link_xyz": os.path.join(data_dir, "linkxyz.log"),
    "segmentation_diagnostics": os.path.join(data_dir, "segmentation_diagnostics.log"),
    "alphawrap" : os.path.join(data_dir, "alphawrap.log")
}


############################################################################
### preprocessing ###
############################################################################

filtered_vegetation_laz_name = 'forest.laz'
filtered_vegetation_xyz_name = 'forest.xyz'

dbscan_params = {
    "thinning_factor": .1, # Set to a value between 0 and 1 to thin the point cloud
    "nb_neighbors": 20, # Number of neighbors for outlier removal
    "std_ratio": 2.0 # Standard deviation ratio for outlier removal
}

setup_logging(log_files["preprocessing"])
process_point_cloud(
    data_dir = data_dir,
    input_filename=original_pointcloud, 
    output_laz_name=filtered_vegetation_laz_name, 
    output_xyz_name=filtered_vegetation_xyz_name,
    **dbscan_params
    )

############################################################################
### segmentation ###
############################################################################

segmentation_results_folder = os.path.join(data_dir, "segmentation_results")
wsl_exe = "./segment_trees"  
windows_exe   = r"./segmentation_code/build/Debug/segmentation.exe"                    # C++ binary

segmenter_exe_name = windows_exe

num_cores = 1

# Configuration variables (adjust as needed)
radius_values = [1000] #, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000], 
vertical_res_values = [150] #, 50, 100, 200]
min_points_values = [3] # , 5, 10] 

setup_logging(log_files["segmentation"])
if len(radius_values) == 1 and len(vertical_res_values) == 1 and len(min_points_values) == 1:
    run_single_segmentation(
        data_dir=data_dir,
        segmenter_cpp_exe= segmenter_exe_name,
        input_file_name=filtered_vegetation_xyz_name,
        output_dir=segmentation_results_folder,
        radius=radius_values[0],
        vertical_res=vertical_res_values[0],
        min_points=min_points_values[0]
    )
else:
    run_parallel_segmentation(
        data_dir=data_dir,
        segmenter_cpp_exe= segmenter_exe_name,
        input_file_name=filtered_vegetation_xyz_name,
        output_dir=segmentation_results_folder,
        num_cores=num_cores,
        radius_values=radius_values,
        vertical_res_values=vertical_res_values,
        min_points_values=min_points_values
    )
############################################################################
### link xyz laz###
############################################################################

pcd_clusters_folder = os.path.join(data_dir, "clusters")
segmented_laz_with_tid_filename = "forest_tid.laz"

setup_logging(log_files["link_xyz"])
process_forest_data(
    data_dir = data_dir,
    input_las_file_name = filtered_vegetation_laz_name, 
    clusters_folder_path = pcd_clusters_folder, 
    output_las_file_name = segmented_laz_with_tid_filename
    )


############################################################################
### tuning diagnostics ###
############################################################################

csv_output_filename = os.path.join(data_dir, "segmentation_stats.csv")

setup_logging(log_files["segmentation_diagnostics"])
create_tuning_csv(
    data_dir = data_dir, 
    input_dir = segmentation_results_folder, 
    output_csv = csv_output_filename)

############################################################################
### alphawrap instances ###
############################################################################

# input_xyz = os.path.join(data_dir, "forest_tid_test.xyz")  # Input segmented point cloud file
# wrapper_cpp_exe = "./point_wrap/build/example_alphawrap"  # Path to the C++ Alpha Wrapping executable

# tree_meshes_folder = os.path.join(data_dir, "meshes")           # Folder to store individual mesh files
# alpha_pdal_thinning_factor = 1            # Thinning factor for PDAL conversion
# all_trees_together_meshed_obj_path = os.path.join(data_dir, "final_mesh.obj")    # Final merged mesh output

# # Run the alphawrap_instances function with the specified parameters
# setup_logging(log_files["alphawrap"])
# alphawrap_instances(data_dir, input_xyz, wrapper_cpp_exe, pcd_clusters_folder, tree_meshes_folder, alpha_pdal_thinning_factor, all_trees_together_meshed_obj_path)

# Here I might need to redo it since I already have the las tid file?