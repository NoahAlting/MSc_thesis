import matplotlib.pyplot as plt
import open3d as o3d
import numpy as np
import rerun as rr
import laspy
import os

def calculate_ndvi(red, nir):
    red = np.array(red, dtype=np.float64)
    nir = np.array(nir, dtype=np.float64)
    
    return (nir - red) / (nir + red + 1e-8) # add small eps to avoid division by 0 

# Remove outliers using SOR
def remove_outliers(las_data, nb_neighbors=20, std_ratio=2.0):
    # Convert LAS data to Open3D point cloud
    xyz = np.vstack((las_data.x, las_data.y, las_data.z)).transpose()
    print(f"xyz shape: {xyz.shape}, dtype: {xyz.dtype}")
    print(f"Contains NaN: {np.isnan(xyz).any()}, Contains Inf: {np.isinf(xyz).any()}")
    xyz_subset = xyz[:10000]  # Use only the first 10,000 points

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz_subset)
    
    # Perform statistical outlier removal
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    
    # Filter the original LAS data
    filtered_las = las_data[ind]
    
    return filtered_las


def main():
    
    #get pointcloud to look at
    input_file = os.path.join('data', 'bws_sq250.LAZ')
    output_file = os.path.join('data', 'test_small.LAZ')
    
    #open LAS
    with laspy.open(input_file) as f:
        las = f.read()
        #available data contains:
        #['X', 'Y', 'Z', 'intensity', 'return_number', 'number_of_returns', 'synthetic', 
        # 'key_point', 'withheld', 'overlap', 'scanner_channel', 'scan_direction_flag', 
        # 'edge_of_flight_line', 'classification', 'user_data', 'scan_angle', 'point_source_id',
        # 'gps_time', 'red', 'green', 'blue', 'nir']

        red = las.red
        nir = las.nir

    ndvi = calculate_ndvi(red, nir)

    #create new pointcloud
    out_las = las
    out_las.add_extra_dim(laspy.ExtraBytesParams(name="ndvi", type=np.float32))
    out_las.ndvi = ndvi

    
    #Filter 1:  remove points with ndvi < threshold
    ndvi_threshold = -1
    out_las = out_las[out_las.ndvi > ndvi_threshold]

    #Filter 2:  remove points with single return
    out_las = out_las[out_las.number_of_returns > 1]

    #Filter 3:  remove last return of all remaining points
                #because I assume that this is ground/grass and not trees
    out_las = out_las[out_las.return_number != out_las.number_of_returns]

    # After your previous filtering steps:
    print('start outlier removal')
    out_las = remove_outliers(out_las, nb_neighbors=20, std_ratio=2.0)
    print("Outlier removal completed!")

    # Prepare for visualization
    xyz = np.column_stack((out_las.x, out_las.y, out_las.z))
    ndvi_colors = (out_las.ndvi - np.min(out_las.ndvi)) / (np.max(out_las.ndvi) - np.min(out_las.ndvi))
    colors = np.column_stack((ndvi_colors, np.zeros_like(ndvi_colors), 1 - ndvi_colors))  # NDVI as green

    # Create Open3D PointCloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    # pcd.colors = o3d.utility.Vector3dVector(colors)

    # Visualize the point cloud
    print("Visualizing point cloud...")
    o3d.visualization.draw_geometries([pcd])



if __name__ == "__main__":
    main()
    print(f'Successfully ran {os.path.basename(__file__)}!')
