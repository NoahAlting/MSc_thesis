import os
import sys
import subprocess
import numpy as np
import pandas as pd
import geopandas as gpd
import seaborn as sns

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.cm as cm
import matplotlib.colors as mcolors

from tqdm import tqdm
from shapely.geometry import Point
from shapely.ops import unary_union

from shared_logging import setup_module_logger

logger = None


def compute_tree_convex_hulls(gdf, idx=None):
    hulls = []
    for tid, group in gdf.groupby("tree_id"):
        if len(group) < 3:
            logger.warning(f"Iter {idx}: tree {tid} < 3 pts, skipping hull")
            continue
        union = unary_union(group.geometry)
        hulls.append({"tree_id": tid, "geometry": union.convex_hull})
    return gpd.GeoDataFrame(hulls, crs=gdf.crs)


def create_tree_hulls_from_segmentation(data_dir, segmentation_filename):
    global logger
    if logger is None:
        logger = setup_module_logger("diagnostics", data_dir)

    logger.info("[diagnostics] Creating tree hulls from segmentation: %s", segmentation_filename)

    segmentation_path = os.path.join(data_dir, "segmentation_results", segmentation_filename)
    output_dir = os.path.join(data_dir, "tree_hulls")
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(segmentation_path):
        logger.error("Segmentation file not found: %s", segmentation_path)
        return

    try:
        seg_df = pd.read_csv(segmentation_path, sep=r"\s+", header=None, names=["tree_id", "x", "y", "z"])
        seg_gdf = gpd.GeoDataFrame(seg_df, geometry=gpd.points_from_xy(seg_df.x, seg_df.y), crs="EPSG:28992")

        hulls_gdf = compute_tree_convex_hulls(seg_gdf)

        if hulls_gdf.empty:
            logger.warning("No hulls generated for %s", segmentation_filename)
            return

        output_geojson = os.path.join(output_dir, f"{os.path.splitext(segmentation_filename)[0]}.geojson")
        hulls_gdf.to_file(output_geojson, driver="GeoJSON")

        logger.info("✓ Hulls saved to: %s", output_geojson)

    except Exception as e:
        logger.exception("Failed to process segmentation %s: %s", segmentation_filename, str(e))


def create_hull_geojsons_from_df(df_filtered, data_dir, exe_path, input_xyz):
    """
    Re-runs segmentation and creates GeoJSONs for each row in a filtered DataFrame,
    showing progress and expected total runtime.
    """
    global logger
    if logger is None:
        logger = setup_module_logger("diagnostics", data_dir)

    if "Runtime (s)" in df_filtered.columns:
        total_runtime_est = df_filtered["Runtime (s)"].sum()
        logger.info("Estimated total compute time for %d iterations: %.2f s (%.2f min)",
                    len(df_filtered), total_runtime_est, total_runtime_est / 60)

    for _, row in tqdm(df_filtered.iterrows(), total=len(df_filtered), desc="Generating hulls", disable=not sys.stdout.isatty()):
        r, v, m = row["Radius"], row["Vres"], row["MinP"]
        idx = int(row["iteration_id"])
        out_name = f"segmentation_{idx:04d}.xyz"
        out_path = os.path.join(data_dir, "segmentation_results", out_name)

        if not os.path.exists(out_path):
            logger.info("Re-running segmentation for iteration %d", idx)
            cmd = [exe_path, os.path.join(data_dir, input_xyz), out_path, str(r), str(v), str(m)]
            try:
                subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                logger.error("Segmentation failed for iter %d: %s", idx, str(e))
                continue

        create_tree_hulls_from_segmentation(data_dir, out_name)


