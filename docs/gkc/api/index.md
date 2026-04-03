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
| **Packet Fill** | [still_charger](still_charger.md) | Fill curation packet scaffolds with concrete source values |
| **Validation / Registry** | [spirit_safe](spirit_safe.md) | SpiritSafe source config, registry discovery, query hydration, and caching |
| **Transform** | [bottler](bottler.md) | Transform data into Wikidata format |
| **Deliver** | [shipper](shipper.md) | Submit data to Wikibase-compatible APIs |
| **Registry / Orchestration** | [spirit_safe](spirit_safe.md) | SpiritSafe registry and profile artifact orchestration |
| **Utilities** | auth | Authentication for Wikidata and OSM |
| | sitelinks | Manage Wikipedia sitelinks |
| | [sparql](sparql.md) | Query Wikidata with SPARQL |
| **Profiles** | [profiles](profiles.md) | Profile loading and validation |
| **Ontology** | [spirit_safe](spirit_safe.md) | Data Distillery semantics materialized through SpiritSafe artifacts |

---

## Quick Reference by Task

### Load a Wikidata Item

```python
from gkc.mash import WikibaseLoader

loader = WikibaseLoader()
template = loader.load("Q42")
```

📖 [Mash Module Documentation](mash.md)

### Format as QuickStatements

```python
from gkc.mash import WikibaseLoader
from gkc.mash_formatters import QSV1Formatter

loader = WikibaseLoader()
template = loader.load("Q42")

formatter = QSV1Formatter()
qs_text = formatter.format(template, for_new_item=True)
```

📖 [Mash Formatters Documentation](mash_formatters.md)

### Discover and Load SpiritSafe Profiles

```python
import gkc

# default mode is GitHub: skybristol/SpiritSafe@main
profiles = gkc.list_profiles()
print(profiles)
```

📖 [SpiritSafe Module Documentation](spirit_safe.md)

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

📖 [Authentication Documentation](../authentication.md)

---

## Core Modules

### [Mash](mash.md)

Load data from Wikidata and other sources as templates for processing.

**Key classes:**
- `WikibaseLoader` - Load Wikidata items
- `WikibaseItemTemplate` - Manipulate loaded data

**Key functions:**
- `strip_entity_identifiers()` - Prepare for new item creation
- `transform_entity_for_write()` - Convert raw entity JSON into shipper-ready payloads
- `fetch_property_labels()` - Get property labels

### [Mash Formatters](mash_formatters.md)

Convert templates to different output formats.

**Key classes:**
- `QSV1Formatter` - Format as QuickStatements V1

### [Still Charger](still_charger.md)

Fill curation packet scaffolds with concrete values from source payloads.

**Key classes/functions:**

- `charge_curation_packet()` - Apply source values to packet entities
- `ChargeReport` and `ChargeIssue` - Structured charging diagnostics

### [Spirit Safe](spirit_safe.md)

Configure SpiritSafe source mode, discover profile registrants, resolve profile/query references, and hydrate/cache SPARQL-driven allowed-items lists.

**Key classes/functions:**

- `SpiritSafeSourceConfig`
- `set_spirit_safe_source()`, `get_spirit_safe_source()`
- `list_profiles()`, `profile_exists()`
- `resolve_profile_path()`, `resolve_query_ref()`
- `LookupCache`, `LookupFetcher`

### [Bottler](bottler.md)

Transform data into Wikidata item structure.

**Key classes:**

- `DataTypeTransformer` - Build Wikibase datavalues by datatype
- `SnakBuilder` - Create snak structures from transformed values
- `ClaimBuilder` - Build statement objects with qualifiers/references
- `Distillate` - Load and hold mapping configuration for transformation flows

### [Shipper](shipper.md)

Submit data to Wikibase via the API.

**Key classes:**
- `WikidataShipper` - Submit QuickStatements or JSON to Wikidata
- `WikibaseShipper` - Primary write interface for Wikibase item/property operations
- `CommonsShipper` - Wikimedia Commons submission (planned)
- `OpenStreetMapShipper` - OSM submission (planned)

### [Spirit Safe](spirit_safe.md)

Own profile/materialization orchestration for Data Distillery semantics in runtime artifacts.

**Key functions:**

- `export_entity_profile_json_documents()`
- `export_spiritsafe_manifest()`
- `hydrate_value_lists_from_cache()`

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

### [Profiles](profiles.md)

Legacy module notice and contract direction for superseded YAML-era profile surfaces.

**Current runtime owners:**
- `spirit_safe` - JSON profile artifacts and loading
- `still_charger` - packet assembly/charging
- `fermenter` - validation/coercion/conformance
- `wizard` - interactive runtime

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