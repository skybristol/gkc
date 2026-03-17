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

**[confirmed]** 2026-03-07: Mash refactor complete. `gkc.mash` is now a package with generic `WikibaseApiClient`, `MashSourceAdapter` protocol, explicit filtering helpers, and all Wikidata-specific naming migrated to Wikibase-generic naming. Cooperage deprecated; functions migrated to mash and utilities.
  Source: MashRefactor sprint completion, Code Cleaner collaboration

**[confirmed]** 2026-03-07: Module boundaries validated. Mash = generic Wikibase reads, Shipper = generic Wikibase writes (validated against Data Distillery), Wikibase = DD orchestration + transformation logic. No new client code in wikibase module.
  Source: WikibaseV1 architectural review, Phase 0 completion

**[confirmed]** 2026-03-08: Shared profile-to-write planning path implemented in code and CLI: `spirit_safe.create_curation_packet` → `still_charger.charge_curation_packet` → `cooperage.barrel_curation_packet_to_wikibase_plan` → optional `shipper.plan_batch` via `gkc wikibase plan-write --with-shipper-plan`.
  Source: Runtime validation of plan-write pipeline, 2026-03-08

**[confirmed]** 2026-03-08: Direction set for execute-mode follow-on: maintain the current planning command as preflight and add explicit, authenticated write execution as a separate controlled step after diff visibility.
  Source: Wikibase planning workflow alignment, 2026-03-08

## Current Status Summary (2026-03-08)

**Completed Work**:

- **Phase 0, 0.5, 0.9**: Foundation ontology established (Q1-Q6, P1-P5+), audit/init tools working, documentation consolidated.
- **Mash refactor**: Package extraction complete with generic `WikibaseApiClient`, `MashSourceAdapter` protocol, and validated Data Distillery compatibility.
- **Shipper validation**: `WikibaseShipper` works with any Wikibase instance; DD property-create contract validated.
- **Cooperage deprecation**: Functions migrated to mash/utilities; module scheduled for removal in v0.4.0.
- **Documentation**: Mash, shipper, wikibase docs updated; architecture and CLI reference complete.

**Next Focus** (Phase 1 carry-forward):

- Import existing SpiritSafe Entity Profiles into Data Distillery as GKC Entity Profile items.
- Create property metadata and specification entities for Fermenter registry contracts.
- Complete authenticated execute-mode orchestration for profile import/write operations.
- Finalize declarative profile-profile coverage for all importable structures and reverse-path readiness.

**Architecture Clarity**:

- Mash and shipper are generic, instance-agnostic layers.
- Wikibase module owns DD-specific orchestration and transformation logic.
- SpiritSafe YAML remains the operational artifact (offline-first guarantee).
- Data Distillery provides semantic richness, queryability, multilingual support (optional enhancement).

## Current Status Addendum (2026-03-08)

**Implemented Since 2026-03-07**:

- Shared packet pipeline now exists as executable orchestration (`build_wikibase_write_plan`) and CLI (`gkc wikibase plan-write`).
- `still_charger` is established as the packet fill stage with specificationless and strict charging modes.
- `cooperage` now actively performs packet-to-Wikibase operation barreling while keeping compatibility re-exports.
- `plan-write --with-shipper-plan` now computes `WikibaseShipper.plan_batch` diff summaries (create/update/no-op/ambiguous/blocked).

**Direction Toward Execute**:

- Keep `plan-write` as the explicit preflight command for logical path, packet/charge/barrel diagnostics, and diff planning.
- Execute capability is now implemented as a distinct, authenticated step using the same planned operation payloads after review.
- Preserve dry-run-first behavior and clear guardrails (`--require-auth`, explicit execute flag) for safe promotion from plan to write.

## Phase 1 Closeout Pass (2026-03-08)

**Outcome**: Phase 1 is active and materially advanced. Preflight planning and authenticated execute-mode are both implemented with shared-payload parity.

**Completed in this pass**:

- Shared profile-driven planning path implemented and validated end-to-end:
  - `spirit_safe.create_curation_packet`
  - `still_charger.charge_curation_packet`
  - `cooperage.barrel_curation_packet_to_wikibase_plan`
  - optional shipper diff planning via `WikibaseShipper.plan_batch`
