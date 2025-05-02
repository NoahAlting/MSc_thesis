import os
import sys
import subprocess
import time
from itertools import product
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import laspy
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box
from shapely.ops import unary_union
from tqdm import tqdm

from shared_logging import setup_module_logger

logger = None
# --------------------------------------------------------------------- helpers
def load_forest_gdf(laz_file_path):
    with laspy.open(laz_file_path) as las:
        pts   = las.read()
        scale = las.header.scales
        off   = las.header.offsets

        X = pts.X * scale[0] + off[0]
        Y = pts.Y * scale[1] + off[1]
        Z = pts.Z * scale[2] + off[2]

        attrs = {d.name: np.asarray(getattr(pts, d.name)) for d in pts.point_format}
        df    = pd.DataFrame(attrs)
        df["geometry"] = [Point(x, y, z) for x, y, z in zip(X, Y, Z)]
        return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:28992")


def get_bbox_from_las(las_path):
    with laspy.open(las_path) as f:
        mn, mx = f.header.min, f.header.max
    return box(mn[0], mn[1], mx[0], mx[1])


def compute_tree_convex_hulls(gdf, idx=None):
    hulls = []
    for tid, grp in gdf.groupby("tree_id"):
        if len(grp) < 3:
            logger.warning("Iter %s: tree %s < 3 pts, skip", idx, tid)
            continue
        hulls.append({"tree_id": tid, "geometry": unary_union(grp.geometry).convex_hull})
    return gpd.GeoDataFrame(hulls, crs=gdf.crs)
