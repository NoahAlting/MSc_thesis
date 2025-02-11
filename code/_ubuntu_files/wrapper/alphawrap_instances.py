import os
import subprocess
import pandas as pd
import pymeshlab
import json
from tqdm import tqdm

def process_xyz_clusters(input_xyz, output_folder):
    """Read XYZ, clean it in memory, and save separate files for each tree_id (cluster)."""
    os.makedirs(output_folder, exist_ok=True)
    df = pd.read_csv(input_xyz, sep=r'\s+', header=None, usecols=[0, 1, 2, 3], names=["tree_id", "x", "y", "z"])
    cluster_files = []
    for tree_id, tree_cluster in tqdm(df.groupby("tree_id"), desc="Processing XYZ to clusters"):
        cluster_filename = os.path.join(output_folder, f"tree_{int(tree_id)}.xyz")
        if tree_cluster.shape[0] < 10:
            print(f"Warning: Skipping cluster {tree_id} with less than 10 points.")
            continue
        tree_cluster[["x", "y", "z"]].to_csv(cluster_filename, sep=' ', header=False, index=False)
        cluster_files.append(cluster_filename)
    return cluster_files

def convert_xyz_to_las(cluster_files, thinning_factor=1):
    """Convert XYZ files to LAS using PDAL with optional thinning."""
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
                    "radius": thinning_factor
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
        subprocess.run(["pdal", "pipeline", pipeline_file], check=True)
        las_files.append(las_file)
    return las_files

def run_alpha_wrap(las_files, output_mesh_folder, alpha_wrap_exe, relative_alpha=20, relative_offset=50):
    """Run the C++ Alpha Wrapping script on each LAS file, logging output to a file."""
    os.makedirs(output_mesh_folder, exist_ok=True)
    mesh_files = []
    log_path = os.path.join(output_mesh_folder, "alpha_wrap.log")

    with open(log_path, "w") as log_file:
        for las_file in tqdm(las_files, desc="Running Alpha Wrapper"):
            log_file.write("Wrapping " + las_file + "\n")
            log_file.flush()

            filename_hardcoded = os.path.basename(las_file).split('.')[0] + f"_{relative_alpha}_{relative_offset}.obj"
            mesh_file = os.path.join(output_mesh_folder, filename_hardcoded)
            # Run the Alpha Wrapping executable and redirect output to log file
            subprocess.run(
                [alpha_wrap_exe, las_file, str(relative_alpha), str(relative_offset), output_mesh_folder],
                check=True,
                stdout=log_file,
                stderr=log_file
            )
            # Write a separator line after each iteration
            log_file.write("\n" + "="*40 + "\n")
            log_file.flush()

            mesh_files.append(mesh_file)
    return mesh_files

def main(input_xyz, alpha_wrap_exe, relative_alpha, relative_offset, final_output="forest.obj"):
    clusters_folder = "clusters"
    meshes_folder = "meshes"

    # Process XYZ into separate cluster files
    cluster_files = process_xyz_clusters(input_xyz, clusters_folder)
    
    # Convert to LAS using PDAL
    las_files = convert_xyz_to_las(cluster_files)

    # Run Alpha Wrapping on Each Cluster LAS file with logging
    mesh_files = run_alpha_wrap(las_files, meshes_folder, alpha_wrap_exe, relative_alpha, relative_offset)

    
if __name__ == "__main__":
    input_xyz = "whm_01_0028.xyz"  
    alpha_wrap_exe = "./point_wrap/build/example_alphawrap"  # Path to C++ executable wrapper

    #alpha wrap parameters
    relative_alpha = 20
    relative_offset = 50

    main(input_xyz, alpha_wrap_exe, relative_alpha, relative_offset)