- Wikibase CLI preflight path implemented:
  - `gkc wikibase plan-write`
  - optional `--with-shipper-plan` for create/update/no-op/ambiguous/blocked previews
  - auth/runtime flags added to support controlled promotion toward execute
- Wikibase CLI execution path implemented:
  - `gkc wikibase execute-write`
  - authenticated by design
  - dry-run by default with explicit `--execute` for write submission
  - per-operation write status reporting (`submitted` / `dry_run` / `blocked` / `error`)
- Documentation alignment completed for current architecture and operator usage:
  - API updates for wikibase/cooperage/still_charger
  - CLI updates for plan-write preflight and shipper diff visibility
  - architecture contract updates for execute guardrails
- Operator notebook added and validated with API-first execution flow and JSON artifact outputs.

**Carry-forward to complete Phase 1**:

- Finalize declarative profile-profile coverage for remaining importable structures.
- Complete profile import command surface (`import-profiles`) on top of shared plan/execute orchestration.
- Confirm round-trip readiness requirements for Phase 3 handoff.

**Phase boundary note**:

- This closeout confirms Phase 1 preflight + execution orchestration maturity and narrows remaining Phase 1 scope to profile-profile declarative coverage and import flow completion.

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

- `gkc.mash` is the canonical read/retrieval layer for Wikibase/Wikidata-compatible APIs. Fully refactored as a package with generic `WikibaseApiClient`, `MashSourceAdapter` protocol, and explicit filtering helpers. Do not reimplement generic retrieval clients inside `gkc.wikibase`.
- `gkc.shipper` is the canonical write/delivery layer for Wikibase-compatible APIs, including Data Distillery. `WikibaseShipper` works with any Wikibase instance. Do not duplicate write operators in `gkc.wikibase`.
- `gkc.wikibase` is Data Distillery semantic-backbone orchestration: ontology profile loading, audit/init orchestration, semantic planning, transformation logic for SpiritSafe projections, and coordination of read/write flows through mash + shipper.
- `gkc.still_charger` is the canonical packet-fill layer for applying source values to curation packet scaffolds.
- `gkc.cooperage` currently owns packet-to-operation barreling transforms used by profile-driven write planning, while preserving compatibility re-exports for legacy schema/RDF helper imports.
- SpiritSafe remains the operational artifact and runtime cache surface; synchronization logic must preserve lossless round-trip behavior.

### Existing Capability Reuse (Current Code Reality)

- **Mash refactor complete**: `gkc.mash` is now a full package with `WikibaseApiClient` as the generic read client for any Wikibase instance, `MashSourceAdapter` protocol for extensibility, and all Wikidata-specific naming migrated to generic Wikibase naming.
- **Shipper validated**: `gkc.shipper.WikibaseShipper` provides all write primitives (`write_item`, `write_property`, `plan_batch`) and is fully validated against Data Distillery property create contracts (datatype in serialized payload).
- **Foundation orchestration established**: `gkc.wikibase.foundation` implements audit/init flows by composing mash + shipper, not owning low-level HTTP.
- **Still Charger active**: `gkc.still_charger.charge_curation_packet` fills packet scaffolds from source values with structured reports.
- **Cooperage active for barreling**: `gkc.cooperage.barrel_curation_packet_to_wikibase_plan` transforms charged packet data into shipper-compatible operations.
- All planned work must extend these validated layers, not fork or duplicate them.

### Documentation Status (Post-Mash Refactor)

- **Mash**: `docs/gkc/api/mash.md` now documents `WikibaseApiClient` as the generic read client with Data Distillery examples, `MashSourceAdapter` protocol, and quick-start blocks for all public routes.
- **Shipper**: `docs/gkc/api/shipper.md` updated with quick-start blocks for all public routes, architecture notes confirming it works with any Wikibase instance, and Data Distillery property-create contract notes.
- **Wikibase**: `docs/architecture/DataDistillery-Wikibase.md`, `docs/gkc/cli/wikibase.md`, and `docs/gkc/api/wikibase.md` completed in Phase 0.9 with foundation patterns and audit/init behavior.
- **Cooperage**: `docs/gkc/api/cooperage.md` documents deprecated surface with migration guide; module will be removed in v0.4.0.
- **Remaining gap**: No cross-module contract page yet describing orchestration handoffs for agent orientation (lower priority now that boundaries are clear).

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

