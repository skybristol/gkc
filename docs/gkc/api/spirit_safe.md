# SpiritSafe API

## Overview

The `gkc.spirit_safe` module provides profile registry integration, SPARQL lookup hydration, JSON Entity Profile generation from cache entities, and cache management for SpiritSafe-backed workflows.

This module supports two source modes:

- `github` (default): fetches profile and query assets from the SpiritSafe repository
- `local`: uses a local SpiritSafe clone for branch-based development and testing

## Quick Start

### Loading the Registry Manifest

The manifest is the machine-readable registry of all available profiles. Start by loading it to discover what profiles are available:

```python
from gkc.spirit_safe import load_manifest

# Load manifest from default GitHub source
manifest = load_manifest()

# View available profiles
print(f"Registry contains {len(manifest.profile_ids)} profiles:")
for profile_id in manifest.profile_ids:
    entry = manifest.get_profile_entry(profile_id)
    print(f"  - {profile_id}: {entry.get('name')}")

# Check manifest metadata
print(f"Manifest generated at: {manifest.generated_at}")
print(f"Commit SHA: {manifest.commit_sha}")
```

### Exploring Profile Metadata

Once you have the manifest, you can inspect detailed metadata for any profile:

```python
from gkc.spirit_safe import load_manifest

manifest = load_manifest()

# Get profile metadata
entry = manifest.get_profile_entry("TribalGovernmentUS")

print(f"Name: {entry.get('name')}")
print(f"Version: {entry.get('version')}")
print(f"Description: {entry.get('description')}")
print(f"Related profiles: {entry.get('related_profiles')}")
print(f"Statement linkages: {len(entry.get('statement_linkages', []))}")
```

### Loading a Single Profile

Load a profile's YAML definition to work with its structure:

```python
from gkc.spirit_safe import load_profile

# Load by profile ID
profile_data = load_profile("TribalGovernmentUS")

# Access profile structure
print(f"Profile name: {profile_data.get('name')}")
statement_ids = [s.get("id") for s in profile_data.get("statements", [])]
print(f"Statements: {statement_ids}")

# Access specific statement configuration by id
official_name = next(
    (s for s in profile_data.get("statements", []) if s.get("id") == "official_name"),
    None,
)
if official_name:
    print(f"Official name max_count: {official_name.get('max_count')}")
```

### Loading Profile Packages

Profile packages include the primary profile plus all related profiles at a specified depth, enabling multi-entity curation workflows:

```python
from gkc.spirit_safe import load_profile_package

# Load TribalGovernmentUS with depth 1 (includes related profiles)
package = load_profile_package("TribalGovernmentUS", depth=1)

print(f"Primary profile: {package['primary_profile']}")
print(f"Profiles included: {list(package['profiles'].keys())}")
print(f"Depth: {package['depth']}")

# Access loaded profiles
tribal_profile = package['profiles']['TribalGovernmentUS']
office_profile = package['profiles']['OfficeHeldByHeadOfState']

# Access the profile graph
graph = package['graph']
print(f"Graph has {len(graph.nodes)} nodes")
```

### Working with the Profile Graph

The profile graph represents relationships between profiles, enabling graph traversal and dependency analysis:

Supported `ProfileGraph` methods used in this section:

- `get_neighbors(profile_id)`
- `get_edges(source_profile, target_profile=None)`
- `get_cardinality(source_profile, target_profile)`
- `traverse(start_profile, max_depth=1)`
- `has_profile(profile_id)`
- `profile_count()`

```python
from gkc.spirit_safe import get_profile_graph, load_manifest

manifest = load_manifest()
graph = get_profile_graph(manifest)

# Explore graph structure
print(f"Total nodes: {len(graph.nodes)}")

# Count edges by iterating per-source edges
edge_count = 0
for source_profile in graph.nodes:
    edge_count += len(graph.get_edges(source_profile))
print(f"Total edges: {edge_count}")

# Get neighbors for a specific profile
neighbors = graph.get_neighbors("TribalGovernmentUS")
print(f"TribalGovernmentUS neighbors: {neighbors}")

# Traverse from a profile
reachable = graph.traverse("TribalGovernmentUS", max_depth=1)
print(f"Reachable within depth 1: {reachable}")

# Find all edges
for source_profile in graph.nodes:
    for edge in graph.get_edges(source_profile):
        print(f"{source_profile} -> {edge.target_profile} (via {edge.via_statement})")
```

