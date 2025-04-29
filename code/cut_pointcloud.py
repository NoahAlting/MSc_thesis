import laspy
import numpy as np
import os

def crop_laz(input_file, output_file, min_bounds, max_bounds):
    """
    Crops a LAZ point cloud to a smaller subsection defined by a bounding box.
    
    Parameters:
    - input_file (str): Path to the input LAZ file.
    - output_file (str): Path to save the cropped LAZ file.
    - min_bounds (tuple): Minimum x, y, z bounds for cropping (e.g., (x_min, y_min, z_min)).
    - max_bounds (tuple): Maximum x, y, z bounds for cropping (e.g., (x_max, y_max, z_max)).
    """
    # Load the LAZ file
    las = laspy.read(input_file)  # Removed context manager
    
    # Extract point data
    points = np.vstack((las.x, las.y, las.z)).T

    # Create a mask for points inside the bounding box
    mask = (
        (points[:, 0] >= min_bounds[0]) & (points[:, 0] <= max_bounds[0]) &
        (points[:, 1] >= min_bounds[1]) & (points[:, 1] <= max_bounds[1]) &
        (points[:, 2] >= min_bounds[2]) & (points[:, 2] <= max_bounds[2])
    )

    # Filter points using the mask
    cropped_points = las.points[mask]

    # Create a new LAS/LAZ file with the cropped points
    cropped_las = laspy.LasData(las.header)
    cropped_las.points = cropped_points

    # Save the cropped points to a new file
    cropped_las.write(output_file)
    print(f"Cropped point cloud saved to {output_file}")

if __name__ == "__main__":
    # Example usage

    input_file = os.path.join('data', 'pcd_wilhelmina_park', 'ahn5_37EN1_14.laz')
    output_file = os.path.join('data', 'pcd_wilhelmina_park', "whm_500.laz")  

    # Coordinates for test sample set taken from CloudCompare
    center = (83536, 447342)
    bbox_dim = (500, 500)

    min_bounds = (
        center[0] - bbox_dim[0] / 2, 
        center[1] - bbox_dim[1] / 2,
        -100  # Minimum Z
    )
    max_bounds = (
        center[0] + bbox_dim[0] / 2, 
        center[1] + bbox_dim[1] / 2,
        100   # Maximum Z
    )

    crop_laz(input_file, output_file, min_bounds, max_bounds)