### Phase 1 - Profile-Driven Entity Import via Profile Profiles — **[IN PROGRESS]**

**Purpose**: Import existing SpiritSafe Entity Profiles into Data Distillery using declarative Profile Profiles that map YAML structure to Wikibase claims, establishing the pattern for profile-driven orchestration and demonstrating bidirectional transformation capability.

**Context**: Mash/shipper architectural boundaries are locked. Foundation ontology (Q1-Q6, P1-P5+) provisioned. Profile Profiles dogfood the profile system for meta-modeling, validating that profiles can drive transformation logic.

**Approach**: Build transformation logic declaratively as YAML profiles rather than imperative Python code.

Work items:

- **Profile Profile definitions** (in `gkc/wikibase/foundation_profiles/`):
  - `entity_profile_profile.yaml`: Maps Entity Profile YAML structure → Wikibase GKC Entity Profile items (Q3)
    - Declares how profile metadata (name, version, description, status) maps to item labels/descriptions/claims
    - Maps top-level profile fields to Wikibase properties
    - Includes bidirectional direction metadata (YAML ↔ Wikibase)
  - `property_profile.yaml`: Maps property definitions → GKC Entity Property items (Q5)
    - Each statement in a profile becomes an item
    - Maps YAML fields (property_id, datatype, constraints) to item claims
    - Links back to parent profile via claims
  - `specification_profile.yaml`: Maps specifications → GKC Property Specification items (Q6)
    - Each specification constraint becomes an item
    - Maps specification type, parameters, messages to claims
    - Links to parent property via claims
  - Each profile includes interlinks and bidirectional transformation rules

- **Name resolution orchestration** (in `gkc/wikibase/init.py`):
  - Load Profile Profiles from foundation config
  - For each Profile Profile, resolve human-readable names ("instance_of", "label", "has_specification") → QID/PID
    - Use mash `WikibaseApiClient` to search entities by label
    - Store resolved mappings in `foundation_profiles_resolved.json`
  - Extend existing `init_wikibase_foundation()` to provision resolved mapper on first run
  - Re-run to detect/update if ontology changes

- **Generic profile-driven transformation** (in `gkc/wikibase/transform.py`):
  - Load SpiritSafe profile YAML
  - Apply applicable Profile Profile(s) as declarative transform spec
  - For each Profile Profile rule:
    - Extract values from source YAML per rule path
    - Build Wikibase entity plan (label, description, claims)
    - Map values through resolved identifier cache
  - Generate create/update/skip decisions
  - No special handling per profile type; logic driven entirely by Profile Profile declarations

- **Orchestration flow** (extend `gkc wikibase` CLI):
  - `gkc wikibase import-profiles [--profile NAME] [--from-path PATH] [--dry-run] [--execute]`
  - Steps:
    1. Ensure foundation profiles resolved (run init if needed)
    2. Load Profile Profiles + resolved mapper
    3. For each SpiritSafe profile, apply transformation
    4. Present diff plans to user
    5. Execute via shipper on `--execute`
  - Reports: created/updated/skipped counts, diff plans per entity, error details

- **Bidirectional design**:
  - Profile Profiles include `bidirectional: true` with field-level direction metadata
  - Same rules drive both import (Phase 1) and export (Phase 3)
  - No separate export transform logic needed; same Profile Profile applied in reverse

- **Placement and future migration**:
  - Store in `gkc/wikibase/foundation_profiles/` for now (foundational infrastructure)
  - Future: when pattern stabilizes, can migrate to SpiritSafe as "configurator" profiles
  - Enables configuration-as-code approach: changes to Profile Profile update behavior without code changes

Scope anchors:

- Issue #121 (Define Data Distillery semantic model for Fermenter registries)
- Issue #122 (Build SpiritSafe manifest projection + sync pipeline) — import direction only
- SpiritSafe Phase 1 completion (manifest + profile_graph metadata available for reference)

Exit criteria:

- Profile Profiles defined for all entity types (Entity Profile, Property, Specification)
- Name resolution orchestration resolves foundation names → QID/PID automatically
- Generic transformation logic applies Profile Profiles without special-case code
- All existing SpiritSafe profiles (TribalGovernmentUS, OfficeHeldByHeadOfState) successfully imported
- Diff plans accurate and actionable
- Round-trip validation: import → export produces semantically equivalent YAML
- Bidirectional metadata in Profile Profiles is sufficient for Phase 3 export (no new logic needed)

Phase 1 progress snapshot (2026-03-08):

- Preflight write planning path is implemented and validated in code, CLI, tests, docs, and operator notebook.
- Execute-mode write replay is implemented via `execute_wikibase_write_plan` and `gkc wikibase execute-write`, with authenticated gating and dry-run-by-default safety behavior.

---

### Phase 2 - SPARQL Query Registry and Allowed-Items Hydration

**Purpose**: Model SPARQL queries as Wikibase entities to support allowed-items list hydration and establish query-driven validation patterns.

**Context**: Profiles imported in Phase 1 reference SPARQL queries for allowed-items constraints. We need these queries registered in Data Distillery and integrated with SpiritSafe cache hydration workflows.

Work items:

- **SPARQL Query Entity Model** (in `gkc.wikibase`):
  - Define foundation entity for SPARQL Query (new Q item, instance of foundation type).
  - Create query items with metadata: label, description, query purpose, target endpoint.
  - Store query code in discussion pages (Wikidata Query Service + QLever syntax variants).
  - Link queries to properties/profiles that reference them.

- **Query Import from SpiritSafe** (in `gkc.wikibase`):
  - Read `.sparql` files from SpiritSafe profile query directories.
  - Create Data Distillery query entities with source provenance.
  - Link to parent profile and target endpoint configuration.

- **Hydration Integration** (coordinate with SpiritSafe):
  - Query references in profile YAML point to Data Distillery query IDs.
  - SpiritSafe manifest tracks query metadata for cache invalidation.
  - Hydration workflow retrieves query code from DD or local cache.

- **CLI Extension**:
  - `gkc wikibase import-queries [--profile NAME] [--dry-run] [--execute]`
  - Reports: query entity creation, linkage to profiles, cache metadata.

Scope anchors:

- Issue #122 (Build SpiritSafe manifest projection + sync pipeline)
- SpiritSafe allowed-items hydration workflows

Exit criteria:

- All SpiritSafe SPARQL queries registered as Data Distillery entities.
- Query code retrievable via mash for hydration workflows.
- Query-to-profile linkage enables semantic discovery of dependent profiles.
- Cache manifest includes query metadata for refresh policy decisions.

---

### Phase 3 - Export and Transformation Pipeline (Wikibase-led)

**Purpose**: Build transformation logic that exports Data Distillery entities back to SpiritSafe YAML + cache artifacts with lossless round-trip fidelity.

**Context**: Cooperage is deprecated. Transformation logic lives in `gkc.wikibase` until a clearer reusable pattern emerges. Focus on DD→SpiritSafe projection with structural validation.

Work items:

- **Export Orchestration** (in `gkc.wikibase.export`):
  - Retrieve profile entities from Data Distillery via mash.
  - Transform entity claims/metadata to profile YAML structure.
  - Generate property definitions, specifications, and cross-profile linkage metadata.
  - Write output to SpiritSafe directory structure with manifest updates.

- **Structural Validation** (in `gkc.wikibase.export`):
  - Compare exported YAML against import source for structural equivalence.
  - Report diff of labels, descriptions, claims, specifications.
  - Validate against SpiritSafe schema (profile_graph, linkage metadata).

- **Cache Artifact Generation** (in `gkc.wikibase.export`):
  - Generate property index JSON for Fermenter resolution.
  - Generate specification index JSON with multilingual messages.
  - Generate query metadata for hydration workflows.
  - Update manifest with export timestamp, source revision, artifact URLs.

