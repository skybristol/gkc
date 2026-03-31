# Bottler API

## Overview

The `gkc.bottler` module provides canonical Wikibase JSON construction primitives. This is where distilled and validated data is transformed into the precise structure required by Wikidata: labels, descriptions, aliases, claims with qualifiers, references, and related item components.

**Key principle**: All code that produces Wikibase JSON structures should use bottler primitives, not build JSON inline. This ensures determinism, consistency, and maintainability across the entire pipeline.

The module provides:

- **DataTypeTransformer**: Static methods to convert source data values to Wikibase datatypes (items, quantities, times, etc.)
- **SnakBuilder**: Construct individual snaks (the property-value pairs that form claims)
- **ClaimBuilder**: Build complete claim structures with qualifiers and references
- **LanguageBuilder**: Construct multilingual label/description/alias blocks
- **EntityShellBuilder**: Build blank Wikibase entity scaffolds from profile metadata
- **Utility functions**: Helpers for value normalization and claim construction

## Quick Start: Build a Complete Entity Shell

```python
from gkc.bottler import EntityShellBuilder

metadata = {
    "labels": {"en": "Example Item", "de": "Beispiel Artikel"},
    "descriptions": {"en": "An example Wikidata item"},
    "aliases": {"en": ["Example", "Test Item"]},
    "statement_pids": ["P31", "P17", "P625"],
}

builder = EntityShellBuilder()
shell = builder.build_entity_shell(metadata)

# Result is a valid Wikibase entity structure ready for use in packets
print(shell)
# Output:
# {
#   "labels": {"en": {"value": "Example Item", "language": "en"}, ...},
#   "descriptions": {...},
#   "aliases": {...},
#   "claims": {"P17": [], "P31": [], "P625": []}  # sorted deterministically
# }
```

## Complete Example: Build a Statement with Qualifier and Reference

```python
from gkc.bottler import DataTypeTransformer, SnakBuilder, ClaimBuilder

# 1. Create transformer
transformer = DataTypeTransformer()

# 2. Create snak builder
snak_builder = SnakBuilder(transformer)

# 3. Create claim builder
claim_builder = ClaimBuilder(snak_builder)

# 4. Build a claim with qualifiers and references
claim = claim_builder.create_claim(
    property_id="P31",  # instance of
    value="Q5",  # human
    datatype="wikibase-item",
    qualifiers=[
        {
            "property": "P585",  # point in time
            "value": "2005-06-15",
            "datatype": "time",
        }
    ],
    references=[
        {
            "P248": {"value": "Q5", "datatype": "wikibase-item"},  # stated in
            "P813": {"value": "2005-06-15", "datatype": "time"},  # retrieved
        }
    ],
    rank="preferred",
)

print(claim)
# Returns a complete Wikibase statement structure
```


quantity_snak = builder.create_snak("P1082", 1000, "quantity", {"unit": "1"})
time_snak = builder.create_snak("P571", "2005-01-15", "time")
text_snak = builder.create_snak(
    "P1476",
    "Sample title",
    "monolingualtext",
    {"language": "en"},
)
coord_snak = builder.create_snak("P625", {"lat": 51.5, "lon": -0.12}, "globe-coordinate")
url_snak = builder.create_snak("P856", "https://example.org", "url")
string_snak = builder.create_snak("P1477", "Example string", "string")

print(item_snak)
print(quantity_snak)
print(time_snak)
print(text_snak)
print(coord_snak)
print(url_snak)
print(string_snak)
```

### `ClaimBuilder.create_claim()`

```python
from gkc.bottler import DataTypeTransformer, SnakBuilder, ClaimBuilder

claim_builder = ClaimBuilder(SnakBuilder(DataTypeTransformer()))

claim = claim_builder.create_claim(
    property_id="P31",
    value="Q5",
    datatype="wikibase-item",
    qualifiers=[
        {"property": "P580", "value": "2005-01-15", "datatype": "time"},
    ],
    references=[
        {
            "P248": {"value": "Q123", "datatype": "wikibase-item"},
            "P854": {"value": "https://example.org", "datatype": "url"},
        }
    ],
    rank="normal",
)

