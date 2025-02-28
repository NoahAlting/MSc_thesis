import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from shapely.geometry import Polygon, Point, box
from collections import Counter, defaultdict
import geopandas as gpd
import laspy

# Set warning options
pd.set_option('future.no_silent_downcasting', True)

def load_forest_gdf(laz_file_path):
    """Loads forest from a point cloud file as a GeoDataFrame, applying scale and offset transformations."""
    with laspy.open(laz_file_path) as las:
        points = las.read()
        scale = las.header.scales
        offset = las.header.offsets

        # print(f"LAS Scale:\t{scale}")
        # print(f"LAS Offset:\t{offset}")

        # Convert from scaled integers to real-world coordinates
        X = points.X * scale[0] + offset[0]
        Y = points.Y * scale[1] + offset[1]
        Z = points.Z * scale[2] + offset[2]

        # Construct dataframe with transformed coordinates
        attributes = {dimension.name: getattr(points, dimension.name) for dimension in points.point_format}
        df = pd.DataFrame(attributes)

    # Update transformed coordinates in the dataframe
    df['X'] = X
    df['Y'] = Y
    df['Z'] = Z

    # Drop irrelevant columns
    df = df[[
        'tree_id', 'X', 'Y', 'Z', 'red', 'green', 'blue', 'nir', 'ndvi', 'norm_g', 'mtvi2'
    ]]

    # Create the geometry column
    df['geometry'] = df.apply(lambda row: Point(row['X'], row['Y'], row['Z']), axis=1)
    df.drop(columns=['X', 'Y', 'Z'], inplace=True)

    return gpd.GeoDataFrame(df, geometry='geometry', crs="EPSG:28992")


def load_municipality_geojson(filename):
    """Loads GeoJSON data from a file and returns only the specified columns."""
    gdf = gpd.read_file(filename)
    assert all(gdf.geometry.type == "Point"), "GeoJSON must contain Point geometries"

    # Define the columns to keep
    columns = [
    "OBJECTID", "BOOMSORTIMENT", "geometry" #, "AANLEGJAAR", "HOOGTE", "DIAMETER"
    # "ID", "BORNAME", "ELEMENTNUMMER", "BEHEERGROEP", "BOOMSTATUS", "TAKVRIJE_ZONE", "OMGEVINGSRISICOKLASSEN",  
    # "AMBITIENIVEAU", "STANDPLAATS", "BEHEERDER", "EIGENAAR", "EXTRA_INFORMATIE_2"
    # "EXTRA_INFORMATIE_3", "GROENGEBIEDCODE", "GROENGEBIEDNAAM", "GEMEENTE", "BUURT", "WIJK"
    # "LIGGING", "BEHEEROBJECTSOORT", "BEHEEROBJECTOMSCHRIJVING", "OBJECTID",
    ]

    gdf = gdf[columns]
    # Set datatypes
    gdf["BOOMSORTIMENT"] = gdf["BOOMSORTIMENT"].astype(pd.StringDtype())
    # gdf["HOOGTE"] = gdf["HOOGTE"].astype(pd.StringDtype())

    gdf = gdf.to_crs("EPSG:28992") 
    return gdf


def compute_tree_bounding_boxes(gdf):
    """Computes the bounding box for each tree_id in a GeoDataFrame, excluding unclassified (-1)."""
    gdf = gdf[gdf["tree_id"] != -1]  # Exclude unclassified trees
    bbox_gdf = gdf.groupby("tree_id")["geometry"].apply(lambda geom: box(*geom.total_bounds)).reset_index()
    return gpd.GeoDataFrame(bbox_gdf, geometry="geometry", crs=gdf.crs)


# Path to your LAZ file
laz_file_path = "whm_01_tid.laz"

# Load the forest point cloud
gdf_forest = load_forest_gdf(laz_file_path)

# ---------------------------------------------------
# test for convex hulls

def compute_tree_convex_hulls(gdf):
    """Computes the 2D convex hull for each tree_id in a GeoDataFrame, excluding unclassified (-1)."""
    gdf = gdf[gdf["tree_id"] != -1]  # Exclude unclassified trees
    hull_gdf = gdf.groupby("tree_id")["geometry"].apply(lambda geom: Polygon(geom.unary_union.convex_hull.exterior)).reset_index()
    return gpd.GeoDataFrame(hull_gdf, geometry="geometry", crs=gdf.crs)

hull_gdf = compute_tree_convex_hulls(gdf_forest)

# Export to GeoJSON
hull_gdf.to_file("tree_convex_hulls.geojson", driver="GeoJSON")

# ---------------------------------------------------

# tree_bboxes = compute_tree_bounding_boxes(gdf_forest)
tree_bboxes = hull_gdf

# add centroid column 
tree_bboxes['bbox_centroid'] = tree_bboxes.centroid

