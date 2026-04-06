# SpiritSafe API

## Overview

`gkc.spirit_safe` provides SpiritSafe source configuration, lookup hydration, JSON Entity Profile export, value-list hydration, and curation packet scaffolding.

Current architecture:

- Runtime packet assembly loads `still/profiles/<QID>.json` directly.
- Registry/discovery tooling enumerates `still/profiles/*.json` directly.
- Value lists are materialized in `still/value_lists/cache/<QID>.json` and consumed as cache artifacts.

## Quick Start

### Complete Workflow: Create, Charge, and Validate a Packet

The typical workflow for curation involves three stages:

1. **Create** — Scaffold packet from profile (spirit_safe module)
2. **Charge** — Populate packet with data from Wikidata (still_charger module)
3. **Validate** — Check completeness and constraints (validation module)

```python
from pathlib import Path
from gkc.spirit_safe import set_spirit_safe_source
from gkc.still_charger import create_curation_packet, charge_packet_from_wikidata_items

# 1. Configure source
set_spirit_safe_source(mode="local", local_root="/path/to/SpiritSafe")

# 2. Create empty scaffold from profile Q4 (TribalGovernmentUS)
packet = create_curation_packet("Q4", operation_mode="single", depth=1)
print(f"Created packet {packet['packet_id']} with {len(packet['data']['entities'])} entities")

# 3. Map entities to Wikidata QIDs and charge
qid_map = {entity["id"]: "Q195562" for entity in packet["data"]["entities"]}  # Cherokee Nation
charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)

# 4. Check for issues
errors = [n for n in notices if n.severity == "error"]
warnings = [n for n in notices if n.severity == "warning"]
print(f"Charged: {len(charged_packet['data']['entities'])} entities, {len(errors)} errors, {len(warnings)} warnings")

# Now packet is ready for validation or review
```

See [Still Charger API](still_charger.md) for packet-assembly and charging documentation.

### Configure SpiritSafe Source

```python
from gkc.spirit_safe import set_spirit_safe_source, get_spirit_safe_source

set_spirit_safe_source(mode="github", github_repo="skybristol/SpiritSafe", github_ref="main")
print(get_spirit_safe_source())
```

```python
from gkc.spirit_safe import set_spirit_safe_source

set_spirit_safe_source(mode="local", local_root="/path/to/SpiritSafe")
```

### Load JSON Profiles and Build Profile Packages

```python
from gkc.spirit_safe import load_profile, load_profile_package

profile = load_profile("Q4")
print(profile["entity"])

package = load_profile_package("Q4", depth=1)
print(package["primary_profile"])
print(sorted(package["profiles"].keys()))
```

### Resolve Profile Links and Graph Traversal

```python
from gkc.spirit_safe import resolve_profile_link

link = resolve_profile_link("Q4", "Q40")
print(link)
```

### Create and Validate Curation Packets

```python
from gkc.spirit_safe import validate_packet_structure
from gkc.still_charger import create_curation_packet

# Creates an EMPTY scaffold with entity slots defined by the profile
packet = create_curation_packet("Q4", operation_mode="bulk", depth=1)
is_valid, errors = validate_packet_structure(packet)
print(packet["packet_id"], is_valid, errors)

# Packets are empty at this point - no data values populated
# To populate with Wikidata or other source data, see still_charger.charge_packet_from_wikidata_items()
for entity in packet["data"]["entities"]:
    print(entity["id"], "data:" if entity.get("data") else "empty")
```

**Important:** `create_curation_packet()` returns an **empty scaffold**. To populate it with data from Wikidata or other sources, use the **Still Charger** module:

```python
from gkc.still_charger import charge_packet_from_wikidata_items

qid_map = {entity["id"]: "Q195562" for entity in packet["data"]["entities"]}
charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)
```

See [Still Charger API](still_charger.md) for complete documentation on charging packets.

### Export JSON Profiles from Cache Entities

```python
from gkc.spirit_safe import export_entity_profile_json_documents

result = export_entity_profile_json_documents(
    cache_entities_dir="/path/to/SpiritSafe/still/entities",
    output_dir="/path/to/SpiritSafe/still/profiles",
)
print(result.written_ids)
```

When `cache_entities_dir` is part of a normal SpiritSafe checkout, the exporter loads `config/semantic_anchors.json` and the local meta-wikibase config automatically and uses them to resolve internal ontology concepts such as profile class, statement links, prompts, and value-list classification.

For the full concept, lifecycle, and runtime boundary, see [Semantic Anchors](../../architecture/meta-wikibase/semantic-anchors.md).

If you are building from an ad hoc cache directory outside the standard SpiritSafe layout, pass an explicit semantic anchor document:

```python
from gkc.spirit_safe import build_entity_profile_json_documents

anchors = {
    "entities": {
        "_instance_of": {"id": "P1", "datatype": "wikibase-item"},
        "_entity_profile": {"id": "Q3"},
        "_has_statement": {"id": "P157", "datatype": "wikibase-item"},
        "_name_identifier": {"id": "P214", "datatype": "string"},
    }
}

documents = build_entity_profile_json_documents(
    cache_entities_dir="/tmp/still/entities",
    semantic_anchor_document=anchors,
)
```

### Hydrate Value Lists from Cache Entities

```python
from gkc.spirit_safe import hydrate_value_lists_from_cache

result = hydrate_value_lists_from_cache(
    cache_entities_dir="/path/to/SpiritSafe/still/entities",
    queries_dir="/path/to/SpiritSafe/still/value_lists/queries",
    cache_queries_dir="/path/to/SpiritSafe/still/value_lists/cache",
)
print(result.hydrated_ids)
```

## Public API Reference

### Configuration

::: gkc.spirit_safe.SpiritSafeSourceConfig

::: gkc.spirit_safe.set_spirit_safe_source

::: gkc.spirit_safe.get_spirit_safe_source

### Registry Metadata and Lookups

::: gkc.spirit_safe.list_profiles

::: gkc.spirit_safe.profile_exists

::: gkc.spirit_safe.resolve_profile_path

::: gkc.spirit_safe.resolve_query_ref

::: gkc.spirit_safe.LookupCache

::: gkc.spirit_safe.LookupFetcher

### Entity Profile and Value-List Artifacts

::: gkc.spirit_safe.EntityProfileJsonBuilder

::: gkc.spirit_safe.EntityProfileJsonExportResult

::: gkc.spirit_safe.build_entity_profile_json_documents

::: gkc.spirit_safe.export_entity_profile_json_documents

::: gkc.spirit_safe.ValueListHydrationResult

::: gkc.spirit_safe.discover_value_list_ids

::: gkc.spirit_safe.export_value_list_sparql_queries

::: gkc.spirit_safe.hydrate_value_list_query_caches

::: gkc.spirit_safe.hydrate_value_lists_from_cache

### Packet Workflows

::: gkc.spirit_safe.load_profile

::: gkc.spirit_safe.load_profile_package

::: gkc.spirit_safe.resolve_profile_link

::: gkc.spirit_safe.validate_packet_structure

## Theoretical Design Notes

- Packet-level conformance notices shared across charge/barrel/validation are architecturally planned but not yet standardized in a single public type.
- Wizard integration should consume packet structures and value-list routes directly from packet artifacts, without local manifest inference.
