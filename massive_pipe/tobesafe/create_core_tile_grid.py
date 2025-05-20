import os
import json
import subprocess
from pathlib import Path
import geopandas as gpd
from shapely.geometry import box
import math
from concurrent.futures import ProcessPoolExecutor, as_completed

# --- Config ---
tiles_root = Path("tiles")
output_geojson = "tile_grid_core.geojson"
core_width = 1000
core_height = 1250
buffer_m = 25  # each tile has 25m buffer on all sides
crs_epsg = "EPSG:28992"
max_workers = os.cpu_count() or 8

def process_tile(tile_folder: Path):
    laz_file = tile_folder / "raw.LAZ"
    if not laz_file.exists():
        return None

    try:
        result = subprocess.run(
            ["pdal", "info", str(laz_file)],
            check=True, capture_output=True, text=True
        )
        info = json.loads(result.stdout)
        bounds = info["stats"]["bbox"]["native"]["bbox"]
        raw_minx = bounds["minx"]
        raw_miny = bounds["miny"]
        tile_id = tile_folder.name

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
        print(f"Error processing {tile_folder.name}: {e}")
        return None

if __name__ == "__main__":
    tile_folders = [f for f in tiles_root.iterdir() if f.is_dir()]
    features = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_tile, tile): tile.name for tile in tile_folders}
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
