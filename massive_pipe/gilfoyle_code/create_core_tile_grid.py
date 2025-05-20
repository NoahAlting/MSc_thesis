import os
import sys
import json
import subprocess
import geopandas as gpd
from shapely.geometry import box
import math
from concurrent.futures import ProcessPoolExecutor, as_completed

# --- Config ---
core_width = 1000
core_height = 1250
buffer_m = 25  # each tile has 25m buffer on all sides
crs_epsg = "EPSG:28992"

def process_tile(tile_folder):
    laz_file = os.path.join(tile_folder, "raw.LAZ")
    if not os.path.exists(laz_file):
        return None

    try:
        result = subprocess.run(
            ["pdal", "info", laz_file],
            check=True, capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        bounds = info["stats"]["bbox"]["native"]["bbox"]
        raw_minx = bounds["minx"]
        raw_miny = bounds["miny"]
        tile_id = os.path.basename(tile_folder)

        # Adjust to remove south-west buffer (centered core)
        adjusted_minx = raw_minx + buffer_m
        adjusted_miny = raw_miny + buffer_m

        core_minx = math.floor(adjusted_minx / core_width) * core_width
        core_miny = math.floor(adjusted_miny / core_height) * core_height
        core_maxx = core_minx + core_width
        core_maxy = core_miny + core_height

        geometry = box(core_minx, core_miny, core_maxx, core_maxy)

        return {
            "tile_id": tile_id,
            "core_bbox": [core_minx, core_miny, core_maxx, core_maxy],
            "geometry": geometry
        }

    except Exception as e:
        print(f"Error processing {tile_id}: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_core_tile_grid.py <case_dir> <num_cores>")
        sys.exit(1)

    case_dir = sys.argv[1]
    num_cores = int(sys.argv[2])

    tiles_root = os.path.join(case_dir, "tiles")
    output_geojson = os.path.join(case_dir, "tile_grid_core.geojson")

    tile_folders = [os.path.join(tiles_root, f) for f in os.listdir(tiles_root) if os.path.isdir(os.path.join(tiles_root, f))]
    features = []

    with ProcessPoolExecutor(max_workers=num_cores) as executor:
        futures = {executor.submit(process_tile, tile): os.path.basename(tile) for tile in tile_folders}
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                features.append(result)

    if features:
        gdf = gpd.GeoDataFrame(features, geometry="geometry", crs=crs_epsg)
        gdf.to_file(output_geojson, driver="GeoJSON")
        print(f"✅ Saved {len(gdf)} core tile polygons to {output_geojson}")
    else:
        print("❌ No tile features extracted.")
