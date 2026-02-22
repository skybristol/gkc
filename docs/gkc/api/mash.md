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

## Entity Profiles

### Overview

A **GKC Entity Profile** is a canonical definition of how an entity type should be structured in the GKC distillery workflow. It captures:
- Which Wikidata properties apply to an entity type
- Classification constraints (P31/P279 requirements)
- Multilingual labels and descriptions
- Target system compatibility

Entity Profiles serve as the bridge between raw Wikidata schemas and GKC processing pipelines.

### Generating Entity Profiles from EntitySchemas

```python
from gkc.recipe import RecipeBuilder

# Create a recipe builder
rb = RecipeBuilder()

# Load an EntitySchema (E502, Tribe)
rb.load_from_eid("E502")

# Generate a GKC Entity Profile
profile_data = rb.generate_gkc_entity_profile(profile_id="tribe")

print(profile_data)
# {
#   "id": "tribe",
#   "source_eid": "E502",
#   "labels": {"en": "Tribe"},
#   "descriptions": {"en": "An ethnic group or community"},
#   "properties": ["P31", "P17", "P625", "P580", "P582"],
#   "classification_constraints": {
#     "p31": ["Q7840353"],  # ethnic group
#     "p279": []
#   },
#   "target_systems": ["wikidata"]
# }
```

### Working with GKCEntityProfile Objects

```python
from gkc import GKCEntityProfile
from gkc.recipe import RecipeBuilder

# Generate a profile
rb = RecipeBuilder()
rb.load_from_eid("E502")
profile_dict = rb.generate_gkc_entity_profile(profile_id="tribe")

# Convert to GKCEntityProfile pydantic model
profile = GKCEntityProfile(**profile_dict)

# Access fields
print(profile.id)  # "tribe"
print(profile.source_eid)  # "E502"
print(profile.labels)  # {"en": "Tribe"}

# Modify properties as needed for hand-tuning
profile.properties.append("P242")  # Add geographic area

# Serialize back to dictionary
updated_dict = profile.to_dict()

# Validate the updated profile
profile2 = GKCEntityProfile(**updated_dict)
```

### Saving Profiles for Version Control

```python
from gkc.recipe import RecipeBuilder
import json
from pathlib import Path

rb = RecipeBuilder()
rb.load_from_eid("E502")
profile_dict = rb.generate_gkc_entity_profile(profile_id="tribe")

# Save to JSON file
output_dir = Path("./profiles")
output_dir.mkdir(exist_ok=True)

filename = output_dir / "tribe_entity_profile.json"
with open(filename, "w") as f:
    json.dump(profile_dict, f, indent=2)

print(f"Saved: {filename}")
```

### Understanding Profile Structure

**id**: Internal GKC identifier for this entity type (derived from EntitySchema label or specified explicitly)

**source_eid**: The original Wikidata EntitySchema ID (e.g., "E502")

**labels**: Multilingual labels from the EntitySchema, using package language configuration

**descriptions**: Multilingual descriptions from the EntitySchema

**properties**: List of Wikidata property IDs that apply to entities of this type

**classification_constraints**: 
- `p31`: Required values for "instance of" (P31) property
- `p279`: Required values for "subclass of" (P279) property

**target_systems**: Platform(s) where entities of this type can be created (initially just "wikidata")

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
