# SPARQL Query Utilities for GKC

A comprehensive SPARQL query utility module for the Global Knowledge Commons (GKC) project, providing a clean Pythonic interface for querying Wikidata and other SPARQL endpoints.

## Quick Start

```python
from gkc import SPARQLQuery

# Create executor
executor = SPARQLQuery()

# Execute query
results = executor.query("""
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q146 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
    LIMIT 10
""")

# Convert to DataFrame
df = executor.to_dataframe(query)

# Export to CSV
executor.to_csv(query, filepath="results.csv")
```

## Features

- **Multiple Input Formats**: Raw SPARQL or Wikidata Query Service URLs
- **Multiple Output Formats**: JSON, DataFrames, CSV, Dictionary lists
- **Flexible Configuration**: Custom endpoints, timeouts, user agents
- **Robust Error Handling**: Comprehensive error messages and exception handling
- **Optional Pandas Support**: Works with or without pandas
- **Type Hints**: Full type annotations for IDE support
- **Comprehensive Tests**: 24 test cases with 83% coverage
- **Complete Documentation**: Full API reference and examples

## Installation

The SPARQL module is included in GKC. For optional pandas support:

```bash
pip install pandas
```

## Usage

### Basic Query

```python
from gkc import SPARQLQuery

executor = SPARQLQuery()
results = executor.query("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }")
```

### Query from Wikidata URL

```python
# Share queries as Wikidata URLs
url = "https://query.wikidata.org/#SELECT%20?item%20WHERE%20..."
results = executor.query(url)  # Automatically extracts and executes
```

### Convert to DataFrame

```python
df = executor.to_dataframe(query)
print(df.head())
```

### Export to CSV

```python
executor.to_csv(query, filepath="results.csv")
```

### Custom Endpoints

```python
executor = SPARQLQuery(
    endpoint="https://dbpedia.org/sparql",
    timeout=60
)
```

## API Reference

### Classes

#### `SPARQLQuery`

Main class for executing SPARQL queries.

**Methods:**
- `query(query, format='json', raw=False)` - Execute query
- `to_dict_list(query)` - Convert to list of dicts
- `to_dataframe(query)` - Convert to DataFrame
- `to_csv(query, filepath=None)` - Export to CSV
- `parse_wikidata_query_url(url)` - Extract query from URL (static)
- `normalize_query(query)` - Normalize query string (static)

#### `SPARQLError`

Custom exception for SPARQL query errors.

### Functions

#### `execute_sparql(query, endpoint=..., format='json')`

Quick function to execute a single query.

#### `execute_sparql_to_dataframe(query, endpoint=...)`

Quick function to execute query and return DataFrame.

## Documentation

- [Utilities Guide](../utilities.md) - SPARQL usage patterns and examples
- [Examples](https://github.com/skybristol/gkc/blob/main/examples/sparql_query_example.py)

## Examples

### Example 1: Find Cities with Large Populations

```python
from gkc import SPARQLQuery

executor = SPARQLQuery()

query = """
SELECT ?item ?itemLabel ?population WHERE {
  ?item wdt:P31 wd:Q3624078 .
  ?item wdt:P1082 ?population .
  FILTER(?population > 5000000)
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY DESC(?population)
LIMIT 10
"""

results = executor.to_dict_list(query)
for row in results:
    print(f"{row['itemLabel']}: {row['population']}")
```

### Example 2: Data Analysis with DataFrame

```python
from gkc import execute_sparql_to_dataframe

df = execute_sparql_to_dataframe("""
SELECT ?item ?itemLabel ?population WHERE {
  ?item wdt:P31 wd:Q3624078 .
  ?item wdt:P1082 ?population .
}
""")

# Analyze with pandas
top_10 = df.nlargest(10, 'population')
print(top_10)
```

## Testing

Run tests with:

```bash
pytest tests/test_sparql.py -v
```

**Results:**
- 22 tests passed
- 2 tests skipped (pandas optional)
- 83% code coverage

## Resources

- [Wikidata Query Service](https://query.wikidata.org/)
- [SPARQL Tutorial](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service)
- [Wikidata Properties](https://www.wikidata.org/wiki/Wikidata:List_of_properties)

## License

MIT License - See LICENSE file for details

## Author

GKC Contributors
