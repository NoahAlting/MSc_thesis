import geopandas as gpd
from shapely.geometry import Point

# Load data
polygons = gpd.read_file("filtered_renumbered_hulls.geojson")
points = gpd.read_file("Bomen_light.geojson")

# Ensure same CRS
points = points.to_crs(polygons.crs)

# Track matches
point_to_polygons = {}  # point index -> list of polygon indices

# Spatial index for speed
sindex = polygons.sindex

for idx_point, point_geom in points.geometry.items():
    possible_matches_index = list(sindex.intersection(point_geom.bounds))
    for idx_poly in possible_matches_index:
        if polygons.geometry[idx_poly].contains(point_geom):
            point_to_polygons.setdefault(idx_point, []).append(idx_poly)

# Initialize label column
polygons["label"] = "H0"

# Count points per polygon
from collections import defaultdict
polygon_counts = defaultdict(int)

for point_idx, poly_list in point_to_polygons.items():
    if len(poly_list) > 1:
        for pid in poly_list:
            polygons.at[pid, "label"] = "Hpartial"
    else:
        polygon_counts[poly_list[0]] += 1

# Apply non-overlapping counts
for pid, count in polygon_counts.items():
    if polygons.at[pid, "label"] != "Hpartial":
        if count == 1:
            polygons.at[pid, "label"] = "H1"
        elif count == 2:
            polygons.at[pid, "label"] = "H2"
        elif count == 3:
            polygons.at[pid, "label"] = "H3"
        elif count >= 4:
            polygons.at[pid, "label"] = "H4+"

# Save to file
polygons.to_file("hulls_with_labels.geojson", driver="GeoJSON")


# Create new column for species
polygons["species"] = None

# Assign species to H1 polygons
for point_idx, poly_list in point_to_polygons.items():
    if len(poly_list) == 1:
        pid = poly_list[0]
        if polygons.at[pid, "label"] == "H1":
            species = points.at[point_idx, "BOOMSORTIMENT"]
            polygons.at[pid, "species"] = species

# Filter H1 polygons
h1_polygons = polygons[polygons["label"] == "H1"]




# Save to new GeoJSON
h1_polygons.to_file("hulls_H1_with_species.geojson", driver="GeoJSON")
h1_polygons["species"].value_counts().to_csv("species_counts_H1.csv")

