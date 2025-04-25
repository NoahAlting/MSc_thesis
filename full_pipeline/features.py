import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from scipy.spatial import distance_matrix


# ---------------------------- Height Feature Functions ----------------------------


# ------ Height Features ------

def Hmax(tree):
    """Maximum height"""
    return {"Hmax": tree["z"].max()}

def Hmed(tree):
    """Median height"""
    return {"Hmed": tree["z"].median()}

def Hbase(tree):
    """Crown base height (lowest point)"""
    return {"Hbase": tree["z"].min()}

def Hmean(tree):
    """Mean height"""
    return {"Hmean": tree["z"].mean()}

def Hstd(tree):
    """Standard deviation of height"""
    return {"Hstd": tree["z"].std()}

def Hcv(tree):
    """Coefficient of variation of height"""
    mean = tree["z"].mean()
    return {"Hcv": tree["z"].std() / mean if mean != 0 else np.nan}

def Hkur(tree):
    """Kurtosis of height"""
    return {"Hkur": tree["z"].kurtosis()}

def Hp25(tree):
    """25th percentile of height"""
    return {"Hp25": tree["z"].quantile(0.25)}

def Hp90(tree):
    """90th percentile of height"""
    return {"Hp90": tree["z"].quantile(0.90)}


def Hfirst_mean(tree):
    """Mean height of first or single returns"""
    tree["return_number"] = pd.to_numeric(tree["return_number"], errors="coerce")
    tree["number_of_returns"] = pd.to_numeric(tree["number_of_returns"], errors="coerce")

    mask = (tree["return_number"] == 1) | (tree["number_of_returns"] == 1)

    if mask.sum() == 0:
        return {"Hfirst_mean": np.nan}

    return {"Hfirst_mean": tree.loc[mask, "z"].mean()}




# ------ Intensity Features ------

def Imax(tree):
    """Maximum intensity"""
    return {"Imax": tree["intensity"].max()}

def Imean(tree):
    """Mean intensity"""
    return {"Imean": tree["intensity"].mean()}

def Istd(tree):
    """Standard deviation of intensity"""
    return {"Istd": tree["intensity"].std()}

def Icv(tree):
    """Coefficient of variation of intensity"""
    mean = tree["intensity"].mean()
    return {"Icv": tree["intensity"].std() / mean if mean != 0 else np.nan}

def Ikur(tree):
    """Kurtosis of intensity"""
    return {"Ikur": tree["intensity"].kurtosis()}

def Iske(tree):
    """Skewness of intensity"""
    return {"Iske": tree["intensity"].skew()}

def Ip25(tree):
    """25th percentile intensity"""
    return {"Ip25": tree["intensity"].quantile(0.25)}

def Ip90(tree):
    """90th percentile intensity"""
    return {"Ip90": tree["intensity"].quantile(0.90)}

def Ifirst_mean(tree):
    """Mean intensity of first-or-single returns"""
    if "return_number" not in tree.columns or "number_of_returns" not in tree.columns:
        return {"Ifirst_mean": np.nan}
    first_or_single = tree[tree["return_number"] == 1]
    return {"Ifirst_mean": first_or_single["intensity"].mean()}

def IaHmed(tree):
    """Mean intensity above median height"""
    zmed = tree["z"].median()
    return {"IaHmed": tree[tree["z"] > zmed]["intensity"].mean()}

def IbHmed(tree):
    """Mean intensity below median height"""
    zmed = tree["z"].median()
    return {"IbHmed": tree[tree["z"] <= zmed]["intensity"].mean()}

def IabHmed(tree):
    """Ratio of IaHmed to IbHmed"""
    zmed = tree["z"].median()
    above = tree[tree["z"] > zmed]["intensity"].mean()
    below = tree[tree["z"] <= zmed]["intensity"].mean()
    return {"IabHmed": above / below if below != 0 else np.nan}


# ------ Crown Size and Shape Features ------

def crown_width_at_percentile_gdf(tree, height_percentile=50, height_tol=0.5):
    z_target = tree["z"].quantile(height_percentile / 100)
    slice_mask = (tree["z"] >= z_target - height_tol) & (tree["z"] <= z_target + height_tol)
    slice_df = tree.loc[slice_mask, ["x", "y"]]

    if len(slice_df) < 3:
        return np.nan

    gdf = gpd.GeoDataFrame(slice_df, geometry=gpd.points_from_xy(slice_df["x"], slice_df["y"]))
    hull = gdf.unary_union.convex_hull

    # Estimate width as the longest distance between hull boundary points
    if hull.geom_type == "Polygon":
        coords = list(hull.exterior.coords)
        dist_matrix = distance_matrix(coords, coords)
        width = np.max(dist_matrix)
        return width
    else:
        return np.nan

def CWHmed(tree):
    """Crown width at median height"""
    return {"CWHmed": crown_width_at_percentile_gdf(tree, height_percentile=50)}

def CWHp75(tree):
    """Crown width at 75th percentile height"""
    return {"CWHp75": crown_width_at_percentile_gdf(tree, height_percentile=75)}

def CWHp90(tree):
    """Crown width at 90th percentile height"""
    return {"CWHp90": crown_width_at_percentile_gdf(tree, height_percentile=90)}

