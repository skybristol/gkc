# Wikibase V1 Plan

## Decision Log

**[confirmed]** 2026-03-06: Adopt hybrid approach with Profile YAML as actionable artifact for GKC code; Wikibase and SpiritSafe maintained in sync via bidirectional utilities.
  Source: Issue #127, comment 2026-03-06

**[confirmed]** 2026-03-06: Support fully offline operation with local SpiritSafe clone; network access to Data Distillery Wikibase is optional enhancement, not requirement.
  Source: Issue #127, comment 2026-03-06

**[confirmed]** 2026-03-06: GKC Entity Properties represented as Wikibase items (not properties); classified as subclass of "GKC Entity Property" (Q5).
  Source: Issue #127, Q&A section 1

**[confirmed]** 2026-03-06: Use "same as" (P5) or similar semantic relationship to link GKC Entity Properties to Wikidata properties and other GKC partner identifiers (Wikipedia template params, OSM tags, etc.).
  Source: Issue #127, Q&A section 1

**[confirmed]** 2026-03-06: GKC Property Specifications modeled as distinct Wikibase entity type (Q6), linked to properties via claims; house multilingual guidance, not executable logic.
  Source: Issue #127, Q&A section 3

**[confirmed]** 2026-03-06: Executable specification details (regex patterns, JSON schemas, SPARQL queries) stored in Wikibase discussion pages or as external references in SpiritSafe; Wikibase stores metadata and relationships, not full execution logic.
  Source: Issue #127, Q&A section 3

**[confirmed]** 2026-03-06: Each GKC Entity Profile represented as single Wikibase item (e.g., Q4 for Tribal Government); classified under "GKC Entity Profile" (Q3).
  Source: Issue #127, Q&A section 2

**[confirmed]** 2026-03-06: Cross-profile relationships (profile_graph) encoded as claims on GKC Entity Property items; enables semantic queries for packet assembly and graph traversal.
  Source: Issue #127, Q&A section 2

**[confirmed]** 2026-03-06: No profile versioning via new Q-IDs; treat profiles as living entities with revision history; defer formal versioning strategy until use case emerges.
  Source: Issue #127, Q&A section 2

**[confirmed]** 2026-03-06: SPARQL queries modeled as distinct Wikibase entity type (not yet created); query code stored in discussion pages; support both Wikidata Query Service and QLever syntax.
  Source: Issue #127, Q&A section 6

**[confirmed]** 2026-03-06: Multilingual validation messages stored as monolingual text properties on GKC Property Specification items; enables different message types (consequences, guidance, error text) per language.
  Source: Issue #127, Q&A section 4

**[confirmed]** 2026-03-06: Allowed-items lists hydrated via SPARQL and stored in SpiritSafe cache (not in Wikibase claims); Wikibase stores query references and metadata only.
  Source: Issue #127, Q&A section 8

**[confirmed]** 2026-03-06: Sync strategy uses GitHub Actions with scheduled checks for Wikibase updates; manifest build integrated with sync operations.
  Source: Issue #127, Q&A section 6

**[confirmed]** 2026-03-06: SpiritSafe serves as optimized runtime cache transformed from Wikibase; transformation must be lossless and testable; offline fallback is first-class requirement.
  Source: Issue #127, Q&A section 7

**[confirmed]** 2026-03-06: Start with import of existing SpiritSafe profiles to Wikibase; establish modeling patterns and adjust both sides as needed during initial sync.
  Source: Issue #127, comment 2026-03-06

**[confirmed]** 2026-03-06: Synthetic test profiles will be created in Data Distillery for integration testing and round-trip fidelity validation.
  Source: Issue #127, Q&A section 10

**[confirmed]** 2026-03-06: Foundation ontology defined as machine-readable GKC Entity Profiles at `gkc/wikibase/foundation_profiles/`; dogfooding approach validates profile system for metadata/ontology use cases; enables automated audit and init tooling.
  Source: WikibaseV1 planning discussion, 2026-03-06

## Purpose

The Data Distillery Wikibase (`datadistillery.wikibase.cloud`) serves as a semantic registry and collaborative workspace for GKC metadata infrastructure.

This document defines the V1 implementation plan for establishing the Wikibase semantic model, building bidirectional sync tooling with SpiritSafe, and integrating Wikibase-backed metadata into Fermenter operations.

**Key Goals:**

- Establish foundational Wikibase ontology (entity types, properties, semantic relationships)
- Dogfood GKC Entity Profile mechanism by defining foundation ontology as machine-readable profiles
- Build robust bidirectional sync between Wikibase and SpiritSafe
- Maintain SpiritSafe YAML as the actionable artifact for GKC operations
- Enable offline-first development with optional Wikibase enhancement
- Support Fermenter V1 requirements for property metadata, constraints, and multilingual messaging

## Guiding Decisions (Confirmed)

