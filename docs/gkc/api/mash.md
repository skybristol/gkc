# Mash Module API

## Overview

Load data from Wikidata, Wikipedia, and other sources as templates for processing. The Mash stage is the entry point to the data distillery workflow, preparing source data for validation, transformation, and submission.

**Current implementations:**

- Wikidata items (QID)
- Wikidata properties (PID)
- Wikidata EntitySchemas (EID)
- Wikipedia templates

**Future implementations:** OSM, Wikimedia Commons, CSV files, JSON APIs, dataframes

## Quick Start

```python
from gkc.mash import WikidataLoader, WikipediaLoader

# Load Wikidata entities
loader = WikidataLoader()

# Load a single item
item = loader.load_item("Q42")

# Load multiple items in batch
items = loader.load_items(["Q42", "Q5", "Q30"])

# Load a property
prop = loader.load_property("P31")

# Load an EntitySchema
schema = loader.load_entity_schema("E502")

# Load Wikipedia templates
wp_loader = WikipediaLoader()
template = wp_loader.load_template("Infobox settlement")

# Filter and transform
item.filter_languages(["en", "es"])
summary = item.summary()
print(summary)
```

---

## Core Classes

### WikidataLoader

::: gkc.mash.WikidataLoader
    options:
      show_root_heading: false
      heading_level: 4

### WikidataTemplate

::: gkc.mash.WikidataTemplate
    options:
      show_root_heading: false
      heading_level: 4

### WikidataPropertyTemplate

::: gkc.mash.WikidataPropertyTemplate
    options:
      show_root_heading: false
      heading_level: 4

### WikidataEntitySchemaTemplate

::: gkc.mash.WikidataEntitySchemaTemplate
    options:
      show_root_heading: false
      heading_level: 4

### WikipediaLoader

::: gkc.mash.WikipediaLoader
    options:
      show_root_heading: false
      heading_level: 4

### WikipediaTemplate

::: gkc.mash.WikipediaTemplate
    options:
      show_root_heading: false
      heading_level: 4

---

## Utility Functions

### strip_entity_identifiers()

::: gkc.mash.strip_entity_identifiers
    options:
      show_root_heading: false
      heading_level: 4

### fetch_property_labels()

::: gkc.mash.fetch_property_labels
    options:
      show_root_heading: false
      heading_level: 4

---

## Data Classes

### ClaimSummary

::: gkc.mash.ClaimSummary
    options:
      show_root_heading: false
      heading_level: 4

---

## Examples

### Load and filter a Wikidata item

```python
from gkc.mash import WikidataLoader

# Initialize the loader
loader = WikidataLoader()

# Load an item
template = loader.load_item("Q42")  # Douglas Adams

# Filter to English only
template.filter_languages("en")

# Exclude certain properties
template.filter_properties(exclude_properties=["P18", "P373"])

# Remove qualifiers and references for simplicity
template.filter_qualifiers()
template.filter_references()

# Get a summary
summary = template.summary()
print(f"Loaded {summary['qid']}: {summary['labels']}")
print(f"Total statements: {summary['total_statements']}")
```

### Load multiple items in batch

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

# Load multiple items efficiently
qids = ["Q42", "Q5", "Q30", "Q515"]
templates = loader.load_items(qids)

for qid, template in templates.items():
    print(f"{qid}: {template.labels.get('en', 'No label')}")
```

### Prepare entity data for new item creation

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

# Load an item
template = loader.load_item("Q42")

# Strip identifiers to prepare for creating a new item
new_item_data = template.to_shell()

# Now you can modify labels, claims, etc. and use this for a new item
import json
print(json.dumps(new_item_data, indent=2))
```

### Convert item to QuickStatements format

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()
template = loader.load_item("Q42")

# For updating existing item
qs_update = template.to_qsv1(for_new_item=False)
print(qs_update)

# For creating new item (uses CREATE/LAST syntax)
qs_new = template.to_qsv1(for_new_item=True)
print(qs_new)

