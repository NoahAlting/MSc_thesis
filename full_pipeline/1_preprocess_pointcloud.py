import numpy as np
import laspy
import os
import open3d as o3d
import logging

def setup_logging(log_file):
    """Configure logging to write to the specified log file only."""
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    # Set up logging to file only
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file, mode='w')]
    )

def remove_outliers(las_data, nb_neighbors=20, std_ratio=2.0):
    """Remove outliers using Statistical Outlier Removal (SOR)."""
    xyz = np.vstack((las_data.x, las_data.y, las_data.z)).transpose()
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    logging.info("Removed outliers using nb_neighbors=%d, std_ratio=%.2f", nb_neighbors, std_ratio)
    return las_data[ind]

def process_point_cloud(input_filename, data_dir, thinning_factor=1.0, nb_neighbors=20, std_ratio=2.0):
    # Build full input path and log it
    input_path = os.path.join(data_dir, input_filename)
    logging.info("Reading LAS file from: %s", input_path)
    
    # Open and read the LAS file
    with laspy.open(input_path, laz_backend=laspy.LazBackend.Laszip) as f:
        original_las = f.read()

        # Optionally thin the point cloud
        if 0 < thinning_factor < 1.0:
            logging.info("Thinning the point cloud with factor %f", thinning_factor)
            step = int(1 / thinning_factor)
            thinned_points = original_las.points[::step]
            logging.info("Original points: %d, Thinned points: %d", len(original_las.points), len(thinned_points))
            original_las.points = thinned_points
        else:
            logging.info("Thinning not applied. Keeping all points.")

        # Log basic point attribute summary
        logging.info("Point Attributes:")
        col_width = 25
        for dimension in f.header.point_format.dimension_names:
            dtype = original_las[dimension].dtype
            min_val = original_las[dimension].min()
            max_val = original_las[dimension].max()
            logging.info("%s %s Min: %s Max: %s",
                         dimension.ljust(col_width),
                         str(dtype).ljust(col_width),
                         str(min_val).ljust(col_width),
                         max_val)

    # Normalize color bands (assuming 8-bit values)
    bit8 = 255
    nir_raw = np.array(original_las.nir, dtype=np.float64) / bit8
    red_raw = np.array(original_las.red, dtype=np.float64) / bit8
    green_raw = np.array(original_las.green, dtype=np.float64) / bit8
    blue_raw = np.array(original_las.blue, dtype=np.float64) / bit8

    # Functions to calculate vegetation indices
    def get_ndvi(red, nir):
        red = np.array(red, dtype=np.float64)
        nir = np.array(nir, dtype=np.float64)
        return (nir - red) / (nir + red + 1e-8)

    def get_norm_g(red, green, blue):
        red = np.array(red, dtype=np.float64)
        green = np.array(green, dtype=np.float64)
        blue = np.array(blue, dtype=np.float64)
        return green / (red + green + blue)

    def get_mtvi2(nir, red, green):
        nir = np.array(nir, dtype=np.float64)
        red = np.array(red, dtype=np.float64)
        green = np.array(green, dtype=np.float64)
        return 1.5 * (1.2 * (nir - green) - 2.5 * (red - green)) / np.sqrt((2 * nir + 1)**2 - (6 * nir - 5 * np.sqrt(red) - 0.5))

    # Calculate and add vegetation features (NDVI, norm_g, MTVI2)
    if 'ndvi' not in original_las.point_format.dimension_names:
        original_las.add_extra_dim(laspy.ExtraBytesParams(name='ndvi', type=np.float32))
    original_las.ndvi = get_ndvi(red_raw, nir_raw)
    logging.info("Calculated NDVI.")

    if 'norm_g' not in original_las.point_format.dimension_names:
        original_las.add_extra_dim(laspy.ExtraBytesParams(name='norm_g', type=np.float32))
    original_las.norm_g = get_norm_g(red_raw, green_raw, blue_raw)
    logging.info("Calculated normalized green (norm_g).")

    if 'mtvi2' not in original_las.point_format.dimension_names:
        original_las.add_extra_dim(laspy.ExtraBytesParams(name='mtvi2', type=np.float32))
    original_las.mtvi2 = get_mtvi2(nir_raw, red_raw, green_raw)
    logging.info("Calculated MTVI2.")

    # --- Filtering the point cloud ---
    # Create a copy for filtering
    las = laspy.LasData(original_las.header)
    las.points = original_las.points.copy()

    # Example filters (customize as needed)
    # las = las[las.classification == 1]  # Keep only unclassified points
    # las = las[las.ndvi > 0.0]           # NDVI threshold
    # las = las[las.norm_g > 0.36]        # Normalized green threshold
    # las = las[las.mtvi2 > 0.32]         # MTVI2 threshold

    # Remove points with single return and last returns
    las = las[las.number_of_returns > 1]
    las = las[las.return_number != las.number_of_returns]
    logging.info("Applied filtering based on return numbers.")

    # Remove outliers using SOR
    las = remove_outliers(las, nb_neighbors=nb_neighbors, std_ratio=std_ratio)

    # --- Save the processed point cloud ---
    output_laz = os.path.join(data_dir, "forest.laz")
    las.write(output_laz)
    logging.info("LAS file saved to %s", output_laz)

    # Save with correct world coordinates (applying scales and offsets)
    scale = las.header.scales  # [scale_x, scale_y, scale_z]
    offset = las.header.offsets  # [offset_x, offset_y, offset_z]
    xyz_data_crs = np.vstack((las.X * scale[0] + offset[0],
                              las.Y * scale[1] + offset[1],
                              las.Z * scale[2] + offset[2])).T
    output_xyz_crs = os.path.join(data_dir, "forest.xyz")
    np.savetxt(output_xyz_crs, xyz_data_crs, fmt="%.6f")
    logging.info("XYZ file saved to %s", output_xyz_crs)
    logging.info("="* 60 + "Processing complete.")

if __name__ == "__main__":
    # Main configuration: adjust these variables as needed
    data_dir = os.path.join('delft_250')
    input_file = 'whm_250.laz'

    thinning_factor = 1.0      # Set to a value between 0 and 1 to thin the point cloud
    nb_neighbors = 20          # Number of neighbors for outlier removal
    std_ratio = 2.0            # Standard deviation ratio for outlier removal

    # Setup logging to file "preprocess.log" in the data folder
    log_file = os.path.join(data_dir, "preprocess.log")
    setup_logging(log_file)

    process_point_cloud(input_file, data_dir, thinning_factor, nb_neighbors, std_ratio)