- **CLI Extension**:
  - `gkc wikibase export-profiles [--profile NAME] [--output DIR] [--validate]`
  - Reports: exported profiles, validation results, cache artifacts written.

Scope anchors:

- Issue #122 (Build SpiritSafe manifest projection + sync pipeline) — export direction
- Issue #125 (Design Data Distillery snapshot/export path)

Exit criteria:

- Export produces valid SpiritSafe YAML passing schema validation.
- Round-trip test: import → export → structural diff shows no semantic loss.
- Cache artifacts (properties.json, specifications.json, messages.json) generated and consumable by Fermenter stubs.
- Manifest tracks last export revision for drift detection.

---

### Phase 4 - Bidirectional Sync and Conflict Resolution

**Purpose**: Automate sync workflows with drift detection, conflict policies, and GitHub Actions integration.

**Context**: Import (Phase 1) and export (Phase 3) are implemented. Now orchestrate bidirectional sync with conflict resolution and automation.

Work items:

- **Sync Orchestration** (in `gkc.wikibase.sync`):
  - `gkc wikibase sync --direction [from-wikibase|to-wikibase|bidirectional]`
  - Drift detection: compare revision IDs in manifest vs. current DD state.
  - Conflict detection: identify entities modified in both DD and SpiritSafe since last sync.
  - Conflict policies: last-write-wins, manual-review-required, prefer-wikibase, prefer-spiritsafe.

- **Revision Tracking** (via mash reads):
  - Retrieve entity revision IDs from Data Distillery.
  - Track last-synced revision in manifest for each profile/property/query.
  - Detect modifications via revision ID comparison.

- **Conflict Reporting**:
  - Generate conflict report JSON with entity IDs, conflict type, modifications.
  - CLI output shows conflicts requiring manual resolution.
  - Optional auto-resolution with explicit policy flag.

- **GitHub Actions Workflow** (in SpiritSafe repo):
  - Scheduled workflow polls Data Distillery for changes.
  - Triggers export + validation + PR creation on detected drift.
  - Manual trigger for import direction (SpiritSafe → DD).

- **Documentation**:
  - Conflict resolution runbook.
  - Sync policy decision guide.
  - Troubleshooting common drift scenarios.

Scope anchors:

- Issue #122 (Build SpiritSafe manifest projection + sync pipeline)
- GitHub Actions integration for automation

Exit criteria:

- Manual sync runs successfully in both directions with conflict detection.
- Automated scheduled workflow runs without manual intervention for test period.
- Conflict policies are configurable and documented.
- Manifest tracks sync state with revision provenance.

---

### Phase 5 - Fermenter Property Registry and Validation Message Resolution

**Purpose**: Integrate Data Distillery property metadata and multilingual validation messages into Fermenter runtime with offline/online parity.

**Context**: Cache artifacts (properties.json, specifications.json, messages.json) are generated in Phase 3 export. Now consume them in Fermenter with optional live fallback via mash.

Work items:

- **Property Metadata Registry** (in `gkc.fermenter` or new resolver module):
  - Load property index from SpiritSafe cache (offline mode).
  - Retrieve property metadata: datatype, specifications, allowed-items query reference.
  - Optional live fallback: fetch from Data Distillery via mash on cache miss.

- **Specification Resolver** (in Fermenter):
  - Load specification index from cache.
  - Resolve specification by property + spec type.
  - Retrieve parameters, executable logic references, multilingual messages.
  - Optional live fallback via mash.

- **Multilingual Message Resolution** (in Fermenter):
  - Load message index from cache.
  - Resolve message by key + language code.
  - Implement fallback chain: requested language → English → profile default → system default.
  - Template parameter substitution for parametric messages.
  - Optional live refresh via mash.

- **Offline/Online Parity Testing** (in tests):
  - Identical test suite runs in offline (cache-only) and online (mash-fallback) modes.
  - Validate deterministic outcomes for covered contracts.
  - Performance benchmarks: cache resolution < 10ms, live fallback < 100ms.

- **Source Provenance Tracking**:
  - Resolver outputs indicate source: cache / live / profile-default / system-default.
  - Logging/debugging includes provenance metadata.

