import numpy as np
import rerun as rr
import laspy
import os
import open3d as o3d
import matplotlib.pyplot as plt
from collections import Counter

# Input file and thinning options
input_file = os.path.join('..', 'data', 'pcd_wilhelmina_park', 'whm_100x100.LAZ')
thinning_factor = 1.0  # 1.0 means keep all points

# --- Load the LAS file and process as in the pipeline ---
with laspy.open(input_file, laz_backend=laspy.LazBackend.Laszip) as f:
    original_las = f.read()

    if 0 < thinning_factor < 1.0:
        print(f"Thinning the point cloud with factor {thinning_factor}...")
        step = int(1 / thinning_factor)
        thinned_points = original_las.points[::step]
        print(f"Original points: {len(original_las.points)}, Thinned points: {len(thinned_points)}")
        original_las.points = thinned_points
    else:
        print("Thinning not applied. Keeping all points.")

    # Print point attributes for diagnostics
    print("\nPoint Attributes:")
    col_width = 25
    for dimension in f.header.point_format.dimension_names:
        dtype = original_las[dimension].dtype
        min_val = original_las[dimension].min()
        max_val = original_las[dimension].max()
        print(f"{dimension.ljust(col_width)} {str(dtype).ljust(col_width)} "
              f"Min: {str(min_val).ljust(col_width)} Max: {max_val}")

# Normalize color bands
bit8 = 255
nir_raw = np.array(original_las.nir, dtype=np.float64) / bit8
red_raw = np.array(original_las.red, dtype=np.float64) / bit8
green_raw = np.array(original_las.green, dtype=np.float64) / bit8
blue_raw = np.array(original_las.blue, dtype=np.float64) / bit8

# --- Define vegetation index functions ---
def get_ndvi(red, nir):
    red = np.array(red, dtype=np.float64)
    nir = np.array(nir, dtype=np.float64)
    return (nir - red) / (nir + red + 1e-8)

def get_norm_g(red, green, blue):
    red = np.array(red, dtype=np.float64)
    green = np.array(green, dtype=np.float64)
    blue = np.array(blue, dtype=np.float64)
    return green / (red + green + blue)

def get_mtvi2(nir, red, green):
    nir = np.array(nir, dtype=np.float64)
    red = np.array(red, dtype=np.float64)
    green = np.array(green, dtype=np.float64)
    return 1.5 * (1.2 * (nir - green) - 2.5 * (red - green)) / np.sqrt((2 * nir + 1)**2 - (6 * nir - 5 * np.sqrt(red) - 0.5))

# Calculate vegetation features and add to LAS
if 'ndvi' not in original_las.point_format.dimension_names:
    original_las.add_extra_dim(laspy.ExtraBytesParams(name='ndvi', type=np.float32))
original_las.ndvi = get_ndvi(red_raw, nir_raw)

if 'norm_g' not in original_las.point_format.dimension_names:
    original_las.add_extra_dim(laspy.ExtraBytesParams(name='norm_g', type=np.float32))
original_las.norm_g = get_norm_g(red_raw, green_raw, blue_raw)

if 'mtvi2' not in original_las.point_format.dimension_names:
    original_las.add_extra_dim(laspy.ExtraBytesParams(name='mtvi2', type=np.float32))
original_las.mtvi2 = get_mtvi2(nir_raw, red_raw, green_raw)

# --- Diagnostic Plots ---
# Plot raw band histograms
bins = 64
alpha = 0.3
plt.hist(blue_raw, bins=bins, alpha=alpha, label='Blue', color='blue')
plt.hist(green_raw, bins=bins, alpha=alpha, label='Green', color='green')
plt.hist(red_raw, bins=bins, alpha=alpha, label='Red', color='red')
plt.hist(nir_raw, bins=bins, alpha=alpha, label='NIR', color='orange')
plt.xlabel('Value')
plt.ylabel('Frequency')
plt.title('Band Value Distribution for raw pointcloud')
plt.legend()
plt.show()

print(f'Blue band: max = {blue_raw.max():.4f}, min = {blue_raw.min():.4f}')
print(f'Green band: max = {green_raw.max():.4f}, min = {green_raw.min():.4f}')
print(f'Red band: max = {red_raw.max():.4f}, min = {red_raw.min():.4f}')
print(f'NIR band: max = {nir_raw.max():.4f}, min = {nir_raw.min():.4f}')

# Function to plot multiple histograms in subplots
def subplots_attribute_histograms(attribute_layers: dict, title="Attribute Histograms"):
    max_columns = 3
    num_attributes = len(attribute_layers)
    num_rows = (num_attributes + max_columns - 1) // max_columns
    fig, axes = plt.subplots(num_rows, max_columns, figsize=(15, 5 * num_rows))
    axes = axes.flatten()
    for idx, (name, data) in enumerate(attribute_layers.items()):
        ax = axes[idx]
        ax.hist(data, bins=32)
        ax.set_title(f"{name}")
        ax.set_xlabel("Value")
        ax.set_ylabel("Frequency")
        ax.grid(linestyle='--', alpha=0.7)
    for idx in range(num_attributes, len(axes)):
        axes[idx].axis('off')
    fig.suptitle(title)
    plt.tight_layout()
    plt.show()

