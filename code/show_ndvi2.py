import open3d as o3d
import numpy as np
import laspy
import os
import matplotlib.pyplot as plt

def get_ndvi(red, nir):
    red = np.array(red, dtype=np.float64)
    nir = np.array(nir, dtype=np.float64)

    red = red / 65535
    nir = nir / 255

    return (nir - red) / (nir + red + 1e-8)

def visualize_window(pointcloud):
    vis = o3d.visualization.Visualizer()
    vis.create_window(window_name="Open3D Point Cloud Viewer", width = 1920//2, height = 1080//2)
    vis.add_geometry(pointcloud)

    render_option = vis.get_render_option()
    render_option.background_color = np.array([0.1, 0.1, 0.1])
    vis.get_view_control().set_zoom(0.5)

    vis.run()
    vis.destroy_window()


def plot_histogram(array1, x_label1, array2=None, x_label2=None):
    plt.figure(figsize=(10, 6))
    
    # Plot the first array
    plt.hist(array1, bins=50, alpha=0.7, label=f"{x_label1}")
    
    # Plot the second array if provided
    if array2 is not None and x_label2 is not None:
        plt.hist(array2, bins=50, alpha=0.7, label=f"{x_label2}")
    
    # Add labels and grid
    plt.xlabel("Value", fontsize=14)
    plt.ylabel("Frequency", fontsize=14)
    if array2 is not None and x_label2 is not None:
        plt.legend(fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.show()



def main():
    input_file = os.path.join('data', 'bws_500.LAZ')

    with laspy.open(input_file) as f:
        las = f.read()
    
        red = las.red
        nir = las.nir

    ndvi = get_ndvi(red, nir)

    # copy pointcloud and do calculations on the copy
    out_las = las
    out_las.add_extra_dim(laspy.ExtraBytesParams(name='ndvi', type=np.float32))
    out_las.ndvi = ndvi

    # Filter 1: Filter out points with NDVI value under threshold
    ndvi_threshold = -0.1
    # out_las = out_las[out_las.ndvi > ndvi_threshold]

    # Filter 2: Remove points with single return
    out_las = out_las[out_las.number_of_returns > 1]

    # Filter 3: Remove last return of all remaining points
    out_las = out_las[out_las.return_number != out_las.number_of_returns]


    plot_histogram(nir, 'nir', out_las.nir, 'nir after filtering')



    #prep for visualization
    xyz = np.column_stack((out_las.x, out_las.y, out_las.z))
    ndvi_colors = out_las.ndvi
    colors = plt.cm.viridis(ndvi_colors)[:, :3]

    pcloud = o3d.geometry.PointCloud()
    pcloud.points = o3d.utility.Vector3dVector(xyz)
    pcloud.colors = o3d.utility.Vector3dVector(colors)

    visualize_window(pointcloud=pcloud)


if __name__ == "__main__":
    main()
    print('Completed succesfully!')