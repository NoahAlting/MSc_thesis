import os
import logging
import pandas as pd
import numpy as np
import geopandas as gpd
import laspy
from shapely.geometry import Point, box, Polygon
from shapely.ops import unary_union

from shared_logging import setup_module_logger
logger = None  # to be initialized when needed


#--------------------------------------------------
# LOADERS
#--------------------------------------------------

def load_forest_gdf(laz_file_path):
    with laspy.open(laz_file_path) as las:
        points = las.read()
        scale = las.header.scales
        offset = las.header.offsets

        X = points.X * scale[0] + offset[0]
        Y = points.Y * scale[1] + offset[1]
        Z = points.Z * scale[2] + offset[2]

        attributes = {dim.name: np.array(getattr(points, dim.name)) for dim in points.point_format}
        df = pd.DataFrame(attributes)
        df['X'] = X
        df['Y'] = Y
        df['Z'] = Z

        # df = df[['tree_id', 'X', 'Y', 'Z', 'red', 'green', 'blue', 'nir', 'ndvi', 'norm_g', 'mtvi2']]
        df['geometry'] = df.apply(lambda row: Point(row['X'], row['Y'], row['Z']), axis=1)
        df.drop(columns=['X', 'Y', 'Z'], inplace=True)

        return gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:28992")

def load_municipality_geojson(filename):
    gdf = gpd.read_file(filename)
    assert all(gdf.geometry.type == "Point"), "GeoJSON must contain Point geometries"
    gdf = gdf[["OBJECTID", "BOOMSORTIMENT", "geometry"]]
    gdf["BOOMSORTIMENT"] = gdf["BOOMSORTIMENT"].astype(pd.StringDtype())
    return gdf.to_crs("EPSG:28992")

#--------------------------------------------------
# MATCHING
#--------------------------------------------------

def compute_tree_convex_hulls(gdf):
    gdf = gdf[gdf["tree_id"] != -1]
    hull_gdf = gdf.groupby("tree_id")["geometry"].apply(
        lambda geom: Polygon(unary_union(geom).convex_hull.exterior)
    ).reset_index()
    return gpd.GeoDataFrame(hull_gdf, geometry="geometry", crs=gdf.crs)



def match_species(forest_gdf, muni_gdf):
    global logger
    logger.info("Computing convex hulls for trees")

    hulls = compute_tree_convex_hulls(forest_gdf)
    hulls['bbox_centroid'] = hulls.centroid
    muni_gdf = muni_gdf.to_crs(hulls.crs)

    joined = gpd.sjoin(muni_gdf, hulls, how="left", predicate="within")

    hulls["matched_OBJECTIDs"] = hulls["tree_id"].map(
        joined.groupby("tree_id")["OBJECTID"].apply(list)
    )

    exploded = hulls.explode("matched_OBJECTIDs").rename(columns={"matched_OBJECTIDs": "OBJECTID"})
    exploded = exploded.merge(
        muni_gdf[["OBJECTID", "BOOMSORTIMENT", "geometry"]], on="OBJECTID", how="left"
    ).rename(columns={"geometry_x": "bbox_geometry", "geometry_y": "tree_point"})

    exploded["distance_to_centroid"] = exploded.apply(
        lambda row: row["bbox_centroid"].distance(row["tree_point"])
        if row["tree_point"] and not pd.isna(row["tree_point"]) else None,
        axis=1
    )

    return exploded[["tree_id", "OBJECTID", "BOOMSORTIMENT", "distance_to_centroid"]]

#--------------------------------------------------
# FILTERING
#--------------------------------------------------

def filter_consistent_species_matches(exploded_df, muni_gdf):
    df = exploded_df.copy()
    # df = df.explode("OBJECTID").rename(columns={"OBJECTID": "matched_OBJECTID"})
    df = df.rename(columns={"OBJECTID": "matched_OBJECTID"})
    df["matched_OBJECTID"] = df["matched_OBJECTID"].astype("Int64")

    df = df.merge(
        muni_gdf[["OBJECTID", "BOOMSORTIMENT"]],
        left_on="matched_OBJECTID",
        right_on="OBJECTID",
        how="left",
        suffixes=("", "_muni")  # 👈 prevents BOOMSORTIMENT from being renamed
    )

    species_counts = df.groupby("tree_id")["BOOMSORTIMENT"].nunique()
    consistent_tree_ids = species_counts[species_counts == 1].index

    df_filtered = df[df["tree_id"].isin(consistent_tree_ids)].copy()

    result = df_filtered.groupby("tree_id").agg(
        match_count=("matched_OBJECTID", "count"),
        BOOMSORTIMENT=("BOOMSORTIMENT", "first"),
        matched_OBJECTIDs=("matched_OBJECTID", list)
    ).reset_index()
    return result