Scope anchors:

- Issue #121 (Define Data Distillery semantic model for Fermenter registries)
- Issue #124 (Specify Data Distillery query contracts for Fermenter resolvers)
- Issue #126 (Fermenter contract tests for Data Distillery online/offline parity)

Exit criteria:

- Fermenter validation workflows consume property/specification metadata from cache.
- Multilingual messages resolve correctly with fallback chain.
- Offline mode is deterministic and complete for existing profiles.
- Online mode provides equivalent outcomes with optional live refresh.
- Source provenance visible in validation output.

---

### Phase 6 - Synthetic Fixtures and End-to-End Validation

**Purpose**: Validate complete workflow with synthetic Data Distillery entities in isolated test ranges.

**Context**: All core workflows are implemented. Now validate with synthetic fixtures to ensure production safety and enable automated regression testing.

Work items:

- **Fixture Definition** (in `gkc/wikibase/testing/`):
  - Define synthetic profiles, properties, specifications, queries as YAML fixtures.
  - Clear labeling convention (e.g., "TEST: Property Name") to prevent pollution.
  - Test range QID allocation (e.g., Q9900-Q9999 reserved for testing).

- **Fixture Provisioning** (via shipper):
  - `gkc wikibase testing provision-fixtures [--fixture-set NAME]`
  - Create test entities in Data Distillery via `WikibaseShipper`.
  - Store fixture metadata (created QIDs, revision IDs) for cleanup.

- **Fixture Cleanup** (via shipper):
  - `gkc wikibase testing cleanup-fixtures [--fixture-set NAME]`
  - Delete or blank test entities safely.
  - Verify no production entities affected.

- **Round-Trip Validation**:
  - Import fixture YAML → Data Distillery (via Phase 1 import).
  - Export DD entities → YAML (via Phase 3 export).
  - Structural diff: assert semantic equivalence.
  - Report any round-trip loss or transformation errors.

- **End-to-End Workflow Tests**:
  - Test sync bidirectional with fixtures (Phase 4).
  - Test Fermenter resolution with fixture cache (Phase 5).
  - Test SPARQL query hydration with fixture queries (Phase 2).
  - Validate multilingual message resolution with fixture messages.

- **CI Integration**:
  - Automated fixture lifecycle in test suite.
  - Safety checks prevent accidental production writes.
  - Test isolation ensures parallel test runs don't conflict.

Scope anchors:

- Issue #126 (Fermenter contract tests for Data Distillery online/offline parity)
- End-to-end validation requirements

Exit criteria:

- Synthetic fixtures provision/cleanup reliably without manual intervention.
- Round-trip tests pass with 100% structural equivalence.
- End-to-end workflow tests cover import/export/sync/resolution paths.
- Test failures clearly identify root cause layer (mash/shipper/wikibase/fermenter).
- CI runs fixture tests safely in isolated test ranges.

---

## Coordinated Module Layout (V1)

The V1 layout aligns with validated boundaries and deprecates cooperage.

```
gkc/
  mash/                  # Generic Wikibase read layer (PACKAGE, refactor complete)
    __init__.py
    core.py              # WikibaseApiClient, loaders, templates
    protocols.py         # MashSourceAdapter, DataTemplate
  
  shipper.py             # Generic Wikibase write layer (validated against DD)
  cooperage.py           # DEPRECATED compatibility facade (remove in v0.4.0)
  utilities.py           # Helper functions (entity URI, validation)

  wikibase/
    __init__.py
    foundation.py        # DD ontology audit/init orchestration (Phase 0 complete)
    init.py              # Name resolution + Profile Profiles mapper provisioning (Phase 1)
    transform.py         # Generic profile-driven transformation logic (Phase 1)
    import_profiles.py   # Profile import orchestration CLI command (Phase 1)
    foundation_profiles/ # Foundation entity/property definitions + Profile Profiles (Phase 0 + Phase 1)
      foundation_entities.yaml              # Q1-Q6 definitions (Phase 0)
      foundation_properties.yaml            # P1-P5+ definitions (Phase 0+)
      foundation_metadata.yaml              # Ontology metadata (Phase 0)
      foundation_profiles_resolved.json     # Resolved name → QID/PID mapper (generated Phase 1)
      entity_profile_profile.yaml           # Profile Profile for Entity Profiles (Phase 1)
      property_profile.yaml                 # Profile Profile for Properties (Phase 1)
      specification_profile.yaml            # Profile Profile for Specifications (Phase 1)
      README.md                             # Documentation of all profiles
    import_queries.py    # SPARQL query import orchestration (Phase 2)
    export.py            # DD → SpiritSafe transformation (Phase 3)
    sync.py              # Bidirectional sync + conflict resolution (Phase 4)
    resolver.py          # Property/spec/message resolution for Fermenter (Phase 5)
    testing/             # Fixture definitions + provision/cleanup (Phase 6)
      fixtures/
      provision.py
      cleanup.py
```

