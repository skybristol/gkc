# Mash Module API

## Overview

Load data from Wikidata and other sources as templates for processing. The Mash stage is the entry point to the data distillery workflow, preparing source data for validation, transformation, and submission.

**Current implementations:** Wikidata items  
**Future implementations:** CSV files, JSON APIs, dataframes

## Quick Start

```python
from gkc.mash import WikidataLoader, strip_entity_identifiers

# Load a Wikidata item
loader = WikidataLoader()
template = loader.load("Q42")

# Filter to specific languages
template.filter_languages(["en", "es"])

# View summary
summary = template.summary()
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
template = loader.load("Q42")  # Douglas Adams

# Filter to English only
template.filter_languages("en")

# Exclude certain properties
template.filter_properties(["P18", "P373"])  # Exclude image and Commons category

# Remove qualifiers and references for simplicity
template.filter_qualifiers()
template.filter_references()

# Get a summary
summary = template.summary()
print(f"Loaded {summary['qid']}: {summary['labels']}")
print(f"Total statements: {summary['total_statements']}")
```

### Prepare entity data for new item creation

```python
from gkc.mash import WikidataLoader, strip_entity_identifiers
import json

loader = WikidataLoader()

# Load the raw entity data
entity_data = loader.load_entity_data("Q42")

# Strip identifiers to prepare for creating a new item
new_item_data = strip_entity_identifiers(entity_data)

# Now you can modify labels, claims, etc. and use this for a new item
new_item_data["labels"]["en"]["value"] = "Douglas Adams (clone)"

# Export as JSON
print(json.dumps(new_item_data, indent=2))
```

### Load with custom user agent

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader(
    user_agent="MyBot/1.0 (https://example.com; user@example.com)"
)

template = loader.load("Q42")
```

### Fetch property labels for display

```python
from gkc.mash import fetch_property_labels

# Get labels for multiple properties
property_ids = ["P31", "P21", "P569", "P570"]
labels = fetch_property_labels(property_ids)

print(labels)
# {'P31': 'instance of', 'P21': 'sex or gender', 'P569': 'date of birth', 'P570': 'date of death'}
```

### Work with multiple language versions

```python
from gkc.mash import WikidataLoader
import gkc

# Set package-level language configuration
gkc.set_languages(["en", "es", "fr"])

loader = WikidataLoader()
template = loader.load("Q42")

# Filter using package configuration
template.filter_languages()  # Uses package setting

# Or specify explicitly
template.filter_languages(["en", "de"])

# Keep all languages
template.filter_languages("all")
```

---

## Error Handling

### Item not found

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

try:
    template = loader.load("Q999999999999")
except RuntimeError as e:
    print(f"Error: {e}")
    # Error: no-such-entity: Q999999999999 not found on Wikidata
```

### Network errors

```python
from gkc.mash import WikidataLoader

loader = WikidataLoader()

try:
    template = loader.load("Q42")
except RuntimeError as e:
    print(f"Failed to fetch item: {e}")
```

---

## See Also

- [Mash CLI](../cli/mash.md) - Command-line interface for mash operations
- [Mash Formatters API](mash_formatters.md) - Convert templates to output formats
- Recipe API - Build validation recipes from EntitySchemas (documentation coming soon)
