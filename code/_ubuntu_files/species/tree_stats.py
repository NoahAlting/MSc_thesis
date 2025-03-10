import laspy
import pandas as pd
import rerun as rr
import numpy as np

# Path to your LAZ file
laz_file_path = "whm_01_tid.laz"

# Open the LAZ file
with laspy.open(laz_file_path) as las:
    points = las.read()
    
    # Extract all attributes dynamically
    attributes = {dimension.name: getattr(points, dimension.name) for dimension in points.point_format}
    
    # Convert to DataFrame
    df_pcd = pd.DataFrame(attributes)

# Drop irrelevant columns
df_pcd = df_pcd[['X', 'Y', 'Z', 'red', 'green', 'blue', 'nir', 'ndvi', 'norm_g', 'mtvi2', 'tree_id']]

# Convert LAS scaled integer coordinates to floating-point coordinates
scale = las.header.scales
offset = las.header.offsets
df_pcd['X'] = df_pcd['X'] * scale[0] + offset[0]
df_pcd['Y'] = df_pcd['Y'] * scale[1] + offset[1]
df_pcd['Z'] = df_pcd['Z'] * scale[2] + offset[2]

# Print the DataFrame info
print(df_pcd.info())

# Compute tree-wise summary statistics
df_tree_summary = df_pcd.groupby('tree_id').agg({
    'Z': ['mean', 'min', 'max', 'median'],
    'ndvi': 'mean',
    'mtvi2': 'mean'
}).reset_index()

# Rename columns for clarity
df_tree_summary.columns = ['tree_id', 'Z_mean', 'Z_min', 'Z_max', 'Z_median', 'ndvi_mean', 'mtvi2_mean']

print("\nTree summary statistics:")
print(df_tree_summary.head())  # Print the first few rows for verification

# Function to visualize a specific tree
def visualize_tree(df_pcd, tree_id):
    """Visualizes a specific tree using Rerun."""
    df_tree = df_pcd[df_pcd['tree_id'] == tree_id].copy()

    if df_tree.empty:
        print(f"No points found for tree_id={tree_id}.")
        return

    # Normalize color values (convert from 16-bit to 8-bit)
    df_tree['red'] = (df_tree['red'] / df_tree['red'].max()).astype(np.uint8)
    df_tree['green'] = (df_tree['green'] / df_tree['green'].max()).astype(np.uint8)
    df_tree['blue'] = (df_tree['blue'] / df_tree['blue'].max()).astype(np.uint8)

    # Connect to the running Rerun viewer
    rr.init("tree_visualization", spawn=False)  
    rr.connect()  # Explicitly connect to the Rerun instance

    # Set time sequence to avoid overwriting logs
    rr.set_time_sequence(f"tree_{tree_id}", 0)

    # Log the point cloud
    rr.log(
        f"tree_{tree_id}",
        rr.Points3D(
            positions=df_tree[['X', 'Y', 'Z']].values,
            colors=df_tree[['red', 'green', 'blue']].values
        )
    )

    print(f"Visualization started for tree_id={tree_id}. Open Rerun viewer to see the tree.")

# Run the visualization with user input
if __name__ == "__main__":
    print("\nAvailable tree IDs:", df_pcd['tree_id'].unique())
    user_tree_id = int(input("Enter tree_id to visualize: "))  # Allow user to input tree_id
    visualize_tree(df_pcd, user_tree_id)