def CL_Hmax(tree):
    """Ratio of crown length to maximum height"""
    hmax = tree["z"].max()
    hbase = tree["z"].min()
    return {"CL_Hmax": (hmax - hbase) / hmax if hmax != 0 else np.nan}

def Hmed_CW(tree):
    """Crown height to width ratio at median height"""
    hmax = tree["z"].max()
    hbase = tree["z"].min()
    width = crown_width_at_percentile_gdf(tree, 50)
    return {"Hmed_CW": (hmax - hbase) / width if width != 0 else np.nan}

def Hp75_CW(tree):
    """Crown height to width ratio at 75th percentile height"""
    hmax = tree["z"].max()
    hbase = tree["z"].min()
    width = crown_width_at_percentile_gdf(tree, 75)
    return {"Hp75_CW": (hmax - hbase) / width if width != 0 else np.nan}

def Hp90_CW(tree):
    """Crown height to width ratio at 90th percentile height"""
    hmax = tree["z"].max()
    hbase = tree["z"].min()
    width = crown_width_at_percentile_gdf(tree, 90)
    return {"Hp90_CW": (hmax - hbase) / width if width != 0 else np.nan}


def CWHp90_Hmean(tree):
    """Ratio of crown width at 90th percentile height to mean height"""
    hmean = tree["z"].mean()
    width = crown_width_at_percentile_gdf(tree, 90)
    return {"CWHp90_Hmean": width / hmean if hmean != 0 else np.nan}

def CWns_ew(tree):
    """Ratio of North-South crown width to East-West crown width"""
    x_range = tree["x"].max() - tree["x"].min()
    y_range = tree["y"].max() - tree["y"].min()
    return {"CWns_ew": y_range / x_range if x_range != 0 else np.nan}

def CRR(tree):
    """Canopy Relief Ratio: (Hmean - Hbase) / (Hmax - Hbase)"""
    hmax = tree["z"].max()
    hbase = tree["z"].min()
    hmean = tree["z"].mean()
    return {"CRR": (hmean - hbase) / (hmax - hbase) if hmax != hbase else np.nan}


# ------ Crown Porosity and Density Features ------

def Hmean_med(tree):
    """(Hmean - Hmed) / Hmax"""
    hmean = tree["z"].mean()
    hmed = tree["z"].median()
    hmax = tree["z"].max()
    return {"Hmean_med": (hmean - hmed) / hmax if hmax != 0 else np.nan}

def NHmean(tree, height_tol=0.5):
    """Point density at mean height: count / crown width"""
    zmean = tree["z"].mean()
    slice_mask = (tree["z"] >= zmean - height_tol) & (tree["z"] <= zmean + height_tol)
    count = slice_mask.sum()
    width = crown_width_at_percentile_gdf(tree, height_percentile=50)
    
    return {"NHmean": count / width if width != 0 else np.nan}

def NHmed(tree, height_tol=0.5):
    """Point density at median height"""
    zmed = tree["z"].median()
    slice_mask = (tree["z"] >= zmed - height_tol) & (tree["z"] <= zmed + height_tol)
    count = slice_mask.sum()
    width = crown_width_at_percentile_gdf(tree, height_percentile=50)
    return {"NHmed": count / width if width != 0 else np.nan}

def NHp90(tree, height_tol=0.5):
    """Point density at 90th percentile height"""
    zp90 = tree["z"].quantile(0.90)
    slice_mask = (tree["z"] >= zp90 - height_tol) & (tree["z"] <= zp90 + height_tol)
    count = slice_mask.sum()
    width = crown_width_at_percentile_gdf(tree, height_percentile=90)
    return {"NHp90": count / width if width != 0 else np.nan}

def Nfirst(tree):
    """Percentage of first-or-single returns"""
    rn = np.array(tree["return_number"])
    nr = np.array(tree["number_of_returns"])
    total = len(tree)
    if total == 0:
        return {"Nfirst": np.nan}
    first_or_single = np.sum((rn == 1) | (nr == 1))
    return {"Nfirst": first_or_single / total}


def Nlast(tree):
    """Percentage of last returns"""
    rn = np.array(tree["return_number"])
    nr = np.array(tree["number_of_returns"])
    total = len(tree)
    
    if total == 0:
        return {"Nlast": np.nan}
    last = np.sum(rn == nr)
    return {"Nlast": last / total}


def N(tree):
    """Total number of points"""
    return {"N": len(tree)}

# ---------------------------- Feature Functions ----------------------------
# List of feature functions
# to be used in the feature extraction process
height_features = [Hmax, Hmed, Hbase, Hmean, Hstd, Hcv, Hkur, Hp25, Hp90, Hfirst_mean]
intensity_features = [Imax, Imean, Istd, Icv, Ikur, Iske, Ip25, Ip90, Ifirst_mean, IaHmed, IbHmed, IabHmed]
crown_shape_features = [CWHmed, CWHp75, CWHp90, CL_Hmax, Hmed_CW, Hp75_CW, Hp90_CW, CWHp90_Hmean, CWns_ew, CRR]
density_features = [Hmean_med, NHmean, NHmed, NHp90, Nfirst, Nlast, N]