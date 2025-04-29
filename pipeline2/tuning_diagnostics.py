import os
import pandas as pd
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)


def process_xyz_file(file_name, file_path):
    parts = file_name.replace(".xyz", "").split("_")
    radius = int(parts[2])
    vertical_res = int(parts[4])
    min_points = int(parts[6])

    columns = ["tree_id", "x", "y", "z", "red", "green", "blue"]
    data = pd.read_csv(file_path, delimiter=' ', header=None, names=columns)

    num_points = len(data)
    tree_count = data["tree_id"].nunique()

    return file_name, radius, vertical_res, min_points, num_points, tree_count


def create_tuning_csv(data_dir, input_dir, output_csv):
    if os.path.exists(output_csv):
        df = pd.read_csv(output_csv)
        logger.info("%s exists, going to append data!", output_csv)
    else:
        df = pd.DataFrame(columns=["File Name", "Radius", "Vertical Res", "Min Points", "Num Points", "tree_count"])
        logger.info("Creating %s", output_csv)

    for file_name in tqdm(os.listdir(input_dir), desc='Processing segmentation results to csv'):
        if file_name.endswith(".xyz") and "r_" in file_name and "vres_" in file_name and "minp_" in file_name:
            file_path = os.path.join(input_dir, file_name)

            parts = file_name.replace(".xyz", "").split("_")
            radius = int(parts[2])
            vertical_res = int(parts[4])
            min_points = int(parts[6])

            if not df[(df["Radius"] == radius) & (df["Vertical Res"] == vertical_res) & (df["Min Points"] == min_points)].empty:
                logger.info("Duplicate found for R=%d, VRES=%d, MINP=%d — removing %s", radius, vertical_res, min_points, file_name)
                os.remove(file_path)
                continue

            result = process_xyz_file(file_name, file_path)
            df.loc[len(df)] = result

            new_file_name = f"{data_dir}_{len(df)-1:04d}.xyz"
            new_file_path = os.path.join(input_dir, new_file_name)
            os.rename(file_path, new_file_path)
            df.at[len(df) - 1, "File Name"] = new_file_name
            logger.info("Renamed %s to %s", file_name, new_file_name)

    df.to_csv(output_csv, index=False)
    logger.info("Summary saved to %s", output_csv)


if __name__ == "__main__":
    from shared_logging import setup_logging

    data_dir = "whm_100"
    log_file = os.path.join(data_dir, "segmentation_diagnostics.log")
    setup_logging(log_file)
    logger.info("Diagnostics script started standalone.")

    input_dir = os.path.join(data_dir, "segmentation_results")
    output_csv = os.path.join(data_dir, "segmentation_stats.csv")

    create_tuning_csv(data_dir, input_dir, output_csv)

    logger.info("Diagnostics script finished.")
