import os
import subprocess
import pandas as pd
import pymeshlab
import json
from tqdm import tqdm

def process_xyz_clusters(input_xyz, output_folder):
    """Read XYZ, clean it in memory, and save separate files for each tree_id (cluster)."""
    os.makedirs(output_folder, exist_ok=True)  # Create the output folder if it doesn't exist

    # Read the input XYZ file into a DataFrame
    df = pd.read_csv(input_xyz, sep=r'\s+', header=None, usecols=[0, 1, 2, 3], names=["tree_id", "x", "y", "z"])

    cluster_files = []
    # Group the data by tree_id and save each group as a separate XYZ file
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
    
    # Iterate over each cluster file and convert it to LAS format
    for xyz_file in tqdm(cluster_files, desc="Converting XYZ to LAS"):
        las_file = xyz_file.replace(".xyz", ".las")

        # Define the PDAL pipeline for conversion with optional thinning
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

        # Save the pipeline configuration to a JSON file
        pipeline_file = xyz_file.replace(".xyz", "_pipeline.json")
        with open(pipeline_file, "w") as f:
            json.dump(pipeline, f, indent=4)

        # Run the PDAL pipeline
        subprocess.run(["pdal", "pipeline", pipeline_file], check=True)
        las_files.append(las_file)

    return las_files

def run_alpha_wrap(las_files, output_mesh_folder, alpha_wrap_exe):
    """Run the C++ Alpha Wrapping script on each LAS file."""
    os.makedirs(output_mesh_folder, exist_ok=True)  # Create the output folder if it doesn't exist
    mesh_files = []
    
    # Iterate over each LAS file and run the Alpha Wrapping executable
    for las_file in tqdm(las_files, desc="Running Alpha Wrapping"):
        # mesh_file = os.path.join(os.path.basename(las_file).replace(".las", ".obj"))
        
        relative_alpha = 20 #hardcoded for example
        relative_offset = 50 #hardcoded for example

        filename_hardcoded = os.path.basename(las_file).split('.')[0] + f"_{relative_alpha}_{relative_offset}.obj" #hardcoded for example
        mesh_file = os.path.join(output_mesh_folder, filename_hardcoded)

        # Run the Alpha Wrapping executable
        subprocess.run([alpha_wrap_exe, las_file, str(relative_alpha), str(relative_offset), output_mesh_folder], check=True)
        mesh_files.append(mesh_file)
    
    return mesh_files

def main(input_xyz, alpha_wrap_exe, final_output="final_mesh.obj"):
    clusters_folder = "clusters"
    meshes_folder = "meshes"

    # Step 1: Process XYZ into separate cluster files
    cluster_files = process_xyz_clusters(input_xyz, clusters_folder)

    # Step 2: Convert to LAS using PDAL
    las_files = convert_xyz_to_las(cluster_files)

    # Step 3: Run Alpha Wrapping on Each Cluster
    print(f'Running {alpha_wrap_exe}')
    mesh_files = run_alpha_wrap(las_files, meshes_folder, alpha_wrap_exe)


if __name__ == "__main__":
    input_xyz = "whm_01_0028.xyz"  # Input segmented point cloud
    alpha_wrap_exe = "./point_wrap/build/example_alphawrap"  # Path to your C++ executable
    
    main(input_xyz, alpha_wrap_exe)
