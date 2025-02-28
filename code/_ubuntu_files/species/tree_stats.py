import laspy
import pandas as pd

# Path to your LAZ file
laz_file_path = "whm_01_tid.laz"

# Open the LAZ file
with laspy.open(laz_file_path) as las:
    points = las.read()
    
    # Extract all attributes dynamically
    attributes = {dimension.name: getattr(points, dimension.name) for dimension in points.point_format}
    
    # Convert to DataFrame
    df_pcd = pd.DataFrame(attributes)

# drop irrelevant columns
df_pcd = df_pcd[[
    'X', 'Y', 'Z',
    'red', 'green', 'blue', 'nir', 'ndvi', 'norm_g', 'mtvi2', 'tree_id'
    # 'intensity', 'return_number', 'number_of_returns', 'classification',
    # 'synthetic', 'key_point', 'withheld', 'overlap', 'scanner_channel', 'scan_direction_flag',
    # 'edge_of_flight_line', 'user_data', 'scan_angle', 'point_source_id', 'gps_time'
]]

# Print the DataFrame
print(df_pcd.info())

#group by tree id
df_tree_summary = df_pcd.groupby('tree_id').agg({
    'X': ['mean', 'min', 'max'],
    'Y': ['mean', 'min', 'max'],
    'Z': ['mean', 'min', 'max'],
    'ndvi': 'mean',
    'mtvi2': 'mean'
}).reset_index()

print(df_tree_summary.info())
