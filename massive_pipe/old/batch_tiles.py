import logging
import os
import sys

from shared_logging import setup_logging
from preprocess_pointcloud import process_point_cloud
from hull_segment import run_hull_analysis

data_dir = 'pointcloud_tiles'
dir_raw = os.path.join(data_dir, 'raw')
dir_clipped = os.path.join(data_dir, 'clipped')
dir_filtered = os.path.join(data_dir, 'filtered')


