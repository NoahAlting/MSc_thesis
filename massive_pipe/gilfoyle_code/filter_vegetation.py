import os
import sys
import numpy as np
import laspy
import open3d as o3d
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
from shared_logging import setup_module_logger

# --------------------------
# Input arguments
# --------------------------
if len(sys.argv) < 2:
    print("Usage: python filter_tiles_full.py <case_dir> [cores]")
    sys.exit(1)

case_dir = sys.argv[1]
cores = int(sys.argv[2]) if len(sys.argv) > 2 else 8
tiles_dir = os.path.join(case_dir, "tiles")

# --------------------------
# Dimensions to retain
# --------------------------
keep_fields = {
    "X", "Y", "Z",
    "intensity", "return_number", "number_of_returns",
    "classification",
    "red", "green", "blue", "nir"
}

# --------------------------
# Helper Outlier removal
# --------------------------
def remove_outliers(las_data, nb_neighbors=20, std_ratio=2.0):
    xyz = np.vstack((las_data.x, las_data.y, las_data.z)).T
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz)
    _, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    return las_data[ind]

# --------------------------
# Per-tile processing
# --------------------------
def process_tile(input_las: str, output_las: str, output_xyz: str):
    tile_name = os.path.basename(os.path.dirname(input_las))

    if not os.path.exists(input_las):
        print(f"Skipping {tile_name}: clipped.LAZ not found")
        return


    try:
        logger = setup_module_logger("vegetation_filter", "logs/vegetation_filter.log")

        las = laspy.read(input_las)

        # Create filtered header
        header = laspy.LasHeader(point_format=las.header.point_format, version=las.header.version)
        header.scales = las.header.scales
        header.offsets = las.header.offsets
        new_las = laspy.LasData(header)

        # Keep only selected fields
        for dim in keep_fields:
            if hasattr(las, dim):
                setattr(new_las, dim, getattr(las, dim))
            else:
                logger.warning("Missing dimension '%s' in %s", dim, tile_name)

        # Add vegetation indices
        red = np.array(new_las.red, dtype=np.float64) / 255
        nir = np.array(new_las.nir, dtype=np.float64) / 255
        # green = np.array(new_las.green, dtype=np.float64) / 255
        # blue = np.array(new_las.blue, dtype=np.float64) / 255

        def get_ndvi(r, n): return (n - r) / (n + r + 1e-8)
        # def get_norm_g(r, g, b): return g / (r + g + b + 1e-8)
        # def get_mtvi2(n, r, g): return 1.5 * (1.2 * (n - g) - 2.5 * (r - g)) / np.sqrt((2 * n + 1)**2 - (6 * n - 5 * np.sqrt(r) - 0.5))

        new_las.add_extra_dim(laspy.ExtraBytesParams(name="ndvi", type=np.float32))
        new_las.ndvi = get_ndvi(red, nir)

        # new_las.add_extra_dim(laspy.ExtraBytesParams(name="norm_g", type=np.float32))
        # new_las.norm_g = get_norm_g(red, green, blue)

        # new_las.add_extra_dim(laspy.ExtraBytesParams(name="mtvi2", type=np.float32))
        # new_las.mtvi2 = get_mtvi2(nir, red, green)

        # Example filters (customize as needed)
        new_las = new_las[new_las.classification == 1]  # Keep only unclassified points
        new_las = new_las[new_las.ndvi > 0.0]           # NDVI threshold
        # new_las = new_las[new_las.norm_g > 0.36]        # Normalized green threshold
        # new_las = new_las[new_las.mtvi2 > 0.32]         # MTVI2 threshold

        # Return filtering and outlier removal
        new_las = new_las[new_las.number_of_returns > 1]
        new_las = new_las[new_las.return_number != new_las.number_of_returns]
        new_las = remove_outliers(new_las, nb_neighbors=20, std_ratio=2.0)

        # Save LAZ
        new_las.write(output_las)

        # Optional: also write XYZ
        scale = new_las.header.scales
        offset = new_las.header.offsets
        xyz_data = np.vstack((new_las.X * scale[0] + offset[0],
                              new_las.Y * scale[1] + offset[1],
                              new_las.Z * scale[2] + offset[2])).T
        np.savetxt(output_xyz, xyz_data, fmt="%.6f")

        logger.info("Filtered and saved %s", tile_name)

    except Exception as e:
        print(f"Failed {tile_name}: {e}")

# --------------------------
# Run all tiles
# --------------------------
if __name__ == "__main__":
    tile_folders = [f for f in os.listdir(tiles_dir)
                    if os.path.isdir(os.path.join(tiles_dir, f))]

    with ProcessPoolExecutor(max_workers=cores) as executor:
        list(tqdm(executor.map(process_tile, tile_folders), total=len(tile_folders)))