# Print results
# print('='*50 + "gdf_forest")
# print(tree_bboxes.info())

# Load municipality data
gdf_municipality = load_municipality_geojson("Bomen_in_beheer_door_gemeente_Delft.geojson")

# Print results
# print('='*50 + "gdf_municipality")
# print(gdf_municipality.info())

# Ensure CRS matches
print("CRS of tree_bboxes:", tree_bboxes.crs)
print("CRS of gdf_municipality:", gdf_municipality.crs)

#align crs (not necessary if CRS is already the same)
gdf_municipality = gdf_municipality.to_crs(tree_bboxes.crs)

# Perform a spatial join: find which municipality trees fall within each tree bounding box
joined_gdf = gpd.sjoin(gdf_municipality, tree_bboxes, how="left", predicate="within")

# Group by tree_id and store matching OBJECTIDs as a list
tree_bboxes["matched_OBJECTIDs"] = tree_bboxes["tree_id"].map(
    joined_gdf.groupby("tree_id")["OBJECTID"].apply(list)
)

# Print results
print('='*50 + "tree_bboxes with matched OBJECTIDs")
print(tree_bboxes.info())
print(tree_bboxes.head(50))


# Ensure OBJECTID is treated as a list and explode it into individual rows
tree_bboxes_exploded = tree_bboxes.explode("matched_OBJECTIDs").rename(columns={"matched_OBJECTIDs": "OBJECTID"})

# Convert OBJECTID to integer to avoid mismatches
# Replace NaN OBJECTIDs with -1 before converting to integer
# tree_bboxes_exploded["OBJECTID"] = tree_bboxes_exploded["OBJECTID"]#.fillna(-1).astype(int) #could be nice to set to -1 if NaN

# Merge with gdf_municipality to get the corresponding geometry (point coordinates)
# Merge and rename geometry columns
tree_bboxes_exploded = tree_bboxes_exploded.merge(
    gdf_municipality[["OBJECTID", "BOOMSORTIMENT", "geometry"]], 
    on="OBJECTID", 
    how="left"
).rename(columns={"geometry_x": "bbox_geometry", "geometry_y": "tree_point"})


# Print results
# print('='*50 + "tree_bboxes_exploded")
# print(tree_bboxes_exploded.info())


# Compute distance between bbox centroid and municipality tree point
tree_bboxes_exploded["distance_to_centroid"] = tree_bboxes_exploded.apply(
    lambda row: row["bbox_centroid"].distance(row["tree_point"]) if row["tree_point"] and not pd.isna(row["tree_point"]) else None,
    axis=1
)
matches = tree_bboxes_exploded[['tree_id', "OBJECTID", 'BOOMSORTIMENT', 'distance_to_centroid']]#.dropna()

# Print results
# print('='*50 + "matches")
# print(matches.head(50))


# ---------------------------------------------------
# Estimate species based on weighted voting
# ---------------------------------------------------

def weighted_voting(matches):
    """Estimates the most likely value for each group based on weighted voting and returns match count, match IDs, and species list."""

    # Convert 'Nader te bepalen' and <NA> to NaN for proper filtering
    # matches["BOOMSORTIMENT"] = matches["BOOMSORTIMENT"].replace({"Nader te bepalen": pd.NA}).astype("string")

    # Drop rows where "BOOMSORTIMENT" is NaN
    # valid_matches = matches.dropna(subset=["distance_to_centroid", "BOOMSORTIMENT"]).copy()

    valid_matches = matches.copy()
    # Compute weights: Inverse of distance (closer matches contribute more)
    valid_matches["weight"] = 1 / valid_matches["distance_to_centroid"]

    # Compute the count of valid rows per tree_id
    counts = valid_matches["tree_id"].value_counts().rename("match_count").astype("int32")

    # Compute weighted votes
    weighted_values = (
        valid_matches.groupby(["tree_id", "BOOMSORTIMENT"])["weight"]
        .sum()
        .reset_index()
    )

    # Find the most weighted species for each tree_id
    estimate_df = weighted_values.loc[
        weighted_values.groupby("tree_id")["weight"].idxmax(), ["tree_id", "BOOMSORTIMENT"]
    ].rename(columns={"BOOMSORTIMENT": "weighted_distance_estimate"})

    # Aggregate OBJECTID and species matches as lists
    aggregated_matches = valid_matches.groupby("tree_id").agg(
        match_ids=("OBJECTID", list),  # List of matched OBJECTID
        match_species=("BOOMSORTIMENT", list)  # List of matched species
    ).reset_index()

    # Merge all computed values into the final result
    result = (
        estimate_df
        .merge(counts, left_on="tree_id", right_index=True, how="left")  # Add match_count
        .merge(aggregated_matches, on="tree_id", how="left")  # Add match_ids & match_species
    )

    return result

