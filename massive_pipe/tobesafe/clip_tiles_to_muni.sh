#!/bin/bash

# --------------------------
# Config & Paths
# --------------------------
case_dir="$1"
cores="${2:-8}"

if [[ -z "$case_dir" || ! -d "$case_dir/tiles" ]]; then
    echo "Usage: ./clip_tiles.sh <case_dir> [cores]"
    echo "Example: ./clip_tiles.sh delft 20"
    exit 1
fi

TILES_DIR="$case_dir/tiles"
TMP_DIR="$case_dir/tmp_pipelines"
WKT_FILE="$case_dir/bbox_delft_muni.wkt"

# --------------------------
# Load and clean WKT polygon
# --------------------------
if [[ ! -f "$WKT_FILE" ]]; then
    echo "❌ WKT file not found: $WKT_FILE"
    exit 1
fi

WKT_POLYGON=$(tr -d '\n' < "$WKT_FILE" | sed 's/\"//g')

mkdir -p "$TMP_DIR"
export WKT_POLYGON
export TMP_DIR

# --------------------------
# Clip single tile
# --------------------------
process_tile_folder() {
    local tile_path="$1"
    local raw_file="$tile_path/raw.LAZ"
    local clipped_file="$tile_path/clipped.LAZ"
    local tmp_pipeline="$TMP_DIR/$(basename "$tile_path").json"

    if [[ ! -f "$raw_file" ]]; then
        echo "❌ Skipping $tile_path: raw.LAZ not found"
        return
    fi

    # Build inline JSON pipeline
    cat > "$tmp_pipeline" <<EOF
{
  "pipeline": [
    "$raw_file",
    {
      "type": "filters.crop",
      "polygon": "$WKT_POLYGON"
    },
    {
      "type": "writers.las",
      "filename": "$clipped_file",
      "compression": true,
      "minor_version": 4,
      "dataformat_id": 8
    }
  ]
}
EOF

    # echo "🟦 Clipping $(basename "$tile_path")..." >&2
    pdal pipeline "$tmp_pipeline"
}

export -f process_tile_folder

# --------------------------
# Parallel processing
# --------------------------
find "$TILES_DIR" -mindepth 1 -maxdepth 1 -type d | \
    parallel --bar -j "$cores" process_tile_folder {}

# --------------------------
# Cleanup
# --------------------------
rm -r "$TMP_DIR"
echo "✅ All tiles clipped."
