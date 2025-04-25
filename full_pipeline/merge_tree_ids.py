import os
import numpy as np
import pandas as pd
import laspy

from shared_logging import setup_module_logger
logger = None  # to be initialized when needed


def merge_tree_ids_into_las(
    data_dir,
    forest_las_name,
    segmentation_xyz,
    output_las_name
    ):
    """
    Merge tree IDs (from segmentation_xyz) into the LAS point cloud (forest_las_name).
    Save the result as a new LAS file (output_las_name).
    """
    global logger
    if logger is None:
        logger = setup_module_logger("3_merge", data_dir)

    logger.info("=" * 60 + "Merging tree IDs into LAS")
    logger.info("Parameters → data_dir: %s | forest_las_name: %s | segmentation_xyz: %s | output_las_name: %s",
                data_dir, forest_las_name, segmentation_xyz, output_las_name)

    logger.info("[merge_tree_ids_into_las] Merger function called")

    # Load LAS point cloud with full attributes
    forest_las_path = os.path.join(data_dir, forest_las_name)
    las = laspy.read(forest_las_path)
    coords_scaled = np.vstack((las.X, las.Y, las.Z)).T
    coords_real = coords_scaled * las.header.scales + las.header.offsets
    logger.info("Loaded LAS file with %d points", len(las.points))

    # Load segmentation result (xyz with tree_id in column 0)
    segmentation_path = os.path.join(data_dir, "segmentation_results", segmentation_xyz)
    seg_df = pd.read_csv(segmentation_path, sep=r"\s+", header=None, names=["tree_id", "x", "y", "z"])
    logger.info("Loaded segmentation file with %d labeled points", len(seg_df))

    # Round coordinates to reduce float noise (optional but helps join)
    precision = 5
    seg_coords = seg_df[["x", "y", "z"]].round(precision)
    las_coords_df = pd.DataFrame(coords_real.round(precision), columns=["x", "y", "z"])
    las_coords_df["tree_id"] = -1  # init tree_id

    # Build index for fast matching
    seg_df["key"] = seg_coords.astype(str).agg("_".join, axis=1)
    las_coords_df["key"] = las_coords_df[["x", "y", "z"]].astype(str).agg("_".join, axis=1)
    tree_id_map = seg_df.set_index("key")["tree_id"].to_dict()
    las_coords_df["tree_id"] = las_coords_df["key"].map(tree_id_map).fillna(-1).astype(np.int32)

    # Log match statistics
    unmatched_count = (las_coords_df["tree_id"] == -1).sum()
    matched_count = (las_coords_df["tree_id"] != -1).sum()
    total_points = len(las_coords_df)
    unmatched_ratio = unmatched_count / total_points
    logger.info("Matched points: %d", matched_count)
    logger.warning("Unmatched points (tree_id = -1): %d", unmatched_count)
    if unmatched_ratio > 0.05:
        logger.warning("⚠️  High unmatched ratio: %.2f%% of points were not assigned a tree_id", unmatched_ratio * 100)

    # Log tree count and top 5 largest trees in table format
    tree_counts = las_coords_df[las_coords_df["tree_id"] != -1]["tree_id"].value_counts()
    logger.info("Number of unique trees: %d", tree_counts.size)
    logger.info("Top 5 largest trees by point count:")
    logger.info("%-10s | %-10s", "Tree ID", "Point Count")
    logger.info("%s", "-" * 23)
    for tree_id, count in tree_counts.head(5).items():
        logger.info("%-10d | %-10d", tree_id, count)

    # Assign tree_id into LAS
    if "tree_id" not in las.point_format.dimension_names:
        las.add_extra_dim(laspy.ExtraBytesParams(name="tree_id", type=np.int32))
    las.tree_id = las_coords_df["tree_id"].to_numpy()

    # Log LAS attribute ranges
    logger.info("Point Attributes:")
    col_width = 25
    for dim in las.point_format.dimension_names:
        arr = las[dim]
        logger.info("%s %s Min: %s Max: %s",
                    dim.ljust(col_width),
                    str(arr.dtype).ljust(col_width),
                    str(arr.min()).ljust(col_width),
                    str(arr.max()))

    # Save modified LAS
    output_path = os.path.join(data_dir, output_las_name)
    las.write(output_path)
    logger.info("Saved LAS with tree_id to: %s", output_path)


if __name__ == "__main__":
    data_dir = "whm_100"
    logger = setup_module_logger("3_merge", data_dir)


    merge_tree_ids_into_las(
        data_dir=data_dir,
        forest_las_name="forest.laz",
        segmentation_xyz="segmentation_0003.xyz",
        output_las_name="forest_tid.laz"
    )