# Convert 'Nader te bepalen' to NaN
# matches["BOOMSORTIMENT"] = matches["BOOMSORTIMENT"].replace({"Nader te bepalen": pd.NA}).astype("string")

# df_species = weighted_voting(matches)

# print('='*50 + "df_species")
# print(df_species.info())
# print(df_species.head(50))


# ---------------------------------------------------
# Keep only trees with single match
# ---------------------------------------------------

def filter_unique_single_matches(df, gdf_municipality):
    """
    Filters a DataFrame to keep only rows where the specified object ID column contains exactly one match
    and drops any rows where the same object ID appears more than once.

    Parameters:
        df (pd.DataFrame): Input DataFrame containing object ID lists.

    Returns:
        pd.DataFrame: Filtered DataFrame with unique single-object matches.
    """
    # Ensure NaN values are treated as empty lists
    df = df.copy()  # Avoid modifying the original DataFrame
    df["matched_OBJECTIDs"] = df["matched_OBJECTIDs"].apply(lambda x: x if isinstance(x, list) else [])

    # Keep only rows where there's exactly one match
    single_matches = df[df["matched_OBJECTIDs"].apply(lambda x: len(x) == 1)].copy()

    # Convert matched_OBJECTIDs from list to a scalar value (since they are single-item lists)
    single_matches["matched_OBJECTID"] = single_matches["matched_OBJECTIDs"].str[0]

    # Drop rows where `matched_OBJECTID` appears more than once
    single_matches = single_matches[~single_matches.duplicated(subset=["matched_OBJECTID"], keep=False)]

    # Drop the old list column
    single_matches = single_matches.drop(columns=["matched_OBJECTIDs"])

    # merge single_matches with gdf_municipality to get the 'BOOMSORTIMENT' 

    single_matches = single_matches.merge(
        gdf_municipality[["OBJECTID", "BOOMSORTIMENT"]], 
        left_on="matched_OBJECTID", 
        right_on="OBJECTID", 
        how="left"
    ).drop(columns=["OBJECTID"])

    return single_matches[["tree_id", "matched_OBJECTID", "BOOMSORTIMENT"]] # Return only the relevant columns


def filter_consistent_species_matches(df, gdf_municipality):
    """
    Filters a DataFrame to keep only rows where:
      - A `tree_id` has at least one matched OBJECTID.
      - All matched OBJECTIDs have the exact same BOOMSORTIMENT.
      - Includes a count of how many OBJECTIDs were matched per tree_id.
      - Groups OBJECTIDs into a list per tree_id.

    Parameters:
        df (pd.DataFrame): Input DataFrame containing object ID lists.
        gdf_municipality (gpd.GeoDataFrame): Municipality dataset containing OBJECTID and BOOMSORTIMENT.

    Returns:
        pd.DataFrame: Filtered DataFrame with consistent species matches and match counts.
    """
    # Ensure NaN values are treated as empty lists
    df = df.copy()
    df["matched_OBJECTIDs"] = df["matched_OBJECTIDs"].apply(lambda x: x if isinstance(x, list) else [])

    # Explode the matches to create one row per OBJECTID
    df_exploded = df.explode("matched_OBJECTIDs").rename(columns={"matched_OBJECTIDs": "matched_OBJECTID"})

    # Convert OBJECTID to integer
    df_exploded["matched_OBJECTID"] = df_exploded["matched_OBJECTID"].astype("Int64")

    # Merge to get species information
    df_exploded = df_exploded.merge(
        gdf_municipality[["OBJECTID", "BOOMSORTIMENT"]], 
        left_on="matched_OBJECTID", 
        right_on="OBJECTID", 
        how="left"
    ).drop(columns=["OBJECTID"])

    # Group by tree_id and check if all BOOMSORTIMENT values are the same
    species_counts = df_exploded.groupby("tree_id")["BOOMSORTIMENT"].nunique()

    # Keep only tree_id values where all matched objects have the same species
    consistent_tree_ids = species_counts[species_counts == 1].index

    # Filter the dataset to only keep these consistent tree_ids
    df_filtered = df_exploded[df_exploded["tree_id"].isin(consistent_tree_ids)].copy()

    # Group by tree_id to get:
    # - List of matched OBJECTIDs
    # - Common species (since they are all the same)
    # - Count of matches
    df_grouped = df_filtered.groupby("tree_id").agg(
        match_count=("matched_OBJECTID", "count"),  # Count how many OBJECTIDs matched
        BOOMSORTIMENT=("BOOMSORTIMENT", "first"),  # Since all are the same, take first
        matched_OBJECTIDs=("matched_OBJECTID", list)  # List of matched OBJECTIDs
    ).reset_index()

    return df_grouped

single_matches = filter_consistent_species_matches(tree_bboxes, gdf_municipality)

# # print results
print('='*50 + "single_matches")
print(single_matches.info())
print(single_matches.head(50))