# Plot attribute histograms before filtering
attributes_before = {
    'NDVI': original_las.ndvi,
    'norm_g': original_las.norm_g,
    'mtvi2': original_las.mtvi2
}
subplots_attribute_histograms(attributes_before, title='Attribute Histograms Before Filtering')

# --- Print Classification Information ---
AHN_classification_mapping = {
    0: "Created, never classified",
    1: "Unclassified",
    2: "Ground",
    6: "Building",
    9: "Water",
    14: "High tension",
    26: "Civil structure"
}
classification_values = original_las.classification
unique_values = np.unique(classification_values)
print("Unique Classification Values and Meanings:")
for value in unique_values:
    meaning = AHN_classification_mapping.get(value, "Unknown")
    print(f"Class {value}: {meaning}")
counts = Counter(classification_values)
sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
print("\nClassification Counts (Ordered by Frequency):")
header = f"{'Class':<10}{'Meaning':<25}{'Points':>15}"
print(header)
print("-" * len(header))
for cls, count in sorted_counts:
    meaning = AHN_classification_mapping.get(cls, "Unknown")
    print(f"{str(cls):<10}{meaning:<25}{str(count):>15}")

# --- Filtering (same as in the pipeline) ---
las = laspy.LasData(original_las.header)
las.points = original_las.points.copy()
las = las[las.number_of_returns > 1]
las = las[las.return_number != las.number_of_returns]

def remove_outliers(las_data, nb_neighbors=20, std_ratio=2.0):
    xyz = np.vstack((las_data.x, las_data.y, las_data.z)).transpose()
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    return las_data[ind]

las = remove_outliers(las, nb_neighbors=20, std_ratio=2.0)

# Plot histograms after filtering
attributes_after = {
    'NDVI': las.ndvi,
    'norm_g': las.norm_g,
    'mtvi2': las.mtvi2
}
subplots_attribute_histograms(attributes_after, title="Attribute Histograms After Filtering")

# --- Visualization with rerun ---
def normalize_array(arr):
    return (arr - np.min(arr)) / (np.max(arr) - np.min(arr))

def apply_colormap(values: np.array, colormap_name="viridis"):
    cmap = plt.get_cmap(colormap_name)
    return cmap(values)[:, :3]

def labels_list(las_data):
    return [f"NDVI: {ndvi:.3f}, norm_green: {ng:.3f}, mtvi2: {mtvi2:.3f}"
            for ndvi, ng, mtvi2 in zip(las_data.ndvi, las_data.norm_g, las_data.mtvi2)]

def visualize_pcd_filtered_vs_original(las_filtered, las_original):
    rr.init("Filtered vs Original", spawn=True)
    points_original = np.column_stack((las_original.x, las_original.y, las_original.z))
    points_filtered = np.column_stack((las_filtered.x, las_filtered.y, las_filtered.z))
    colors_original = np.column_stack((
        normalize_array(las_original.red),
        normalize_array(las_original.green),
        normalize_array(las_original.blue)
    ))
    colors_filtered = np.column_stack((np.zeros(len(points_filtered)),
                                        np.ones(len(points_filtered)),
                                        np.zeros(len(points_filtered))))
    rr.log("original", rr.Points3D(positions=points_original,
                                    colors=colors_original,
                                    radii=0.1,
                                    labels=labels_list(las_original)))
    rr.log("filtered", rr.Points3D(positions=points_filtered,
                                    colors=colors_filtered,
                                    radii=0.2,
                                    labels=labels_list(las_filtered)))
    print("Visualization ready. Run 'rerun' in terminal to view.")

def visualize_multiple_pcd_attributes(las_filtered, las_original, attributes_dict):
    rr.init("Multiple Attribute Viewer", spawn=True)
    points_original = np.column_stack((las_original.x, las_original.y, las_original.z))
    points_filtered = np.column_stack((las_filtered.x, las_filtered.y, las_filtered.z))
    colors_original = np.column_stack((
        normalize_array(las_original.red),
        normalize_array(las_original.green),
        normalize_array(las_original.blue)
    ))
    rr.log("original_point_cloud", rr.Points3D(
        positions=points_original,
        colors=colors_original,
        radii=0.1,
        labels=labels_list(las_original)
    ))
    for name, values in attributes_dict.items():
        normalized_values = normalize_array(values)
        attribute_colors = apply_colormap(normalized_values)
        rr.log(f"{name}", rr.Points3D(
            positions=points_filtered,
            colors=attribute_colors,
            radii=0.2,
            labels=labels_list(las_filtered)
        ))
    print("Visualization for multiple attributes is ready. Run 'rerun' in terminal to view.")

# Visualize filtered vs original
visualize_pcd_filtered_vs_original(las, original_las)

# Visualize dynamic attribute layers
filtered_attr_of_interest = {
    'NDVI': las.ndvi,
    'normalized green': las.norm_g,
    'MTVI2': las.mtvi2
}
visualize_multiple_pcd_attributes(las, original_las, filtered_attr_of_interest)

# The diagnostics script can also include saving the processed files if desired.
