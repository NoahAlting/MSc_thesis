import os
import sys
import laspy
from concurrent.futures import ProcessPoolExecutor

# --------------------------
# Handle input arguments
# --------------------------
if len(sys.argv) < 2:
    print("Usage: python prefilter_tiles.py <case_dir> [cores]")
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
    "red", "green", "blue", "nir"
}

# --------------------------
# Tile processor function
# --------------------------
def process_tile(tile_name):
    tile_path = os.path.join(tiles_dir, tile_name)
    input_file = os.path.join(tile_path, "clipped.LAZ")
    output_file = os.path.join(tile_path, "filtered.LAZ")

    if not os.path.exists(input_file):
        print(f"❌ Skipping {tile_name}: clipped.LAZ not found")
        return

    try:
        las = laspy.read(input_file)

        header = laspy.LasHeader(point_format=las.header.point_format, version=las.header.version)
        header.scales = las.header.scales
        header.offsets = las.header.offsets

        new_las = laspy.LasData(header)

        for dim in keep_fields:
            if hasattr(las, dim):
                setattr(new_las, dim, getattr(las, dim))
            else:
                print(f"⚠️ {tile_name}: Missing {dim}, skipping it.")

        new_las.write(output_file)
        print(f"✅ Filtered: {tile_name}")
    except Exception as e:
        print(f"❌ Failed {tile_name}: {e}")

# --------------------------
# Run in parallel
# --------------------------
if __name__ == "__main__":
    tile_folders = [f for f in os.listdir(tiles_dir)
                    if os.path.isdir(os.path.join(tiles_dir, f))]
    with ProcessPoolExecutor(max_workers=cores) as executor:
        executor.map(process_tile, tile_folders)