### Architecture and Ownership

- **Hybrid model**: Wikibase and SpiritSafe maintained in sync; neither is exclusively "master"
- Profile YAML remains the operational artifact consumed by GKC code
- Wikibase provides semantic richness, queryability, and multilingual support
- SpiritSafe provides optimized runtime cache and offline fallback
- Transformation between Wikibase and SpiritSafe must be lossless and bidirectional

### Wikibase Semantic Model

- **GKC Entity Profile**: Wikibase item (instance of Q3) representing a complete entity profile
- **GKC Entity Property**: Wikibase item (instance of Q5) representing a property/statement definition
- **GKC Property Specification**: Wikibase item (instance of Q6) representing a validation/coercion constraint
- **SPARQL Query Entity**: Wikibase item (new entity type) representing a reusable query for allowed-items hydration
- Foundation entities already established: Q1 (entity), P1 (instance of), P2 (subclass of), P5 (same as)

### Property Modeling

- GKC Entity Properties are items, not Wikibase properties (they describe properties, not serve as them)
- Each property links to Wikidata property via "same as" (P5) or similar relationship
- Property items can link to other GKC partner identifiers (OSM tags, Wikipedia template params)
- Profile-local property IDs (e.g., `instance_of`, `official_website`) stored as textual identifiers on property items

### Constraint/Specification Modeling

- Specifications modeled as semantic entities with multilingual labels/descriptions
- Executable logic (regex patterns, JSON schemas) lives in Wikibase discussion pages or SpiritSafe files
- Wikibase stores relationships and metadata; Fermenter implements executable rules
- Distinguish definition-time specs (schema validation) from runtime specs (coercion/validation)

### Multilingual Messaging

- Validation messages stored as monolingual text claims on GKC Property Specification items
- Message namespace consolidated under `gkc.fermenter.*`
- Parametric messages use template placeholders; Fermenter handles rendering
- Fallback chain: requested language → English → profile default → system default

### Sync and Transformation

- GitHub Actions-based scheduler checks Wikibase for updates (polls revision API or change feed)
- Transformation produces valid YAML profiles + JSON manifest + optimized property/specification indexes
- Round-trip fidelity testing: Wikibase → YAML → Wikibase produces identical structure
- `last_synced_revision` tracked in manifest.json for drift detection
- Manual trigger available via CLI: `gkc wikibase sync`

### Offline and Fallback

- GKC code operates fully offline with SpiritSafe clone (no network dependency)
- Wikibase connection optional; provides live updates, collaborative editing, and semantic queries
- Snapshot exports versioned and published with manifest describing schema/currency
- Fermenter deterministic offline/online parity (Phase 1 contract requirement)

### Query Contracts

Wikibase supports the following query patterns for Fermenter and other GKC components:

- **Property metadata lookup**: Given property ID or Wikidata P-code, retrieve datatype, specifications, allowed-items query reference
- **Specification resolution**: Given property + spec type, retrieve descriptor, parameters, multilingual messages
- **Profile structure**: Given profile QID, retrieve all associated statements/properties with specifications
- **Cross-profile relationships**: Given profile QID, retrieve neighbor profiles and edge metadata (for packet assembly)
- **Multilingual message lookup**: Given message key + language code, retrieve localized text with fallback

## Outstanding Design Inputs (Deferred)

The following are explicitly deferred for post-V1 planning:

- **Staging Wikibase instance** for testing changes before production promotion (mentioned in counter-arguments, not yet scoped)
- **GKC Profile Editor UI** to abstract Wikibase complexity for non-technical contributors
- **Webhook-based change detection** vs. polling (start with polling, optimize later)
- **QLever integration** for complex SPARQL queries beyond Blazegraph capacity
- **Contribution workflow** for community curation and PR-equivalent review in Wikibase context
- **Allowed-items cache scalability** beyond SpiritSafe repo storage (future high-volume scenarios)

## Current Status (2026-03-06)

Completed in this session:

- `gkc wikibase audit` and `gkc wikibase init` are implemented and exercised against Data Distillery.
- Foundation ontology profiles are in place and expanded (Phase 0 + substantial Phase 0.5 seed terms).
- Init now includes summary enforcement and bot-mode defaulting behavior from auth username format.
- Diff-style planning support was added in shipper flow to inspect create/update/no-op decisions.
- Dry-run and execute reporting now includes actionable request payload visibility and API error propagation.
- Critical property-create bug was resolved: property `datatype` must be placed inside the `data` JSON payload for `wbeditentity` property creation on this instance.

Notes and decisions captured from execution debugging:

- Data Distillery accepted manual property creation and API write authentication, but rejected property creates when `datatype` was passed as a top-level request param.
- Verified fix path: embed `datatype` inside `data` JSON for `new=property` writes.
- Property creation now succeeds with this request shape.
- Keep this behavior treated as instance contract for Data Distillery until proven otherwise on additional Wikibase targets.

