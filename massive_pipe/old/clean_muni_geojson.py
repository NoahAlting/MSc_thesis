import geopandas as gpd
from shapely import wkt
from shapely.geometry import Point
from sklearn.cluster import DBSCAN
import alphashape
import numpy as np
from shapely import wkt

# Parameters
input_file = "Bomen_in_beheer_door_gemeente_Delft.geojson"
buffer_dist = 10
alpha_val = .005
eps = 100        # in meters, tweak depending on point density
min_samples = 5
bbox_output = "bbox_delft_muni.geojson"
light_output = "Bomen_light.geojson"

# Load data
gdf = gpd.read_file(input_file)[["OBJECTID", "BOOMSORTIMENT", "geometry"]]
if gdf.crs.is_geographic:
    gdf = gdf.to_crs(epsg=28992)  # RD New

# Extract coordinates
coords = np.array([(geom.x, geom.y) for geom in gdf.geometry])

# Run DBSCAN clustering
clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
gdf["cluster"] = clustering.labels_

# Keep only the largest cluster (excluding noise: label = -1)
main_cluster = gdf["cluster"].value_counts().idxmax()
filtered_gdf = gdf[gdf["cluster"] == main_cluster].copy()

# Create alpha shape polygon
points = [(pt.x, pt.y) for pt in filtered_gdf.geometry]
alpha_shape = alphashape.alphashape(points, alpha_val).buffer(buffer_dist)

# Save result as geojson
filtered_gdf[["OBJECTID", "BOOMSORTIMENT", "geometry"]].to_file(light_output, driver="GeoJSON")
gpd.GeoDataFrame(geometry=[alpha_shape], crs=gdf.crs).to_file(bbox_output, driver="GeoJSON")

# Save result as WKT
with open("bbox_delft_muni.wkt", "w") as f:
    f.write(alpha_shape.wkt)
    
# Report
print(f"Original: {len(gdf)}, kept after DBSCAN: {len(filtered_gdf)}")
