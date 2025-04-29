import laspy
import numpy as np
import pandas as pd
import glob
import os
import logging
import io

logger = logging.getLogger(__name__)


def process_forest_data(data_dir, input_las_file_name, clusters_folder_path, output_las_file_name):
    input_las_path = os.path.join(data_dir, input_las_file_name)
    logger.info("Loading forest LAS file from: %s", input_las_path)
    forest_las = laspy.read(input_las_path)
    forest_xyz = np.vstack((forest_las.X, forest_las.Y, forest_las.Z)).T

    columns = ['X', 'Y', 'Z', 'ndvi', 'mtvi2', 'norm_g']
    forest_data = np.column_stack((forest_xyz, forest_las.ndvi, forest_las.mtvi2, forest_las.norm_g))
    forest_df = pd.DataFrame(forest_data, columns=columns)
    forest_df['tree_id'] = -1

    buf = io.StringIO()
    forest_df.info(buf=buf)
    logger.info("Forest DataFrame Info:\n%s", buf.getvalue())
    logger.info("Forest DataFrame Head:\n%s", forest_df.head().to_string())

    for tree_file in glob.glob(os.path.join(clusters_folder_path, "*.xyz")):
        tree_id = int(os.path.basename(tree_file).split('_')[1].split('.')[0])
        tree_xyz = np.loadtxt(tree_file)
        tree_df = pd.DataFrame(tree_xyz, columns=['X', 'Y', 'Z'])
        tree_df['tree_id'] = tree_id

        forest_df = forest_df.merge(tree_df, on=['X', 'Y', 'Z'], how='left', suffixes=('', '_tree'))
        if 'tree_id_tree' in forest_df.columns:
            forest_df['tree_id'] = forest_df['tree_id_tree'].fillna(forest_df['tree_id'])
            forest_df.drop(columns=['tree_id_tree'], inplace=True)

        if tree_id == 1:
            buf = io.StringIO()
            tree_df.info(buf=buf)
            logger.info("Tree 1 DataFrame Info:\n%s", buf.getvalue())
            logger.info("Tree 1 DataFrame Head:\n%s", tree_df.head().to_string())

    scale = forest_las.header.scales
    offset = forest_las.header.offsets
    forest_df[['X', 'Y', 'Z']] = forest_df[['X', 'Y', 'Z']] * scale + offset
    forest_df['tree_id'] = forest_df['tree_id'].astype(np.int32)

    logger.info("Final Forest DataFrame Info:")
    buf = io.StringIO()
    forest_df.info(buf=buf)
    logger.info("\n%s", buf.getvalue())
    logger.info("Final Forest DataFrame Head:\n%s", forest_df.head().to_string())

    tree_id_array = forest_df['tree_id'].to_numpy(dtype=np.int32)
    forest_las.add_extra_dim(
        laspy.ExtraBytesParams(name="tree_id", type=np.int32, description="Tree ID Assignment")
    )
    forest_las.tree_id = tree_id_array

    output_las_path = os.path.join(data_dir, output_las_file_name)
    forest_las.write(output_las_path)
    logger.info("Modified LAS file saved at: %s", output_las_path)



if __name__ == "__main__":
    from shared_logging import setup_logging
    
    data_dir = "delft_250"
       
    log_file = os.path.join(data_dir, "linkxyz.log")
    setup_logging(log_file)
    logger.info("Link xyz script started separately.")


    input_las_file_name = "forest.laz"
    clusters_folder_path = os.path.join(data_dir, "clusters")
    output_las_file_name = "forest_tid.laz"

    process_forest_data(data_dir, input_las_filename, clusters_folder_path, output_las_file_name)

    logger.info("Link xyz script finished.")
