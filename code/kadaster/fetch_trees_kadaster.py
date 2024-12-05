import argparse
import os
from SPARQLWrapper import SPARQLWrapper, CSV


# Set up argument parser
parser = argparse.ArgumentParser(description="Fetch tree data from kadaster API with SPARQL for a specific municipality.")
parser.add_argument("municipality", type=str, help="Name of the municipality (e.g., 'Delft')")

# Parse the arguments
args = parser.parse_args()
municipality_name = args.municipality

# Set up the SPARQL endpoint
sparql = SPARQLWrapper("https://api.labs.kadaster.nl/datasets/bgt/lv/services/bgt/sparql")
sparql.setQuery(f"""
prefix bgt: <https://bgt.basisregistraties.overheid.nl/bgt2/def/>
prefix skos: <http://www.w3.org/2004/02/skos/core#>

select ?boom ?geometry
where {{
  ?boom a bgt:VegetatieObjectRegistratie;
        bgt:plusType bgt:Boom;
        bgt:geometrie ?geometry;
        (bgt:bronhouder/skos:prefLabel) "{municipality_name}"@nl.
}}
""")
sparql.setReturnFormat(CSV)

# Execute the query and fetch results
results = sparql.query().convert()

# Save results to a CSV file
output_filename = f"trees_data_{municipality_name.lower()}.csv"

output_file = os.path.join("data", "kadaster", output_filename)

with open(output_file, "wb") as f:
    f.write(results)

print(f"Data has been exported to {output_file}")