### Resolving Profile Linkages

Use linkage resolution to find target profiles and cardinality constraints for cross-profile statements:

```python
from gkc.spirit_safe import resolve_profile_link

# Resolve linkage from TribalGovernmentUS to related profile
linkage = resolve_profile_link(
    "TribalGovernmentUS",
    "office_held_by_head_of_state"
)

if linkage:
    print(f"Target profile: {linkage['target_profile']}")
    print(f"Relationship type: {linkage['relationship_type']}")
    print(f"Cardinality min: {linkage['cardinality']['min']}")
    print(f"Cardinality max: {linkage['cardinality']['max']}")
    
    # Check workflow policy
    policy = linkage.get('workflow_policy', {})
    print(f"Creation mode: {policy.get('creation_mode')}")
    print(f"Required: {policy.get('required')}")
```

### Creating Curation Packets

Curation packets are self-contained work units for multi-entity workflows, containing entity scaffolds, cross-references, and cardinality constraints:

```python
from gkc.spirit_safe import create_curation_packet

# Create a single-entity packet
packet = create_curation_packet(
    profile_id="TribalGovernmentUS",
    operation_mode="single"
)

print(f"Packet ID: {packet['packet_id']}")
print(f"Operation mode: {packet['operation_mode']}")
print(f"Entities: {len(packet['entities'])}")

# Create a bulk packet with related profiles
bulk_packet = create_curation_packet(
    profile_id="TribalGovernmentUS",
    operation_mode="bulk",
    depth=1
)

print(f"Bulk packet ID: {bulk_packet['packet_id']}")
print(f"Entities: {len(bulk_packet['entities'])}")
print(f"Cross-references: {len(bulk_packet['cross_references'])}")

# Inspect packet structure
for entity in bulk_packet['entities']:
    print(f"  Entity {entity['id']}: {entity['profile']}")

for cross_ref in bulk_packet['cross_references']:
    print(f"  {cross_ref['from_profile']} -> {cross_ref['to_profile']}")
    print(f"    via: {cross_ref['via_statement']}")
    print(f"    cardinality: {cross_ref['cardinality']}")
```

### Validating Packet Structure

Validate that a curation packet is well-formed and satisfies all structural constraints:

```python
from gkc.spirit_safe import create_curation_packet, validate_packet_structure

# Create a packet
packet = create_curation_packet(
    profile_id="TribalGovernmentUS",
    operation_mode="bulk",
    depth=1
)

# Validate packet structure
is_valid, errors = validate_packet_structure(packet)

if is_valid:
    print("✓ Packet is valid")
else:
    print("✗ Packet validation failed:")
    for error in errors:
        print(f"  - {error}")
```

### Using Local SpiritSafe for Development

When working on profile development, switch to a local SpiritSafe clone:

```python
from gkc.spirit_safe import load_manifest, load_profile_package
import gkc

# Switch to local mode
gkc.set_spirit_safe_source(
    mode="local",
    local_root="/path/to/SpiritSafe"
)

# Now all operations use local files
manifest = load_manifest()
package = load_profile_package("TribalGovernmentUS", depth=1)

# Switch back to GitHub mode
gkc.set_spirit_safe_source(mode="github")
```

### Saving and Loading Packets

Curation packets can be serialized to JSON for persistence and sharing:

```python
import json
from gkc.spirit_safe import create_curation_packet, validate_packet_structure

# Create and save a packet
packet = create_curation_packet(
    profile_id="TribalGovernmentUS",
    operation_mode="bulk",
    depth=1
)

with open("curation_packet.json", "w") as f:
    json.dump(packet, f, indent=2, default=str)

# Load and validate a saved packet
with open("curation_packet.json", "r") as f:
    loaded_packet = json.load(f)

is_valid, errors = validate_packet_structure(loaded_packet)
print(f"Loaded packet is valid: {is_valid}")
```

### Building JSON Entity Profiles from Cache Entities

Build in-memory JSON Entity Profile documents directly from SpiritSafe `cache/entities` data:

```python
from gkc.spirit_safe import build_entity_profile_json_documents

docs = build_entity_profile_json_documents(
    "/path/to/SpiritSafe/cache/entities"
)

print(len(docs))
print(docs[0]["entity"])
```

### Exporting JSON Entity Profiles to Files

Write one JSON file per profile QID (`<output>/<QID>.json`):

```python
from gkc.spirit_safe import export_entity_profile_json_documents

result = export_entity_profile_json_documents(
    cache_entities_dir="/path/to/SpiritSafe/cache/entities",
    output_dir="/path/to/SpiritSafe/profiles",
)

print(result.output_dir)
print(result.written_ids)
```

Optional `profile_ids` filtering is supported:

```python
from gkc.spirit_safe import export_entity_profile_json_documents

result = export_entity_profile_json_documents(
    cache_entities_dir="/path/to/SpiritSafe/cache/entities",
    output_dir="/path/to/SpiritSafe/profiles",
    profile_ids=["Q4", "Q39"],
)

print(result.written_ids)
```

## Public API Quick Starts by Route

### `set_spirit_safe_source` and `get_spirit_safe_source`

```python
from gkc.spirit_safe import set_spirit_safe_source, get_spirit_safe_source

set_spirit_safe_source(mode="github", github_repo="skybristol/SpiritSafe", github_ref="main")
source = get_spirit_safe_source()
print(source.mode, source.github_repo, source.github_ref)
```

### `list_profiles`, `profile_exists`, and `get_profile_metadata`

```python
from gkc.spirit_safe import list_profiles, profile_exists, get_profile_metadata

profiles = list_profiles()
print(profiles)

if profile_exists("TribalGovernmentUS"):
    metadata = get_profile_metadata("TribalGovernmentUS")
    print(metadata.name, metadata.version, metadata.status)
```

### `resolve_profile_path` and `resolve_query_ref`

```python
from gkc.spirit_safe import resolve_profile_path, resolve_query_ref

profile_path = resolve_profile_path("TribalGovernmentUS")
query_path = resolve_query_ref("queries/wikidata_language_items_en.sparql", profile_path)
print(profile_path)
print(query_path)
```

### `LookupCache` and `LookupFetcher`

```python
from gkc.spirit_safe import LookupCache, LookupFetcher

cache = LookupCache()
fetcher = LookupFetcher(cache=cache)

query = """
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q5 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language \"en\" . }
}
LIMIT 5
"""

results = fetcher.fetch(query, refresh_policy="manual", max_results=5)
print(len(results))
```

### `hydrate_profile_lookups`

```python
from gkc.spirit_safe import hydrate_profile_lookups, resolve_profile_path

summary = hydrate_profile_lookups(
    [resolve_profile_path("TribalGovernmentUS")],
    dry_run=True,
)

print(summary["profiles_scanned"], summary["lookup_specs_found"], summary["unique_queries"])
```

### `Manifest` and `load_manifest`

```python
from gkc.spirit_safe import load_manifest

manifest = load_manifest()
print(manifest.generated_at, manifest.commit_sha)
print(manifest.profile_ids)
print(manifest.get_profile_entry("TribalGovernmentUS"))
```

### `load_profile` and `load_profile_package`

```python
from gkc.spirit_safe import load_profile, load_profile_package

profile = load_profile("TribalGovernmentUS")
package = load_profile_package("TribalGovernmentUS", depth=1)

print(profile.get("name"))
print(package["primary_profile"], sorted(package["profiles"].keys()))
```

### `get_profile_graph` and `resolve_profile_link`

```python
from gkc.spirit_safe import get_profile_graph, resolve_profile_link

graph = get_profile_graph()
print(graph.profile_count())

linkage = resolve_profile_link("TribalGovernmentUS", "office_held_by_head_of_state")
print(linkage)
```

### `create_curation_packet` and `validate_packet_structure`

```python
from gkc.spirit_safe import create_curation_packet, validate_packet_structure

packet = create_curation_packet(
    profile_id="TribalGovernmentUS",
    operation_mode="bulk",
    depth=1,
)

is_valid, errors = validate_packet_structure(packet)
print(packet["packet_id"], packet["operation_mode"], is_valid, errors)
```

## Source Configuration

### `SpiritSafeSourceConfig`