print(claim)
```

### `Distillate.__init__()` and `Distillate.from_file()`

```python
import json
import tempfile
from pathlib import Path

from gkc.bottler import Distillate

config = {
    "reference_library": {
        "official_source": [
            {"property": "P248", "value": "Q123", "datatype": "wikibase-item"}
        ]
    },
    "qualifier_library": {
        "start_date": [
            {"property": "P580", "value": "2005-01-15", "datatype": "time"}
        ]
    },
    "mappings": {
        "claims": [
            {
                "property": "P31",
                "references": [
                    {"name": "inline_ref", "property": "P248", "value": "Q123", "datatype": "wikibase-item"}
                ],
                "qualifiers": [
                    {"name": "inline_qual", "property": "P580", "value": "2005-01-15", "datatype": "time"}
                ],
            }
        ]
    },
}

# Direct initialization
bottler = Distillate(config)
print(sorted(bottler.reference_library.keys()))
print(sorted(bottler.qualifier_library.keys()))

# File-based initialization
with tempfile.TemporaryDirectory() as tmpdir:
    path = Path(tmpdir) / "distillate.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    loaded = Distillate.from_file(str(path))
    print(isinstance(loaded, Distillate))
```

## API Reference (mkdocstrings)

### `DataTypeTransformer`

::: gkc.bottler.DataTypeTransformer
    options:
      show_root_heading: false
      heading_level: 4

### `SnakBuilder`

::: gkc.bottler.SnakBuilder
    options:
      show_root_heading: false
      heading_level: 4

### `ClaimBuilder`

::: gkc.bottler.ClaimBuilder
    options:
      show_root_heading: false
      heading_level: 4

### `LanguageBuilder`

::: gkc.bottler.LanguageBuilder
    options:
      show_root_heading: false
      heading_level: 4

### `EntityShellBuilder`

::: gkc.bottler.EntityShellBuilder
    options:
      show_root_heading: false
      heading_level: 4

### Utility Functions

#### `normalize_claim_datavalue()`

::: gkc.bottler.normalize_claim_datavalue
    options:
      show_root_heading: false
      heading_level: 5

#### `build_claim_from_property_and_value()`

::: gkc.bottler.build_claim_from_property_and_value
    options:
      show_root_heading: false
      heading_level: 5

### `Distillate`

::: gkc.bottler.Distillate
    options:
      show_root_heading: false
      heading_level: 4

## Design Principles

1. **Determinism**: All builders produce byte-identical output for identical input, enabling stable packet digests and test assertions.

2. **Composition**: Builders are composable—SnakBuilder uses DataTypeTransformer; ClaimBuilder uses SnakBuilder, etc.

3. **Flexibility**: Configuration is passed as simple dictionaries, allowing future extensibility without API churn.

4. **Validation-Agnostic**: Bottler focuses on structure production, not validation. Validation is handled by fermenter.

5. **Profile-Aware**: When integrated with still_charger and EntityShellBuilder, bottler generates profile-compliant packet shells.

## Integration: Using Bottler in still_charger

Profile-only curation packets now include Wikibase JSON entity shells:

```python
from gkc.still_charger import create_curation_packet

packet = create_curation_packet("Q4", operation_mode="single")

# Each entity in data.entities now includes an "entity" field with canonical Wikibase JSON
for entity in packet["data"]["entities"]:
    print(entity["entity"])  # Fully formed Wikibase entity shell
    # {
    #   "labels": {...},
    #   "descriptions": {...},
    #   "aliases": {...},
    #   "claims": {...}
    # }
```

This ensures profile-only packets have shape-consistent, deterministic Wikibase JSON scaffolds ready for charging and validation.

## See Also

- [Still Charger API](still_charger.md) — Packet assembly and charging
- [Fermenter API](fermenter.md) — Validation and coercion
- [Architecture Overview](../architecture/modules.md) — Module boundaries and contracts