def create_hull_geojsons_from_ids(iter_ids, df_stats, data_dir, exe_path, input_xyz):
    """
    Re-runs segmentation and creates GeoJSONs for the iterations in *iter_ids*.

    Parameters
    ----------
    iter_ids : list[int] | list[str]
        Desired iteration_id values, e.g. [3, 7, 15].
    df_stats : pd.DataFrame
        DataFrame that contains the columns: iteration_id, Radius, Vres, MinP.
        Typically the full segmentation_stats_public.csv already loaded.
    data_dir : str
        Base folder (where segmentation_results/ lives).
    exe_path : str
        Path to segmentation executable.
    input_xyz : str
        Name of input .xyz file (relative to *data_dir*).
    """
    global logger
    if logger is None:
        logger = setup_module_logger("diagnostics", data_dir)

    # make sure iteration_id is numeric for indexing
    df_stats = df_stats.copy()
    df_stats["iteration_id"] = pd.to_numeric(df_stats["iteration_id"], errors="coerce")

    # sanity check: which requested IDs are present?
    missing = [i for i in iter_ids if i not in df_stats["iteration_id"].values]
    if missing:
        logger.warning("The following iteration IDs are not in the dataframe: %s", missing)

    # loop over valid IDs with tqdm
    rows = df_stats[df_stats["iteration_id"].isin(iter_ids)]
    for _, row in tqdm(
        rows.iterrows(),
        total=len(rows),
        desc="Generating hulls (by ID)",
        disable=not sys.stdout.isatty(),
    ):
        r, v, m = row["Radius"], row["Vres"], row["MinP"]
        idx = int(row["iteration_id"])
        out_name = f"segmentation_{idx:04d}.xyz"
        out_path = os.path.join(data_dir, "segmentation_results", out_name)

        if not os.path.exists(out_path):
            logger.info("Re-running segmentation for iteration %d", idx)
            cmd = [
                exe_path,
                os.path.join(data_dir, input_xyz),
                out_path,
                str(r),
                str(v),
                str(m),
            ]
            try:
                subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except subprocess.CalledProcessError as e:
                logger.error("Segmentation failed for iter %d: %s", idx, e)
                continue

        create_tree_hulls_from_segmentation(data_dir, out_name)


def plot_filtered_statistics(
    df,
    x_column,
    y_columns,
    title="Filtered Segmentation Statistics",
    xlabel=None,
    ylabel="Percentage (%)",
    figsize=(10, 6),
    legend_loc="best"
):
    """
    Plots multiple y-columns against one x-column from a DataFrame.

    Parameters:
        df (pd.DataFrame): Filtered DataFrame to plot from.
        x_column (str): Column to use on x-axis (e.g. 'N_hulls').
        y_columns (list of str): Columns to plot as individual lines.
        title (str): Title of the plot.
        xlabel (str): Optional label for x-axis.
        ylabel (str): Label for y-axis.
        figsize (tuple): Size of the figure.
        legend_loc (str): Legend position.
    """
    if x_column not in df.columns:
        raise ValueError(f"Column '{x_column}' not found in DataFrame.")

    for col in y_columns:
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not found in DataFrame.")

    plt.figure(figsize=figsize)
    df_sorted = df.sort_values(x_column)

    for col in y_columns:
        plt.scatter(df_sorted[x_column], df_sorted[col], marker='o', label=col)

    plt.title(title)
    plt.xlabel(xlabel or x_column)
    plt.ylabel(ylabel)
    plt.grid(True)
    plt.legend(loc=legend_loc)
    plt.tight_layout()
    plt.show()


