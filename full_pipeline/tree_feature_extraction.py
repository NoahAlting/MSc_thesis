import os
import sys
import laspy
import pandas as pd
import numpy as np
from tqdm import tqdm

from shared_logging import setup_module_logger
logger = None  # to be initialized when needed

from features import (height_features, intensity_features,
                      crown_shape_features, density_features)


def run_feature_extraction_single_thread(data_dir, las_name, feature_funcs):
    global logger
    if logger is None:
        logger = setup_module_logger("4_tree_feature_extraction", data_dir)

    logger.info("=" * 60 + "Tree Feature Extraction")
    logger.info("Parameters → data_dir: %s | las_name: %s", data_dir, las_name)
    
    logger.info("[tree_analysis] Feature extraction started as a single thread")

    las_path = os.path.join(data_dir, las_name)
    logger.info("Reading LAS: %s", las_path)

    las = laspy.read(las_path)
    scale = las.header.scales
    offset = las.header.offsets

    tree_ids = np.unique(las.tree_id)
    tree_ids = tree_ids[tree_ids != -1]

    features = []

    logger.info("Extracting features for %d trees", len(tree_ids))
    for tid in tqdm(tree_ids, desc="processing trees", disable=not sys.stdout.isatty()):
        mask = las.tree_id == tid
        df_tree = pd.DataFrame({
            "x": las.X[mask] * scale[0] + offset[0],
            "y": las.Y[mask] * scale[1] + offset[1],
            "z": las.Z[mask] * scale[2] + offset[2],
            "intensity": np.array(las.intensity[mask]),
            "return_number": np.array(las.return_number[mask]),
            "number_of_returns": np.array(las.number_of_returns[mask]),
            "ndvi": las.ndvi[mask] if hasattr(las, "ndvi") else np.repeat(np.nan, mask.sum()),
            "norm_g": las.norm_g[mask] if hasattr(las, "norm_g") else np.repeat(np.nan, mask.sum()),
            "mtvi2": las.mtvi2[mask] if hasattr(las, "mtvi2") else np.repeat(np.nan, mask.sum())
        })

        row = {"tree_id": tid}
        for func in feature_funcs:
            try:
                result = func(df_tree)
                row.update(result)

                # Log if any feature value is NaN
                for k, v in result.items():
                    if isinstance(v, float) and np.isnan(v):
                        logger.warning("Tree %s → Feature '%s' returned NaN", tid, k)

            except Exception as e:
                logger.error("Tree %s → Feature '%s' raised an error: %s", tid, func.__name__, str(e))
                row[func.__name__] = np.nan

        logger.info("✓ Tree %d features extracted", tid)
        features.append(row)


    df_all = pd.DataFrame(features)

    output_csv = os.path.join(data_dir, "tree_features.csv")
    df_all.to_csv(output_csv, index=False)
    logger.info("Saved features to: %s", output_csv)

    logger.info("✓ Feature extraction completed")
    return len(df_all)


# ---------------------------- Feature Functions ----------------------------

# height_features = [Hmax, Hmed, Hbase, Hmean, Hstd, Hcv, Hkur, Hp25, Hp90, Hfirst_mean]
# intensity_features = [Imax, Imean, Istd, Icv, Ikur, Iske, Ip25, Ip90, Ifirst_mean, IaHmed, IbHmed, IabHmed]
# crown_shape_features = [CWHmed, CWHp75, CWHp90, CL_Hmax, Hmed_CW, Hp75_CW, Hp90_CW, CWHp90_Hmean, CWns_ew, CRR]
# density_features = [Hmean_med, NHmean, NHmed, NHp90, Nfirst, Nlast, N]

if __name__ == "__main__":
    data_dir = "whm_100"
    las_name = "forest_tid.laz"

    logger = setup_module_logger("4_tree_feature_extraction", data_dir)


    run_feature_extraction_single_thread(
        data_dir=data_dir,
        las_name=las_name,
        feature_funcs=height_features + intensity_features + crown_shape_features + density_features
    )




