---
title: Spirit Safe Integration Architecture
description: Technical design for profile graph, linkage metadata, and multi-entity workflows
---

# Spirit Safe Integration Architecture

This document describes the technical architecture for integrating SpiritSafe registry data into GKC for multi-entity curation workflows. It covers profile graphs, linkage metadata, and data models for multi-entity workflows.

## Overview

The architecture comprises three interconnected layers:

**Registry Infrastructure** (SpiritSafe):
- Manifest builder that generates `cache/manifest.json` from profile directories
- Profile YAML with linkage metadata at the statement level
- Metadata YAML with profile_graph sections showing bidirectional relationships

**Python Models** (gkc/profiles/models.py):
- Pydantic models to parse linkage metadata from profiles
- ProfileGraph model to traverse relationships between profiles
- Helper methods on ProfileDefinition for multi-entity operations

**High-Level APIs** (spirit_safe module):
- Manifest loading and caching
- Profile package loading (primary + related)
- Curation packet creation with cross-references
- Graph-aware validation

---

## Linkage Metadata Models

Linkage metadata defines cross-profile relationships at the statement level. It consists of four layered Pydantic models in `gkc/profiles/models.py`:

### LinkageRelationship

```python
class LinkageRelationship(BaseModel):
    type: str  # Relationship identifier (e.g., "office_of_head_of_state")
    direction: Literal["unidirectional", "bidirectional"]
    reverse_statement_hint: Optional[str]  # Hint for reverse traversal
```

**Purpose**: Describe the nature of the relationship and how to traverse it bidirectionally.

**Example** (from TribalGovernmentUS):
```yaml
relationship:
  type: office_of_head_of_state
  direction: bidirectional
  reverse_statement_hint: applies_to_jurisdiction  # OfficeHeldByHeadOfState uses this
```

### LinkageCardinality

```python
class LinkageCardinality(BaseModel):
    min: int = 0  # Minimum linked entities required
    max: int = 1  # Maximum linked entities allowed
```

**Purpose**: Enforce constraints on how many linked entities are allowed.

**Examples**:
- `min=0, max=1`: Optional link to exactly one related entity
- `min=1, max=1`: Required link to exactly one related entity
- `min=0, max=*`: Optional link to unlimited related entities

### LinkageWorkflowPolicy

```python
class LinkageWorkflowPolicy(BaseModel):
    create: bool  # Can curator create new linked entities?
    select_existing: bool  # Can curator select existing entities?
```

**Purpose**: Control what workflow actions are permitted for linked entities.

**Examples**:
- `create=True, select_existing=True`: Can create new or select existing
- `create=False, select_existing=True`: Can only select existing
- `create=True, select_existing=False`: Can only create new

### LinkageTraversal

```python
class LinkageTraversal(BaseModel):
    max_depth: int = 1  # Maximum depth when loading related profiles
```

**Purpose**: Limit how far to traverse when loading multi-entity packages.

**Example**: `max_depth=1` means load only direct neighbors, not transitive relationships.

### StatementLinkage

Combines all four models into complete linkage specification:

```python
class StatementLinkage(BaseModel):
    target_profile: str  # Which profile to link to
    relationship: LinkageRelationship
    cardinality: LinkageCardinality
    workflow_policy: LinkageWorkflowPolicy
    traversal: LinkageTraversal
```

**Location in profile YAML**:
```yaml
statements:
  - id: office_held_by_head_of_state
        io_map:
            - to: https://www.wikidata.org/entity/P1906
    entity_profile: OfficeHeldByHeadOfState  # Link to profile name
    linkage:  # Complete linkage specification
      target_profile: OfficeHeldByHeadOfState
      relationship:
        type: office_of_head_of_state
        direction: bidirectional
        reverse_statement_hint: applies_to_jurisdiction
      cardinality:
        min: 0
        max: 1
      workflow_policy:
        create: allowed  # YAML uses "allowed"/"disallowed" which normalizes to bool
        select_existing: allowed
      traversal:
        max_depth: 1
```