def plot_parameter_heatmaps(
    df,
    metric_col,
    highlight_col=None,
    highlight_thresh=None,
    title="Effect of Radius and Vres across Min Points",
    cmap="viridis",
):
    """Facet-grid heatmaps of metric_col (Radius × Vres) per MinP.
       Cells whose *highlight_col* ≥ *highlight_thresh* get a red outline."""
    required_cols = ["Radius", "Vres", "MinP", metric_col]
    for c in required_cols:
        if c not in df.columns:
            raise ValueError(f"Missing column {c}")
    if highlight_col and highlight_col not in df.columns:
        raise ValueError(f"Highlight column {highlight_col} not found")

    # ensure highlight column numeric
    if highlight_col:
        df = df.copy()
        df[highlight_col] = pd.to_numeric(df[highlight_col], errors="coerce")

    minp_vals = sorted(df["MinP"].unique())
    n_sub = len(minp_vals)
    n_cols = 2
    n_rows = (n_sub + 1) // n_cols

    pivots_m, pivots_h, all_vals = [], [], []
    for mp in minp_vals:
        sub = df[df["MinP"] == mp]
        piv_m = (sub.pivot_table(index="Vres", columns="Radius",
                                 values=metric_col, aggfunc="mean")
                    .sort_index())
        pivots_m.append(piv_m)
        all_vals.extend(piv_m.values.flatten())

        if highlight_col:
            piv_h = (sub.pivot_table(index="Vres", columns="Radius",
                                     values=highlight_col, aggfunc="mean")
                        .sort_index())
            pivots_h.append(piv_h)

    vmin, vmax = np.nanmin(all_vals), np.nanmax(all_vals)

    fig, axes = plt.subplots(
        n_rows, n_cols, figsize=(7 * n_cols, 6.5 * n_rows), squeeze=False
    )

    for i, (mp, piv_m) in enumerate(zip(minp_vals, pivots_m)):
        ax = axes[i // n_cols][i % n_cols]
        sns.heatmap(
            piv_m,
            annot=True,
            fmt=".0f",
            cmap=cmap,
            cbar=False,
            vmin=vmin,
            vmax=vmax,
            ax=ax,
        )

        # add red rectangle for cells meeting threshold
        if highlight_col and highlight_thresh is not None:
            piv_h = pivots_h[i]
            for y, vres in enumerate(piv_h.index):
                for x, rad in enumerate(piv_h.columns):
                    val = piv_h.loc[vres, rad]
                    if pd.notna(val) and val >= highlight_thresh:
                        ax.add_patch(
                            Rectangle(
                                (x, y), 1, 1,
                                fill=False, edgecolor="red", linewidth=2
                            )
                        )

        ax.set_title(f"MinP = {mp}", fontsize=12)
        ax.set_xlabel("Radius")
        ax.set_ylabel("Vres")

    # shared colour-bar
    cax = fig.add_axes([0.92, 0.25, 0.02, 0.5])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    fig.colorbar(sm, cax=cax, label=metric_col)

    # delete empty axes
    for j in range(n_sub, n_rows * n_cols):
        fig.delaxes(axes[j // n_cols][j % n_cols])

    fig.suptitle(title, fontsize=16, y=1.02)
    fig.tight_layout(rect=[0, 0, 0.9, 0.98], h_pad=1.5, w_pad=2.5)
    plt.show()


def plot_dual_axis_by_params(df, title="Parameter vs N_hulls and 1-to-1 Match Ratio"):
    """
    Plots three subplots:
    - X = Radius, Vres, MinP
    - Y1 (left) = N_hulls (log scale)
    - Y2 (right) = 1_to_1_matches (%)
    Also draws horizontal lines at N_trees and 3*N_trees.
    """
    params = ["Radius", "Vres", "MinP"]
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=False)

    n_trees = df["N_trees"].iloc[0]  # Assumes same across rows

    for i, param in enumerate(params):
        ax1 = axes[i]
        color1 = "tab:blue"
        ax1.set_xlabel(param)
        ax1.set_ylabel("N_hulls (log)", color=color1)
        ax1.set_yscale("log")
        ax1.scatter(df[param], df["N_hulls"], color=color1, label="N_hulls", alpha=0.7)
        ax1.tick_params(axis="y", labelcolor=color1)

        # Add reference lines
        ax1.axhline(n_trees, color="gray", linestyle="dotted", label="N_trees")
        ax1.axhline(3 * n_trees, color="dimgray", linestyle="dotted", label="3 × N_trees")

        ax2 = ax1.twinx()
        color2 = "tab:red"
        ax2.set_ylabel("1-to-1 matches (%)", color=color2)
        ax2.scatter(df[param], df["1_to_1_matches (%)"], color=color2, marker="x", label="1-to-1 (%)", alpha=0.7)
        ax2.tick_params(axis="y", labelcolor=color2)

        ax1.set_title(f"{param} vs N_hulls and 1-to-1 (%)")

    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    plt.show()



def plot_parameter_boxplots(df, metric_col="N_hulls", ratio_col="1_to_1_matches (%)"):
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=False)

    param_cols = ["Radius", "Vres", "MinP"]
    titles = [
        "Radius vs Metrics",
        "Vres vs Metrics",
        "MinP vs Metrics"
    ]

    for i, param in enumerate(param_cols):
        ax = axes[i]
        sns.boxplot(data=df, x=param, y=metric_col, ax=ax, color="skyblue")
        ax.set_ylabel(metric_col, color="blue")
        ax.set_yscale("log")
        ax.set_title(titles[i], fontsize=12)

        ax2 = ax.twinx()
        sns.boxplot(data=df, x=param, y=ratio_col, ax=ax2, color="lightcoral", boxprops=dict(alpha=0.4))
        ax2.set_ylabel(ratio_col, color="red")

    plt.suptitle("Boxplots of N_hulls and 1-to-1 Matches (%) across Parameters", fontsize=16)
    plt.tight_layout()
    plt.show()



import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import math

def plot_radius_vs_metrics_line_by_vres(df, minp_filter=1, title="Radius vs Metrics colored by Vres", each_minp=False):
    """
    If each_minp=False: Single plot for selected MinP.
    If each_minp=True: Grid of subplots for all MinP values found in df.
    """

    minp_values = sorted(df["MinP"].unique()) if each_minp else [minp_filter]
    n = len(minp_values)
    n_cols = 2
    n_rows = math.ceil(n / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(9 * n_cols, 6 * n_rows), facecolor="#606060")
    axes = np.array(axes).reshape(-1)

    for i, minp in enumerate(minp_values):
        ax1 = axes[i]
        ax1.set_facecolor("#606060")
        df_minp = df[df["MinP"] == minp]
        unique_vres = sorted(df_minp["Vres"].unique())

        cmap = plt.get_cmap("viridis", len(unique_vres))
        norm = mcolors.Normalize(vmin=min(unique_vres), vmax=max(unique_vres))

        for vres in unique_vres:
            subset = df_minp[df_minp["Vres"] == vres].sort_values("Radius")
            color = cmap(norm(vres))
            ax1.plot(subset["Radius"], subset["N_hulls"], marker='o', label=f"Vres={vres}", color=color)

        ax1.set_yscale("log")
        ax1.set_xlabel("Radius", color="white")
        ax1.set_ylabel("N_hulls", color="white")
        ax1.tick_params(axis="x", colors="white")
        ax1.tick_params(axis="y", colors="white")
        ax1.set_xticks(sorted(df_minp["Radius"].unique()))

        n_trees = df_minp["N_trees"].iloc[0]
        ax1.axhline(n_trees, color="white", linestyle="--", linewidth=1, label="N_trees")
        ax1.axhline(3 * n_trees, color="white", linestyle="--", linewidth=1.5, label="3 × N_trees")

        # Right axis
        ax2 = ax1.twinx()
        ax2.set_ylabel("1-to-1 matches (%)", color="white")
        ax2.tick_params(axis="y", colors="white")

        for vres in unique_vres:
            subset = df_minp[df_minp["Vres"] == vres]
            color = cmap(norm(vres))
            ax2.scatter(subset["Radius"], subset["1_to_1_matches (%)"], marker='x', color=color, alpha=0.9)

        ax1.set_title(f"MinP = {minp}", color="white", fontsize=13)
        legend = ax1.legend(loc="upper right", frameon=False)
        for text in legend.get_texts():
            text.set_color("white")

    # Remove unused subplots if needed
    for j in range(len(minp_values), len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle(title, color="white", fontsize=18)
    fig.subplots_adjust(right=0.88)
    fig.tight_layout()
    plt.show()



if __name__ == "__main__":
    data_dir = "whm_100"
    exe = "./segmentation_code/build/segmentation"
    csv_path = os.path.join(data_dir, "hull_analysis.csv")
    input_xyz = "forest.xyz"

    df = pd.read_csv(csv_path)

    # Filter results ================================================
    # df_filtered = df[
    #     (df["N_hulls"] > df["N_trees"]) & # At least one hull per public tree
    #     (df["N_hulls"] < 3 * df["N_trees"])]# & # At most 2:1 ratio for private:public trees
    # #     (df["1_hull (%)"] > 90) # At least 90% of public trees have 1 hull
    
    # df_filtered.to_csv(os.path.join(data_dir, "filtered_stats.csv"), index=False)
    # ===============================================================

    # Plot filtered statistics ======================================
    # x_col = "N_hulls"
    # y_cols = ["0_hulls (%)", "1_hull (%)", "2_hull (%)", "3_hull (%)", "4+_hull (%)"]

    # plot_filtered_statistics(
    #     df=df,
    #     x_column=x_col,
    #     y_columns=y_cols,
    #     title="Hull Distribution vs. Number of Hulls",
    #     xlabel="Number of Hulls",
    #     ylabel="Percentage of Public Trees"
    # )
    # ===============================================================

    # create hull geojsons ==========================================

    # choose iterations to export
    # ids_to_export = [318]

    # create_hull_geojsons_from_ids(
    #     iter_ids=ids_to_export,
    #     df_stats=df,
    #     data_dir=data_dir,
    #     exe_path=exe,
    #     input_xyz=input_xyz,
    # )
    # create_hull_geojsons_from_df(df_top3, data_dir, exe, input_xyz)
    # ===============================================================

    # Plot parameter heatmaps ========================================
    highlight_col = "1_to_1_matches (%)"
    highlight_thresh = 78

    # plot_parameter_heatmaps(
    #     df=df_filtered,
    #     metric_col="N_hulls",
    #     highlight_col=highlight_col,
    #     highlight_thresh=highlight_thresh,        
    #     title=f"N_hulls – cells with {highlight_col}≥{highlight_thresh}"
    # )
    # ===============================================================

    # Plot radius dual axis =========================================
    # plot_dual_axis_by_params(df)
    # plot_parameter_boxplots(df)
    # One MinP:
    # plot_radius_vs_metrics_line_by_vres(df, minp_filter=1)

    # All MinP in subplots:
    plot_radius_vs_metrics_line_by_vres(df, each_minp=True)



    
    #================================================================