from SPARQLWrapper import SPARQLWrapper, JSON
import geopandas as gpd
from shapely.wkt import loads
from tqdm import tqdm

# Set up the SPARQL endpoint
sparql = SPARQLWrapper("https://api.labs.kadaster.nl/datasets/bgt/lv/services/bgt/sparql")
sparql.setQuery("""
prefix bgt: <https://bgt.basisregistraties.overheid.nl/bgt2/def/>
prefix skos: <http://www.w3.org/2004/02/skos/core#>

select ?boom ?geometry
where {
  ?boom a bgt:VegetatieObjectRegistratie;
        bgt:plusType bgt:Boom;
        bgt:geometrie ?geometry;
        (bgt:bronhouder/skos:prefLabel) "Delft"@nl.
}
""")
sparql.setReturnFormat(JSON)

# Execute query and fetch results
print("Fetching data from the SPARQL endpoint...")
results = sparql.query().convert()
bindings = results["results"]["bindings"]

# Process results into a GeoDataFrame
print("Processing data...")
data = []
for binding in tqdm(bindings, desc="Processing trees", unit="tree", dynamic_ncols=True):
    boom = binding["boom"]["value"]
    geometry = binding["geometry"]["value"]
    # Remove the CRS prefix (everything up to the semicolon)
    if "SRID=" in geometry:
        geometry_wkt = geometry.split(";")[-1]
    else:
        geometry_wkt = geometry
    # Parse geometry
    try:
        parsed_geometry = loads(geometry_wkt)
        data.append({"boom": boom, "geometry": parsed_geometry})
    except Exception as e:
        print(f"Error parsing geometry for {boom}: {e}")

# Create a GeoDataFrame from valid entries
if data:
    gdf = gpd.GeoDataFrame(data, crs="EPSG:28992")  # BGT uses EPSG:28992 (Amersfoort / RD New)
else:
    print("No valid geometries found. Exiting...")
    exit()

# Export to shapefile
output_file = "trees_delft.shp"
print("Saving shapefile...")
gdf.to_file(output_file)

print(f"Shapefile saved as {output_file}")
