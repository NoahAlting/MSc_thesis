import os
import sys
import geopandas as gpd
from shapely.geometry import Point
from sklearn.cluster import DBSCAN
import alphashape
import numpy as np

# --------------------------
# Handle input argument
# --------------------------
if len(sys.argv) < 2:
    print("Usage: python preprocess_municipality_trees.py <case_dir>")
    sys.exit(1)

case_dir = sys.argv[1]
os.makedirs(case_dir, exist_ok=True)

# --------------------------
# Parameters
# --------------------------
input_file = os.path.join(case_dir, "Bomen_in_beheer_door_gemeente_Delft.geojson")
light_output = os.path.join(case_dir, "Bomen_light.geojson")
bbox_output = os.path.join(case_dir, "bbox_delft_muni.geojson")
wkt_output = os.path.join(case_dir, "bbox_delft_muni.wkt")

buffer_dist = 10
alpha_val = 0.005
eps = 100
min_samples = 5

# --------------------------
# Load and filter
# --------------------------
gdf = gpd.read_file(input_file)[["OBJECTID", "BOOMSORTIMENT", "geometry"]]
if gdf.crs.is_geographic:
    gdf = gdf.to_crs(epsg=28992)  # RD New

coords = np.array([(geom.x, geom.y) for geom in gdf.geometry])
clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
gdf["cluster"] = clustering.labels_

main_cluster = gdf["cluster"].value_counts().idxmax()
filtered_gdf = gdf[gdf["cluster"] == main_cluster].copy()

points = [(pt.x, pt.y) for pt in filtered_gdf.geometry]
alpha_shape = alphashape.alphashape(points, alpha_val).buffer(buffer_dist)

# --------------------------
# Save outputs
# --------------------------
filtered_gdf[["OBJECTID", "BOOMSORTIMENT", "geometry"]].to_file(light_output, driver="GeoJSON")
gpd.GeoDataFrame(geometry=[alpha_shape], crs=gdf.crs).to_file(bbox_output, driver="GeoJSON")

with open(wkt_output, "w") as f:
    f.write(alpha_shape.wkt)

print(f"Original: {len(gdf)}, kept after DBSCAN: {len(filtered_gdf)}")
print(f"✅ Saved to: {light_output}, {bbox_output}, {wkt_output}")