# --------------------------------------------------------------------- main
def run_segmentation_public_matching(
    data_dir,
    exe,
    input_xyz,
    output_dir,
    radius_vals,
    vres_vals,
    min_pts_vals,
    municipality_geojson,
    forest_las_name,
    csv_name,
    cores=4,
    overwrite_existing_combos=False,
    delete_segmentation_after_processing=False,
):
    global logger
    if logger is None:
        logger = setup_module_logger("segmentation_public_match", data_dir)

    logger.info("🔰  Public-tree matching sweep started")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, csv_name)

    # ------------------------------------------------------------------ data
    muni_gdf = gpd.read_file(municipality_geojson).to_crs("EPSG:28992")
    forest_bbox = get_bbox_from_las(os.path.join(data_dir, forest_las_name))
    public_trees_gdf = muni_gdf[muni_gdf.within(forest_bbox)].reset_index(drop=True)
    total_public = len(public_trees_gdf)
    logger.info("Public trees inside bbox: %d", total_public)

    combos = list(product(radius_vals, vres_vals, min_pts_vals))

    # ---------------------------------------------------------------- CSV init
    if os.path.exists(csv_path):
        df_master = pd.read_csv(csv_path)
    else:
        header = [
            "iteration_id", "Runtime (s)", "Radius", "Vres", "MinP",
            "N_points", "N_hulls", "N_trees",
            "0_hulls (%)", "1_hull (%)", "2_hull (%)", "3_hull (%)", "4+_hull (%)",
            "1_to_1_matches (%)",
        ]
        df_master = pd.DataFrame(columns=header)
        df_master.to_csv(csv_path, index=False)

    existing_combos = set(zip(df_master["Radius"],
                              df_master["Vres"],
                              df_master["MinP"]))

    # ------------------------------------------------------------- task runner
    def run_segmentation_task(args):
        (r, v, m), idx = args
        if not overwrite_existing_combos and (r, v, m) in existing_combos:
            logger.info("skip combo R=%.2f Vres=%.2f MinP=%d", r, v, m)
            return None

        out_xyz = os.path.join(output_dir, f"segmentation_{idx:04d}.xyz")
        cmd = [exe, os.path.join(data_dir, input_xyz), out_xyz,
               str(r), str(v), str(m)]

        start = time.time()
        try:
            subprocess.run(cmd, check=True, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            logger.error("Segmentation failed iter %d: %s", idx, e)
            return None
        runtime = time.time() - start

        # ------------------- analyse
        seg_df  = pd.read_csv(out_xyz, sep=r"\s+", header=None,
                              names=["tree_id", "x", "y", "z"])
        seg_gdf = gpd.GeoDataFrame(seg_df,
                                   geometry=gpd.points_from_xy(seg_df.x,
                                                               seg_df.y),
                                   crs="EPSG:28992")

        hulls_gdf = compute_tree_convex_hulls(seg_gdf, idx)
        if hulls_gdf.empty:
            logger.warning("No hulls iter %d", idx)
            return None

        # === one spatial join gives every (tree, hull) pair
        sj = gpd.sjoin(public_trees_gdf[["geometry"]],
                       hulls_gdf[["geometry"]],
                       predicate="within",
                       how="left")

        hulls_per_tree = (sj.groupby(level=0)
                            .size()
                            .reindex(public_trees_gdf.index, fill_value=0))

        zero_pct   = (hulls_per_tree == 0).mean() * 100
        one_pct    = (hulls_per_tree == 1).mean() * 100
        two_pct    = (hulls_per_tree == 2).mean() * 100
        three_pct  = (hulls_per_tree == 3).mean() * 100
        four_pct   = (hulls_per_tree >= 4).mean() * 100

        # ---- 1-to-1 logic  (cannot exceed 100 %)
        trees_per_hull = sj.groupby("index_right").size()
        single_tree_hulls = trees_per_hull[trees_per_hull == 1].index

        tree_to_hull = sj.groupby(level=0)["index_right"].first()
        one_to_one_mask = (hulls_per_tree == 1) & (tree_to_hull.isin(single_tree_hulls))
        one_to_one_pct = one_to_one_mask.mean() * 100  # guaranteed ≤ 100

        logger.info(
            "Iter %d | R=%.2f Vres=%.2f MinP=%d | runtime=%.2fs | 1-to-1=%.1f%%",
            idx, r, v, m, runtime, one_to_one_pct
        )

        if delete_segmentation_after_processing:
            try:
                os.remove(out_xyz)
            except OSError:
                pass

        return {
            "iteration_id": idx,
            "Radius": r,
            "Vres": v,
            "MinP": m,
            "Runtime (s)": runtime,
            "N_points": len(seg_df),
            "N_hulls": len(hulls_gdf),
            "N_trees": total_public,
            "0_hulls (%)": zero_pct,
            "1_hull (%)": one_pct,
            "2_hull (%)": two_pct,
            "3_hull (%)": three_pct,
            "4+_hull (%)": four_pct,
            "1_to_1_matches (%)": one_to_one_pct,
        }

    # ------------------------------------------------------------- run threads
    tasks = [((r, v, m), idx) for idx, (r, v, m) in enumerate(combos)]
    with ThreadPoolExecutor(max_workers=cores) as pool:
        futures = [pool.submit(run_segmentation_task, t) for t in tasks]
        for fut in tqdm(as_completed(futures), total=len(tasks),
                        desc="Public Matching Sweep",
                        disable=not sys.stdout.isatty()):
            res = fut.result()
            if res is None:
                continue

            key = (res["Radius"], res["Vres"], res["MinP"])
            mask = ((df_master["Radius"] == key[0]) &
                    (df_master["Vres"]   == key[1]) &
                    (df_master["MinP"]   == key[2]))
            df_master = df_master[~mask]
            df_master = pd.concat([df_master, pd.DataFrame([res])], ignore_index=True)
            existing_combos.add(key)

            # --- write immediately so progress is not lost
            df_master.to_csv(csv_path, index=False)

    logger.info("✅  Sweep finished – results written to %s", csv_path)
# --------------------------------------------------------------------- runner
if __name__ == "__main__":
    run_segmentation_public_matching(
        data_dir="whm_100_unfiltered",
        exe="./segmentation_code/build/segmentation",
        input_xyz="forest.xyz",
        output_dir="whm_100/segmentation_results",
        radius_vals=[1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10],
        vres_vals=[0.5, 1, 1.5, 2, 2.5, 3],
        min_pts_vals=[1, 2, 3, 4, 5],
        municipality_geojson="Bomen_in_beheer_door_gemeente_Delft.geojson",
        forest_las_name="forest.laz",
        csv_name="segmentation_stats_public.csv",
        cores=8,
        overwrite_existing_combos=False,
        delete_segmentation_after_processing=True,
    )
