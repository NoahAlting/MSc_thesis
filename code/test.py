import open3d as o3d
import numpy as np

# Generate a simple test point cloud
xyz_test = np.random.rand(1000, 3)

def visualize_pointcloud(xyz):
    """
    Visualize a point cloud using Open3D.
    """
    try:
        # Create Open3D PointCloud
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(xyz)

        # Visualize the point cloud
        o3d.visualization.draw_geometries([pcd], 
                                          window_name="Open3D Point Cloud Viewer", 
                                          width=1280, height=720,
                                          left=50, top=50)  # Customize window size and position

        print("PointCloud visualization succeeded!")
    except Exception as e:
        print(f"Failed to visualize PointCloud: {e}")

# Test the visualization
visualize_pointcloud(xyz_test)
