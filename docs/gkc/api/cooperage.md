# Cooperage API

## Overview

The cooperage module is the active packet-to-operation barreling layer between `still_charger` and `shipper`.

Current primary functionality converts charged curation packet entities into operation payloads compatible with `WikibaseShipper.plan_batch` and write methods.

Legacy schema/RDF helpers remain available as compatibility re-exports.

## Quick Start

```python
from gkc.cooperage import barrel_curation_packet_to_wikibase_plan

packet = {
    "packet_id": "pkt-demo",
    "entities": [
        {
            "id": "ent-001",
            "profile": "TribalGovernmentUS",
            "profile_structure": {
                "statements": [{"id": "instance_of", "io_map": [{"to": "https://www.wikidata.org/entity/P31"}]}]
            },
            "data": {
                "labels": {"en": "Cherokee Nation"},
                "statements": {"instance_of": [{"value": "Q7840353"}]},
            },
        }
    ],
}

operations, report = barrel_curation_packet_to_wikibase_plan(packet)

print(report.operations_created)
print(operations[0]["kind"], operations[0]["label"])
```

## Public API Quick Starts

### `barrel_curation_packet_to_wikibase_plan()`

```python
from gkc.cooperage import barrel_curation_packet_to_wikibase_plan

operations, report = barrel_curation_packet_to_wikibase_plan(
    packet,
    property_id_map={"instance_of": "P31"},
)

print(report.operations_created)
print(report.entities_skipped)
print([issue.message for issue in report.issues])
```

### `BarrelIssue` and `BarrelPlanReport`

```python
from gkc.cooperage import BarrelIssue, BarrelPlanReport

issue = BarrelIssue(
    severity="warning",
    entity_id="ent-001",
    field="statements.instance_of",
    message="No property mapping found",
)

report = BarrelPlanReport(operations_created=0, entities_skipped=1, issues=[issue])
print(report.entities_skipped, report.issues[0].severity)
```

### Compatibility re-exports

```python
from gkc.cooperage import fetch_entity_rdf, fetch_schema_specification

rdf_ttl = fetch_entity_rdf("Q42", format="ttl")
schema_text = fetch_schema_specification("E502")

print(len(rdf_ttl), len(schema_text))
```

## API Reference (mkdocstrings)

### `BarrelIssue`

::: gkc.cooperage.BarrelIssue
    options:
      show_root_heading: false
      heading_level: 4

### `BarrelPlanReport`

::: gkc.cooperage.BarrelPlanReport
    options:
      show_root_heading: false
      heading_level: 4

### `barrel_curation_packet_to_wikibase_plan()`

::: gkc.cooperage.barrel_curation_packet_to_wikibase_plan
    options:
      show_root_heading: false
      heading_level: 4

### `CooperageError` (compatibility)

::: gkc.cooperage.CooperageError
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_entity_rdf()` (compatibility)

::: gkc.cooperage.fetch_entity_rdf
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_schema_specification()` (compatibility)

::: gkc.cooperage.fetch_schema_specification
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_entity_schema_json()` (compatibility)

::: gkc.cooperage.fetch_entity_schema_json
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_entity_schema_metadata()` (compatibility)

::: gkc.cooperage.fetch_entity_schema_metadata
    options:
      show_root_heading: false
      heading_level: 4

### `get_entity_uri()` (compatibility)

::: gkc.cooperage.get_entity_uri
    options:
      show_root_heading: false
      heading_level: 4

### `validate_entity_reference()` (compatibility)

::: gkc.cooperage.validate_entity_reference
    options:
      show_root_heading: false
      heading_level: 4

## See Also

- [Still Charger API](still_charger.md)
- [Shipper API](shipper.md)
- [Wikibase API](wikibase.md)