SpiritSafe additions:

```
SpiritSafe/
  cache/
    dd_wikibase/         # Data Distillery export artifacts
      properties.json    # Property metadata index (Phase 3)
      specifications.json # Specification metadata index (Phase 3)
      messages.json      # Multilingual message index (Phase 3)
      queries.json       # Query metadata index (Phase 2)
      sync_state.json    # Last sync revision + conflict log (Phase 4)
  .github/
    workflows/
      sync-from-dd.yml   # Scheduled DD → SpiritSafe sync (Phase 4)
```

---

## Migration Strategy

**Phase 0, 0.5, 0.9 Complete**: Foundation ontology established, mash refactored, shipper validated, documentation consolidated.

**Remaining phases** are focused on profile-driven buildout:

1. **Phase 1**: Import SpiritSafe profiles to Data Distillery (profiles \u2192 DD entities)
2. **Phase 2**: Register SPARQL queries as DD entities + hydration integration
3. **Phase 3**: Export DD entities back to SpiritSafe YAML + cache artifacts (DD \u2192 SpiritSafe)
4. **Phase 4**: Automate bidirectional sync with conflict resolution
5. **Phase 5**: Integrate DD metadata into Fermenter with offline/online parity
6. **Phase 6**: Validate workflows with synthetic fixtures

Rollback strategy:

- SpiritSafe YAML remains authoritative throughout V1.
- Wikibase serves as collaborative semantic layer, not runtime requirement.
- Offline-first operation guaranteed; DD connection is optional enhancement.
- Any phase can be paused without breaking existing workflows.

Success metrics:

- **Round-trip fidelity**: 100% structural equivalence for import \u2192 export cycles.
- **Sync reliability**: Automated sync runs without manual intervention for 30-day test period.
- **Offline parity**: Fermenter validation passes identically in offline (cache-only) and online (DD-enhanced) modes.
- **Performance**: Property resolution < 10ms from cache, < 100ms from DD live fetch.
- **Coverage**: All existing SpiritSafe profiles (TribalGovernmentUS, OfficeHeldByHeadOfState) successfully imported, exported, and validated.

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

## Documentation Maintenance (Ongoing)

**Completed** (Phase 0.9):

- `docs/gkc/api/mash.md`: Fully updated with generic Wikibase read contracts and Data Distillery examples.
- `docs/gkc/api/shipper.md`: Updated with boundary clarification and quick-start blocks for all public routes.
- `docs/architecture/DataDistillery-Wikibase.md`: Architecture overview and implementation contracts.
- `docs/gkc/cli/wikibase.md`: CLI reference for audit/init commands.
- `docs/gkc/api/wikibase.md`: Foundation API reference.

**Cooperage deprecated** (mash refactor completion):

- `docs/gkc/api/cooperage.md`: Documents deprecated surface with migration guide to mash/utilities.

**Future additions** (as phases complete):

- `docs/gkc/api/wikibase.md`: Expand with import/export/sync/resolver APIs as implemented.
- `docs/gkc/cli/wikibase.md`: Add import-profiles, import-queries, export-profiles, sync commands.
- `docs/architecture/` cross-module contract page (optional, lower priority now that boundaries are validated).
- Sync runbook and conflict resolution guide (Phase 4).
