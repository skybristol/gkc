# GKC Utility Modules

GKC provides two main utility modules for working with Wikidata and other knowledge graph systems:

- **SPARQL Query Utilities**: Execute SPARQL queries against Wikidata and other endpoints
- **ShEx Validation Utilities**: Validate RDF data against ShEx schemas

These utilities are independent, reusable components that work both as Python libraries and through the CLI.

---

## SPARQL Query Utilities

The GKC SPARQL module provides utilities for executing SPARQL queries against Wikidata, DBpedia, or any other SPARQL endpoint. It supports multiple input formats (raw queries, Wikidata URLs) and output types (JSON, DataFrames, CSV).

### Features

- **Multiple Input Formats**: Raw SPARQL queries or Wikidata Query Service URLs
- **Multiple Output Types**: JSON objects, Python dictionaries, pandas DataFrames, CSV
- **Error Handling**: Comprehensive error messages and custom exceptions
- **Custom Endpoints**: Query any SPARQL endpoint, not just Wikidata
- **Pandas Integration**: Optional pandas support for data analysis
- **Clean API**: Both class-based and convenience functions

### Installation

The SPARQL module is included in GKC. For optional pandas support:

```bash
pip install pandas
```

### Quick Start

#### Basic Query

```python
from gkc import SPARQLQuery

executor = SPARQLQuery()
results = executor.query("""
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q146 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
    LIMIT 5
""")
print(results)
```

#### Query from Wikidata URL

