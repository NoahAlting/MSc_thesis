import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import math
import matplotlib.colors as mcolors
import os
import seaborn as sns



def plot_radius_vs_metrics_line_by_vres(df, minp_filter=1, title="Radius vs Metrics colored by Vres", each_minp=False):
    """
    If each_minp=False: Single plot for selected MinP.
    If each_minp=True: Grid of subplots for all MinP values found in df.
    """

    # Adjust for your CSV column names
    df = df.rename(columns={
        "R": "Radius",
        "minP": "MinP",
        "N_muni": "N_trees"
    })

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
        ax2.set_ylabel("OS_tree (%)", color="white")
        ax2.tick_params(axis="y", colors="white")

        for vres in unique_vres:
            subset = df_minp[df_minp["Vres"] == vres]
            color = cmap(norm(vres))
            ax2.scatter(subset["Radius"], subset["OS_tree%"], marker='x', color=color, alpha=0.9)

        ax1.set_title(f"MinP = {minp}", color="white", fontsize=13)
        legend = ax1.legend(loc="upper right", frameon=False)
        for text in legend.get_texts():
            text.set_color("white")

    for j in range(len(minp_values), len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle(title, color="white", fontsize=18)
    fig.subplots_adjust(right=0.88)
    fig.tight_layout()
    plt.show()




def plot_hx_heatmaps_by_minp(df):
    """
    Plot heatmaps of normalized Hx values (Hx / N_muni) by Radius and Vres for each MinP.
    Each subplot corresponds to one MinP value. Shared colormap, gray background, white axes, and gray text inside cells.
    """
    df = df.rename(columns={"R": "Radius", "minP": "MinP"})

    # Normalized column
    # column = "Hmulti"
    # norm_col = f"{column}_norm"
    # df[norm_col] = df[column] / df["N_muni"]

    # Test equation

    equation = "equation"

    # adjusted match score
    AMS = (df["H1"] - df["H2"] - 2 * df["H3"] - 3 * df["H4+"]) #increasing penalty for increasing underestimation
    AMS_norm = AMS / (df["N_muni"]) # normalize by number of muni trees to be expected

    private_ratio = df["N_muni"] / df["H0"] # public trees / trees with no match #if N_public = N_private, this is 1



    H1H0_percentage = df["OS_tree%"] # amount of H1 trees that have overlap with empty trees in percentage 



    df[equation] = AMS_norm * private_ratio / H1H0_percentage # equation to be plotted
    
    column = equation
    norm_col = equation


    minp_values = sorted(df["MinP"].unique())
    n = len(minp_values)
    n_cols = 2
    n_rows = int(np.ceil(n / n_cols))

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4.5 * n_rows))
    axes = np.array(axes).reshape(-1)
    cmap = "viridis"

    # Global color limits
    vmin = df[norm_col].min()
    vmax = df[norm_col].max()

    for i, minp in enumerate(minp_values):
        ax = axes[i]
        ax.set_facecolor("#606060")
        sub = df[df["MinP"] == minp]

        pivot = sub.pivot_table(index="Vres", columns="Radius", values=norm_col)

        sns.heatmap(
            pivot,
            ax=ax,
            cmap=cmap,
            vmin=vmin,
            vmax=vmax,
            annot=True,
            fmt=".2f",
            annot_kws={"color": "lightgray", "fontsize": 8},
            linewidths=0.5,
            linecolor="white",
            cbar=(i == len(minp_values) - 1)
        )

        ax.set_title(f"{column} / N_muni — MinP = {minp}", color="white")
        ax.set_xlabel("Radius")
        ax.set_ylabel("Vres")
        ax.tick_params(axis="x")
        ax.tick_params(axis="y")

    # Clean up unused axes
    for j in range(len(minp_values), len(axes)):
        fig.delaxes(axes[j])

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
        
    data_dir = "whm_100"
    # Load CSV
    csv_path = os.path.join(data_dir, "hull_analysis.csv")
    df = pd.read_csv(csv_path)

    # plot_radius_vs_metrics_line_by_vres(df, each_minp=True)
    
    # plot_hx_heatmaps_by_minp(df, column="H0")
    plot_hx_heatmaps_by_minp(df)
    # plot_hx_heatmaps_by_minp(df, column="H2")
    # plot_hx_heatmaps_by_minp(df, column="H3")
    # plot_hx_heatmaps_by_minp(df, column="H4+")
