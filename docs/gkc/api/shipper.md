# Shipper API

## Overview

The shipper module is the write/delivery layer for GKC outputs.

For Wikibase-compatible targets (including Data Distillery and Wikidata), use `WikibaseShipper`.

**Note**: `WikibaseShipper` works with any Wikibase instance. Configure the target via the `api_url` parameter in your `WikiverseAuth` object.

## Quick Start

```python
from gkc import WikiverseAuth
from gkc.shipper import WikibaseShipper

# Example: Wikidata
auth = WikiverseAuth(
    username="my_username",
    password="my_password",
    api_url="https://www.wikidata.org/w/api.php",
)
auth.login()

# Or Data Distillery
# auth = WikiverseAuth(
#     username="my_username",
#     password="my_password",
#     api_url="https://datadistillery.wikibase.cloud/w/api.php",
# )

shipper = WikibaseShipper(auth=auth, dry_run_default=True)

result = shipper.write_item(
    payload={
        "labels": {"en": {"language": "en", "value": "Test item"}},
        "descriptions": {"en": {"language": "en", "value": "Created from shipper docs"}},
    },
    summary="Create test item",
)

print(result.status)
```

## Public API Quick Starts

### `WriteResult`

```python
from gkc.shipper import WriteResult

result = WriteResult(
    entity_id="Q123",
    revision_id=456,
    status="submitted",
    warnings=[],
    api_response={"success": 1},
)

as_dict = result.to_dict()
as_json = result.to_json()
print(as_dict["entity_id"], as_json)
```

### `DiffOperation` and `DiffPlan`

```python
from gkc.shipper import DiffOperation, DiffPlan

operation = DiffOperation(
    kind="item",
    label="GKC Property Specification",
    status="create",
    reasons=["label_not_found"],
)

plan = DiffPlan(operations=[operation], summary={"total": 1, "create": 1})
print(operation.to_dict())
print(plan.to_dict())
```

### `Shipper` (base interface)

```python
from gkc.shipper import Shipper, ShipperError

class DemoShipper(Shipper):
    def write(self, payload, **kwargs):
        raise ShipperError("Demo write failure")

try:
    DemoShipper().write({"foo": "bar"})
except ShipperError:
    pass
```

### `WikibaseShipper.plan_batch()`

```python
from gkc import WikiverseAuth
from gkc.shipper import WikibaseShipper

auth = WikiverseAuth(
    username="my_username",
    password="my_password",
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
)
auth.login()

shipper = WikibaseShipper(auth=auth)

plan = shipper.plan_batch(
    [
        {
            "kind": "item",
            "label": "GKC Query Entity",
            "payload": {
                "labels": {"en": {"language": "en", "value": "GKC Query Entity"}},
                "descriptions": {"en": {"language": "en", "value": "Classifier for query entities"}},
            },
        },
        {
            "kind": "property",
            "label": "query reference",
            "datatype": "wikibase-item",
            "payload": {
                "labels": {"en": {"language": "en", "value": "query reference"}},
                "descriptions": {"en": {"language": "en", "value": "Links to query entities"}},
            },
        },
    ]
)

print(plan.summary)
for op in plan.operations:
    print(op.status, op.kind, op.label)
```

### `WikibaseShipper.write_item()`

```python
from gkc import WikiverseAuth
from gkc.shipper import WikibaseShipper

auth = WikiverseAuth(
    username="my_username",
    password="my_password",
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
)
auth.login()

shipper = WikibaseShipper(auth=auth, dry_run_default=True)

# Validation-only call
validated = shipper.write_item(
    payload={
        "labels": {"en": {"language": "en", "value": "Validation sample"}},
        "descriptions": {"en": {"language": "en", "value": "Validate item payload"}},
    },
    summary="Validate item payload",
    validate_only=True,
)

# Dry-run update call
update_preview = shipper.write_item(
    payload={"descriptions": {"en": {"language": "en", "value": "Updated description"}}},
    summary="Preview item update",
    entity_id="Q1",
    dry_run=True,
)

print(validated.status, update_preview.status)
```

### `WikibaseShipper.write_property()`

```python
from gkc import WikiverseAuth
from gkc.shipper import WikibaseShipper

auth = WikiverseAuth(
    username="my_username",
    password="my_password",
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
)
auth.login()

shipper = WikibaseShipper(auth=auth, dry_run_default=True)

property_preview = shipper.write_property(
    payload={
        "labels": {"en": {"language": "en", "value": "has specification"}},
        "descriptions": {"en": {"language": "en", "value": "Links a property to specification entities"}},
    },
    datatype="wikibase-item",
    summary="Preview property create",
    dry_run=True,
)

print(property_preview.status)
print(property_preview.request_payload)
```

### `CommonsShipper`

```python
from gkc import WikiverseAuth
from gkc.shipper import CommonsShipper

auth = WikiverseAuth(api_url="https://commons.wikimedia.org/w/api.php")
shipper = CommonsShipper(auth=auth)

try:
    shipper.write(payload={"filename": "example.jpg"})
except NotImplementedError:
    pass
```

### `OpenStreetMapShipper`

```python
from gkc.auth import OpenStreetMapAuth
from gkc.shipper import OpenStreetMapShipper

auth = OpenStreetMapAuth(username="my_osm_user", password="my_osm_password")
shipper = OpenStreetMapShipper(auth=auth)

try:
    shipper.write(payload={"type": "node"})
except NotImplementedError:
    pass
```

## Data Distillery Write Contract Note

For Data Distillery property creation requests (`new=property`), `datatype` is embedded in serialized `data` payload JSON.

Use `write_property()` to preserve this request shape.

## API Reference (mkdocstrings)

### `ShipperError`

::: gkc.shipper.ShipperError
    options:
      show_root_heading: false
      heading_level: 4

### `WriteResult`

::: gkc.shipper.WriteResult
    options:
      show_root_heading: false
      heading_level: 4

### `DiffOperation`

::: gkc.shipper.DiffOperation
    options:
      show_root_heading: false
      heading_level: 4

### `DiffPlan`

::: gkc.shipper.DiffPlan
    options:
      show_root_heading: false
      heading_level: 4

### `Shipper`

::: gkc.shipper.Shipper
    options:
      show_root_heading: false
      heading_level: 4

### `WikibaseShipper`

::: gkc.shipper.WikibaseShipper
    options:
      show_root_heading: false
      heading_level: 4

### `CommonsShipper`

::: gkc.shipper.CommonsShipper
    options:
      show_root_heading: false
      heading_level: 4

### `OpenStreetMapShipper`

::: gkc.shipper.OpenStreetMapShipper
    options:
      show_root_heading: false
      heading_level: 4

## Migration Note

**Deprecated**: `WikidataShipper` has been removed as of this version. Use `WikibaseShipper` instead—it works with all Wikibase instances including Wikidata.

**Migration**:
```python
# Before (deprecated)
from gkc.shipper import WikidataShipper
shipper = WikidataShipper(auth=auth)

# After
from gkc.shipper import WikibaseShipper
shipper = WikibaseShipper(auth=auth)
```

## See Also

- [Mash API](mash.md)
- [Wikibase API](wikibase.md)
- [Authentication API](auth.md)