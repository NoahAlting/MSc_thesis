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

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_forest_gdf(laz_file_path):
    """Load entire forest LAS/LAZ into a GeoDataFrame (EPSG:28992)."""
    with laspy.open(laz_file_path) as las:
        pts   = las.read()
        scale = las.header.scales
        off   = las.header.offsets
        X = pts.X * scale[0] + off[0]
        Y = pts.Y * scale[1] + off[1]
        Z = pts.Z * scale[2] + off[2]
        attrs = {d.name: np.asarray(getattr(pts, d.name)) for d in pts.point_format}
        df = pd.DataFrame(attrs)
        df["geometry"] = [Point(x, y, z) for x, y, z in zip(X, Y, Z)]
        return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:28992")

def get_bbox_from_las(las_path):
    with laspy.open(las_path) as f:
        mn, mx = f.header.min, f.header.max
    return box(mn[0], mn[1], mx[0], mx[1])

def compute_tree_convex_hulls(gdf, idx=None):
    """Convex hull per tree_id (skip groups with <3 pts)."""
    hulls = []
    for tid, grp in gdf.groupby("tree_id"):
        if len(grp) < 3:
            logger.warning("Iter %s: tree %s < 3 pts, skip", idx, tid)
            continue
        hulls.append({"tree_id": tid, "geometry": unary_union(grp.geometry).convex_hull})
    return gpd.GeoDataFrame(hulls, crs=gdf.crs)

def compute_overlaps_with_H0s(hulls_HX, hulls_H0):
    """Returns: dict of HX_idx : list of overlapping H0 indices"""
    result = {}
    for hx_idx, hx_geom in hulls_HX.geometry.items():
        overlaps = hulls_H0[hulls_H0.geometry.intersects(hx_geom)]
        if not overlaps.empty:
            result[hx_idx] = list(overlaps.index)
    return result

# ---------------------------------------------------------------------------
# Main sweep
# ---------------------------------------------------------------------------

