# Phase 3 Implementation Complete - Handoff Notes

**Date**: 2026-03-04  
**Status**: Phase 3 Complete ✅ (spirit_safe module, manifest loading, profile packages, curation packets)

---

## Phase 3 Implementation Summary

**What Was Implemented**:

### Core Functions (gkc/spirit_safe.py)
1. **`load_manifest()`** - Load SpiritSafe registry manifest from GitHub or local source with caching
2. **`load_profile(profile_id)`** - Load individual profile YAML
3. **`load_profile_package(profile_id, depth)`** - Load primary profile + related profiles at specified depth
4. **`get_profile_graph()`** - Build complete ProfileGraph from manifest
5. **`resolve_profile_link(source_profile, statement_id)`** - Resolve cross-profile linkage metadata
6. **`create_curation_packet(profile_id, mode, depth)`** - Create multi-entity work units with scaffolds, cross-references, and cardinality constraints
7. **`validate_packet_structure(packet)`** - Validate packet structure and cardinality feasibility

### Data Models
- **`Manifest` dataclass** - Represents loaded registry with profile metadata and relationships
- **`ProfileGraph` model** (from Phase 2) - Integrated for graph traversal
- **Entity scaffolds** in packets - Profile structure for Wizard form generation

### Testing Summary
- 20 comprehensive tests covering all Phase 3 functions
- Integration tests demonstrating full workflow: manifest → profile → package → packet
- Validation tests for packet structure and cardinality constraints
- **All 237 gkc tests passing**

---

## Handoff Notes for Wizard Engineer (Phase 4 Multi-Entity UI Development)

### Available APIs

**Profile Loading**:
```python
from gkc.spirit_safe import load_profile_package, create_curation_packet

# Load primary profile + related profiles at specified depth
package = load_profile_package(profile_id="TribalGovernmentUS", depth=1)
# Returns:
# {
#     "primary_profile": "TribalGovernmentUS",
#     "profiles": {...profiles dict...},
#     "graph": ProfileGraph(...),
#     "manifest_commit_sha": "...",
#     "depth": 1
# }
```

**Packet Creation**:
```python
# Create multi-entity work unit with entity scaffolds and cross-references
packet = create_curation_packet(
    profile_id="TribalGovernmentUS",
    operation_mode="single" or "bulk",
    depth=1
)
# Returns:
# {
#     "packet_id": "pkt-...",
#     "operation_mode": "single",
#     "created_at": "ISO 8601",
#     "entities": [
#         {
#             "id": "ent-001",
#             "profile": "TribalGovernmentUS",
#             "data": {},  # Curator fills in
#             "profile_structure": {"statements": {...}}
#         },
#         # ... more entities in multi-entity packet
#     ],
#     "cross_references": [
#         {
#             "from": "ent-001",
#             "to": "ent-002",
#             "via_statement": "office_held_by_head_of_state",
#             "cardinality": {"min": 0, "max": 1},
#             "workflow_policy": {...}
#         }
#     ],
#     "cardinality_constraints": [
#         {
#             "from": "ent-001",
#             "to": "ent-002",
#             "min": 0,
#             "max": 1
#         }
#     ],
#     "profile_package": {...package data...}
# }
```

