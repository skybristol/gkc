# SpiritSafe Testing Architecture

**Purpose**: Document the testing strategy for GKC's integration with SpiritSafe, including test fixture management, sync strategies, and best practices for local development without network dependencies.

---

## Overview

GKC's functionality depends deeply on SpiritSafe profiles—for validation, wizard generation, CLI operations, and data transformation. To enable robust, fast, and network-independent testing, GKC maintains a **local replica of the SpiritSafe registry structure** at `tests/fixtures/spiritsafe/`.

This document describes:

- Why we need a complete local SpiritSafe replica (not just profile JSON files)
- How test profiles are managed in the canonical SpiritSafe repository
- How the fixture sync process works (manual and automated)
- Testing patterns and best practices

---

## Why a Complete Local SpiritSafe Replica?

### The Problem

GKC's profile registry and curation functionality (and beyond) requires:

- **Profile loading**: Load JSON profile artifacts + metadata
- **Manifest operations**: Discover profiles, query registry metadata
- **Profile graphs**: Traverse relationships between profiles
- **Curation packets**: Create multi-entity work units with cross-references
- **Query hydration**: Load SPARQL queries and cached results for allowed-items lists
- **CLI operations**: Registry discovery, packet creation, validation

Testing these features requires access to:

1. Multiple interconnected profiles (with real linkage metadata)
2. A valid manifest.json (generated from profiles)
3. SPARQL query files (for choice lists)
4. Cached query results (for hydration testing)
5. Profile metadata objects embedded in profile JSON artifacts (for version/authorship info)

### The Solution

**Local SpiritSafe Replica**: `gkc/tests/fixtures/spiritsafe/`

This is a **complete mirror** of the SpiritSafe repository structure, containing:

```
tests/fixtures/spiritsafe/
├── profiles/
│   ├── Q4.json                        # Tribal Government profile artifact
│   ├── Q39.json                       # Office profile artifact
│   └── ...
├── cache/
│   ├── entities/                      # Raw Wikibase cache entities
│   ├── queries/                       # Hydrated value-list results
│   ├── manifest.json                  # Generated artifact manifest
│   └── entity_index.json              # Normalized derived index
└── queries/                           # SPARQL query files
```

**Benefits**:

- ✅ **No network dependency**: Tests run offline, fast, and reliably
- ✅ **Version stability**: Fixtures are pinned to specific profile versions (via sync process)
- ✅ **Complete coverage**: All GKC features can be tested (manifest, graphs, packets, queries)
- ✅ **Reproducible**: Every developer and CI environment gets identical fixtures
- ✅ **Self-contained**: No external dependencies on GitHub API or live SpiritSafe repo

---

## Test Profile Strategy: Purpose-Built Profiles in SpiritSafe

### Dual-Purpose Test Profiles

Rather than creating synthetic test data only for GKC, we maintain **purpose-built test profiles in the canonical SpiritSafe repository** (on the `main` branch).

**Rationale**:

1. **Dogfooding**: Test profiles go through SpiritSafe CI validation (ensures they're valid examples)
2. **Documentation**: Test profiles serve as comprehensive examples of profile features
3. **Shared maintenance**: Both SpiritSafe and GKC benefit from well-structured test profiles
4. **Realistic testing**: GKC tests use actual production profile structures, not mocks

### Example: EntityProfileExemplar

**Purpose**: A test profile designed to exercise all profile features and edge cases.

**Coverage goals**:

- **All datatypes**: item, url, string, quantity, time, monolingualtext, globecoordinate, external-id, commonsMedia
- **Linkage patterns**: References to other profiles with various cardinality constraints (1:1, 1:many, optional)
- **Complex qualifiers**: Nested structures with multiple qualifier combinations
- **Reference patterns**: Required, optional, target-specific, allowed-lists
- **Metadata features**: Multilingual labels/descriptions, sitelinks, aliases
- **Edge cases**: Optional vs required, max_count limits, fixed values, constraints

**Profile graph involvement**:

- EntityProfileExemplar links to TribalGovernmentUS (demonstrates bidirectional edges)
- Creates multi-level graph for traversal tests (depth 2+)

### Production Profiles as Test Data

In addition to purpose-built test profiles, we use **real production profiles** from SpiritSafe:

- **TribalGovernmentUS**: Real profile with linkage metadata (office_held_by_head_of_state)
- **OfficeHeldByHeadOfState**: Reciprocal profile with bidirectional edge back to TribalGovernmentUS

These provide realistic test scenarios for:

- Actual profile graph traversal
- Real cardinality constraints (max=1 for office_held_by_head_of_state)
- Production SPARQL queries and cached results
- Real-world metadata structures

---

## Fixture Sync Strategy

### Source of Truth

**SpiritSafe repository (`main` branch)** is the single source of truth for all profiles (test and production).

- Profiles in SpiritSafe evolve with schema changes
- CI ensures profiles remain valid
- Manifest is auto-generated on every commit

### Sync Process

GKC's `tests/fixtures/spiritsafe/` is a **periodic snapshot** of the SpiritSafe repository.

**When to sync**:

- After SpiritSafe profile schema changes (linkage metadata and metadata graph extensions)
- When new test profiles are added to SpiritSafe
- When production profiles are significantly updated (new statements, restructured metadata)
- When manifest format changes

**How to sync**:

#### Manual Sync (For Immediate Development Needs)

```bash
# From gkc repository root
cd ~/code/gkc

# Copy entire SpiritSafe structure
rm -rf tests/fixtures/spiritsafe/*
cp -r ~/code/SpiritSafe/profiles tests/fixtures/spiritsafe/
cp -r ~/code/SpiritSafe/cache tests/fixtures/spiritsafe/
cp -r ~/code/SpiritSafe/queries tests/fixtures/spiritsafe/ 2>/dev/null || true

# Verify structure
ls -R tests/fixtures/spiritsafe/

# Run tests to ensure fixtures work
poetry run pytest tests/ -k spiritsafe -v
```

#### Automated Sync (GitHub Actions Workflow)

**Workflow**: `.github/workflows/sync-spiritsafe-fixtures.yml`

**Trigger options**:

- **Scheduled**: Daily (or weekly) check for SpiritSafe updates
- **Manual**: Workflow dispatch for on-demand sync
- **Webhook** (future): Triggered by SpiritSafe repository push events

**Process**:

1. Check SpiritSafe manifest for new commit SHA
2. If SHA differs from last sync, clone SpiritSafe
3. Copy profiles/, cache/, queries/ to gkc/tests/fixtures/spiritsafe/
4. Run gkc test suite to verify fixtures
5. If tests pass, create PR with fixture updates
6. PR description includes:
   - SpiritSafe commit SHA
   - List of changed profiles
   - Manifest diff summary

**Benefits**:

- Keeps fixtures up-to-date automatically
- PR review process ensures no breaking changes
- Clear audit trail of what changed and when

### Sync Script (Future Enhancement)

**Tool**: `scripts/sync-spiritsafe-fixtures.sh`

```bash
#!/usr/bin/env bash
# Sync SpiritSafe profiles to gkc test fixtures

SPIRITSAFE_PATH="${1:-$HOME/code/SpiritSafe}"
GKC_FIXTURES="tests/fixtures/spiritsafe"

echo "Syncing from $SPIRITSAFE_PATH to $GKC_FIXTURES"

# Clear old fixtures
rm -rf "$GKC_FIXTURES"/{profiles,cache,queries}

# Copy structure
cp -r "$SPIRITSAFE_PATH/profiles" "$GKC_FIXTURES/"
cp -r "$SPIRITSAFE_PATH/cache" "$GKC_FIXTURES/"
[ -d "$SPIRITSAFE_PATH/queries" ] && cp -r "$SPIRITSAFE_PATH/queries" "$GKC_FIXTURES/"

# Record sync metadata
echo "$(cd "$SPIRITSAFE_PATH" && git rev-parse HEAD)" > "$GKC_FIXTURES/SYNC_SHA.txt"
date -u +"%Y-%m-%dT%H:%M:%SZ" > "$GKC_FIXTURES/SYNC_DATE.txt"

echo "Sync complete. Run tests with: poetry run pytest tests/ -k spiritsafe"
```

---

## Testing Patterns with Local Fixtures

### Configuring Tests for Local Mode

All GKC tests that load profiles should use **local mode** pointing to the fixture directory:

```python
import pytest
from pathlib import Path
from gkc import set_spirit_safe_source

@pytest.fixture
def spiritsafe_local_source():
    """Configure SpiritSafe source to use local test fixtures."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "spiritsafe"
    set_spirit_safe_source(mode="local", local_root=str(fixture_path))
    yield fixture_path
    # Optional teardown: restore previous source config
```

### Example Test: Profile Loading with Linkage

```python
def test_profile_linkage_metadata(spiritsafe_local_source):
    """Verify linkage metadata is parsed from Q4 profile artifact."""
    from gkc.spirit_safe import load_profile

    profile = load_profile("Q4")

    office_stmt = next(
        (
            statement
            for statement in profile.get("statements", [])
            if statement.get("name_identifier") == "office_held_by_head_of_state"
        ),
        None,
    )
    assert office_stmt is not None

    profile_graph = profile.get("metadata", {}).get("profile_graph", [])
    assert any(edge.get("target_profile") for edge in profile_graph)
```

### Example Test: Manifest Loading

```python
def test_manifest_loading(spiritsafe_local_source):
    """Load manifest and verify profile graph metadata."""
    from gkc.spirit_safe import load_manifest
    
    manifest = load_manifest()
    
    # Verify manifest structure
    assert "profiles" in manifest
    assert len(manifest["profiles"]) >= 2  # At least TribalGovernmentUS, OfficeHeldByHeadOfState
    
    # Find TribalGovernmentUS in manifest
    tribal_profile = next(
        (p for p in manifest["profiles"] if p["id"] == "TribalGovernmentUS"),
        None
    )
    assert tribal_profile is not None
    assert "profile_graph" in tribal_profile
    assert "OfficeHeldByHeadOfState" in tribal_profile["profile_graph"]["neighbors"]
```

### Example Test: Profile Graph Traversal

```python
def test_profile_graph_traversal(spiritsafe_local_source):
    """Test profile graph construction and traversal."""
    from gkc.profiles.graph import ProfileGraph
    
    graph = ProfileGraph.load_from_manifest()
    
    # Get neighbors of TribalGovernmentUS
    neighbors = graph.get_neighbors("TribalGovernmentUS")
    assert "OfficeHeldByHeadOfState" in neighbors
    
    # Verify bidirectional edge
    reverse_neighbors = graph.get_neighbors("OfficeHeldByHeadOfState")
    assert "TribalGovernmentUS" in reverse_neighbors
    
    # Check cardinality constraint
    cardinality = graph.get_cardinality("TribalGovernmentUS", "OfficeHeldByHeadOfState")
    assert cardinality["max"] == 1
```

### Test Coverage Goals

With the complete local SpiritSafe replica, tests should cover:

- ✅ JSON Entity Profile loading (all datatypes, statements, qualifiers, references)
- ✅ Linkage metadata extraction from statements
- ✅ Profile metadata loading (version, authors, profile_graph)
- ✅ Manifest loading and integrity validation
- ✅ Profile graph construction and traversal
- ✅ Cardinality constraint validation
- ✅ Curation packet creation (single and multi-entity)
- ✅ Query file loading and cache result parsing
- ✅ Profile discovery and search operations

---

## Maintenance and Best Practices

### When Fixtures Become Stale

**Symptoms**:

- GKC tests fail after SpiritSafe profile schema changes
- Manifest format evolves and fixtures are out of date
- New profile features not reflected in test fixtures

**Solution**: Re-sync fixtures using manual process or trigger GitHub Action

### Adding New Test Scenarios

**Process**:

1. **Identify gap**: "We need to test profile with 3+ linkages" or "Need globecoordinate datatype coverage"
2. **Update SpiritSafe profile**: Add feature to EntityProfileExemplar (or create new test profile in SpiritSafe)
3. **Validate in SpiritSafe**: Ensure profile passes SpiritSafe CI
4. **Sync to gkc**: Run manual sync or wait for automated sync
5. **Write test**: Add test case in gkc that exercises new feature

### Version Pinning

**Current approach**: Fixtures are synced at specific points in time (manual or automated)

**Tracking**: Record SpiritSafe commit SHA in `SYNC_SHA.txt` for audit trail

**Future**: Could use git submodules or vendored dependencies for explicit version control

### Testing Against Multiple SpiritSafe Versions

**Current**: Single fixture version (latest sync)

**Future option**: Maintain multiple fixture sets for backward compatibility testing:

```
tests/fixtures/
├── spiritsafe/           # Latest (current main)
├── spiritsafe-v1.0/      # Stable release version
└── spiritsafe-legacy/    # Legacy profile format
```

---

## GitHub Actions Workflow Specification

### Workflow File: `.github/workflows/sync-spiritsafe-fixtures.yml`

**Triggers**:

- `schedule`: Daily at 2 AM UTC
- `workflow_dispatch`: Manual trigger
- (Future) `repository_dispatch`: Webhook from SpiritSafe

**Steps**:

1. **Check for updates**:
   - Fetch SpiritSafe manifest.json
   - Compare commit SHA with `tests/fixtures/spiritsafe/SYNC_SHA.txt`
   - If same, exit early (no changes)

2. **Clone SpiritSafe**:
   - `actions/checkout@v3` for both gkc (working dir) and SpiritSafe

3. **Sync structure**:
   - Copy profiles/, cache/, queries/ to gkc fixtures
   - Record new SHA and sync timestamp

4. **Validate fixtures**:
   - Run `poetry run pytest tests/ -k spiritsafe -v`
   - If tests fail, stop workflow and notify

5. **Create PR**:
   - Commit fixture changes to branch `sync/spiritsafe-YYYY-MM-DD`
   - Create PR with auto-generated description:
     ```
     ## SpiritSafe Fixture Sync

     **Source Commit**: `abc123def` (SpiritSafe main)
     **Sync Date**: 2026-03-04T02:00:00Z
     **Test Status**: ✅ All tests passing

     ### Changed Profiles
     - TribalGovernmentUS (linkage metadata updated)
     - EntityProfileExemplar (new statements added)

     ### Manifest Changes
     - 2 profiles updated
     - Commit SHA: abc123def → def456ghi
     ```

6. **Notify maintainers**: Comment on PR or send notification

**Benefits**:

- Automated, hands-off sync process
- Clear audit trail in PR history
- Test validation before merge
- No breaking changes slip through

---

## Future Enhancements

### Submodule Approach

**Alternative**: Use git submodules to pin SpiritSafe version:

```bash
git submodule add https://github.com/skybristol/SpiritSafe tests/fixtures/spiritsafe
```

**Pros**: Explicit version tracking, easy updates with `git submodule update`
**Cons**: Adds complexity to git workflow, requires submodule understanding

### Vendored Profiles

**Alternative**: Publish SpiritSafe profiles as a Python package (e.g., `spiritsafe-profiles`)

**Pros**: Standard dependency management via poetry/pip
**Cons**: Adds publishing overhead, version management complexity

### Test Profile Versioning

**Enhancement**: Maintain test profiles with semantic versions in SpiritSafe

**Structure**:

```
profiles/
├── EntityProfileExemplar/
│   ├── v1.0/   # Stable version for backward compat tests
│   ├── v2.0/   # New schema version
│   └── latest/ # Symlink to current version
```

**Benefit**: GKC can test against multiple profile schema versions

---

## Conclusion

The SpiritSafe testing architecture provides GKC with robust, fast, and network-independent testing by maintaining a complete local replica of the SpiritSafe registry. By leveraging purpose-built test profiles in the canonical SpiritSafe repository and syncing them periodically (manually or via automation), we ensure:

- **Realistic tests**: Using production profile structures, not synthetic mocks
- **Complete coverage**: All GKC features (manifest, graphs, packets, CLI) testable locally
- **Maintainability**: Single source of truth (SpiritSafe main), clear sync process
- **Quality**: Test profiles validated in SpiritSafe CI before use in GKC tests

This architecture supports current development and scales to future GKC enhancements.

---

## See Also

- [SpiritSafe Registry Architecture](SpiritSafe.md) — Overall registry design and governance
- [Profile Loading Architecture](profile-loading.md) — How GKC loads profiles from sources
- [GKC Entity Profiles](../gkc/profiles.md) — Profile schema reference
- [SpiritSafe Repository](https://github.com/skybristol/SpiritSafe) — Canonical profile registry

---

**Last Updated:** March 4, 2026  
**Maintainer:** Profile Architect  
**Status:** Implementation in progress (fixture sync)
