import numpy as np
import laspy
import rerun as rr
import os
import matplotlib.pyplot as plt

def normalize_array(arr):
    return (arr - np.min(arr)) / (np.max(arr) - np.min(arr))

#Get a normalized colormap for attributes that are not RGB
def apply_colormap(values:np.array, colormap_name="viridis"):
    cmap = plt.get_cmap(colormap_name)
    return cmap(values)[:, :3]  # Extract RGB (ignore alpha)

def voxelize_point_cloud(las_file, voxel_size, output_file):

    # Load the point cloud
    las = laspy.read(las_file)

    # Extract coordinates and initialize attributes
    points = np.column_stack((las.x, las.y, las.z))

    attributes = {
        "nir": np.array(las.nir, dtype=np.float64),
        "red": np.array(las.red, dtype=np.float64),
        "green": np.array(las.green, dtype=np.float64),
        "blue": np.array(las.blue, dtype=np.float64),
        "ndvi": np.array(las.ndvi, dtype=np.float64),
        "norm_g": np.array(las.norm_g, dtype=np.float64),
        "mtvi2": np.array(las.mtvi2, dtype=np.float64)
    }

    # Compute voxel indices
    min_bounds = points.min(axis=0)
    max_bounds = points.max(axis=0)
    voxel_indices = np.floor((points - min_bounds) / voxel_size).astype(int)

    # Create a dictionary to store voxel information
    voxel_dict = {}
    for idx, (i, j, k) in enumerate(voxel_indices):
        key = (i, j, k)
        if key not in voxel_dict:
            voxel_dict[key] = {
                "points": [],
                **{attr: [] for attr in attributes}
            }
        voxel_dict[key]["points"].append(points[idx])
        for attr, values in attributes.items():
            voxel_dict[key][attr].append(values[idx])

    # Create voxelized point cloud
    voxel_centers = []
    voxel_attributes = {attr: [] for attr in attributes}
    for key, values in voxel_dict.items():
        center = (np.array(key) + 0.5) * voxel_size + min_bounds
        voxel_centers.append(center)

        # Calculate average attributes
        for attr in attributes:
            voxel_attributes[attr].append(np.mean(values[attr]))

    voxel_centers = np.array(voxel_centers)
    for attr in voxel_attributes:
        voxel_attributes[attr] = np.array(voxel_attributes[attr])

    # Save the voxelized point cloud
    header = laspy.LasHeader(point_format=3, version="1.2")

    # Add extra dimensions for unsupported attributes
    extra_dims = [
        laspy.ExtraBytesParams(name="nir", type=np.float64),
        laspy.ExtraBytesParams(name="ndvi", type=np.float64),
        laspy.ExtraBytesParams(name="norm_g", type=np.float64),
        laspy.ExtraBytesParams(name="mtvi2", type=np.float64)
    ]
    header.add_extra_dims(extra_dims)

    # Create the voxelized LAS file
    voxelized_las = laspy.LasData(header)
    voxelized_las.x = voxel_centers[:, 0]
    voxelized_las.y = voxel_centers[:, 1]
    voxelized_las.z = voxel_centers[:, 2]
    voxelized_las.red = voxel_attributes["red"].astype(np.uint16)
    voxelized_las.green = voxel_attributes["green"].astype(np.uint16)
    voxelized_las.blue = voxel_attributes["blue"].astype(np.uint16)

    # Add the extra dimensions to the file
    voxelized_las.nir = voxel_attributes["nir"]
    voxelized_las.ndvi = voxel_attributes["ndvi"]
    voxelized_las.norm_g = voxel_attributes["norm_g"]
    voxelized_las.mtvi2 = voxel_attributes["mtvi2"]
    
    # voxel_coloring = np.column_stack((
    #         normalize_array(voxel_attributes["red"]),   # Normalized red
    #         normalize_array(voxel_attributes["green"]), # Normalized green
    #         normalize_array(voxel_attributes["blue"]),  # Normalized blue
    #     ))

    voxel_coloring = apply_colormap(normalize_array(voxel_attributes["ndvi"]))

    # Visualize with rerun
    rr.init("Voxelized Point Cloud", spawn=True)
    rr.log("voxelized_voxels", rr.Boxes3D(
        centers=voxel_centers,
        half_sizes=np.full((voxel_centers.shape[0], 3), voxel_size / 2),  # Half the voxel size for cube dimensions
        colors=voxel_coloring,  
    ))

    print("Visualization ready. Run 'rerun' in terminal to view.")

    # Write to output file
    # voxelized_las.write(output_file)

    # print(f"Voxelized point cloud saved to {output_file}")



if __name__ == "__main__":    
    
    # Parameters
    input_file = os.path.join('data', "pcd_wilhelmina_park", "filtered_test_001.laz")
    output_file = os.path.join('data', "pcd_wilhelmina_park", "voxelized_pointcloud.laz")
    voxel_size = 3  # Set voxel size in the desired units
    
    # Run voxelization
    voxelize_point_cloud(input_file, voxel_size, output_file)
