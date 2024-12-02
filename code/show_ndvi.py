import matplotlib.pyplot as plt
import open3d as o3d
import numpy as np
import laspy
import os


def calculate_ndvi(red, nir):
    red = np.array(red, dtype=np.float64)
    nir = np.array(nir, dtype=np.float64)

    red = red / 65535 #red channel is 16-bits
    nir = nir / 255 #nir channel is 8-bits

    return (nir - red) / (nir + red + 1e-8)  # Add small epsilon to avoid division by zero


def remove_outliers(las_data, nb_neighbors=20, std_ratio=2.0):
    xyz = np.vstack((las_data.x, las_data.y, las_data.z)).transpose()
    print(f"xyz shape: {xyz.shape}, dtype: {xyz.dtype}")

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    print('checkpoint')
    # Perform statistical outlier removal
    _, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    
    # Filter the original LAS data
    filtered_las = las_data[ind]
    return filtered_las


def visualize_window(pcd):
    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Open3D Point Cloud Viewer", width=1920//2, height=1080//2)
    vis.add_geometry(pcd)
    
    # Set fullscreen mode
    render_option = vis.get_render_option()
    render_option.background_color = np.array([0.1, 0.1, 0.1])  # Optional: Set a background color
    vis.get_view_control().set_zoom(0.5)  # Optional: Adjust zoom level

    vis.run()
    vis.destroy_window()


def plot_ndvi_histogram(ndvi_values):
    """Plot a histogram of NDVI values."""
    plt.figure(figsize=(10, 6))
    plt.hist(ndvi_values, bins=50, color='green', alpha=0.7, edgecolor='black')
    plt.title("NDVI Histogram", fontsize=16)
    plt.xlabel("NDVI Value", fontsize=14)
    plt.ylabel("Frequency", fontsize=14)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.show()



def main():
    input_file = os.path.join('data', 'bws_100.LAZ')
    # output_file = os.path.join('data', 'output.LAZ')
    # Open LAS file
    with laspy.open(input_file) as f:
        las = f.read()
        #available data contains:
        #['X', 'Y', 'Z', 'intensity', 'return_number', 'number_of_returns', 'synthetic', 
        # 'key_point', 'withheld', 'overlap', 'scanner_channel', 'scan_direction_flag', 
        # 'edge_of_flight_line', 'classification', 'user_data', 'scan_angle', 'point_source_id',
        # 'gps_time', 'red', 'green', 'blue', 'nir']

    # Calculate NDVI
    ndvi = calculate_ndvi(las.red, las.nir)

    # Add NDVI as an extra dimension
    out_las = las
    out_las.add_extra_dim(laspy.ExtraBytesParams(name="ndvi", type=np.float32))
    out_las.ndvi = ndvi

    # Filter 1: Filter out points with NDVI value under threshold
    ndvi_threshold = -0.1
    out_las = out_las[out_las.ndvi > ndvi_threshold]

    # Filter 2: Remove points with single return
    out_las = out_las[out_las.number_of_returns > 1]

    # Filter 3: Remove last return of all remaining points
    out_las = out_las[out_las.return_number != out_las.number_of_returns]

    # Perform outlier removal
    print('trying to remove outliers')
    # out_las = remove_outliers(out_las, nb_neighbors=20, std_ratio=2.0)
    print('outliers removed')

    # Plot histogram of NDVI values
    # plot_ndvi_histogram(ndvi)
    # plot_ndvi_histogram(out_las.ndvi)


    # Prepare for visualization
    xyz = np.column_stack((out_las.x, out_las.y, out_las.z))
    ndvi_colors = (out_las.ndvi - np.min(out_las.ndvi)) / (np.max(out_las.ndvi) - np.min(out_las.ndvi))
    colors = plt.cm.viridis(ndvi_colors)[:, :3]  # Use viridis colormap for NDVI

    # Create Open3D PointCloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    pcd.colors = o3d.utility.Vector3dVector(colors)

    # Visualize the point cloud in fullscreen
    print("Visualizing point cloud in fullscreen mode...")
    visualize_window(pcd)



if __name__ == "__main__":
    main()
    print("Script completed successfully!")