def run_hull_analysis(data_dir, exe, input_xyz, output_dir,
                radius_vals, vres_vals, min_pts_vals, municipality_geojson,
                forest_las_name, csv_name="hull_analysis.csv", cores=4,
                overwrite_existing_combos=False,
                delete_segmentation_after_processing=False,
                save_geojsons=False,
                use_existing_geojsons=False, test=False):

    """Run segmentation parameter sweep in parallel and log per‑iteration stats."""

    # ----------------------- logging / paths -------------------
    global logger
    if logger is None:
        logger = setup_module_logger("hull_analysis", data_dir)
    logger.info("=" * 60 + "Hull Analysis")
    logger.info("[run_hull_analysis] Preprocessing function called")

    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, csv_name)

    # ----------------------- Muni data (static) ----------------------
    muni_gdf = gpd.read_file(municipality_geojson).to_crs("EPSG:28992")
    forest_bbox = get_bbox_from_las(os.path.join(data_dir, forest_las_name))
    public_trees = muni_gdf[muni_gdf.within(forest_bbox)].reset_index(drop=True)

    total_public = len(public_trees)
    total_points = load_forest_gdf(os.path.join(data_dir, forest_las_name)).shape[0]

    logger.info("Public trees inside bbox: %d", total_public)

    combos = list(product(radius_vals, vres_vals, min_pts_vals))

    # ----------------------- CSV init -------------------------
    header = [
        "it_id", "R", "Vres", "minP", "runtime",
        "Pcd_loss", "N_muni", "muni_skip", "N_hulls",
        # "N_est_private", 
        "H0", "H1", "H2", "H3", "H4+", "Hmulti",
        "OS_tree", "OS_tree%", "OS_avg_per_tree"
    ]

    if not os.path.exists(csv_path):
        pd.DataFrame(columns=header).to_csv(csv_path, index=False)

    try:
        df_existing = pd.read_csv(csv_path)
        existing_combos = set(zip(df_existing["R"], df_existing["Vres"], df_existing["minP"]))

    except Exception:
        existing_combos = set()

    # ----------------------- Running a single task-----------------------
    def run_task(args):
        # ------------------ Actual Segmentation ----------------------
        (r, v, m), idx = args

        if not overwrite_existing_combos and (r, v, m) in existing_combos:
            return None

        out_xyz = os.path.join(output_dir, f"segmentation_{idx:04d}.xyz")
        out_geojson = os.path.join(output_dir, f"segmentation_hulls_{idx}.geojson")

        cmd = [exe, os.path.join(data_dir, input_xyz), out_xyz, str(r), str(v), str(m)]

        if not use_existing_geojsons:
            start = time.time()
            try:
                subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                logger.error("Segmentation failed iter %d: %s", idx, e)
                return None
            runtime = time.time() - start
        else:
            runtime = 0.0
            logger.info("Using existing geojson for iteration %d", idx)

            if not os.path.exists(out_geojson):
                logger.error("Existing geojson not found for iteration %d", idx)
                return None


        # ------------------ Unpack xyz to geopandas ---------------------------
        if not use_existing_geojsons:
            seg_df = pd.read_csv(out_xyz, sep=r"\s+", header=None, names=["tree_id", "x", "y", "z"])
            seg_gdf = gpd.GeoDataFrame(seg_df, geometry=gpd.points_from_xy(seg_df.x, seg_df.y), crs="EPSG:28992")
            hulls_gdf = compute_tree_convex_hulls(seg_gdf, idx)
            pointcloud_loss_pct = 100 * (1 - len(seg_df) / total_points)

            if hulls_gdf.empty:
                os.remove(out_xyz)
                return None
        else:
            hulls_gdf = gpd.read_file(out_geojson)
            hulls_gdf = hulls_gdf.to_crs("EPSG:28992")
            hulls_gdf["tree_id"] = hulls_gdf["tree_id"].astype(int)
            pointcloud_loss_pct = np.nan


        # Muni point features --------------------------------
        muni_in_hull = gpd.sjoin(hulls_gdf, public_trees[["geometry"]], predicate="contains", how="left")
        muni_in_hull = muni_in_hull[~muni_in_hull["index_right"].isna()]

        
        # Keep NaNs so we can count hulls with 0 muni points
        points_per_hull = muni_in_hull.groupby(level=0).size()
        points_per_hull = points_per_hull.reindex(hulls_gdf.index, fill_value=0)


        # Muni points not in any hull
        all_muni_idxs = set(public_trees.index)
        matched_muni_idxs = set(muni_in_hull["index_right"].dropna().astype(int))
        
        p_skip = len(all_muni_idxs - matched_muni_idxs)



        # Convex hull features -------------------------------

        # hulls class separation
        H0 = hulls_gdf.loc[points_per_hull[points_per_hull == 0].index]
        H1 = hulls_gdf.loc[points_per_hull[points_per_hull == 1].index]
        H2 = hulls_gdf.loc[points_per_hull[points_per_hull == 2].index]
        H3 = hulls_gdf.loc[points_per_hull[points_per_hull == 3].index]
        H4plus = hulls_gdf.loc[points_per_hull[points_per_hull >= 4].index]

        Hmulti = hulls_gdf.loc[points_per_hull[points_per_hull > 1].index]

        if test:
            # Default to H0 (no muni points inside)
            hulls_gdf["muni_class"] = ""
            hulls_gdf["multi"] = False

            # Set H0 where no muni points are inside
            class_map = {
                "H0": H0.index,
                "H1": H1.index,
                "H2": H2.index,
                "H3": H3.index,
                "H4+": H4plus.index,
            }
            for label, idxs in class_map.items():
                hulls_gdf.loc[idxs, "muni_class"] = label

            # Set multi where more than one muni point is inside
            hulls_gdf.loc[Hmulti.index, "multi"] = True


            # Save labeled GeoJSON
            hulls_gdf.to_file(os.path.join(output_dir, f"test_{idx}.geojson"), driver="GeoJSON")


        # over-segmentation
        
        # hulls with exactly 1 muni point and overlap with empty hulls


        logger.info("-----------------------------------")
        # Compute and log overlaps for each class
        H1H0_intersection = compute_overlaps_with_H0s(H1, H0) # {H1_idx: [H0_idx,...], ...}
        # H2H0_intersection = compute_overlaps_with_H0s(H2, H0)
        # H3H0_intersection = compute_overlaps_with_H0s(H3, H0)
        # H4pH0_intersection = compute_overlaps_with_H0s(H4plus, H0)

        # for dummy_i, infodict in enumerate([H1H0_intersection, H2H0_intersection, H3H0_intersection, H4pH0_intersection]):
        #     logger.info("----------------")
        #     Hx = dummy_i + 1
        #     logger.info("H%d overlaps with H0s", Hx)
        #     for Hx_tid, h0_list in infodict.items():    
        #         logger.info("Tree %s overlaps with trees: %s", Hx_tid, h0_list)

        OS1_tree = len(H1H0_intersection)
        OS1_per_tree_avg = np.mean([len(v) for v in H1H0_intersection.values()])



        # over‑segmentation (hull overlaps)
        # muni_hull_ids = points_per_hull.index
        # muni_hulls    = hulls_gdf.loc[muni_hull_ids]
        # non_muni_hulls = hulls_gdf.drop(muni_hull_ids, errors="ignore")

        # overlap_counts = muni_hulls.geometry.apply(lambda g: non_muni_hulls.geometry.intersects(g).sum())
        # s_over_1 = (overlap_counts > 0).sum()
        # s_over_2 = overlap_counts[overlap_counts > 0].mean() if s_over_1 > 0 else 0

        # private hulls
        # intersects_muni = non_muni_hulls.geometry.apply(lambda g: muni_hulls.geometry.intersects(g).any())
        # contains_point  = non_muni_hulls.geometry.apply(lambda g: public_trees.within(g).any())
        # n_est_private = (~intersects_muni & ~contains_point).sum()

        



        # writing and saving/deleting -----------------------
        result = {
            "it_id": idx,
            "R": r,
            "Vres": v,
            "minP": m,
            "runtime": round(runtime, 2),
            "Pcd_loss": round(pointcloud_loss_pct, 2),
            #-----
            "N_muni": total_public,
            "muni_skip": int(p_skip),
            "N_hulls": len(hulls_gdf),
            # "N_est_private": int(n_est_private),
            #-----
            "# H0": int(len(H0)),
            "# H1": int(len(H1)),
            "# H2": int(len(H2)),
            "# H3": int(len(H3)),
            "# H4+": int(len(H4plus)),
            "# Hmulti": int(len(Hmulti)),
            
            "OS_tree": int(OS1_tree),
            #########!!!!!!!!!!!!!!!!!!!!!!!!!
            "OS_tree%" : float(round(OS1_tree/(total_public-p_skip), 2)), #!!!!!!!!!!!!!!!!!!!!!!   pskp or not?!?!?!
            "OS_avg_per_tree": int(OS1_per_tree_avg)
        }


                # save geojsons if requested
        if save_geojsons:
            hulls_gdf.to_file(os.path.join(output_dir, f"segmentation_hulls_{idx}.geojson"), driver="GeoJSON")

        # clean up .xyz if requested
        if delete_segmentation_after_processing:
            try:
                os.remove(out_xyz)
            except OSError:
                pass

        if overwrite_existing_combos:
            # Remove any existing rows for this parameter combo
            df_existing = pd.read_csv(csv_path)
            mask = (df_existing["R"] == r) & (df_existing["Vres"] == v) & (df_existing["minP"] == m)
            df_existing = df_existing[~mask]
            df_existing.to_csv(csv_path, index=False)  # overwrite cleaned file

        return result

    # ----------------------- run threads ----------------------
    tasks = [((r, v, m), idx) for idx, (r, v, m) in enumerate(combos)]

    if use_existing_geojsons:
        # Run sequentially — simpler, faster for feature-only passes
        for t in tqdm(tasks, desc="Hull Analysis", disable=not sys.stdout.isatty()):
            res = run_task(t)
            if res is not None:
                pd.DataFrame([res]).to_csv(csv_path, mode="a", index=False, header=False)
    else:
        # Run in parallel for segmentation-intensive runs
        with ThreadPoolExecutor(max_workers=cores) as pool:
            futures = [pool.submit(run_task, t) for t in tasks]
            with tqdm(total=len(tasks), desc="Hull Analysis", disable=not sys.stdout.isatty()) as bar:
                for fut in as_completed(futures):
                    res = fut.result()
                    if res is not None:
                        pd.DataFrame([res]).to_csv(csv_path, mode="a", index=False, header=False)
                    bar.update(1)


    logger.info("✅ Hull analysis finished — results written to %s", csv_path)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_hull_analysis(
        data_dir="whm_100",
        exe="./segmentation_code/build/segmentation",
        input_xyz="forest.xyz",
        output_dir="whm_100/segmentation_results",
        radius_vals=[1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5],
        vres_vals=[1, 1.25, 1,5, 1.75, 2, 2.25, 2.5, 2.75, 3],
        min_pts_vals=[1, 2, 3, 4, 5],
        municipality_geojson="Bomen_in_beheer_door_gemeente_Delft.geojson",
        forest_las_name="forest.laz",
        csv_name="hull_analysis.csv",
        cores=16,
        overwrite_existing_combos=True,
        delete_segmentation_after_processing=True,
        save_geojsons=True,
        use_existing_geojsons=True,
        test=True
    )