## Phase Plan

### Phase 0 - Wikibase Foundation Ontology and Init

**Purpose**: Define Data Distillery foundation ontology as machine-readable GKC Entity Profiles; build audit and init tooling.

**Approach**: Dogfood the GKC Entity Profile mechanism by defining the Wikibase foundation entities (Q1-Q6, P1-P5, etc.) as profiles. This creates a machine-readable, actionable specification that can drive both validation and entity creation.

Deliverables:

- **Foundation ontology profiles** at `gkc/wikibase/foundation_profiles/`:
  - `foundation_entities.yaml`: Defines required foundation entities (Q1-Q6)
  - `foundation_properties.yaml`: Defines required foundation properties (P1-P5)
  - `foundation_metadata.yaml`: Metadata for the foundation ontology itself
- **Audit script** (`gkc wikibase audit`) that:
  - Reads foundation profiles
  - Queries Wikibase for entities by label
  - Validates existing entities against profile requirements
  - Reports missing, mismatched, or non-conforming entities
- **Init script** (`gkc wikibase init`) that:
  - Runs audit first
  - Creates missing foundation entities per profile definitions
  - Updates non-conforming entities to match profile (with --fix flag)
  - Dry-run mode to preview changes without writing
- Bot account authentication integration via WikiverseAuth API (uses existing `gkc.auth`)
- Markdown documentation generated from foundation profiles (human-readable reference)

Scope anchors:

- Issue #121 (Define Data Distillery semantic model for Fermenter registries)

Exit criteria:

- Foundation ontology defined as valid GKC Entity Profiles
- Audit tool can validate Data Distillery Wikibase against foundation profiles
- Init tool can create missing foundation entities from profiles
- Bot account authenticates successfully and can perform CRUD operations
- Foundation profiles serve as reference for subsequent phases
- Generated documentation describes ontology structure for human readers

Target deliverables:

```
gkc/wikibase/
  foundation_profiles/
    foundation_entities.yaml     # Q1-Q6 definitions
    foundation_properties.yaml   # P1-P5 definitions
    foundation_metadata.yaml     # Ontology metadata
    README.md                    # Foundation ontology docs (generated)

docs/wikibase/
  ontology.md          # Ontology overview (generated from profiles)
  foundation.md        # Foundation entities reference (generated)
  bot-operations.md    # Authentication, CRUD patterns, rate limits
```

Foundation profile structure example:

```yaml
# gkc/wikibase/foundation_profiles/foundation_entities.yaml
name: Data Distillery Foundation Entities
description: >
  Defines the required foundation entity types for the Data Distillery Wikibase.
  These entities form the ontological backbone for GKC metadata infrastructure.

version: 1.0.0
status: stable

# Foundation entities expected in Wikibase
entities:
  - qid: Q1
    label: entity
    description: root entity type in the ontology
    instance_of: null  # Top-level entity
    expected_claims: []
    
  - qid: Q2
    label: GKC Foundation Entity
    description: base class for all GKC-specific entity types
    instance_of: Q1
    subclass_of: Q1
    expected_claims:
      - property: P2  # subclass of
        value: Q1
    
  - qid: Q3
    label: GKC Entity Profile
    description: represents a complete GKC entity profile specification
    instance_of: Q2
    subclass_of: Q2
    expected_claims:
      - property: P2  # subclass of
        value: Q2
  
  - qid: Q5
    label: GKC Entity Property
    description: represents a property/statement definition in a GKC profile
    instance_of: Q2
    subclass_of: Q2
    expected_claims:
      - property: P2  # subclass of
        value: Q2
  
  - qid: Q6
    label: GKC Property Specification
    description: represents a validation/coercion constraint for properties
    instance_of: Q2
    subclass_of: Q2
    expected_claims:
      - property: P2  # subclass of
        value: Q2
```

```yaml
# gkc/wikibase/foundation_profiles/foundation_properties.yaml
name: Data Distillery Foundation Properties
description: >
  Defines the required foundation properties for the Data Distillery Wikibase.

version: 1.0.0
status: stable

properties:
  - pid: P1
    label: instance of
    description: the class of which this subject is a particular example
    datatype: wikibase-item
    
  - pid: P2
    label: subclass of
    description: this item is a subclass of that item
    datatype: wikibase-item
  
  - pid: P5
    label: same as
    description: this item is the same as that item in another system
    datatype: external-id
```

Target CLI Patterns:

```bash
# Audit foundation (read-only check)
gkc wikibase audit \
  --foundation-profiles ./gkc/wikibase/foundation_profiles \
  --output foundation_audit.json

# Output shows:
# ✓ Q1 (entity) - conformant
# ✓ Q2 (GKC Foundation Entity) - conformant
# ✗ Q3 (GKC Entity Profile) - missing instance_of claim
# ✗ Q7 (SPARQL Query) - not found in Wikibase
# Summary: 2/6 entities conformant, 1 non-conformant, 1 missing

# Initialize foundation (create missing + fix non-conformant)
gkc wikibase init \
  --foundation-profiles ./gkc/wikibase/foundation_profiles \
  --fix-nonconforming \
  --dry-run

# With --dry-run, shows planned changes without writing
# Without --dry-run, applies changes

# Create only missing entities (don't fix existing)
gkc wikibase init \
  --foundation-profiles ./gkc/wikibase/foundation_profiles \
  --create-missing-only

# Test bot authentication
gkc wikibase auth test

# Generate documentation from foundation profiles
gkc wikibase generate-docs \
  --foundation-profiles ./gkc/wikibase/foundation_profiles \
  --output ./docs/wikibase/
```

---

### Phase 0.5 - Ontology Seed Expansion (Fermenter-aligned)

**Purpose**: Add the minimum additional ontology terms needed to unblock Fermenter contracts, messaging, and sync provenance without over-scoping V1.

Deliverables:

- Extend `foundation_entities.yaml` with first-order classifier entities for:
  - validation messages
  - validation policies
  - statement behaviors
  - suggestion types
  - refresh policies
  - artifact types and message severities
- Extend `foundation_properties.yaml` with high-value ontology properties for:
  - profile structure (`has statement`, `has qualifier`, `has reference property`, `statement order`)
  - behavior/policy linkage (`value behavior`, `qualifier behavior`, `reference behavior`, `validation policy`)
  - specification linkage (`has specification`)
  - multilingual messaging (`message key`, `error/guidance/consequences/suggestion message text`)
  - lookup hydration (`query reference`, `refresh policy`, `fallback item`, `cache artifact URL`, `cache generated at`)
  - sync provenance (`source profile path`, `source repository ref`, `last synced revision`, `transformed artifact type`)

Exit criteria:

- Expanded ontology profiles validate with `gkc wikibase audit` (label-first matching)
- Message model supports addressable key + monolingual text templates for multilingual retrieval
- Ontology seed set is sufficient to begin Fermenter registry resolver contracts and sync metadata projection

---

### Phase 0.9 - Documentation and Interface Consolidation (next session)

**Purpose**: Consolidate docs and interface contracts after rapid implementation work, before deeper Phase 1/2 expansion.

Deliverables:

- API docs pass for Wikibase init/audit and shipper write behavior (including property create request shape).
- CLI docs pass for `gkc wikibase` commands, arguments, defaults, execute/dry-run semantics, and output artifacts.
- Architecture docs pass tying foundation profiles, runtime config, auth modes, and sync intentions into one coherent narrative.
- Update mkdocs nav and page structure for new Wikibase architecture material and command reference pages.
- Add troubleshooting notes for common API failures observed in practice (datatype placement, auth group mismatch, write summary requirements).

Exit criteria:

- Documentation accurately reflects current behavior of shipped code paths.
- Wikibase command reference is sufficient for first-time setup and repeatable initialization.
- Architecture documentation explicitly captures current constraints and temporary implementation contracts discovered during Phase 0 execution.
- All new docs build cleanly with current MkDocs workflow.

---

### Phase 1 - Wikibase Client Library

**Purpose**: Build core Wikibase API client for authenticated read/write operations.

Deliverables:

- `gkc.wikibase` module with client class for Data Distillery operations
- Authentication integration via WikiverseAuth API (existing `gkc.auth` module)
- CRUD operations: create item, update item, add claim, query items by criteria
- Error handling, rate limiting, retry logic for network operations
- Wikibase JSON serialization/deserialization utilities
- Read operations for retrieving entity data, claims, labels, descriptions

Scope anchors:

- Issue #121 (Define Data Distillery semantic model)
- New issue: Wikibase client library implementation

Exit criteria:

- Client can authenticate with bot account via WikiverseAuth
- Basic CRUD operations tested against Data Distillery Wikibase
- Read operations support retrieving complete entity JSON
- Write operations support creating items and adding claims with references
- Client handles errors gracefully with actionable messages

Target API Patterns:

```python
# Client initialization
from gkc.wikibase import WikibaseClient

client = WikibaseClient(
    endpoint="https://datadistillery.wikibase.cloud",
    auth_handler=None  # Uses gkc.auth.get_authenticated_session
)

# Read operations
entity_data = client.get_entity("Q4")  # Tribal Government profile
property_claims = client.get_claims("Q5", property_id="P5")  # same-as claims

# Write operations
new_item = client.create_item(
    labels={"en": "Test Property"},
    descriptions={"en": "A test GKC Entity Property"},
    instance_of="Q5"  # GKC Entity Property
)

client.add_claim(
    entity_id=new_item["id"],
    property_id="P5",  # same as
    value="P31"  # Wikidata:instance of
)

# Query operations
query_result = client.sparql_query("""
    SELECT ?item ?itemLabel WHERE {
        ?item wdt:P1 wd:Q5 .
        SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
    }
    LIMIT 10
""")
```

Target CLI Patterns:

```bash
# Test client operations
gkc wikibase get Q4
gkc wikibase get Q5 --format json --output property_q5.json

# Create test item
gkc wikibase create-item \
  --label "en:Test Property" \
  --description "en:Test description" \
  --instance-of Q5

# Add claim
gkc wikibase add-claim Q999 \
  --property P5 \
  --value P31 \
  --reference-url "https://www.wikidata.org/wiki/Property:P31"

# SPARQL query
gkc wikibase query \
  --sparql ./query.sparql \
  --output results.json
```

---

### Phase 2 - Profile Import Pipeline

**Purpose**: Import existing SpiritSafe profiles to Wikibase, establishing modeling patterns.

Deliverables:

- Profile YAML parser that extracts entity types, properties, specifications
- Wikibase entity constructor that creates items for profiles, properties, specifications
- Import script that processes SpiritSafe profiles and creates corresponding Wikibase structure
- Mapping logic for profile YAML features → Wikibase claims (statements, qualifiers, references)
- Handling for existing items (update vs. skip vs. error modes)
- Import provenance tracking (which YAML file generated which QID)

Scope anchors:

- Issue #122 (Build SpiritSafe manifest projection + sync pipeline)
- New issue: Profile YAML to Wikibase import implementation

Exit criteria:

- Both existing profiles (TribalGovernmentUS, OfficeHeldByHeadOfState) imported successfully
- All profile statements represented as GKC Entity Property items
- Cross-profile relationships (profile_graph) encoded as claims
- SPARQL queries stored in discussion pages or as query entities
- Import can run incrementally (updates existing items, creates new ones)
- Import log shows mapping from YAML structure to QIDs

Target API Patterns:

```python
# Profile import
from gkc.wikibase.importers import ProfileImporter

importer = ProfileImporter(client=wikibase_client)

result = importer.import_profile(
    profile_yaml_path="./profiles/TribalGovernmentUS/profile.yaml",
    metadata_yaml_path="./profiles/TribalGovernmentUS/metadata.yaml",
    update_existing=True  # Update if profile QID exists
)

# result contains:
# - profile_qid: Q4
# - property_qids: {"instance_of": "Q10", "official_website": "Q11", ...}
# - specification_qids: {"integer_only": "Q20", ...}
# - sparql_query_qids: {"bia_federal_register_issues": "Q30", ...}

# Batch import
from gkc.wikibase.importers import import_spiritsafe_profiles

import_result = import_spiritsafe_profiles(
    spiritsafe_path="./SpiritSafe/profiles",
    client=wikibase_client,
    dry_run=False
)
```

Target CLI Patterns:

```bash
# Import single profile
gkc wikibase import-profile \
  ./SpiritSafe/profiles/TribalGovernmentUS/profile.yaml \
  --metadata ./SpiritSafe/profiles/TribalGovernmentUS/metadata.yaml \
  --update-existing

# Batch import all profiles
gkc wikibase import-spiritsafe \
  ./SpiritSafe/profiles \
  --dry-run  # Preview changes without writing

# Import with mapping output
gkc wikibase import-profile \
  ./profile.yaml \
  --output-mapping ./import_mapping.json

# Verify import
gkc wikibase verify-profile Q4 \
  --compare-yaml ./SpiritSafe/profiles/TribalGovernmentUS/profile.yaml
```

---

### Phase 3 - Export and Transformation Pipeline

**Purpose**: Generate SpiritSafe YAML artifacts from Wikibase entities.

Deliverables:

- Wikibase entity reader that fetches profile/property/specification items with all claims
- YAML profile generator that transforms Wikibase JSON → profile.yaml structure
- YAML metadata generator for metadata.yaml files
- SPARQL query extractor (from discussion pages or query entities)
- Allowed-items cache hydration (execute SPARQL queries, store results)
- Manifest builder that incorporates Wikibase-sourced metadata
- Round-trip validation: Wikibase → YAML → Wikibase fidelity check

Scope anchors:

- Issue #122 (SpiritSafe manifest projection + sync pipeline)
- Issue #125 (Design Data Distillery snapshot/export path)
- New issue: Wikibase to SpiritSafe export implementation

Exit criteria:

- Can export any GKC Entity Profile from Wikibase to valid YAML
- Exported YAML passes existing SpiritSafe schema validation
- Round-trip import/export produces structurally identical Wikibase entities
- SPARQL queries extracted and saved to `.sparql` files
- Manifest.json includes Wikibase sync metadata (last_synced_revision, entity mappings)
- Export handles multilingual content (labels, descriptions, messages)

Target API Patterns:

```python
# Export single profile
from gkc.wikibase.exporters import ProfileExporter

exporter = ProfileExporter(client=wikibase_client)

profile_yaml = exporter.export_profile(
    profile_qid="Q4",
    output_dir="./output/TribalGovernmentUS"
)

# Returns paths:
# - ./output/TribalGovernmentUS/profile.yaml
# - ./output/TribalGovernmentUS/metadata.yaml
# - ./output/TribalGovernmentUS/queries/*.sparql

# Batch export
from gkc.wikibase.exporters import export_all_profiles

export_result = export_all_profiles(
    client=wikibase_client,
    output_dir="./SpiritSafe/profiles",
    include_cache_hydration=True  # Run SPARQL queries and build cache
)

# Round-trip validation
from gkc.wikibase.validators import validate_roundtrip

validation = validate_roundtrip(
    profile_qid="Q4",
    client=wikibase_client,
    temp_dir="./tmp/roundtrip"
)

assert validation.success
assert len(validation.differences) == 0
```

Target CLI Patterns:

```bash
# Export single profile
gkc wikibase export-profile Q4 \
  --output ./output/TribalGovernmentUS \
  --include-queries \
  --hydrate-cache

# Export all profiles
gkc wikibase export-spiritsafe \
  --output ./SpiritSafe \
  --update-manifest

# Round-trip test
gkc wikibase test-roundtrip Q4 \
  --verbose \
  --output-diff ./roundtrip_diff.json

# Batch round-trip validation
gkc wikibase test-roundtrip-all \
  --report ./roundtrip_report.json
```

---

### Phase 4 - Sync Automation and Change Detection

**Purpose**: Automate bidirectional sync with change detection and conflict resolution.

Deliverables:

- Wikibase change detection (poll revision API for updates since last sync)
- GitHub Action workflow for scheduled sync (Wikibase → SpiritSafe)
- Conflict detection when both sides modified between syncs
- Sync strategy configuration (Wikibase-preferred, SpiritSafe-preferred, manual-review)
- Manifest tracking of sync state (revision IDs, timestamps, conflict flags)
- Notification system for sync failures or conflicts

Scope anchors:

- Issue #122 (SpiritSafe manifest projection + sync pipeline)
- New issue: Automated sync workflow implementation

Exit criteria:

- GitHub Action runs on schedule (e.g., daily) and checks for Wikibase changes
- Successful sync updates SpiritSafe YAML files and commits changes
- Conflict detection identifies simultaneous edits to same profile/property
- Manual sync trigger available via CLI and GitHub workflow dispatch
- Sync failures reported via GitHub issue or notification
- Manifest includes full sync provenance (last check, last sync, revision IDs)

Target workflow file:

```yaml
# .github/workflows/sync-wikibase.yml
name: Sync from Data Distillery Wikibase

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      - name: Sync from Wikibase
        run: |
          poetry run gkc wikibase sync \
            --check-conflicts \
            --commit-changes \
            --conflict-strategy manual-review
        env:
          GKC_WIKIBASE_ENDPOINT: ${{ secrets.WIKIBASE_ENDPOINT }}
          WIKIVERSE_AUTH_TOKEN: ${{ secrets.WIKIVERSE_AUTH_TOKEN }}
      - name: Commit changes
        if: success()
        run: |
          git config user.name "GKC Wikibase Sync Bot"
          git config user.email "bot@gkc.example"
          git add .
          git commit -m "Sync from Wikibase (automated)" || echo "No changes"
          git push
```

Target CLI Patterns:

```bash
# Manual sync (Wikibase → SpiritSafe)
gkc wikibase sync \
  --direction from-wikibase \
  --check-conflicts \
  --dry-run

# Sync with conflict strategy
gkc wikibase sync \
  --conflict-strategy wikibase-preferred \
  --commit-message "Sync from Wikibase"

# Reverse sync (SpiritSafe → Wikibase)
gkc wikibase sync \
  --direction to-wikibase \
  --profiles ./SpiritSafe/profiles/TribalGovernmentUS

# Check sync status
gkc wikibase sync-status

# Output:
# Last sync: 2026-03-06 02:00:00 UTC
# Wikibase revision: 1234
# SpiritSafe commit: abc123
# Conflicts: None
# Next scheduled sync: 2026-03-07 02:00:00 UTC
```

---

### Phase 5 - Fermenter Integration

**Purpose**: Enable Fermenter to consume Wikibase-backed metadata with deterministic fallback.

Deliverables:

- Fermenter read interface to SpiritSafe-cached Wikibase metadata
- Property metadata resolver with fallback chain (cache → SpiritSafe YAML → profile-local)
- Specification resolver for validation/coercion rules
- Multilingual message resolver with language fallback
- Online mode: direct Wikibase queries for live metadata (optional enhancement)
- Offline mode: fully functional with SpiritSafe cache only
- Integration tests demonstrating online/offline parity

Scope anchors:

- Issue #124 (Specify Data Distillery query contracts for Fermenter resolvers)
- Issue #126 (Fermenter contract tests for Data Distillery online/offline parity)
- FermenterV1 Phase 1 (Data Distillery integration contracts)

Exit criteria:

- Fermenter can resolve property metadata from Wikibase-sourced cache
- Specification rules fetched from SpiritSafe-optimized indexes
- Multilingual message lookup works with language fallback
- Offline mode passes all Fermenter contract tests
- Online mode (direct Wikibase query) demonstrated for property metadata lookup
- Provenance tracking shows whether metadata came from cache vs. live Wikibase

Target API Patterns:

```python
# Fermenter integration
from gkc.fermenter.resolvers import PropertyMetadataResolver

resolver = PropertyMetadataResolver(
    spiritsafe_cache_path="./SpiritSafe/cache",
    wikibase_client=None  # Offline mode
)

# Resolve property metadata
property_meta = resolver.resolve_property("instance_of")
# Returns:
# {
#   "id": "instance_of",
#   "wikidata_property": "P31",
#   "wikibase_qid": "Q10",
#   "datatype": "item",
#   "specifications": ["Q20", "Q21"],
#   "source": "cache"  # or "wikibase" or "profile"
# }

# Resolve specification
from gkc.fermenter.resolvers import SpecificationResolver

spec_resolver = SpecificationResolver(
    spiritsafe_cache_path="./SpiritSafe/cache"
)

spec = spec_resolver.resolve_specification("Q20")  # integer_only
# Returns:
# {
#   "qid": "Q20",
#   "type": "integer_only",
#   "messages": {
#     "en": {"error": "Must be an integer", "guidance": "..."},
#     "es": {"error": "Debe ser un entero", "guidance": "..."}
#   },
#   "parameters": {},
#   "source": "cache"
# }

# Online mode (optional)
online_resolver = PropertyMetadataResolver(
    spiritsafe_cache_path="./SpiritSafe/cache",
    wikibase_client=wikibase_client,
    prefer_online=True
)

property_meta = online_resolver.resolve_property("instance_of")
# May query Wikibase directly if cache is stale or missing
```

Target CLI Patterns:

```bash
# Test property resolution
gkc fermenter resolve property instance_of \
  --cache ./SpiritSafe/cache \
  --mode offline

# Test specification resolution
gkc fermenter resolve specification Q20 \
  --cache ./SpiritSafe/cache \
  --language en

# Test multilingual message resolution
gkc fermenter resolve message gkc.fermenter.coercion.invalid_qid \
  --language es \
  --fallback en

# Validate offline/online parity
gkc fermenter test parity \
  --cache ./SpiritSafe/cache \
  --wikibase-endpoint https://datadistillery.wikibase.cloud \
  --report ./parity_report.json
```

---

### Phase 6 - Synthetic Test Fixtures

**Purpose**: Create synthetic test profiles in Wikibase for integration testing.

Deliverables:

- Synthetic test profile definitions (minimal valid profiles for various scenarios)
- Test fixture import script (creates test profiles in Wikibase under test namespace)
- Test data cleanup utilities (remove test profiles after testing)
- Integration test suite using synthetic profiles
- Round-trip tests with synthetic data
- Performance baseline tests with synthetic profiles

Scope anchors:

- Issue #126 (Fermenter contract tests for Data Distillery online/offline parity)
- New issue: Synthetic test fixtures implementation

Exit criteria:

- At least 3 synthetic test profiles created in Wikibase (simple, complex, edge-case)
- Test profiles isolated in dedicated namespace (e.g., Q9000-Q9999 range)
- Integration tests use synthetic profiles exclusively (no dependency on production profiles)
- Cleanup script can remove all test fixtures
- CI can run tests against Wikibase test fixtures without affecting production data

Target test profiles:

```yaml
# Synthetic profile: MinimalEntity
# QID: Q9001
# Purpose: Bare minimum valid profile with one statement

# Synthetic profile: ComplexEntity
# QID: Q9002
# Purpose: Full-featured profile with qualifiers, references, multilingual content

# Synthetic profile: EdgeCaseEntity
# QID: Q9003
# Purpose: Tests edge cases (max cardinality, regex validation, allowed-items)
```

Target API Patterns:

```python
# Create test fixtures
from gkc.wikibase.testing import create_synthetic_fixtures

fixtures = create_synthetic_fixtures(
    client=wikibase_client,
    qid_range_start=9001,
    profiles=["minimal", "complex", "edge_case"]
)

# Returns:
# {
#   "minimal": {"profile_qid": "Q9001", "property_qids": {...}},
#   "complex": {"profile_qid": "Q9002", "property_qids": {...}},
#   "edge_case": {"profile_qid": "Q9003", "property_qids": {...}}
# }

# Cleanup test fixtures
from gkc.wikibase.testing import cleanup_synthetic_fixtures

cleanup_synthetic_fixtures(
    client=wikibase_client,
    qid_range=(9001, 9999)
)
```

Target CLI Patterns:

```bash
# Create synthetic fixtures
gkc wikibase create-test-fixtures \
  --qid-start 9001 \
  --profiles minimal,complex,edge_case

# Run integration tests against fixtures
gkc wikibase test integration \
  --use-fixtures \
  --fixture-range 9001-9999

# Cleanup test fixtures
gkc wikibase cleanup-test-fixtures \
  --qid-range 9001-9999 \
  --confirm
```

---

## Initial Module Layout (V1)

Proposed package structure:

```
gkc/wikibase/
  __init__.py
  client.py              # WikibaseClient class, CRUD operations
  auth.py                # Authentication integration (uses gkc.auth)
  serializers.py         # Wikibase JSON ↔ Python object conversion
  
  foundation_profiles/   # Foundation ontology as GKC Entity Profiles
    foundation_entities.yaml     # Q1-Q6 entity definitions
    foundation_properties.yaml   # P1-P5 property definitions
    foundation_metadata.yaml     # Ontology metadata
    README.md                    # Generated documentation
  
  foundation/
    __init__.py
    audit.py             # Foundation ontology audit against profiles
    init.py              # Foundation entity creation from profiles
    profile_loader.py    # Load and parse foundation profiles
  
  importers/
    __init__.py
    profile_importer.py  # Profile YAML → Wikibase entities
    mapping.py           # YAML structure → Wikibase claim mapping
  
  exporters/
    __init__.py
    profile_exporter.py  # Wikibase entities → Profile YAML
    manifest_builder.py  # Manifest generation with Wikibase metadata
    query_extractor.py   # SPARQL query extraction from discussion pages
  
  sync/
    __init__.py
    change_detector.py   # Wikibase revision polling
    conflict_resolver.py # Conflict detection and resolution
    sync_engine.py       # Orchestrates sync operations
  
  testing/
    __init__.py
    fixtures.py          # Synthetic test profile creation
    validators.py        # Round-trip validation utilities
  
  resolvers/
    __init__.py
    property_resolver.py # Property metadata resolution for Fermenter
    spec_resolver.py     # Specification resolution for Fermenter
    message_resolver.py  # Multilingual message resolution
```

SpiritSafe additions:

```
SpiritSafe/
  cache/
    wikibase/
      properties.json    # Property metadata index
      specifications.json # Specification metadata index
      messages.json      # Multilingual message index
      last_sync.json     # Sync state tracking
```

---

## Migration Strategy

Migration is phased and test-gated, with parallel operation during transition.

Approach:

1. **Phase 0-1**: Build foundation without disrupting existing workflows
2. **Phase 2**: Import existing profiles to Wikibase (additive operation, no changes to SpiritSafe yet)
3. **Phase 3**: Test export pipeline in isolation; validate round-trip fidelity before replacing any SpiritSafe files
4. **Phase 4**: Enable automated sync as background process; manual review of changes initially
5. **Phase 5**: Fermenter consumes Wikibase-sourced cache alongside existing profile data (parallel validation)
6. **Phase 6**: Full integration testing with synthetic fixtures before trusting production data

Rollback strategy:

- SpiritSafe YAML remains authoritative throughout V1
- Wikibase serves as enhancement, not requirement
- Any phase can be paused or rolled back without breaking existing GKC functionality
- Offline mode always available as fallback

Success metrics:

- Round-trip fidelity: 100% structural equivalence for imported profiles
- Sync reliability: automated sync runs without manual intervention for 30 days
- Offline parity: Fermenter tests pass identically in offline/online modes
- Performance: Property resolution < 10ms from cache, < 100ms from Wikibase
- Coverage: All existing SpiritSafe profiles successfully imported and exported

---

## Co-Development Session Workflow

Each phase follows this pattern:

1. **Planning session**: Review phase goals, discuss implementation approach, identify open questions
2. **Development sprint**: Implement deliverables, write tests, iterate on design
3. **Integration checkpoint**: Test against real profiles/data, verify exit criteria met
4. **Documentation**: Update ontology docs, API docs, CLI help text
5. **Handoff**: Post GitHub issues for any follow-up work, tag appropriate agents
6. **Commit & merge**: Merge working functionality to main branch
7. **Next phase kickoff**: Review lessons learned, adjust subsequent phases as needed

Between phases:

- Monitor for issues with merged functionality
- Community testing with early adopters (if applicable)
- Performance profiling and optimization
- Documentation refinement based on usage patterns