---

## ProfileDefinition Helper Methods

Extended `ProfileDefinition` class with linkage-aware queries:

### get_statement_linkages()

**Return**: List of ProfileFieldDefinition instances that have linkage metadata.

```python
from gkc.profiles.loaders.yaml_loader import ProfileLoader

loader = ProfileLoader()
profile = loader.load_from_file("profile.yaml")

linked_stmts = profile.get_statement_linkages()
for stmt in linked_stmts:
    print(f"{stmt.id} links to {stmt.linkage.target_profile}")
```

### get_linked_profile_names()

**Return**: Sorted list of unique profile names this profile links to.

```python
neighbors = profile.get_linked_profile_names()
# Returns: ["OfficeHeldByHeadOfState"]
```

### get_link_definition(target_profile: str)

**Return**: StatementLinkage instance for specific target, or None.

```python
linkage = profile.get_link_definition("OfficeHeldByHeadOfState")
if linkage:
    print(f"Cardinality: {linkage.cardinality.min}-{linkage.cardinality.max}")
    print(f"Can create: {linkage.workflow_policy.create}")
```

---

## Profile Graph Model

The ProfileGraph model in `gkc/profiles/graph.py` represents the complete network of profile relationships and provides traversal operations.

### Construction

**From manifest data** (most common):
```python
import json
from gkc.profiles.graph import ProfileGraph

with open("manifest.json") as f:
    manifest = json.load(f)

graph = ProfileGraph.from_manifest_data(manifest["profiles"])
```

**From metadata.yaml** (single profile):
```python
import yaml
from gkc.profiles.graph import ProfileGraph

with open("metadata.yaml") as f:
    metadata = yaml.safe_load(f)

graph = ProfileGraph.from_metadata_dict("TribalGovernmentUS", metadata)
```

### Core Data Structures

- `ProfileNode`: Represents a profile with neighbors and outgoing edges
- `GraphEdge`: Directed edge with metadata (target, statement, relationship type, cardinality, traversal)

### Query Operations

**Get neighbors** (profiles directly connected):
```python
neighbors = graph.get_neighbors("TribalGovernmentUS")
# Returns: ["OfficeHeldByHeadOfState"]
```

**Get edges** (relationships with metadata):
```python
# All edges from TribalGovernmentUS
edges = graph.get_edges("TribalGovernmentUS")

# Specific edge
edges = graph.get_edges("TribalGovernmentUS", "OfficeHeldByHeadOfState")
if edges:
    edge = edges[0]
    print(f"Via statement: {edge.via_statement}")
    print(f"Relationship: {edge.relationship_type}")
    print(f"Cardinality: {edge.cardinality}")
```

**Get cardinality** (min/max constraints):
```python
cardinality = graph.get_cardinality("TribalGovernmentUS", "OfficeHeldByHeadOfState")
if cardinality:
    print(f"Min: {cardinality['min']}, Max: {cardinality['max']}")
```

### Traversal

**Depth-limited graph traversal with cycle prevention**:
```python
# Get all profiles reachable within depth 1
reachable = graph.traverse("TribalGovernmentUS", max_depth=1)
# Returns: ["OfficeHeldByHeadOfState"]

# Traversal automatically prevents infinite loops on bidirectional edges
reachable = graph.traverse("TribalGovernmentUS", max_depth=2)
# Still returns only OfficeHeldByHeadOfState (doesn't loop back)
```

**Parameters**:
- `start_profile`: Profile to start from
- `max_depth`: How many hops to traverse (1 = immediate neighbors only)
- `visited`: Internal set for cycle detection (used recursively)

### Validation

**Validate bidirectional awareness** (checks reciprocal declarations):
```python
errors = graph.validate_bidirectional_awareness()
if errors:
    for error in errors:
        print(f"Graph error: {error}")
else:
    print("Graph is valid - all edges have reciprocal awareness")
```

