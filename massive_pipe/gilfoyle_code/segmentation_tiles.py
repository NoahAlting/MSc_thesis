# segmentation_tiles.py
import os
import subprocess
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPoint
from shared_logging import setup_module_logger

def segment_tile_fixed(
    input_xyz_path: str,
    output_xyz_path: str,
    output_geojson_path: str,
    exe_path: str,
    segmentation_params: dict[str, float]
):
    if not os.path.exists(input_xyz_path):
        print(f"[segment_tile_fixed] Skipping: missing input {input_xyz_path}")
        return

    log_dir = os.path.dirname(input_xyz_path)
    logger = setup_module_logger("segmentation", "logs/segmentation.log")
    logger.info(f"Running segmentation on {input_xyz_path}")

    cmd = [
        exe_path,
        input_xyz_path,
        output_xyz_path,
        str(segmentation_params["radius"]),
        str(segmentation_params["vres"]),
        str(segmentation_params["min_pts"])
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        logger.error("Segmentation failed: %s", e)
        return

    seg_df = pd.read_csv(output_xyz_path, sep=r"\s+", header=None, names=["tid", "x", "y", "z"])
    seg_gdf = gpd.GeoDataFrame(seg_df, geometry=gpd.points_from_xy(seg_df.x, seg_df.y), crs="EPSG:28992")

    hulls = []
    for tid, group in seg_gdf.groupby("tid"):
        if len(group) >= 3:
            hull_geom = MultiPoint(group.geometry.values).convex_hull
            hulls.append({"tid": tid, "geometry": hull_geom})
        else:
            logger.warning("tid %s has fewer than 3 points — skipped", tid)

    hulls_gdf = gpd.GeoDataFrame(hulls, crs="EPSG:28992")
    hulls_gdf.to_file(output_geojson_path, driver="GeoJSON")

    logger.info("Segmentation and hull export complete: %s", output_geojson_path)
