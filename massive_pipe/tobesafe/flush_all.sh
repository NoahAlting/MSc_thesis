#!/bin/bash

# --------------------------
# Handle input argument
# --------------------------
case_dir="$1"
TILES_DIR="$case_dir/tiles"

if [[ -z "$case_dir" || ! -d "$TILES_DIR" ]]; then
    echo "Usage: ./flush_case.sh <case_dir>"
    echo "Example: ./flush_case.sh delft"
    exit 1
fi

# --------------------------
# Confirmation
# --------------------------
echo "⚠️  This will delete all files in each tile folder under '$TILES_DIR' EXCEPT raw.LAZ"
echo "It will also delete any 'logs/' folders inside each tile."
read -p "Type 'yes' to confirm: " confirm

if [[ "$confirm" != "yes" ]]; then
    echo "❌ Aborted."
    exit 1
fi

# --------------------------
# Flush each tile folder
# --------------------------
for tile_path in "$TILES_DIR"/*; do
    if [[ -d "$tile_path" ]]; then
        echo "🧹 Cleaning $(basename "$tile_path")..."

        # Delete all files except raw.LAZ
        find "$tile_path" -type f ! -name "raw.LAZ" -exec rm -f {} +

        # Delete logs folder if present
        if [[ -d "$tile_path/logs" ]]; then
            rm -r "$tile_path/logs"
        fi
    fi
done

echo "✅ Done. All non-raw files and logs folders have been removed."