Checks:
1. All target profiles in edges exist in graph
2. All edges from A→B have reciprocal awareness in B's neighbors list
3. Reports missing profiles or unidirectional edges

### Utility Methods

```python
# Check if profile exists
if graph.has_profile("TribalGovernmentUS"):
    print("Profile found")

# Count profiles
count = graph.profile_count()
print(f"Graph has {count} profiles")
```

---

## Design Principles

### 1. Layered Models

Linkage metadata is split into focused models that each handle one concern:
- **Relationship**: What type of connection
- **Cardinality**: How many linked entities
- **WorkflowPolicy**: What actions are allowed
- **Traversal**: How to navigate the graph

This allows the spirit_safe module to apply constraints independently.

### 2. Manifest as Source of Truth

The manifest contains the authoritative graph structure with all metadata. Profiles are loaded on-demand but the graph is built from manifest once.

This enables:
- Fast registry queries without loading all profiles
- Consistent graph structure across all consumers
- Version control via Git SHA in manifest

### 3. Bidirectional Awareness

ProfileGraph enforces bidirectional edge validation to prevent:
- Data inconsistency (A→B without B→A acknowledgment)
- Missing relationships (one-sided declarations)
- Transitive relationship errors

This is validated at:
- Registry build time (CI in SpiritSafe repo)
- Graph loading time (ProfileGraph.validate_bidirectional_awareness())

### 4. Cycle Prevention During Traversal

Traversal uses visited set to prevent infinite loops on bidirectional edges while still allowing multi-hop traversal. This is crucial for:
- Loading profile packages at any depth
- Finding transitive relationships
- Preventing stack overflow on complex graphs

---

## Integration with Higher-Level APIs

The spirit_safe module builds on these models:

### Profile Package Loading
```python
from gkc.spirit_safe import load_profile_package

# Load primary profile + related profiles within depth
package = load_profile_package("TribalGovernmentUS", depth=1)
# Returns: dict with TribalGovernmentUS + OfficeHeldByHeadOfState + graph
```

### Curation Packet Creation
```python
from gkc.spirit_safe import create_curation_packet

# Create multi-entity packet with cross-references
packet = create_curation_packet("TribalGovernmentUS", operation_mode="single")
# Returns: {
#   "entities": [
#     {"id": "ent-001", "profile": "TribalGovernmentUS", "data": {...}},
#     {"id": "ent-002", "profile": "OfficeHeldByHeadOfState", "data": {...}}
#   ],
#   "cross_references": [...],
#   "cardinality_constraints": [...]
# }
```

### Packet Validation
```python
from gkc.spirit_safe import validate_packet

errors = validate_packet(packet, graph)
if errors:
    print("Packet validation failed:", errors)
```

---

## Testing Strategy

### Unit Tests

Test individual models with fixture data from `tests/fixtures/spiritsafe/`:

**Linkage Parsing** (`tests/test_linkage_parsing.py`):
- Load TribalGovernmentUS profile and verify linkage metadata parsed
- Test string→bool coercion for workflow policies
- Test cardinality validation rules
- Test helper methods (get_statement_linkages, get_link_definition)

**Profile Graph** (`tests/test_profile_graph.py`):
- Build graph from manifest.json
- Test neighbor queries
- Test edge queries and filtering
- Test cardinality extraction
- Test depth-limited traversal
- Test cycle prevention
- Test bidirectional validation (valid graphs, broken graphs)

### Integration Tests

Test interactions between models:

- Load profile YAML → parse linkage metadata → verify accessible via ProfileDefinition helpers
- Load manifest → build ProfileGraph → traverse → get cardinality constraints
- Create graph from metadata.yaml → validate against full graph from manifest

### Fixture Strategy

**`tests/fixtures/spiritsafe/`** contains complete SpiritSafe replica:
- Profiles: TribalGovernmentUS + OfficeHeldByHeadOfState (with linkage metadata)
- Manifest: Complete manifest.json with phase_graph sections
- Metadata: metadata.yaml for each profile
- Queries: SPARQL files (for future use)