# With entity labels as comments
entity_labels = {"P31": "instance of", "Q5": "human"}
qs_labeled = template.to_qsv1(entity_labels=entity_labels)
```

### Load and work with properties

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

# Load a single property
prop = loader.load_property("P31")
print(f"Datatype: {prop.datatype}")
print(f"Labels: {prop.labels}")

# Load multiple properties in batch
pids = ["P31", "P279", "P21"]
props = loader.load_properties(pids)

for pid, prop in props.items():
    print(f"{pid}: {prop.labels.get('en')} ({prop.datatype})")
```

### Load and transform EntitySchemas

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

# Load an EntitySchema
schema = loader.load_entity_schema("E502")
print(f"Schema: {schema.labels.get('en')}")
print(f"ShEx text length: {len(schema.schema_text)}")

# Convert to GKC Entity Profile
profile = schema.to_gkc_entity_profile()
print(profile)
```

### Fetch descriptors for mixed entities

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

# Get labels and descriptions for a mix of items and properties
entity_ids = ["Q42", "P31", "Q5", "P279"]
descriptors = loader.fetch_descriptors(entity_ids)

for eid, info in descriptors.items():
    label = info["labels"].get("en", "No label")
    desc = info["descriptions"].get("en", "No description")
    print(f"{eid}: {label} - {desc}")
```

### Work with multiple language versions

```python
from gkc.mash import WikidataLoader
import gkc

# Set package-level language configuration
gkc.set_languages(["en", "es", "fr"])

loader = WikidataLoader()
template = loader.load_item("Q42")

# Filter using package configuration
template.filter_languages()  # Uses package setting

# Or specify explicitly
template.filter_languages(["en", "de"])

# Keep all languages
template.filter_languages("all")
```

### Load with custom user agent

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader(
    user_agent="MyBot/1.0 (https://example.com; user@example.com)"
)

template = loader.load_item("Q42")
```

### Load and examine a Wikipedia template

```python
from gkc.mash import WikipediaLoader

# Initialize the loader for en.wikipedia.org
loader = WikipediaLoader()

# Load a Wikipedia template
template = loader.load_template("Infobox settlement")

# Get a quick summary
summary = template.summary()
print(f"Template: {summary['title']}")
print(f"Description: {summary['description']}")
print(f"Parameters: {summary['param_count']}")

# Get the full template structure
full_data = template.to_dict()
for param_name in template.param_order[:5]:  # First 5 parameters
    param_info = template.params.get(param_name, {})
    label = param_info.get("label", {}).get("en", param_name)
    print(f"  - {param_name}: {label}")
```

---

## Transformation Methods

All template types support transformation methods for different output formats:

### to_dict()
Returns the raw Wikidata JSON structure, preserving all identifiers. Use this for round-trip processing where you need to preserve the exact structure.

### to_shell()
Strips all identifiers, hashes, and metadata from the entity data, creating a clean template for new entity creation. Removes: `id`, `pageid`, `lastrevid`, `modified`, `ns`, `title`, statement IDs, and all hashes.

### to_qsv1() (Items only)
Converts item templates to QuickStatements V1 format for bulk operations. Supports both update mode (uses QID) and creation mode (uses CREATE/LAST).

### to_gkc_entity_profile() (EntitySchemas only)
Converts EntitySchema templates to GKC Entity Profile format. This transformation is implemented for EntitySchemas and will be added for items and properties in future versions.

---

## Error Handling

### Entity not found

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

try:
    template = loader.load_item("Q999999999999")
except RuntimeError as e:
    print(f"Error: {e}")
    # Error: no-such-entity: Q999999999999 not found on Wikidata
```

### Network errors

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

try:
    template = loader.load_item("Q42")
except RuntimeError as e:
    print(f"Failed to fetch item: {e}")
```

---

## Migration from Previous Version

The mash module has been refactored for consistency across entity types. Key changes:

- `WikidataLoader.load(qid)` is now `WikidataLoader.load_item(qid)` (old method still works but is deprecated)
- `strip_entity_identifiers()` now also removes `ns` and `title` fields
- New batch loading: `load_items()`, `load_properties()`
- New entity types: `load_property()`, `load_entity_schema()`
- Transformation methods moved to template objects: `template.to_shell()`, `template.to_qsv1()`

---

## See Also

- [Mash CLI](../cli/mash.md) - Command-line interface for mash operations
- [Mash Formatters API](mash_formatters.md) - Convert templates to output formats
- Recipe API - Build validation recipes from EntitySchemas
