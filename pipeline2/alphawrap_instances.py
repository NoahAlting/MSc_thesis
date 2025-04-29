import os
import subprocess
import pandas as pd
import pymeshlab
import json
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)


def process_xyz_clusters(input_xyz, output_folder):
    """
    Read the input XYZ file into a DataFrame, split it by tree_id,
    and save each cluster as a separate XYZ file in the output folder.
    """
    logger.info("Processing input XYZ: %s", input_xyz)
    os.makedirs(output_folder, exist_ok=True)
    logger.info("Output folder created/exists: %s", output_folder)

    df = pd.read_csv(
        input_xyz, sep=r'\s+', header=None, usecols=[0, 1, 2, 3],
        names=["tree_id", "x", "y", "z"]
    )

    cluster_files = []
    for tree_id, tree_cluster in tqdm(df.groupby("tree_id"), desc="Processing XYZ to clusters"):
        cluster_filename = os.path.join(output_folder, f"tree_{int(tree_id)}.xyz")
        if tree_cluster.shape[0] < 10:
            # Skip clusters with less than 10 points
            logger.info("Skipping tree_id=%s because it has fewer than 10 points.", tree_id)
            continue

        tree_cluster[["x", "y", "z"]].to_csv(cluster_filename, sep=' ', header=False, index=False)
        logger.info("Created cluster file %s with %d points.", cluster_filename, tree_cluster.shape[0])
        cluster_files.append(cluster_filename)

    logger.info("Total cluster files created: %d", len(cluster_files))
    return cluster_files


def convert_xyz_to_las(cluster_files, alpha_pdal_thinning_factor=1):
    """
    Convert each XYZ file in the list to LAS format using a PDAL pipeline.
    The thinning_factor parameter is used by the PDAL sample filter.
    """
    logger.info("Converting %d cluster files from XYZ to LAS...", len(cluster_files))
    las_files = []

    for xyz_file in tqdm(cluster_files, desc="Converting XYZ to LAS"):
        las_file = xyz_file.replace(".xyz", ".las")
        pipeline = {
            "pipeline": [
                {
                    "type": "readers.text",
                    "filename": xyz_file,
                    "header": "X Y Z"
                },
                {
                    "type": "filters.sample",
                    "radius": alpha_pdal_thinning_factor
                },
                {
                    "type": "writers.las",
                    "filename": las_file,
                    "scale_x": 0.01,
                    "scale_y": 0.01,
                    "scale_z": 0.01
                }
            ]
        }
        pipeline_file = xyz_file.replace(".xyz", "_pipeline.json")
        with open(pipeline_file, "w") as f:
            json.dump(pipeline, f, indent=4)

        try:
            subprocess.run(["pdal", "pipeline", pipeline_file], check=True)
            logger.info("Created LAS file: %s", las_file)
            las_files.append(las_file)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to convert %s to LAS. Error: %s", xyz_file, e)

    return las_files


def run_alpha_wrap(las_files, output_mesh_folder, alpha_wrap_exe):
    """
    Run the C++ Alpha Wrapping executable on each LAS file.
    The function returns a list of generated mesh filenames.
    """
    logger.info("Running Alpha Wrap on %d LAS files...", len(las_files))
    os.makedirs(output_mesh_folder, exist_ok=True)
    mesh_files = []

    for las_file in tqdm(las_files, desc="Running Alpha Wrapping"):
        relative_alpha = 20
        relative_offset = 50
        filename_hardcoded = os.path.basename(las_file).split('.')[0] + f"_{relative_alpha}_{relative_offset}.obj"
        mesh_file = os.path.join(output_mesh_folder, filename_hardcoded)
        try:
            subprocess.run(
                [alpha_wrap_exe, las_file, str(relative_alpha), str(relative_offset), output_mesh_folder],
                check=True
            )
            mesh_files.append(mesh_file)
            logger.info("Alpha-wrapped mesh created: %s", mesh_file)
        except subprocess.CalledProcessError as e:
            logger.error("Alpha Wrap failed for %s. Error: %s", las_file, e)

    return mesh_files


def merge_meshes(mesh_files, final_output):
    """
    Merge multiple mesh files into a single mesh and save it as final_output.
    This uses pymeshlab to load all meshes and merge them.
    """
    logger.info("Merging %d mesh files into %s", len(mesh_files), final_output)
    ms = pymeshlab.MeshSet()
    for mf in mesh_files:
        ms.load_new_mesh(mf)
    ms.merge_visible_meshes()
    ms.save_current_mesh(final_output)
    logger.info("Final merged mesh saved to: %s", final_output)


def alphawrap_instances(data_dir, input_xyz, alpha_wrap_exe, clusters_folder, meshes_folder, thinning_factor, final_output):
    # Step 1: Process the input XYZ file into separate cluster files
    cluster_files = process_xyz_clusters(input_xyz, clusters_folder)

    # Step 2: Convert each cluster XYZ file to LAS format
    las_files = convert_xyz_to_las(cluster_files, thinning_factor)

    # Step 3: Run the Alpha Wrapping executable on each LAS file to generate mesh files
    mesh_files = run_alpha_wrap(las_files, meshes_folder, alpha_wrap_exe)

    # Step 4: Merge all generated mesh files into one final output mesh
    merge_meshes(mesh_files, final_output)


if __name__ == "__main__":
    from shared_logging import setup_logging
    
    data_dir = "delft_250"
    log_file = os.path.join(data_dir, "alphawrap.log")
    setup_logging(log_file)
    logger.info("AlphaWrap script started separately.")

    # Configuration variables
    input_xyz = os.path.join(data_dir, "forest_tid_test.xyz")  # Input segmented point cloud file
    alpha_wrap_exe = "./point_wrap/build/example_alphawrap"    # Path to the C++ Alpha Wrapping executable

    clusters_folder = os.path.join(data_dir, "clusters")   
    meshes_folder = os.path.join(data_dir, "meshes")        
    alpha_pdal_thinning_factor = 1                          
    final_output = os.path.join(data_dir, "final_mesh.obj")

    alphawrap_instances(
        data_dir,
        input_xyz,
        alpha_wrap_exe,
        clusters_folder,
        meshes_folder,
        alpha_pdal_thinning_factor,
        final_output
    )

    logger.info("AlphaWrap script finished.")
