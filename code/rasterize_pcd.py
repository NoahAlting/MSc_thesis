import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin
import os

# Load the LAS file
las = laspy.read(os.path.join('data', "pcd_wilhelmina_park", 'filtered_test_001.laz'))

# Define the attribute to rasterize (e.g., "z" for elevation, "intensity" for intensity, etc.)
attribute_name = "ndvi"  # Change this to the desired attribute (e.g., 'z', 'norm_g', etc.)

output_name = os.path.join('data', "pcd_wilhelmina_park", f'raster_001_{attribute_name}.tif')

# Extract coordinates and the chosen attribute
x = las.x
y = las.y

# Check if the attribute exists in the LAS file
if hasattr(las, attribute_name):
    attribute = getattr(las, attribute_name)
else:
    raise AttributeError(f"The LAS file does not contain the attribute '{attribute_name}'")

# Define grid resolution (e.g., 1 meter)
resolution = .25  # 1-meter grid

# Determine the bounds of the point cloud
x_min, x_max = x.min(), x.max()
y_min, y_max = y.min(), y.max()

# Compute grid dimensions
cols = int((x_max - x_min) / resolution) + 1
rows = int((y_max - y_min) / resolution) + 1

# Initialize a raster grid
raster = np.full((rows, cols), np.nan)

# Bin points into the grid
x_idx = ((x - x_min) / resolution).astype(int)
y_idx = ((y_max - y) / resolution).astype(int)

# Rasterize using the selected attribute
for i, j, value in zip(y_idx, x_idx, attribute):
    if np.isnan(raster[i, j]):
        raster[i, j] = value
    else:
        raster[i, j] = (raster[i, j] + value) / 2  # Average value

# Save as GeoTIFF
transform = from_origin(x_min, y_max, resolution, resolution)
with rasterio.open(
    output_name,
    "w",
    driver="GTiff",
    height=rows,
    width=cols,
    count=1,
    dtype=raster.dtype,
    crs="EPSG:28992",  # Change to your LAS CRS
    transform=transform,
) as dst:
    dst.write(raster, 1)

print(f"Raster saved as {output_name}")
