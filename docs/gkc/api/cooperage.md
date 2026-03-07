# Cooperage API

## Overview

The cooperage module manages schema and reference retrieval utilities used to shape barrel profiles and transformation inputs.

Current public functionality focuses on Wikidata entity and EntitySchema retrieval helpers.

## Quick Start

```python
from gkc.cooperage import fetch_schema_specification, fetch_entity_schema_metadata

schema_text = fetch_schema_specification("E502")
metadata = fetch_entity_schema_metadata("E502", language="en")

print(len(schema_text), metadata["label"])
```

## Public API Quick Starts

### `fetch_entity_rdf()`

```python
from gkc.cooperage import fetch_entity_rdf

rdf_ttl = fetch_entity_rdf("Q42", format="ttl")
rdf_nt = fetch_entity_rdf("P31", format="nt")

print(rdf_ttl[:120])
print(rdf_nt[:120])
```

### `fetch_schema_specification()`

```python
from gkc.cooperage import fetch_schema_specification

schema = fetch_schema_specification("E502")
print(schema[:200])
```

### `fetch_entity_schema_json()`

```python
from gkc.cooperage import fetch_entity_schema_json

schema_json = fetch_entity_schema_json("E502")
print(schema_json.keys())
```

### `fetch_entity_schema_metadata()`

```python
from gkc.cooperage import fetch_entity_schema_metadata

metadata = fetch_entity_schema_metadata("E502", language="en")
print(metadata["label"], metadata["description"], metadata["source"])
```

### `get_entity_uri()`

```python
from gkc.cooperage import get_entity_uri

qid_uri = get_entity_uri("Q42")
pid_uri = get_entity_uri("P31")

print(qid_uri)
print(pid_uri)
```

### `validate_entity_reference()`

```python
from gkc.cooperage import validate_entity_reference

print(validate_entity_reference("Q42"))
print(validate_entity_reference("P31"))
print(validate_entity_reference("E502"))
print(validate_entity_reference("invalid"))
```

### `CooperageError`

```python
from gkc.cooperage import CooperageError, fetch_entity_rdf

try:
    fetch_entity_rdf("", format="ttl")
except ValueError:
    pass

try:
    raise CooperageError("example cooperage failure")
except CooperageError:
    pass
```

## API Reference (mkdocstrings)

### `CooperageError`

::: gkc.cooperage.CooperageError
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_entity_rdf()`

::: gkc.cooperage.fetch_entity_rdf
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_schema_specification()`

::: gkc.cooperage.fetch_schema_specification
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_entity_schema_json()`

::: gkc.cooperage.fetch_entity_schema_json
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_entity_schema_metadata()`

::: gkc.cooperage.fetch_entity_schema_metadata
    options:
      show_root_heading: false
      heading_level: 4

### `get_entity_uri()`

::: gkc.cooperage.get_entity_uri
    options:
      show_root_heading: false
      heading_level: 4

### `validate_entity_reference()`

::: gkc.cooperage.validate_entity_reference
    options:
      show_root_heading: false
      heading_level: 4

## See Also

- [Mash API](mash.md)
- [Shipper API](shipper.md)
- [Wikibase API](wikibase.md)
