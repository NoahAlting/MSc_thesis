import os
import sys
import logging
import geopandas as gpd
import pandas as pd
import numpy as np
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from shared_logging import setup_module_logger
from merge_tree_ids import merge_tree_ids_into_las
from species_matching import compute_tree_convex_hulls, load_forest_gdf

logger = None

def process_segmentation_file(args):
    filename, forest_gdf_base, data_dir, segmentation_dir, hull_output_dir = args
    base = os.path.splitext(filename)[0]
    geojson_out = os.path.join(hull_output_dir, f"{base}.geojson")

    if os.path.exists(geojson_out):
        return f"✓ Skipped {filename} (already exists)"

    merge_tree_ids_into_las(
        data_dir=data_dir,
        forest_las_name="forest.laz",
        segmentation_xyz=filename,
        output_las_name=os.path.join("tree_hulls", f"{base}_tid.laz")
    )

    seg_path = os.path.join(segmentation_dir, filename)
    seg_df = pd.read_csv(seg_path, sep=r"\s+", header=None, names=["tree_id", "x", "y", "z"])

    forest_gdf = forest_gdf_base.copy()
    forest_gdf["x"] = forest_gdf.geometry.x
    forest_gdf["y"] = forest_gdf.geometry.y
    forest_gdf["z"] = forest_gdf.geometry.z

    merged_df = pd.merge(forest_gdf, seg_df, on=["x", "y", "z"], how="left")
    merged_df = merged_df[merged_df["tree_id"].notna()].copy()
    merged_df["tree_id"] = merged_df["tree_id"].astype(int)

    merged_gdf = gpd.GeoDataFrame(merged_df, geometry="geometry", crs=forest_gdf.crs)
    hulls_gdf = compute_tree_convex_hulls(merged_gdf)
    hulls_gdf.to_file(geojson_out, driver="GeoJSON")

    return f"✓ Processed {filename} → {geojson_out}"

def filter_segmentation_files(stats_df, forest_point_count, min_trees, max_trees, max_point_loss):
    min_points = (1 - max_point_loss) * forest_point_count
    filtered = stats_df[(stats_df["Num Trees"] >= min_trees) &
                        (stats_df["Num Trees"] <= max_trees) &
                        (stats_df["Num Points"] >= min_points)]
    return filtered

def generate_all_hulls(data_dir, min_trees=15, max_trees=50, max_point_loss=0.1):
    global logger
    logger = setup_module_logger("diagnostic_hulls", data_dir)

    forest_las_path = os.path.join(data_dir, "forest.laz")
    segmentation_dir = os.path.join(data_dir, "segmentation_results")
    hull_output_dir = os.path.join(data_dir, "tree_hulls")
    stats_csv = os.path.join(data_dir, "segmentation_stats.csv")
    os.makedirs(hull_output_dir, exist_ok=True)

    if not os.path.exists(stats_csv):
        logger.error("Segmentation stats CSV not found at %s", stats_csv)
        return

    stats_df = pd.read_csv(stats_csv)
    forest_point_count = pd.read_csv(os.path.join(data_dir, "forest.xyz"), sep=r"\s+", header=None).shape[0]

    valid_rows = filter_segmentation_files(
        stats_df,
        forest_point_count,
        min_trees,
        max_trees,
        max_point_loss
    )
    logger.info("Filtered down to %d valid segmentation results", len(valid_rows))

    valid_files = set(valid_rows["File Name"])
    forest_gdf_base = load_forest_gdf(forest_las_path)

    args = [
        (f, forest_gdf_base, data_dir, segmentation_dir, hull_output_dir)
        for f in valid_files
    ]

    with ThreadPoolExecutor(max_workers=6) as pool:
        for result in tqdm(pool.map(process_segmentation_file, args), total=len(args), desc="Generating tree hulls", disable=not sys.stdout.isatty()):
            logger.info(result)

if __name__ == "__main__":
    data_dir = "whm_100"

    # Parameterize filtering criteria
    min_trees = 15
    max_trees = 30
    max_point_loss = 0.1  # 10% point loss allowed

    generate_all_hulls(data_dir, min_trees, max_trees, max_point_loss)
