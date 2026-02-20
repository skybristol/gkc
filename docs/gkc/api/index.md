# API Reference

## Overview

The GKC library is organized into modules corresponding to stages of the data distillery workflow. Each module provides Python functions and classes for loading, transforming, validating, and delivering data to knowledge systems like Wikidata.

This reference documents the **library API** - functions and classes you import and use in Python code. For command-line usage, see the [CLI Reference](../cli/index.md).

---

## Module Organization

GKC modules are grouped by their role in the distillery pipeline:

| **Stage** | **Module** | **Purpose** |
|-----------|-----------|-------------|
| **Mash** | [mash](mash.md) | Load data from Wikidata and other sources |
| | [mash_formatters](mash_formatters.md) | Convert templates to output formats |
| **Barrel Schema** | cooperage | Fetch schemas and metadata from target systems |
| | recipe | Build transformation recipes from EntitySchemas |
| **Validation** | spirit_safe | Validate against Barrel Schemas |
| **Transform** | bottler | Transform data into Wikidata format |
| **Deliver** | [shipper](shipper.md) | Submit data to Wikidata |
| **Utilities** | auth | Authentication for Wikidata and OSM |
| | sitelinks | Manage Wikipedia sitelinks |
| | [sparql](sparql.md) | Query Wikidata with SPARQL |

---

## Quick Reference by Task

### Load a Wikidata Item

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()
template = loader.load("Q42")
```

📖 [Mash Module Documentation](mash.md)

### Format as QuickStatements

```python
from gkc.mash import WikidataLoader
from gkc.mash_formatters import QSV1Formatter

loader = WikidataLoader()
template = loader.load("Q42")

formatter = QSV1Formatter()
qs_text = formatter.format(template, for_new_item=True)
```

📖 [Mash Formatters Documentation](mash_formatters.md)

### Build a Recipe from EntitySchema

```python
from gkc.recipe import RecipeBuilder

builder = RecipeBuilder(eid="E502")  # EntitySchema ID
recipe = builder.build()
print(recipe.get_property_mappings())
```

📖 Recipe Module Documentation (coming soon)

### Validate Against EntitySchema

```python
from gkc.spirit_safe import SpiritSafeValidator

validator = SpiritSafeValidator(qid="Q42", eid="E502")
result = validator.check()
print(result.is_valid)
```

📖 Spirit Safe Documentation (coming soon)

### Query Wikidata with SPARQL

```python
from gkc.sparql import SPARQLQuery

executor = SPARQLQuery()
results = executor.query("""
    SELECT ?item ?itemLabel WHERE {
      ?item wdt:P31 wd:Q5 .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
    }
    LIMIT 10
""")
```

📖 [SPARQL Module Documentation](sparql.md)

### Authenticate with Wikidata

```python
from gkc.auth import WikiverseAuth

auth = WikiverseAuth()
auth.login(username="YourUsername", password="YourPassword")
```

📖 Authentication Documentation (coming soon)

---

## Core Modules

### [Mash](mash.md)

Load data from Wikidata and other sources as templates for processing.

**Key classes:**
- `WikidataLoader` - Load Wikidata items
- `WikidataTemplate` - Manipulate loaded data

**Key functions:**
- `strip_entity_identifiers()` - Prepare for new item creation
- `fetch_property_labels()` - Get property labels

### [Mash Formatters](mash_formatters.md)

Convert templates to different output formats.

**Key classes:**
- `QSV1Formatter` - Format as QuickStatements V1

### Recipe

Build transformation recipes from EntitySchemas.

**Key classes:**
- `RecipeBuilder` - Generate recipes from EntitySchemas
- `EntityCatalog` - Fetch and cache entity metadata
- `PropertyLedgerEntry` - Property metadata container
- `ItemLedgerEntry` - Item metadata container

_Documentation coming soon_

### Cooperage

Fetch schemas and metadata from target systems (Barrel Schemas).

**Key functions:**
- `fetch_schema_specification()` - Get EntitySchema ShEx
- `fetch_entity_schema_json()` - Get EntitySchema metadata
- `fetch_entity_rdf()` - Get entity RDF data
- `validate_entity_reference()` - Check if entity exists

_Documentation coming soon_

### Spirit Safe

Validate data against Barrel Schemas before submission.

**Key classes:**
- `SpiritSafeValidator` - Validate against EntitySchemas

_Documentation coming soon_

### Bottler

Transform data into Wikidata item structure.

**Key classes:**
- `DataTypeTransformer` - Transform values to Wikidata format
- `Bottler` - Create Wikidata items from recipes

_Documentation coming soon_

### [Shipper](shipper.md)

Submit data to Wikidata via the API.

**Key classes:**
- `WikidataShipper` - Submit QuickStatements or JSON to Wikidata
- `CommonsShipper` - Wikimedia Commons submission (planned)
- `OpenStreetMapShipper` - OSM submission (planned)

---

## Utility Modules

### Authentication

Manage credentials for Wikidata, Wikipedia, Wikimedia Commons, and OpenStreetMap.

**Key classes:**
- `WikiverseAuth` - Wikidata/Wikipedia authentication
- `OpenStreetMapAuth` - OSM authentication

_Documentation coming soon_

### Sitelinks

Manage and validate Wikipedia sitelinks for Wikidata items.

**Key functions:**
- `validate_sitelink()` - Check if Wikipedia page exists
- `get_sitelink_url()` - Build Wikipedia URL from title

_Documentation coming soon_

### [SPARQL](sparql.md)

Query Wikidata and other SPARQL endpoints.

**Key classes:**
- `SPARQLQuery` - Execute queries and handle results

**Key functions:**
- `execute_sparql()` - Run raw SPARQL queries

---

## Package Configuration

### Language Settings

```python
import gkc

# Set single language
gkc.set_languages("en")

# Set multiple languages
gkc.set_languages(["en", "es", "fr"])

# Get current setting
languages = gkc.get_languages()
```

Many modules use the package-level language configuration for filtering labels, descriptions, and other multilingual content.

---

## See Also

- [CLI Reference](../cli/index.md) - Command-line interface
- [Pipeline Overview](../pipeline_overview.md) - End-to-end workflow
- Examples - Jupyter notebooks with real-world usage (coming soon)
