# Bottler API

## Overview

The bottler module transforms distilled source values into Wikibase/Wikidata claim structures.

It provides:

- Datatype transformation helpers (`DataTypeTransformer`)
- Snak construction (`SnakBuilder`)
- Claim construction with qualifiers/references (`ClaimBuilder`)
- End-to-end mapping configuration container (`Distillate`)

## Quick Start

```python
from gkc.bottler import DataTypeTransformer, SnakBuilder, ClaimBuilder

transformer = DataTypeTransformer()
snak_builder = SnakBuilder(transformer)
claim_builder = ClaimBuilder(snak_builder)

claim = claim_builder.create_claim(
    property_id="P31",
    value="Q5",
    datatype="wikibase-item",
)

print(claim["mainsnak"]["property"], claim["type"], claim["rank"])
```

## Public API Quick Starts

### `DataTypeTransformer.to_wikibase_item()`

```python
from gkc.bottler import DataTypeTransformer

datavalue = DataTypeTransformer.to_wikibase_item("Q42")
print(datavalue)
```

### `DataTypeTransformer.to_quantity()`

```python
from gkc.bottler import DataTypeTransformer

datavalue = DataTypeTransformer.to_quantity(42, unit="1")
print(datavalue)
```

### `DataTypeTransformer.to_time()`

```python
from gkc.bottler import DataTypeTransformer

year_only = DataTypeTransformer.to_time(2005)
month_precision = DataTypeTransformer.to_time("2005-01")
day_precision = DataTypeTransformer.to_time("2005-01-15", precision=11)

print(year_only)
print(month_precision)
print(day_precision)
```

### `DataTypeTransformer.to_monolingualtext()`

```python
from gkc.bottler import DataTypeTransformer

datavalue = DataTypeTransformer.to_monolingualtext("Hello", "en")
print(datavalue)
```

### `DataTypeTransformer.to_globe_coordinate()`

```python
from gkc.bottler import DataTypeTransformer

datavalue = DataTypeTransformer.to_globe_coordinate(51.5074, -0.1278, precision=0.0001)
print(datavalue)
```

### `DataTypeTransformer.to_url()`

```python
from gkc.bottler import DataTypeTransformer

datavalue = DataTypeTransformer.to_url("https://example.org")
print(datavalue)
```

### `SnakBuilder.create_snak()`

```python
from gkc.bottler import DataTypeTransformer, SnakBuilder

builder = SnakBuilder(DataTypeTransformer())

item_snak = builder.create_snak("P31", "Q5", "wikibase-item")
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

### `Distillate`

::: gkc.bottler.Distillate
    options:
      show_root_heading: false
      heading_level: 4

## See Also

- [Mash API](mash.md)
- [Cooperage API](cooperage.md)
- [Shipper API](shipper.md)
