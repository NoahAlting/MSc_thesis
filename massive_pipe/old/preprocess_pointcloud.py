import numpy as np
import laspy
import os
import open3d as o3d

import logging
from shared_logging import setup_module_logger

logger = None  # only initialized later


def remove_outliers(las_data, nb_neighbors=20, std_ratio=2.0):
    xyz = np.vstack((las_data.x, las_data.y, las_data.z)).transpose()
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    logger.info("Removed outliers using nb_neighbors=%d, std_ratio=%.2f", nb_neighbors, std_ratio)
    return las_data[ind]

def process_point_cloud(data_dir, input_filename, output_filename_xyz, output_filename_laz, thinning_factor=1.0, nb_neighbors=20, std_ratio=2.0):
    global logger
    if logger is None:
        logger = setup_module_logger("1_preprocess", data_dir)

    logger.info("=" * 60 + "Processing point cloud")
    logger.info("[process_point_cloud] Preprocessing function called")
    logger.info("Parameters → input_file: %s | data_dir: %s | thinning: %.2f | neighbors: %d | std_ratio: %.2f",
                input_filename, data_dir, thinning_factor, nb_neighbors, std_ratio)

    input_path = os.path.join(data_dir, input_filename)
    logger.info("Reading LAS file from: %s", input_path)

    with laspy.open(input_path, laz_backend=laspy.LazBackend.Lazrs) as f:
        original_las = f.read()

        if 0 < thinning_factor < 1.0:
            logger.info("Thinning the point cloud with factor %f", thinning_factor)
            step = int(1 / thinning_factor)
            thinned_points = original_las.points[::step]
            logger.info("Original points: %d, Thinned points: %d", len(original_las.points), len(thinned_points))
            original_las.points = thinned_points
        else:
            logger.info("Thinning not applied. Keeping all points.")

        logger.info("Point Attributes:")
        col_width = 25
        for dimension in f.header.point_format.dimension_names:
            dtype = original_las[dimension].dtype
            min_val = original_las[dimension].min()
            max_val = original_las[dimension].max()
            logger.info("%s %s Min: %s Max: %s",
                        dimension.ljust(col_width),
                        str(dtype).ljust(col_width),
                        str(min_val).ljust(col_width),
                        max_val)

    bit8 = 255
    nir_raw = np.array(original_las.nir, dtype=np.float64) / bit8
    red_raw = np.array(original_las.red, dtype=np.float64) / bit8
    green_raw = np.array(original_las.green, dtype=np.float64) / bit8
    blue_raw = np.array(original_las.blue, dtype=np.float64) / bit8

    def get_ndvi(red, nir): return (nir - red) / (nir + red + 1e-8)
    def get_norm_g(r, g, b): return g / (r + g + b)
    def get_mtvi2(nir, red, green): return 1.5 * (1.2 * (nir - green) - 2.5 * (red - green)) / np.sqrt((2 * nir + 1)**2 - (6 * nir - 5 * np.sqrt(red) - 0.5))

    if 'ndvi' not in original_las.point_format.dimension_names:
        original_las.add_extra_dim(laspy.ExtraBytesParams(name='ndvi', type=np.float32))
    original_las.ndvi = get_ndvi(red_raw, nir_raw)
    logger.info("Calculated NDVI.")

    if 'norm_g' not in original_las.point_format.dimension_names:
        original_las.add_extra_dim(laspy.ExtraBytesParams(name='norm_g', type=np.float32))
    original_las.norm_g = get_norm_g(red_raw, green_raw, blue_raw)
    logger.info("Calculated normalized green (norm_g).")

    if 'mtvi2' not in original_las.point_format.dimension_names:
        original_las.add_extra_dim(laspy.ExtraBytesParams(name='mtvi2', type=np.float32))
    original_las.mtvi2 = get_mtvi2(nir_raw, red_raw, green_raw)
    logger.info("Calculated MTVI2.")

    las = laspy.LasData(original_las.header)
    las.points = original_las.points.copy()

    las = las[las.number_of_returns > 1]
    las = las[las.return_number != las.number_of_returns]
    logger.info("Applied filtering based on return numbers.")

    las = remove_outliers(las, nb_neighbors=nb_neighbors, std_ratio=std_ratio)

    output_laz = os.path.join(data_dir, output_filename_laz)
    las.write(output_laz)
    logger.info("LAS file saved to %s", output_laz)

    scale = las.header.scales
    offset = las.header.offsets
    xyz_data_crs = np.vstack((las.X * scale[0] + offset[0],
                              las.Y * scale[1] + offset[1],
                              las.Z * scale[2] + offset[2])).T
    
    # ---------------- Post-filter attribute overview ----------------
    logger.info("Point Attributes AFTER filtering:")
    col_width = 25
    for dim in las.point_format.dimension_names:
        dtype   = las[dim].dtype
        min_val = las[dim].min()
        max_val = las[dim].max()
        logger.info(
            "%s %s Min: %s Max: %s",
            dim.ljust(col_width),
            str(dtype).ljust(col_width),
            str(min_val).ljust(col_width),
            max_val,
        )
    # ----------------------------------------------------------------

    output_xyz_crs = os.path.join(data_dir, output_filename_xyz)
    np.savetxt(output_xyz_crs, xyz_data_crs, fmt="%.6f")
    logger.info("XYZ file saved to %s", output_xyz_crs)
    logger.info("=" * 60 + "Processing complete.")

if __name__ == "__main__":
    data_dir = "whm_250"
    logger = setup_module_logger("1_preprocess", data_dir)

    process_point_cloud(
        data_dir=data_dir,
        input_filename='original.laz',
        output_filename_xyz='forest.xyz',
        output_filename_laz='forest.laz',
        thinning_factor=1.0,
        nb_neighbors=20,
        std_ratio=2.0
    )

