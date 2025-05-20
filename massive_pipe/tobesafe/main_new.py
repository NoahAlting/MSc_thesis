import logging
import os
import sys

from shared_logging import setup_logging
from preprocess_pointcloud import process_point_cloud
from hull_segment import run_hull_analysis


# folder definitions
data_dir = 'pointcloud_tiles'
dir_raw = os.path.join(data_dir, 'raw')
dir_clipped = os.path.join(data_dir, 'clipped')
dir_filtered = os.path.join(data_dir, 'filtered')
dir_vegetation = os.path.join(data_dir, 'vegetation')

dbscan_params = {
    'thinning_factor' : 0.5, # 0 is no points, 1 is all
    'nb_neighbors' : 20,
    'std_ratio': 2.0
    }

for filtered_tile in os.listdir(dir_filtered):

    process_point_cloud(
        filename = filtered_tile,
        output_dir = dir_vegetation,
        dbscan_params = dbscan_params
    )