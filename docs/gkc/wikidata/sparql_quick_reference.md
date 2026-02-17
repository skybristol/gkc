# SPARQL Quick Reference

## Installation

The SPARQL module is already part of GKC. Optional pandas support:

```bash
pip install pandas
```

## Import

```python
from gkc import SPARQLQuery, execute_sparql, execute_sparql_to_dataframe, SPARQLError
```

## Basic Usage

### Simple Query

```python
executor = SPARQLQuery()
results = executor.query("""
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q5 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
    LIMIT 10
""")
```

### Convert to Dictionary List

```python
results = executor.to_dict_list(query)
for row in results:
    print(row)
```

### Convert to DataFrame

```python
df = executor.to_dataframe(query)
print(df.head())
```

### Export to CSV

```python
# Get CSV data
csv_data = executor.to_csv(query)

# Save to file
executor.to_csv(query, filepath="results.csv")
```

## Query from Wikidata URL

```python
# Share queries as Wikidata URLs
url = "https://query.wikidata.org/#SELECT%20?item%20WHERE%20..."
results = executor.query(url)

# Extract query from URL
query = SPARQLQuery.parse_wikidata_query_url(url)
```

## Custom Endpoints

```python
executor = SPARQLQuery(
    endpoint="https://custom.sparql.endpoint/query",
    user_agent="MyApp/1.0",
    timeout=60
)
```

## Convenience Functions

```python
# One-off queries
results = execute_sparql("SELECT ?item WHERE { ... }")

# One-off DataFrame queries
df = execute_sparql_to_dataframe("SELECT ?item WHERE { ... }")
```

## Error Handling

```python
from gkc.sparql import SPARQLError

try:
    results = executor.query("SELECT ?item WHERE { ... }")
except SPARQLError as e:
    print(f"Error: {e}")
```

## Common SPARQL Patterns

### Get Items by Type

```sparql
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q5 .
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
LIMIT 10
```

### Filter by Property Value

```sparql
SELECT ?item ?itemLabel ?population WHERE {
  ?item wdt:P31 wd:Q3624078 .
  ?item wdt:P1082 ?population .
  FILTER(?population > 1000000)
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY DESC(?population)
LIMIT 10
```

### Get Related Items

```sparql
SELECT ?subject ?subjectLabel ?object ?objectLabel WHERE {
  ?subject wdt:P27 wd:Q30 .
  ?subject wdt:PROPERTY ?object .
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
LIMIT 10
```

## Common Properties

- `P27` - Country of citizenship
- `P31` - Instance of (type)
- `P131` - Located in
- `P1082` - Population
- `P625` - Coordinates
- `P580` - Start time
- `P582` - End time
- `P585` - Point in time

## Resources

- [Wikidata Query Service](https://query.wikidata.org/)
- [SPARQL Tutorial](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service)
- [Wikidata Properties](https://www.wikidata.org/wiki/Wikidata:List_of_properties)
- [Property Explorer](https://query.wikidata.org/querybuilder/)
