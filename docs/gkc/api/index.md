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
| **Registry / Orchestration** | [wikibase](wikibase.md) | Foundation audit/init and profile-driven write planning orchestration |
| **Utilities** | auth | Authentication for Wikidata and OSM |
| | sitelinks | Manage Wikipedia sitelinks |
| | [sparql](sparql.md) | Query Wikidata with SPARQL |
| **Profiles** | [profiles](profiles.md) | Profile loading and validation |
| **Ontology** | [ontology](ontology.md) | Two-layer ontology extraction from Data Distillery Wikibase |

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
metadata = gkc.get_profile_metadata("TribalGovernmentUS")
print(metadata.version)
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
- `list_profiles()`, `profile_exists()`, `get_profile_metadata()`
- `resolve_profile_path()`, `resolve_query_ref()`
- `hydrate_profile_lookups()`, `LookupCache`, `LookupFetcher`

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

### [Wikibase](wikibase.md)

Coordinate foundation workflows and convert charged packets into shippable write operations.

**Key classes/functions:**

- `build_wikibase_write_plan()` - Build packet -> charge -> operation planning results
- `execute_wikibase_write_plan()` - Replay planned operations through shipper writes
- `barrel_curation_packet_to_wikibase_plan()` - Convert charged packets into plan operations
- `BarrelPlanReport` and `BarrelIssue` - Structured write-planning diagnostics

### [Wikibase](wikibase.md)

Audit and initialize foundation ontology definitions for Data Distillery, and orchestrate packet-to-write planning.

**Key functions:**

- `load_foundation_profiles()`
- `audit_wikibase_foundation()`
- `init_wikibase_foundation()`
- `build_wikibase_write_plan()`

### [Ontology](ontology.md)

Extract ontology index and full profile graph data from Data Distillery Wikibase.

**Key functions:**

- `fetch_ontology_index()`
- `fetch_profile_ids()`
- `fetch_profile_graph()`
- `resolve_statement_guidance()`

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

Profile loading surfaces for validation and form schema generation.

**Key classes:**
- `ProfileLoader` - Load profile artifacts
- `ProfileValidator` - Validate Wikidata items
- `FormSchemaGenerator` - Build form schemas

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