Fixtures synced from SpiritSafe main branch. Sync tracked by `SYNC_SHA.txt` and `SYNC_DATE.txt`.

---

## Error Handling

### Profile Not Found
- `ProfileGraph.get_edges()` returns empty list (not exception)
- `graph.has_profile()` returns False for query safety

### Graph Validation Failures
- `validate_bidirectional_awareness()` returns list of error messages
- Empty list = valid graph
- Non-empty = validation must be addressed before use

### Cardinality Violations
- Validation Agent will check during packet construction
- Raises ValidationError with specific constraint details
- Suggests fixes (reduce count, add required entity, etc.)

---

## Performance Considerations

### Lazy Loading
- profiles are loaded on-demand (not at graph build time)
- manifest is cached by caller (spirit_safe module will implement)
- graph construction is O(|V| + |E|)

### Traversal Efficiency
- Visited set prevents redundant traversal
- Depth limiting stops search early
- O(V + E) in worst case, but typically limited by max_depth

### Caching Opportunities
- Cache manifest by commit SHA
- Cache loaded profiles by name
- Pre-compute transitive closures if needed

---

## Examples

### Complete Workflow: Load Profile Package and Validate Graph

```python
import json
from gkc.profiles.loaders.yaml_loader import ProfileLoader
from gkc.profiles.graph import ProfileGraph

# 1. Load manifest and build graph
with open("cache/manifest.json") as f:
    manifest = json.load(f)

graph = ProfileGraph.from_manifest_data(manifest["profiles"])

# 2. Validate graph structure
errors = graph.validate_bidirectional_awareness()
if errors:
    print("Graph has validation errors!")
    for error in errors:
        print(f"  - {error}")
else:
    print("Graph is valid")

# 3. Load primary profile with linkage metadata
loader = ProfileLoader()
primary = loader.load_from_file("profiles/TribalGovernmentUS/profile.yaml")

# 4. Get linked profiles to load
linked_names = primary.get_linked_profile_names()
print(f"Linked profiles: {linked_names}")

# 5. For each linked profile, get cardinality constraints
for linked_name in linked_names:
    cardinality = graph.get_cardinality("TribalGovernmentUS", linked_name)
    print(f"  {linked_name}: {cardinality['min']}-{cardinality['max']}")

# 6. Check what actions are allowed
linkage = primary.get_link_definition(linked_names[0])
print(f"Can create new: {linkage.workflow_policy.create}")
print(f"Can select existing: {linkage.workflow_policy.select_existing}")
```

### Inspect Profile Graph Structure

```python
from gkc.profiles.graph import ProfileGraph

graph = ProfileGraph.from_manifest_data(manifest["profiles"])

print(f"Profiles in graph: {graph.profile_count()}")
print(f"Has TribalGovernmentUS: {graph.has_profile('TribalGovernmentUS')}")

neighbors = graph.get_neighbors("TribalGovernmentUS")
print(f"Neighbors: {neighbors}")

edges = graph.get_edges("TribalGovernmentUS")
for edge in edges:
    print(f"  → {edge.target_profile} (via {edge.via_statement})")
    print(f"     Type: {edge.relationship_type}")
    print(f"     Cardinality: {edge.cardinality}")

reachable = graph.traverse("TribalGovernmentUS", max_depth=2)
print(f"Reachable within depth 2: {reachable}")
```

---

## See Also

- [Profile Loading Architecture](profile-loading.md) — How GKC loads and parses profiles
- [SpiritSafe Registry Architecture](SpiritSafe.md) — Registry design and manifest builder
- [SpiritSafe Testing Strategy](SpiritSafe-testing.md) — Test fixture approach
- [GKC Entity Profiles](../gkc/profiles.md) — Profile YAML schema reference

---

**Last Updated**: March 4, 2026  
**Status**: Implementation complete, documentation in progress  
**Related Documentation**: UserDocWriter.working.md for curator-facing guides
