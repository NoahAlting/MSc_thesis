import os
import pandas as pd
from tqdm import tqdm

# Specify directories and CSV file
data_case = "whm_01"

input_directory = os.path.join(data_case, "results")
output_csv = os.path.join(data_case, "diagnostics.csv")

# Initialize a DataFrame to store results
if os.path.exists(output_csv):
    # Load existing CSV if it exists
    df = pd.read_csv(output_csv)
    print(f'{output_csv} exists, going to append data!')
else:
    # Initialize a new DataFrame
    df = pd.DataFrame(columns=["File Name", "Radius", "Vertical Res", "Min Points", "Num Points", "tree_count"])
    print(f'creating {output_csv}!')

# Function to process a single .xyz file
def process_xyz_file(file_name, file_path):
    # Extract radius, vertical resolution, and min points from the filename
    parts = file_name.replace(".xyz", "").split("_")
    radius = int(parts[3])  # Example: r_5000 -> 5000
    vertical_res = int(parts[5])  # Example: vres_50 -> 50
    min_points = int(parts[7])  # Example: minp_3 -> 3

    # Load the .xyz file into a pandas DataFrame
    columns = ["tree_id", "x", "y", "z", "red", "green", "blue"]
    data = pd.read_csv(file_path, delimiter=' ', header=None, names=columns)

    # Calculate metrics
    num_points = len(data)
    tree_count = data["tree_id"].nunique()

    # Return all calculated values
    return file_name, radius, vertical_res, min_points, num_points, tree_count

# Process original format files
for file_name in tqdm(os.listdir(input_directory), desc='file'):
    if file_name.endswith(".xyz") and "r_" in file_name and "vres_" in file_name and "minp_" in file_name:
        file_path = os.path.join(input_directory, file_name)
        
        # Extract parameters from the filename
        parts = file_name.replace(".xyz", "").split("_")
        radius = int(parts[3])
        vertical_res = int(parts[5])
        min_points = int(parts[7])

        # Check if the combination already exists in the CSV
        if not df[(df["Radius"] == radius) & (df["Vertical Res"] == vertical_res) & (df["Min Points"] == min_points)].empty:
            # print(f"Combination already exists for {file_name}. Deleting file.")
            os.remove(file_path)  # Delete the file
            continue

        # Process the file and add to the DataFrame
        result = process_xyz_file(file_name, file_path)
        df.loc[len(df)] = result

        # Rename the file based on the DataFrame index
        new_file_name = f"whm_01_{len(df)-1:04d}.xyz"  # Zero-padded index
        new_file_path = os.path.join(input_directory, new_file_name)
        os.rename(file_path, new_file_path)

        # Update the file name in the DataFrame
        df.at[len(df) - 1, "File Name"] = new_file_name

# Save the DataFrame to the CSV
df.to_csv(output_csv, index=False)
print(f"Summary saved to {output_csv}")
