# SpiritSafe API

## Overview

`gkc.spirit_safe` provides SpiritSafe source configuration, lookup hydration, JSON Entity Profile export, value-list hydration, artifact-manifest indexing, and curation packet scaffolding.

Current architecture:

- Runtime packet assembly loads `profiles/<QID>.json` directly.
- `cache/manifest.json` is a tooling/discovery index.
- Value lists are materialized in `cache/queries/<QID>.json` and consumed as cache artifacts.

## Quick Start

### Complete Workflow: Create, Charge, and Validate a Packet

The typical workflow for curation involves three stages:

1. **Create** — Scaffold packet from profile (spirit_safe module)
2. **Charge** — Populate packet with data from Wikidata (still_charger module)
3. **Validate** — Check completeness and constraints (validation module)

```python
from pathlib import Path
from gkc.spirit_safe import create_curation_packet, set_spirit_safe_source
from gkc.still_charger import charge_packet_from_wikidata_items

# 1. Configure source
set_spirit_safe_source(mode="local", local_root="/path/to/SpiritSafe")

# 2. Create empty scaffold from profile Q4 (TribalGovernmentUS)
packet = create_curation_packet("Q4", operation_mode="single", depth=1)
print(f"Created packet {packet['packet_id']} with {len(packet['entities'])} entities")

# 3. Map entities to Wikidata QIDs and charge
qid_map = {entity["id"]: "Q195562" for entity in packet["entities"]}  # Cherokee Nation
charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)

# 4. Check for issues
errors = [n for n in notices if n.severity == "error"]
warnings = [n for n in notices if n.severity == "warning"]
print(f"Charged: {len(charged_packet['entities'])} entities, {len(errors)} errors, {len(warnings)} warnings")

# Now packet is ready for validation or review
```

See [Still Charger API](still_charger.md) for detailed charging documentation.

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

### Build and Export Artifact Manifest

```python
from gkc.spirit_safe import (
    build_spiritsafe_manifest_document,
    export_spiritsafe_manifest,
)

manifest_doc = build_spiritsafe_manifest_document("/path/to/SpiritSafe")
print(manifest_doc["entities"]["count"])

written = export_spiritsafe_manifest("/path/to/SpiritSafe")
print(len(written["profiles"]))
```

### Load Manifest for Registry Tooling

```python
from gkc.spirit_safe import load_manifest

manifest = load_manifest()
print(manifest.generated_at)
print(manifest.profile_qids)
print(manifest.get_profile_entry("Q4"))
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
from gkc.spirit_safe import get_profile_graph, resolve_profile_link

graph = get_profile_graph()
print(graph.get_neighbors("Q4"))

link = resolve_profile_link("Q4", "Q40")
print(link)
```

### Create and Validate Curation Packets

```python
from gkc.spirit_safe import create_curation_packet, validate_packet_structure

# Creates an EMPTY scaffold with entity slots defined by the profile
packet = create_curation_packet("Q4", operation_mode="bulk", depth=1)
is_valid, errors = validate_packet_structure(packet)
print(packet["packet_id"], is_valid, errors)

# Packets are empty at this point - no data values populated
# To populate with Wikidata or other source data, see still_charger.charge_packet_from_wikidata_items()
for entity in packet["entities"]:
    print(entity["id"], "data:" if entity["data"] else "empty")
```

**Important:** `create_curation_packet()` returns an **empty scaffold**. To populate it with data from Wikidata or other sources, use the **Still Charger** module:

```python
from gkc.still_charger import charge_packet_from_wikidata_items

qid_map = {entity["id"]: "Q195562" for entity in packet["entities"]}
charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)
```

See [Still Charger API](still_charger.md) for complete documentation on charging packets.

### Export JSON Profiles from Cache Entities

```python
from gkc.spirit_safe import export_entity_profile_json_documents

result = export_entity_profile_json_documents(
    cache_entities_dir="/path/to/SpiritSafe/cache/entities",
    output_dir="/path/to/SpiritSafe/profiles",
)
print(result.written_ids)
```

### Hydrate Value Lists from Cache Entities

```python
from gkc.spirit_safe import hydrate_value_lists_from_cache

result = hydrate_value_lists_from_cache(
    cache_entities_dir="/path/to/SpiritSafe/cache/entities",
    queries_dir="/path/to/SpiritSafe/queries",
    cache_queries_dir="/path/to/SpiritSafe/cache/queries",
)
print(result.hydrated_ids)
```

## Public API Reference

### Configuration

::: gkc.spirit_safe.SpiritSafeSourceConfig

::: gkc.spirit_safe.set_spirit_safe_source

::: gkc.spirit_safe.get_spirit_safe_source

### Registry Metadata and Lookups

::: gkc.spirit_safe.ProfileMetadata

::: gkc.spirit_safe.list_profiles

::: gkc.spirit_safe.profile_exists

::: gkc.spirit_safe.get_profile_metadata

::: gkc.spirit_safe.resolve_profile_path

::: gkc.spirit_safe.resolve_query_ref

::: gkc.spirit_safe.LookupCache

::: gkc.spirit_safe.LookupFetcher

::: gkc.spirit_safe.hydrate_profile_lookups

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

### Manifest and Packet Workflows

::: gkc.spirit_safe.Manifest

::: gkc.spirit_safe.build_spiritsafe_manifest_document

::: gkc.spirit_safe.export_spiritsafe_manifest

::: gkc.spirit_safe.load_manifest

::: gkc.spirit_safe.load_profile

::: gkc.spirit_safe.load_profile_package

::: gkc.spirit_safe.get_profile_graph

::: gkc.spirit_safe.resolve_profile_link

::: gkc.spirit_safe.create_curation_packet

::: gkc.spirit_safe.validate_packet_structure

## Theoretical Design Notes

- Packet-level conformance notices shared across charge/barrel/validation are architecturally planned but not yet standardized in a single public type.
- Wizard integration should consume packet structures and value-list routes directly from packet artifacts, without local manifest inference.