#--------------------------------------------------
# PUBLIC FUNCTION
#--------------------------------------------------

def export_tree_hulls(data_dir, laz_name, output_name="tree_convex_hulls.geojson"):
    laz_path = os.path.join(data_dir, laz_name)
    forest_gdf = load_forest_gdf(laz_path)
    hull_gdf = compute_tree_convex_hulls(forest_gdf)
    
    output_path = os.path.join(data_dir, output_name)
    hull_gdf.to_file(output_path, driver="GeoJSON")

    logger.info("Exported %d convex hulls to %s", len(hull_gdf), output_path)


def extract_species_labels(data_dir, laz_name, municipality_geojson, export_tree_hull=False):
    global logger
    if logger is None:
        logger = setup_module_logger("5_species_matching", data_dir)

    logger.info("=" * 60 + "Species Matching")
    logger.info("Parameters → data_dir: %s | laz_name: %s | municipality_geojson: %s",
                data_dir, laz_name, municipality_geojson)

    laz_file = os.path.join(data_dir, laz_name)
    muni_path = municipality_geojson

    logger.info("[extract_species_labels] Starting species match pipeline")
    forest_gdf = load_forest_gdf(laz_file)
    logger.info("Forest point cloud loaded: %d points", len(forest_gdf))

    logger.info("------------------------")
    logger.info("LAS attributes:")
    col_width = 25
    for col in forest_gdf.columns:
        if col != "geometry":
            dtype = forest_gdf[col].dtype
            min_val = forest_gdf[col].min()
            max_val = forest_gdf[col].max()
            logger.info("%s %s Min: %s Max: %s", col.ljust(col_width), str(dtype).ljust(col_width), str(min_val), str(max_val))
    
    logger.info("------------------------")
    muni_gdf = load_municipality_geojson(muni_path)
    logger.info("Municipality GeoJSON loaded: %d records", len(muni_gdf))
    for col in ["OBJECTID", "BOOMSORTIMENT"]:
        dtype = muni_gdf[col].dtype
        unique_vals = muni_gdf[col].nunique()
        logger.info("%s %s Unique values: %d", col.ljust(col_width), str(dtype).ljust(col_width), unique_vals)

    logger.info("------------------------")
    logger.info("Computing convex hulls and matching municipality points")
    matched_df = match_species(forest_gdf, muni_gdf)

    logger.info("Filtering consistent matches")
    consistent_matches = filter_consistent_species_matches(matched_df, muni_gdf)
    logger.info("✓ Filtered %d trees with consistent species matches", len(consistent_matches))

    out_path = os.path.join(data_dir, "species_matches.csv")
    consistent_matches.to_csv(out_path, index=False)
    logger.info("Saved results to %s", out_path)

    if export_tree_hull:
        hull_gdf = compute_tree_convex_hulls(forest_gdf)
        hull_path = os.path.join(data_dir, "tree_convex_hulls.geojson")
        hull_gdf.to_file(hull_path, driver="GeoJSON")
        logger.info("✓ Exported %d convex hulls to %s", len(hull_gdf), hull_path)
    else:
        logger.info("✓ Skipped hull export")

    logger.info("✓ Species extraction completed")

    return out_path, len(consistent_matches)

#--------------------------------------------------
# ENTRY POINT
#--------------------------------------------------

if __name__ == "__main__":
    data_dir = "whm_100"
    laz_name = "forest_tid.laz"
    municipality_geojson = "Bomen_in_beheer_door_gemeente_Delft.geojson"

    logger = setup_module_logger("5_species_matching", data_dir)

    try:
        extract_species_labels(
            data_dir=data_dir,
            laz_name=laz_name,
            municipality_geojson=municipality_geojson,
            export_tree_hull=True
        )
    except Exception as e:
        logger.exception("❌ An error occurred during species extraction")
