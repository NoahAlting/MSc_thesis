import os
import geopandas as gpd
import pandas as pd
from tqdm import tqdm

tile_grid_path = "tile_grid_core.geojson"
tiles_dir = "tiles"

# Load tile grid
tile_grid = gpd.read_file(tile_grid_path).set_index("tile_id")
tile_grid = tile_grid.to_crs("EPSG:28992")

accepted_features = []
rejected_features = []
global_id = 1  # global counter to ensure unique IDs

for tile_id in tqdm(os.listdir(tiles_dir)):
    hulls_path = os.path.join(tiles_dir, tile_id, "segmentation_hulls.geojson")
    if not os.path.exists(hulls_path):
        continue

    if tile_id not in tile_grid.index:
        print(f"[WARN] No tile grid entry for {tile_id}")
        continue
    core_poly = tile_grid.loc[tile_id].geometry

    gdf = gpd.read_file(hulls_path)
    gdf = gdf.to_crs("EPSG:28992")
    gdf["centroid"] = gdf.geometry.centroid

    inside = gdf[gdf["centroid"].within(core_poly)].copy()
    outside = gdf[~gdf["centroid"].within(core_poly)].copy()

    # Accepted
    inside["tree_id"] = range(global_id, global_id + len(inside))
    inside["tile"] = tile_id
    global_id += len(inside)
    accepted_features.append(inside.drop(columns=["centroid"]))

    # Rejected
    if not outside.empty:
        outside["tile"] = tile_id
        rejected_features.append(outside.drop(columns=["centroid"]))

# Export accepted
accepted = gpd.GeoDataFrame(pd.concat(accepted_features, ignore_index=True), crs="EPSG:28992")
accepted.to_file("filtered_renumbered_hulls.geojson", driver="GeoJSON")

# Export rejected
if rejected_features:
    rejected = gpd.GeoDataFrame(pd.concat(rejected_features, ignore_index=True), crs="EPSG:28992")
    rejected.to_file("rejected.geojson", driver="GeoJSON")
