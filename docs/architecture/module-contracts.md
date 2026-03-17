# Cross-Module Contracts and Handoffs 

## Purpose

This document defines the current architectural contract between `mash`, `spirit_safe`, `still_charger`, `fermenter`, `cooperage`, `bottler`, `shipper`, and `wikibase` for Data Distillery and broader GKC workflows.

It is written as a practical anti-reinvention guide for contributors and custom agents.

## Boundary Summary

### Mash (`gkc.mash`)

Responsibility:

- Read and retrieve source data from Wikibase/Wikidata-compatible APIs.
- Return stable template structures for downstream processing.
- Provide generic API helpers reusable across Data Distillery and Wikidata.

Out of scope:

- Write or edit operations to remote systems.
- Semantic projection and packaging contracts for runtime artifacts.

Current anchor surface:

- `WikibaseApiClient`
- `WikibaseLoader`
- `WikipediaLoader`

### Spirit Safe (`gkc.spirit_safe`)

Responsibility:

- Load SpiritSafe profile/manifest sources (GitHub or local).
- Build JSON Entity Profiles from SpiritSafe cache entities.
- Extract value-list SPARQL query files from value-list talk pages.
- Hydrate value-list cache artifacts from extracted SPARQL queries.
- Export profile JSON artifacts for downstream packet assembly and hydration.
- Provide profile graph metadata and profile-loading utilities.

Out of scope:

- Direct write execution to Wikibase APIs.
- UI-specific packet interpretation behavior.

Current anchor surface:

- `build_entity_profile_json_documents`
- `export_entity_profile_json_documents`
- `discover_value_list_ids`
- `export_value_list_sparql_queries`
- `hydrate_value_lists_from_cache`
- `load_manifest`
- `load_profile`

Transition-only legacy surface (deferred removal):

- `create_curation_packet`
- `validate_packet_structure`

### Still Charger (`gkc.still_charger`)

Responsibility:

- Assemble curation packet scaffolds from Entity Profile JSON documents.
- Fill curation packet entity scaffolds with concrete source values.
- Support charging from Wikidata entities and other source adapters.
- Emit shared conformance notices and charge summaries.

Out of scope:

- Target payload shaping for any specific destination API.
- API transport execution.

Current anchor surface:

- `build_curation_packet_from_json_profile`
- `charge_curation_packet`
- `charge_packet_from_wikidata_items`
- `ChargeReport`
- `ChargeIssue`

### Fermenter (`gkc.fermenter`)

Responsibility:

- Validate and coerce inbound values using profile-defined directives.
- Provide atomic datatype validators and coercion primitives.
- Enforce fixed values, value-list constraints, and reference-level constraints.
- Emit shared `ConformanceNotice` records with actionable feedback.

Out of scope:

- Packet assembly and packet orchestration.
- Destination-specific payload shaping and transport execution.

Current anchor surface:

- `ConformanceNotice`
- `ValidationResult`
- `validate_*` datatype validators
- `coerce_*` datatype coercers

### Cooperage (`gkc.cooperage`)

Responsibility:

- Convert charged curation packet content into shippable operation plans.
- Host reusable transformation/projection logic that sits between charging and transport.
- Provide compatibility re-exports for schema/specification retrieval utilities.

Out of scope:

- Direct submission to Wikibase/other write APIs.
- Owning profile registry source-of-truth decisions.

Current anchor surface:

- `fetch_entity_rdf`
- `fetch_schema_specification`
- `fetch_entity_schema_json`
- `fetch_entity_schema_metadata`
- `barrel_curation_packet_to_wikibase_plan`
- `BarrelPlanReport`
- `BarrelIssue`

### Bottler (`gkc.bottler`)

Responsibility:

- Transform values and mapping recipes into Wikibase claim/snak/reference payload structures.
- Build transport-ready content objects (`datavalue`, `snak`, `claim`) from validated inputs.

Out of scope:

- Remote API transport and authentication session management.
- Registry synchronization and semantic drift management.

Current anchor surface:

- `DataTypeTransformer`
- `SnakBuilder`
- `ClaimBuilder`
- `Distillate`

### Shipper (`gkc.shipper`)

Responsibility:

- Execute write operations against Wikibase-compatible APIs.
- Enforce write safety behavior (summary checks, dry-run paths, request shaping).
- Provide plan/preview behavior for create/update/no-op decisions.
- Support writes to any Wikibase instance (Wikidata, Data Distillery, etc.).

Out of scope:

- Generic read-model ownership (belongs to mash).
- Semantic modeling and profile ontology design ownership (belongs to wikibase + profile assets).

Current anchor surface:

- `WikibaseShipper` (works with any Wikibase instance)
- `CommonsShipper` (placeholder)
- `OpenStreetMapShipper` (placeholder)
- `DiffPlan`, `DiffOperation`, `WriteResult`

### Wikibase (`gkc.wikibase`)

Responsibility:

- Data Distillery semantic backbone orchestration.
- Foundation ontology audit/init orchestration using mash reads and shipper writes.
- Data Distillery-specific planning, conformance checks, and orchestration state/reporting.

Out of scope:

- Reimplementing generic read client logic.
- Reimplementing generic write transport logic.

Current anchor surface:

- `load_foundation_profiles`
- `audit_wikibase_foundation`
- `init_wikibase_foundation`

## Handoff Flows

### Flow 1: Foundation Audit and Init

1. `wikibase` loads foundation profile definitions.
2. `mash` retrieves current entity/property state from target Wikibase.
3. `wikibase` computes conformance and action plan.
4. `shipper` applies write operations when execution is enabled.
5. `wikibase` publishes structured audit/init reports.

