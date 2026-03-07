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

### Module Responsibility Boundaries (2026-03-07 alignment)

- `gkc.mash` is the canonical read/retrieval layer for Wikibase/Wikidata-compatible APIs. Do not reimplement generic retrieval clients inside `gkc.wikibase`.
- `gkc.shipper` is the canonical write/delivery layer for Wikibase-compatible APIs, including Data Distillery. Do not duplicate write operators in `gkc.wikibase`.
- `gkc.wikibase` is Data Distillery semantic-backbone orchestration: ontology profile loading, audit/init orchestration, semantic planning, and coordination of read/write flows through mash + shipper.
- `gkc.cooperage` is the preferred home for reusable transformation/packaging logic that turns retrieved semantic structures into shippable runtime artifacts (e.g., SpiritSafe-oriented projections, indexes, parity-ready cache bundles).
- SpiritSafe remains the operational artifact and runtime cache surface; synchronization logic must preserve lossless round-trip behavior.

### Existing Capability Reuse (Current Code Reality)

- Generic Wikibase reads already exist in `gkc.mash.WikibaseApiClient` (`wbsearchentities`, `wbgetentities`, entity fetch wrappers).
- Generic Wikibase writes already exist in `gkc.shipper.WikibaseShipper` (`write_item`, `write_property`, `plan_batch`) and are already validated against Data Distillery contracts.
- Foundation audit/init in `gkc.wikibase.foundation` already composes mash + shipper rather than owning low-level HTTP contracts.
- Planned work must extend these layers, not fork them.

### Documentation Fitment Requirements (Identified Gaps)

- `docs/gkc/api/mash.md` is still Wikidata-forward and does not yet document `WikibaseApiClient` as the generic read path for Data Distillery and other Wikibase targets.
- `docs/gkc/api/shipper.md` documents public routes well, but needs a stronger architecture boundary statement clarifying that all Wikibase writes (including Data Distillery ontology operations) flow through shipper.
- `docs/gkc/api/index.md` lists Cooperage but has only a placeholder section; this is insufficient for architectural fitment decisions.
- No dedicated `docs/gkc/api/cooperage.md` exists yet; this blocks clear scoping for transformation/packaging responsibilities.
- We need one cross-module contract page describing mash/shipper/cooperage/wikibase handoffs to orient custom Copilot agents and reduce reinvention.

## Outstanding Design Inputs (Deferred)

The following are explicitly deferred for post-V1 planning:

- **Staging Wikibase instance** for testing changes before production promotion (mentioned in counter-arguments, not yet scoped)
- **GKC Profile Editor UI** to abstract Wikibase complexity for non-technical contributors
- **Webhook-based change detection** vs. polling (start with polling, optimize later)
- **QLever integration** for complex SPARQL queries beyond Blazegraph capacity
- **Contribution workflow** for community curation and PR-equivalent review in Wikibase context
- **Allowed-items cache scalability** beyond SpiritSafe repo storage (future high-volume scenarios)

## Current Status (2026-03-06 to 2026-03-07)

**Phase 0, 0.5, 0.9 Complete**

Completed in Phase 0 (foundation implementation):

- `gkc wikibase audit` and `gkc wikibase init` are implemented and exercised against Data Distillery.
- Foundation ontology profiles are in place and expanded (Phase 0 + substantial Phase 0.5 seed terms).
- Init now includes summary enforcement and bot-mode defaulting behavior from auth username format.
- Diff-style planning support was added in shipper flow to inspect create/update/no-op decisions.
- Dry-run and execute reporting now includes actionable request payload visibility and API error propagation.
- Critical property-create bug was resolved: property `datatype` must be placed inside the `data` JSON payload for `wbeditentity` property creation on this instance.

Completed in Phase 0.5 (ontology expansion):

- Foundation ontology expanded with classifier entities and properties for Fermenter contracts
- Message model implemented with addressable key + monolingual text templates for multilingual support
- Sync provenance properties added for source attribution and revision tracking

Completed in Phase 0.9 (documentation consolidation):

- Updated authentication.md and setup.md with Data Distillery Wikibase environment variables and first-time setup
- Created architecture document (DataDistillery-Wikibase.md) capturing current implementation contract
- Created CLI reference (gkc/cli/wikibase.md) with audit/init commands and patterns
- Created API reference (gkc/api/wikibase.md) with foundation functions and Data Distillery property-create contract
- Updated shipper.md with quick-start blocks for all public routes (write_item, write_property, plan_batch)
- Added Phase 0 execution validation section documenting first thorough shipper API test results
- Updated mkdocs.yml nav with new Wikibase documentation pages
- Validated all documentation with three successful mkdocs builds

Notes and decisions captured from Phase 0 execution debugging:

- Data Distillery accepted manual property creation and API write authentication, but rejected property creates when `datatype` was passed as a top-level request param.
- Verified fix path: embed `datatype` inside `data` JSON for `new=property` writes.
- Property creation now succeeds with this request shape.
- Keep this behavior treated as instance contract for Data Distillery until proven otherwise on additional Wikibase targets.

External coordination notes:

- SpiritSafe Phase 1 completed (PR skybristol/SpiritSafe#4) with manifest builder, profile_graph metadata, and linkage validation schema
- YAML structure now stable with explicit cross-profile relationships declared
- Foundation ready for Phase 1 (client library build) and Phase 2 (profile import) to proceed

## Phase Plan

### Phase 0 - Wikibase Foundation Ontology and Init — **[✓ COMPLETE]**

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

### Phase 0.5 - Ontology Seed Expansion (Fermenter-aligned) — **[✓ COMPLETE]**

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

### Phase 0.9 - Documentation and Interface Consolidation — **[✓ COMPLETE]**

**Purpose**: Consolidate docs and interface contracts after rapid implementation work, before deeper Phase 1/2 expansion.

Deliverables:

- Updates to `docs/gkc/authentication.md` and `docs/gkc/setup.md` on authentication for Data Distillery Wikibase and supporting environment variables
- New architecture document at `docs/architecture/DataDistillery-Wikibase.md` laying out the purpose and motivation for the Wikibase instance and its place in the architecture
- API docs pass for Wikibase init/audit and shipper write behavior (including property create request shape).
- CLI docs pass for `gkc wikibase` commands, arguments, defaults, execute/dry-run semantics, and output artifacts.
- Updates to `docs/gkc/api/shipper.md` to bring it into alignment after recent changes to the API; ensure all public API routes have quick start code blocks
- Update mkdocs nav and page structure for new Wikibase architecture material and command reference pages.
- Add troubleshooting notes for common API failures observed in practice (datatype placement, auth group mismatch, write summary requirements).

Exit criteria:

- Documentation accurately reflects current behavior of shipped code paths.
- Wikibase command reference is sufficient for first-time setup and repeatable initialization.
- Architecture documentation explicitly captures current constraints and temporary implementation contracts discovered during Phase 0 execution.
- All new docs build cleanly with current MkDocs workflow.

**Completion Status**: All deliverables completed and validated in single session (2026-03-06 to 2026-03-07):
- Core documentation: authentication, setup, architecture (DataDistillery-Wikibase.md)
- CLI reference: gkc/cli/wikibase.md with audit/init command patterns
- API reference: gkc/api/wikibase.md with foundation function signatures and Data Distillery contracts
- Shipper updates: quick-start blocks for all public routes (write_item, write_property, plan_batch) plus Phase 0 execution validation section
- Nav updates: mkdocs.yml wired with new Wikibase pages under architecture/CLI/API sections
- Validation: Three successful mkdocs builds with zero blocking errors

---

### Phase 1 - Cross-Module Boundary Hardening and Gap Closure

**Purpose**: Lock in architecture boundaries so we extend existing mash/shipper capabilities instead of recreating clients in `gkc.wikibase`.

Work items by module:

- **Mash**
  - Document and test `WikibaseApiClient` as the default generic read path for Data Distillery and other Wikibase targets.
  - Add any missing read helpers needed by future phases (only if absent), keeping endpoint-agnostic contracts.
- **Shipper**
  - Keep Wikibase write behavior centralized in `WikibaseShipper`.
  - Identify and implement any missing write primitives required by ontology workflows (for example, claim/reference helper surfaces) in shipper, not in `gkc.wikibase`.
- **Wikibase**
  - Restrict `gkc.wikibase` responsibilities to orchestration and semantic planning.
  - Refactor planned APIs that duplicate mash/shipper concerns into thin orchestration wrappers.
- **Documentation**
  - Add/expand docs to make these boundaries explicit for custom agents.

Scope anchors:

- Issue #121 (Define Data Distillery semantic model)
- New issue: Cross-module Wikibase responsibility consolidation

Exit criteria:

- No new generic read/write client created under `gkc.wikibase`.
- All Data Distillery read paths resolve through mash primitives.
- All Data Distillery write paths resolve through shipper primitives.
- Architecture docs explicitly describe ownership boundaries and extension points.

---

### Phase 2 - Dogfooding Ontology Entity Profiles in Data Distillery

**Purpose**: Continue ontology buildout by authoring GKC Entity Profiles for Data Distillery-resident semantic entities (for example, GKC Property Specification entities) and using those profiles to create/update Wikibase entities.

Work items by module:

- **Wikibase**
  - Add ontology-profile sets that describe semantic backbone entities beyond the current foundation seed.
  - Implement orchestration commands that load profile definitions, compute target entity plans, and call mash/shipper for execution.
- **Mash**
  - Provide retrieval support for plan reconciliation (label/QID lookup, existing-claim fetch).
- **Shipper**
  - Execute create/update plans produced by ontology profile orchestration.
  - Preserve Data Distillery-specific request-shape contracts already validated in Phase 0.
- **SpiritSafe**
  - Keep profile/metadata structures aligned with ontology profile authoring needs and provenance metadata.

Scope anchors:

- Issue #122 (Build SpiritSafe manifest projection + sync pipeline)
- New issue: Ontology entity dogfooding profiles and orchestration

Exit criteria:

- New ontology entity families are defined as machine-readable profiles and provisioned through the same profile-driven flow.
- Provisioning run uses mash for reads and shipper for writes with no duplicated client logic.
- Reconciliation output includes clear create/update/no-op decisions and provenance mapping.

---

### Phase 3 - Transformation and Packaging Pipeline (Cooperage-led)

**Purpose**: Build the reusable transformation layer that projects Data Distillery semantic entities into SpiritSafe-ready runtime artifacts.

Work items by module:

- **Cooperage**
  - Own transformation contracts: Wikibase entity graph → SpiritSafe profile/metadata/query/cache artifacts.
  - Implement canonical projection helpers and round-trip structural comparison utilities.
  - Define packaging contracts for shippable semantic bundles consumed by Fermenter and shipper workflows.
- **Mash**
  - Supply input retrieval adapters for entities needed by projection.
- **Wikibase**
  - Orchestrate phase execution and pass retrieved entities into cooperage projection pipelines.
- **SpiritSafe**
  - Validate generated artifacts against schema/linkage checks and manifest expectations.

Scope anchors:

- Issue #122 (SpiritSafe manifest projection + sync pipeline)
- Issue #125 (Design Data Distillery snapshot/export path)
- New issue: Cooperage transformation contracts for Wikibase projections

Exit criteria:

- Projection logic is implemented in cooperage (not in `gkc.wikibase`) and is reusable beyond Data Distillery.
- Generated artifacts pass SpiritSafe validation flows.
- Round-trip checks report structural equivalence and actionable diffs when mismatches occur.

---

### Phase 4 - Sync Automation and Drift Management

**Purpose**: Automate bidirectional synchronization while keeping module boundaries intact.

Work items by module:

- **Mash**
  - Provide revision/change read helpers used for drift detection.
- **Cooperage**
  - Compare projected artifacts vs. current SpiritSafe state and produce deterministic diff sets.
- **Shipper**
  - Apply writes when sync direction targets Wikibase.
- **Wikibase**
  - Orchestrate sync flows (`from-wikibase`, `to-wikibase`), conflict policy application, and reporting.
- **CI/Docs**
  - Implement scheduled workflow and conflict/runbook documentation.

Scope anchors:

- Issue #122 (SpiritSafe manifest projection + sync pipeline)
- New issue: Sync orchestration with module-split execution

Exit criteria:

- Scheduled and manual sync operations run through mash/cooperage/shipper orchestration.
- Conflict decisions are explicit, reviewable, and reproducible.
- Manifest/provenance metadata captures revision baselines and conflict outcomes.

---

### Phase 5 - Fermenter Resolver Integration and Offline/Online Parity

**Purpose**: Use cooperage-produced semantic artifacts and optional mash live reads to satisfy Fermenter contracts with deterministic fallback.

Work items by module:

- **Cooperage**
  - Finalize resolver-facing package/index structures for property metadata, specifications, and multilingual messages.
- **Mash**
  - Provide optional live refresh retrieval path for parity checks and cache miss diagnostics.
- **Fermenter + SpiritSafe**
  - Consume cache-first indexes with fallback chain guarantees.
- **Wikibase**
  - Publish query contracts and semantic assumptions used by resolver construction.

Scope anchors:

- Issue #124 (Specify Data Distillery query contracts for Fermenter resolvers)
- Issue #126 (Fermenter contract tests for Data Distillery online/offline parity)

Exit criteria:

- Offline cache-only mode remains first-class and deterministic.
- Online enhancement mode yields equivalent functional outcomes for covered contracts.
- Source provenance is visible in resolver outputs (cache/live/profile-default).

---

### Phase 6 - Synthetic Fixtures and Contract Test Harness

**Purpose**: Validate end-to-end behavior with synthetic Data Distillery entities while preserving production isolation.

Work items by module:

- **Wikibase**
  - Define synthetic ontology/profile fixtures and orchestration commands.
- **Mash**
  - Support fixture-state retrieval and verification reads.
- **Shipper**
  - Provision and cleanup fixture entities safely in test ranges/namespaces.
- **Cooperage**
  - Produce projected fixture artifacts used for round-trip and parity assertions.
- **Testing/Docs**
  - Document fixture lifecycle, safety guards, and CI integration boundaries.

Scope anchors:

- Issue #126 (Fermenter contract tests for Data Distillery online/offline parity)
- New issue: Synthetic fixture orchestration across mash/shipper/cooperage

Exit criteria:

- Fixture setup/teardown is automated, safe, and isolated from production entities.
- Round-trip and parity tests run fully on synthetic fixtures.
- Failures identify whether root cause is retrieval (mash), transformation (cooperage), write contract (shipper), or orchestration (wikibase).

---

## Coordinated Module Layout (V1)

The V1 layout should align with existing responsibilities and avoid client duplication.

```
gkc/
  mash.py                # Generic Wikibase/Wikidata read primitives and loaders
  shipper.py             # Generic Wikibase-compatible write primitives and planning
  cooperage.py           # Reusable transformation/projection/packaging contracts

  wikibase/
    __init__.py
    foundation.py        # Data Distillery ontology audit/init orchestration
    foundation_profiles/ # Dogfooded ontology/entity profile definitions
      foundation_entities.yaml
      foundation_properties.yaml
      foundation_metadata.yaml
      README.md
    ontology_profiles/   # Next-wave semantic entity profiles for dogfooding
    orchestration/       # Data Distillery-specific orchestration over mash+shipper+cooperage
    sync/                # Sync orchestration and policy handling (not low-level clients)
    testing/             # Fixture definitions + orchestration entrypoints
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

1. **Phase 0-1**: Complete ontology seed and lock boundary contracts (`mash` read, `shipper` write, `wikibase` orchestration)
2. **Phase 2**: Dogfood additional ontology entity profiles and provision via existing read/write layers
3. **Phase 3**: Move export/projection logic into cooperage and validate round-trip fidelity
4. **Phase 4**: Automate sync using orchestration that composes mash/cooperage/shipper
5. **Phase 5**: Drive Fermenter integration from cooperage-built cache artifacts with optional mash live reads
6. **Phase 6**: Validate all contracts with synthetic fixtures and fault-localized tests

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

## Required Documentation Deliverables Before Phase 2+ Execution

To reduce reinvention risk for custom agents and maintain architectural fitment clarity, the following docs are required:

- `docs/gkc/api/mash.md`: add explicit generic Wikibase read contract section with Data Distillery examples.
- `docs/gkc/api/shipper.md`: add boundary section clarifying shipper as the single write surface for Wikibase-compatible targets.
- `docs/gkc/api/cooperage.md` (new): define transformation/projection responsibilities, extension points, and examples tied to semantic artifact packaging.
- `docs/gkc/api/index.md`: replace Cooperage placeholder with live link and concise scope summary.
- `docs/architecture/` cross-module contract page (new): mash ↔ cooperage ↔ shipper ↔ wikibase orchestration handoffs for agent orientation.