::: gkc.spirit_safe.SpiritSafeSourceConfig
    options:
      show_root_heading: false
      heading_level: 4

### `set_spirit_safe_source`

::: gkc.spirit_safe.set_spirit_safe_source
    options:
      show_root_heading: false
      heading_level: 4

### `get_spirit_safe_source`

::: gkc.spirit_safe.get_spirit_safe_source
    options:
      show_root_heading: false
      heading_level: 4

## Profile Registry Access

### `ProfileMetadata`

::: gkc.spirit_safe.ProfileMetadata
    options:
      show_root_heading: false
      heading_level: 4

### `list_profiles`

::: gkc.spirit_safe.list_profiles
    options:
      show_root_heading: false
      heading_level: 4

### `profile_exists`

::: gkc.spirit_safe.profile_exists
    options:
      show_root_heading: false
      heading_level: 4

### `get_profile_metadata`

::: gkc.spirit_safe.get_profile_metadata
    options:
      show_root_heading: false
      heading_level: 4

## Path and Query Resolution

### `resolve_profile_path`

::: gkc.spirit_safe.resolve_profile_path
    options:
      show_root_heading: false
      heading_level: 4

### `resolve_query_ref`

::: gkc.spirit_safe.resolve_query_ref
    options:
      show_root_heading: false
      heading_level: 4

## Lookup Hydration and Caching

### `hydrate_profile_lookups`

::: gkc.spirit_safe.hydrate_profile_lookups
    options:
      show_root_heading: false
      heading_level: 4

### `LookupCache`

::: gkc.spirit_safe.LookupCache
    options:
      show_root_heading: false
      heading_level: 4

### `LookupFetcher`

::: gkc.spirit_safe.LookupFetcher
    options:
      show_root_heading: false
      heading_level: 4

## Manifest and Curation Workflows

### `EntityProfileJsonBuilder`

::: gkc.spirit_safe.EntityProfileJsonBuilder
        options:
            show_root_heading: false
            heading_level: 4

### `EntityProfileJsonExportResult`

::: gkc.spirit_safe.EntityProfileJsonExportResult
        options:
            show_root_heading: false
            heading_level: 4

### `build_entity_profile_json_documents`

::: gkc.spirit_safe.build_entity_profile_json_documents
        options:
            show_root_heading: false
            heading_level: 4

### `export_entity_profile_json_documents`

::: gkc.spirit_safe.export_entity_profile_json_documents
        options:
            show_root_heading: false
            heading_level: 4

### `Manifest`

::: gkc.spirit_safe.Manifest
    options:
      show_root_heading: false
      heading_level: 4

### `load_manifest`

::: gkc.spirit_safe.load_manifest
    options:
      show_root_heading: false
      heading_level: 4

### `load_profile`

::: gkc.spirit_safe.load_profile
    options:
      show_root_heading: false
      heading_level: 4

### `load_profile_package`

::: gkc.spirit_safe.load_profile_package
    options:
      show_root_heading: false
      heading_level: 4

### `get_profile_graph`

::: gkc.spirit_safe.get_profile_graph
    options:
      show_root_heading: false
      heading_level: 4

### `resolve_profile_link`

::: gkc.spirit_safe.resolve_profile_link
    options:
      show_root_heading: false
      heading_level: 4

### `create_curation_packet`

::: gkc.spirit_safe.create_curation_packet
    options:
      show_root_heading: false
      heading_level: 4

### `validate_packet_structure`

::: gkc.spirit_safe.validate_packet_structure
    options:
      show_root_heading: false
      heading_level: 4

## Usage Examples

### Use default GitHub source

```python
import gkc

source = gkc.get_spirit_safe_source()
print(source.mode)  # github
profiles = gkc.list_profiles()
print(profiles)
```

### Use local clone for branch testing

```python
import gkc

gkc.set_spirit_safe_source(
    mode="local",
    local_root="/path/to/SpiritSafe"
)

metadata = gkc.get_profile_metadata("TribalGovernmentUS")
print(metadata.version)
```

### Hydrate lookups from profile names

```python
import gkc

summary = gkc.hydrate_profile_lookups(
    [gkc.resolve_profile_path("TribalGovernmentUS")],
    dry_run=True,
)
print(summary["unique_queries"])
```