If you build a query using the [Wikidata Query Service](https://query.wikidata.org/) (WDQS), the URL can be copied and used directly:

```python
url = "https://query.wikidata.org/#SELECT%20?item%20WHERE%20..."
results = executor.query(url)
```

#### Convert to DataFrame

```python
df = executor.to_dataframe("""
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q146 .
      SERVICE wikibase:label {
        bd:serviceParam wikibase:language "en" .
      }
    }
""")
print(df.head())
```

#### Export to CSV

```python
executor.to_csv(query, filepath="results.csv")
```

### Common Usage Patterns

#### One-off Queries

```python
from gkc import execute_sparql, execute_sparql_to_dataframe

# Simple query
results = execute_sparql("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 } LIMIT 10")

# Get DataFrame directly
df = execute_sparql_to_dataframe("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 } LIMIT 10")
```

#### Custom Endpoints

```python
executor = SPARQLQuery(
    endpoint="https://dbpedia.org/sparql",
    user_agent="MyApp/1.0",
    timeout=60
)
results = executor.query("SELECT ?s ?p ?o WHERE { ... }")
```

#### Error Handling

```python
from gkc.sparql import SPARQLError

try:
    results = executor.query("SELECT ?item WHERE { ... }")
except SPARQLError as e:
    print(f"Query failed: {e}")
```

### Common SPARQL Query Patterns

#### Get Items by Type

```sparql
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q5 .  # Instance of human
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
LIMIT 10
```

#### Filter by Property Value

```sparql
SELECT ?item ?itemLabel ?population WHERE {
  ?item wdt:P31 wd:Q515 .        # Instance of city
  ?item wdt:P1082 ?population .   # Has population
  FILTER(?population > 1000000)
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
ORDER BY DESC(?population)
LIMIT 10
```

#### Get Related Items

```sparql
SELECT ?person ?personLabel ?country ?countryLabel WHERE {
  ?person wdt:P27 ?country .      # Country of citizenship
  ?country wdt:P30 wd:Q15 .       # Country in Africa
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}
LIMIT 10
```

### See Also

- **API Reference**: Detailed API documentation at [gkc/api/sparql.md](api/sparql.md)
- **Wikidata Query Service**: [https://query.wikidata.org/](https://query.wikidata.org/)
- **SPARQL Tutorial**: [https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service)

---

## ShEx Validation Utilities

The GKC ShEx module provides validation of RDF data against ShEx (Shape Expression) schemas. It's designed primarily for validating Wikidata entities against EntitySchemas but also supports local files and custom schemas.

### Features

- **Wikidata Integration**: Validate entities against published EntitySchemas
- **Local File Support**: Validate local RDF files against local ShEx schemas
- **Mixed Mode**: Use Wikidata entities with local schemas or vice versa
- **Multiple Input Sources**: QIDs, EIDs, files, or text strings
- **Detailed Error Reporting**: Clear validation error messages
- **CLI & Library**: Available as both Python API and command-line tool

### Installation

ShEx validation is included in GKC with the PyShEx library:

```bash
pip install gkc
```

### Quick Start

#### Validate Wikidata Entity

```python
from gkc import ShexValidator

# Validate Wikidata item against EntitySchema
validator = ShexValidator(qid='Q14708404', eid='E502')
result = validator.check()

if result.is_valid():
    print("✓ Validation passed!")
else:
    print("✗ Validation failed")
    print(result.results)
```

#### Validate Local Files

```python
# Validate local RDF against local schema
validator = ShexValidator(
    rdf_file='entity.ttl',
    schema_file='schema.shex'
)
result = validator.check()
print(f"Valid: {result.is_valid()}")
```

#### Mixed Validation

```python
# Validate Wikidata entity against local schema
validator = ShexValidator(
    qid='Q42',
    schema_file='custom_schema.shex'
)
result = validator.check()
```

### Common Usage Patterns

#### Fluent API Pattern

```python
validator = ShexValidator(qid='Q42', eid='E502')
validator.load_specification()  # Load schema
validator.load_rdf()             # Load RDF data
validator.evaluate()             # Perform validation

if validator.passes_inspection():
    print("Valid!")
```

#### Using Text Strings

```python
# Validate RDF text against schema text
validator = ShexValidator(
    rdf_text=my_rdf_turtle,
    schema_text=my_shex_schema
)
result = validator.check()
```

#### Error Handling

```python
from gkc.shex import ShexValidationError

try:
    validator = ShexValidator(qid='Q42', eid='E502')
    validator.check()
    
    if not validator.is_valid():
        print("Validation failed:")
        for result in validator.results:
            print(f"  - {result.reason}")
            
except ShexValidationError as e:
    print(f"Validation error: {e}")
```

### CLI Usage

The ShEx validator is also available through the GKC command-line interface:

#### Validate Wikidata Entity

```bash
# Basic validation
gkc shex validate --qid Q14708404 --eid E502
```

#### Validate Local Files

```bash
gkc shex validate --rdf-file entity.ttl --schema-file schema.shex
```

#### Mixed Sources

```bash
# Wikidata entity with local schema
gkc shex validate --qid Q14708404 --schema-file custom_schema.shex

# Local RDF with Wikidata EntitySchema
gkc shex validate --rdf-file entity.ttl --eid E502
```

#### Custom User Agent

```bash
gkc shex validate --qid Q42 --eid E502 --user-agent "MyBot/1.0"
```

### Understanding Validation Results

#### Successful Validation

When validation succeeds, `is_valid()` returns `True`:

```python
validator = ShexValidator(qid='Q14708404', eid='E502')
validator.check()

if validator.is_valid():
    print("Entity conforms to schema")
```

#### Failed Validation

When validation fails, inspect the `results` attribute for details:

```python
validator = ShexValidator(qid='Q736809', eid='E502')
validator.check()

if not validator.is_valid():
    for result in validator.results:
        print(f"Error: {result.reason}")
```

Common error patterns:
- `"not in value set"` - Property value doesn't match allowed values
- `"does not match"` - Data type or format mismatch
- `"Constraint violation"` - Cardinality or required property missing

### When to Use ShEx Validation

**Use ShEx validation when you need to:**

- Verify Wikidata items conform to a specific EntitySchema
- Validate data quality before uploading to Wikidata
- Test EntitySchema definitions with sample data
- Ensure consistency across a set of items
- Develop and debug EntitySchemas

**Example: Pre-upload Quality Check**

```python
# Before uploading to Wikidata
validator = ShexValidator(
    rdf_text=generated_turtle_data,
    eid='E502'  # Target EntitySchema
)

if validator.check().is_valid():
    # Safe to upload
    upload_to_wikidata(data)
else:
    # Fix validation errors first
    log_errors(validator.results)
```

### See Also

- **API Reference**: Detailed API documentation at [gkc/api/shex.md](api/shex.md)
- **CLI Reference**: Command-line usage at [gkc/cli/shex.md](cli/shex.md)
- **EntitySchemas on Wikidata**: [https://www.wikidata.org/wiki/Wikidata:WikiProject_Schemas](https://www.wikidata.org/wiki/Wikidata:WikiProject_Schemas)
- **ShEx Specification**: [http://shex.io/](http://shex.io/)

---

## Additional Resources

- **Wikidata Query Service**: [https://query.wikidata.org/](https://query.wikidata.org/)
- **Wikidata EntitySchemas**: [https://www.wikidata.org/wiki/Wikidata:EntitySchema](https://www.wikidata.org/wiki/Wikidata:EntitySchema)
- **GKC GitHub Repository**: [https://github.com/skybristol/gkc](https://github.com/skybristol/gkc)