**Packet Validation**:
```python
from gkc.spirit_safe import validate_packet_structure

is_valid, errors = validate_packet_structure(packet)
if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

### API Patterns

- All functions work with GitHub (default) or local SpiritSafe source
- Source configurable via `set_spirit_safe_source(mode, github_repo, local_root)`
- Manifest loaded once and cached in-memory for performance
- ProfileGraph provides: `get_neighbors(profile_id)`, `get_edges(source, target)`, `traverse(start, depth)`

### Design Assumptions

- Packets are immutable at UI level (create fresh packet or edit locally in wizard state)
- Entity order in packet determines tab order / presentation sequence
- Cross-references define which entities must be edited together
- Cardinality constraints should display to curator: "Between 0 and 1 office held by head of state"
- Each entity in packet has `profile_structure` containing statement definitions for form generation

### Implementation Steps for Phase 4

1. **Initialize wizard with packet**: Consume `create_curation_packet()` to bootstrap multi-entity session
2. **Multi-entity navigation**: Implement UI to switch between entities in packet (sidebar/tab selection)
3. **Entity form rendering**: Use `profile_structure` from each entity for form generation
4. **Cross-entity linkage display**: Show in context "This office is held by TribalGovernmentUS (ent-001)"
5. **Packet validation**: Call `validate_packet_structure()` before allowing submission
6. **Packet serialization**: Persist packet state during curation session

### Key Integration Points

- Import from `gkc.spirit_safe` module (not internal submodules)
- Use `ProfileGraph` for understanding entity relationships
- Entity IDs in packet always follow `ent-XXX` pattern (3-digit zero-padded)
- Cross-references include cardinality information for UI warnings

---

## Handoff Notes for Validation Agent (Packet-Level Validation)

### Available Data Structures

**Manifest Data** (from `load_manifest()`):
- Profile registry with metadata, graph declarations, statement linkages
- Provides authoritative source for cross-profile relationship rules

**ProfileGraph** (from gkc/profiles/graph.py):
- Queryable model of profile relationships
- Methods: `get_neighbors()`, `get_edges()`, `traverse()`
- Used for understanding multi-entity structures

**Curation Packet Structure**:
```python
packet = {
    "entities": [
        {
            "id": "ent-001",
            "profile": "TribalGovernmentUS",
            "data": {...curator_supplied_data...},
            "profile_structure": {"statements": {...}}
        },
        {
            "id": "ent-002",
            "profile": "OfficeHeldByHeadOfState",
            "data": {...},
            "profile_structure": {"statements": {...}}
        }
    ],
    "cross_references": [
        {
            "from": "ent-001",
            "to": "ent-002",
            "via_statement": "office_held_by_head_of_state",
            "cardinality": {"min": 0, "max": 1}
        }
    ],
    "cardinality_constraints": [
        {
            "from": "ent-001",
            "to": "ent-002",
            "min": 0,
            "max": 1
        }
    ]
}
```

### Key Integration Points

**Packet Structure Validation** (already available):
- Use `validate_packet_structure(packet)` for basic checks
- Returns list of errors if structure is invalid

**Cardinality Enforcement**:
- Each `cardinality_constraint` in packet has `min` and `max` values
- Validate that number of linked entities matches constraints
- Prevent saving packets that violate cardinality rules

**Statement-Level Validation**:
- Existing `validate_value()` methods apply within each entity's statements
- Apply validation to each entity in `packet["entities"]` independently

**Cross-Entity Validation** (future enhancement):
- Check cross-entity references and reciprocal awareness
- Validate consistency between primary and related entities
- Enforce any cross-profile constraints from profile_graph metadata

### Validation Implementation Approach

1. **Per-Entity Validation**: Apply existing statement validation to each entity
2. **Cardinality Validation**: Check count of linked entities against constraints
3. **Cross-Reference Validation**: Ensure cross-references point to valid entities
4. **Reciprocal Awareness**: Check that bidirectional edges are properly represented

### Expected Test Scenarios

- Single-entity packet (no cross-references)
- Multi-entity packet with 0 related entities (constraint fulfilled)
- Multi-entity packet with 1 related entity (max=1 constraint)
- Multi-entity packet with too many related entities (constraint violation)
- Cardinality min not met (insufficient related entities)
- Invalid cross-references (point to nonexistent entities)

### Testing Strategy

- Use `create_curation_packet()` in tests to generate realistic packets
- Generate packets with various cardinality scenarios
- Validate both passing and failing cases
- Test error messages are clear and actionable

---

## Architecture Notes for Future Enhancement

### Curation Packet Post-MVP Features

**Load Wikidata Items into Packet** (design noted, not yet implemented):
```python
packet = create_curation_packet("TribalGovernmentUS")
hydrated_packet = load_wikidata_qids_into_packet(packet, qids=["Q123", "Q456"])
# Now packet["entities"][0]["data"] contains pre-populated Wikidata values
```

This enables:
- Editing existing Wikidata items through wizard
- Fetching related items automatically (traverse statement values)
- Batch updates via same UI

**Export Packet to Target Systems**:
```python
wikidata_batch = export_packet_to_wikidata_json(packet)
quickstatements = export_packet_to_quickstatements(packet) 
osm_changeset = export_packet_to_osm(packet)
```

These functions would use shipper module logic and profile metadata to transform curator data into target system formats.

### Schema Considerations

**Potential Additions to SpiritSafe Profiles**:
- Statement-level `reverse_linkage` hint to declare bidirectional awareness
- Profile-level `curation_workflow` guidance (e.g., "prefer existing" vs "create new")
- Cross-profile cardinality expressions for complex constraints (e.g., 1:many linkages)

---

## CLI Commands (For Future Implementation)

The spirit_safe module provides foundation for these CLI commands:

```bash
# Registry operations
gkc registry list                          # List available profiles
gkc registry graph <profile>               # Show profile relationships
gkc registry info                          # Show manifest metadata

# Profile packages
gkc profile package load <profile> --depth N  # Load primary + related profiles
gkc profile package cardinality <profile>    # Show linkage cardinality rules

# Curation packets
gkc packet create <profile>                # Create curation packet
gkc packet validate <packet.json>          # Validate packet structure
gkc packet info <packet.json>              # Inspect packet contents
gkc packet load-wikidata <packet.json> --qid Q...  # (Future) Hydrate with Wikidata
gkc packet export <packet.json> --format wikidata_json|quickstatements  # (Future)
```

CLI implementation is blocked on Wizard Engineer UI work (to understand full workflow), but spirit_safe APIs are ready.

---

## Test Coverage Summary

**Phase 3 test file**: `tests/test_spirit_safe_phase3.py` (20 tests)

**Test categories**:
- Manifest loading and caching
- Profile YAML loading
- Profile package loading with graph
- Profile graph operations
- Cross-profile linkage resolution
- Single-entity curation packet creation
- Multi-entity curation packet creation with cardinality
- Packet structure validation
- Integration tests (manifest → profile → package → packet workflow)

**All tests passing**: ✅ (20/20 test_spirit_safe_phase3.py + 237 total gkc tests)

---

**Status**: Phase 3 Implementation Complete ✅  
**Last Updated**: 2026-03-04  
**Next**: Wizard Engineer Phase 4 (multi-entity UI development)