### Flow 2: Ontology Dogfooding (Next-Wave Entity Types)

1. Profile definitions describe ontology entities to provision.
2. `wikibase` orchestration resolves desired vs existing state.
3. `mash` performs lookup/reconciliation reads.
4. `bottler` (and cooperage where appropriate) shape payload structures.
5. `shipper` performs dry-run/execute writes.

### Flow 2.5: Shared Profile-to-Write Planning Pipeline (Active)

1. `spirit_safe` loads and exports JSON Entity Profiles and value-list cache artifacts.
2. `still_charger` assembles curation packets from profile JSON and charges packet entities with source values.
3. `fermenter` validates and coerces charged values, emitting shared conformance notices.
4. `cooperage` transforms charged packet data into `WikibaseShipper.plan_batch` operations.
5. `wikibase` orchestration coordinates this flow for Data Distillery-specific workflows.
6. `shipper` computes create/update/no-op diff plans and executes writes when enabled.

### Flow 2.6: SpiritSafe JSON Profile Materialization (Active)

1. `wikibase` cache routes refresh and reconcile per-entity cache files.
2. `spirit_safe` builds JSON Entity Profiles from `cache/entities` artifacts.
3. `spirit_safe` exports per-profile JSON files (for example `profiles/Q4.json`).
4. Downstream packet/hydration stages consume exported profile artifacts.

### Flow 2.7: Value-List Query Hydration (Active)

1. `spirit_safe` discovers value-list entities from cache (`P1 -> Q7`).
2. `mash` reads value-list talk pages and extracts the first `<sparql>` block.
3. `spirit_safe` writes query files (`queries/QID.sparql`).
4. `sparql` executes paginated query hydration to `cache/queries/QID.json`.
5. Failed hydration does not overwrite an existing cache file for that value list.

### Flow 3: Semantic Projection for Runtime Artifacts

1. `mash` retrieves semantic entities and related metadata.
2. `cooperage` applies projection/transformation rules.
3. `bottler` shapes final claim/snak structures where transport payload format is required.
4. Artifacts are validated against SpiritSafe/runtime schema contracts.
5. `wikibase` tracks projection provenance and drift metadata.

### Flow 4: Sync and Drift Management

1. `mash` reads revision/update baselines.
2. `cooperage` computes deterministic artifact diffs.
3. `wikibase` applies sync policy and conflict strategy.
4. `shipper` executes writes when sync direction targets remote Wikibase.
5. Reports and manifest metadata are emitted for traceability.

## Non-Negotiable Contracts

- Do not add a new generic Wikibase client under `gkc.wikibase`.
- Do not bypass `shipper` for Wikibase write execution paths.
- Keep SpiritSafe runtime contracts stable and testable.
- Preserve offline-first behavior: network-backed enhancement must not break cache-only operation.
- Preserve JSON profile export determinism (stable ordering and artifact path shape).

## Decision Matrix for New Work

When adding new functionality, assign ownership using this matrix:

- Need to fetch/query source entity data? -> `mash`
- Need to build/export profile JSON artifacts from SpiritSafe cache entities? -> `spirit_safe`
- Need to assemble curation packets from profile JSON and populate them with source values? -> `still_charger`
- Need atomic validation/coercion and conformance notices? -> `fermenter`
- Need to build/shape values into claim/snak/payload structures? -> `bottler`
- Need schema/specification retrieval or reusable projection logic? -> `cooperage`
- Need to execute write operations to external APIs? -> `shipper`
- Need Data Distillery semantic orchestration, ontology conformance, or sync policy? -> `wikibase`

## Current Gaps to Revisit During Critical Analysis

- Still Charger URI-keyed packet assembly and source resolution are still in active migration from profile-name keyed behavior.
- Fermenter module implementation is pending; current validation/coercion logic remains distributed and not yet unified.
- Cooperage currently provides packet-to-Wikibase operation planning; additional target transformers still need explicit acceptance criteria per phase.
- Boundaries between cooperage and bottler for transformation stages still need explicit acceptance criteria per phase.
- Wikibase orchestration should continue preferring composition over new transport abstractions.
- Cross-module tests should identify failure source by layer (read, transform, payload-shape, write, orchestration).
- Curation packet v2 contract migration from profile-name keys to entity-URI keys remains unfinished and is the next high-risk integration step.

## Theoretical Design Notes

### Execute-Mode Safety Contract (Planned)

This section documents the intended cross-module safety contract for execute mode. It is not fully implemented yet.

Required sequence:

1. `wikibase` builds plan artifacts through the shared packet pipeline.
2. `shipper.plan_batch` produces create/update/no-op/blocked preview.
3. caller explicitly confirms execute intent.
4. `shipper` performs writes with summary/auth/bot context.
5. `wikibase` emits execution report with provenance and failure localization.

Non-negotiable execution guardrails:

- no implicit writes from planning commands
- explicit execute flag required for write calls
- authenticated mode required when policy or target instance requires it
- dry-run report shape should mirror execute report shape for parity
- failures should remain attributable to layer (charge, barrel, shipper, orchestration)

Open design questions:

- whether write execution should stop-on-first-failure or continue-and-report
- whether execute should consume only on-disk plan artifacts or in-memory plan results
- whether operation idempotency checks belong only in shipper or in both shipper and orchestration

## Handoff Summary Template (for Agent-to-Agent Continuity)

Use this concise structure when handing work from one module owner to another:

- Scope completed:
- Module touched:
- Public contracts used:
- Assumptions made:
- Open risks:
- Next owning module:
- Inputs required for next step:
