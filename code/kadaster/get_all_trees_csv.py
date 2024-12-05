from SPARQLWrapper import SPARQLWrapper, CSV

# Set up the SPARQL endpoint
sparql = SPARQLWrapper("https://api.labs.kadaster.nl/datasets/bgt/lv/services/bgt/sparql")
sparql.setQuery("""
prefix bgt: <https://bgt.basisregistraties.overheid.nl/bgt2/def/>
prefix skos: <http://www.w3.org/2004/02/skos/core#>

select ?boom ?municipality ?geometry
where {
  ?boom a bgt:VegetatieObjectRegistratie;
        bgt:plusType bgt:Boom;
        bgt:geometrie ?geometry;
        (bgt:bronhouder/skos:prefLabel) ?municipality.
}
""")
sparql.setReturnFormat(CSV)

# Execute the query and fetch results
results = sparql.query().convert()

# Save results to a CSV file
output_file = "all_trees_data.csv"

with open(output_file, "wb") as f:
    f.write(results)

print(f"Data has been exported to {output_file}")
