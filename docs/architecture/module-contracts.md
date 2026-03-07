# Cross-Module Contracts and Handoffs

## Purpose

This document defines the current architectural contract between `mash`, `cooperage`, `bottler`, `shipper`, and `wikibase` for Data Distillery and broader GKC workflows.

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

### Cooperage (`gkc.cooperage`)

Responsibility:

- Manage schema/specification and reference retrieval utilities.
- Evolve toward canonical transformation/projection contracts that shape semantic data for runtime packaging.
- Provide reusable cross-target transformation primitives that are not write transport concerns.

Out of scope:

- Direct submission to Wikibase/other write APIs.
- Owning profile registry source-of-truth decisions.

Current anchor surface:

- `fetch_entity_rdf`
- `fetch_schema_specification`
- `fetch_entity_schema_json`
- `fetch_entity_schema_metadata`

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

Out of scope:

- Generic read-model ownership (belongs to mash).
- Semantic modeling and profile ontology design ownership (belongs to wikibase + profile assets).

Current anchor surface:

- `WikibaseShipper`
- `WikidataShipper`
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
- Keep profile YAML/SpiritSafe runtime contracts stable and testable.
- Preserve offline-first behavior: network-backed enhancement must not break cache-only operation.

## Decision Matrix for New Work

When adding new functionality, assign ownership using this matrix:

- Need to fetch/query source entity data? -> `mash`
- Need to build/shape values into claim/snak/payload structures? -> `bottler`
- Need schema/specification retrieval or reusable projection logic? -> `cooperage`
- Need to execute write operations to external APIs? -> `shipper`
- Need Data Distillery semantic orchestration, ontology conformance, or sync policy? -> `wikibase`

## Current Gaps to Revisit During Critical Analysis

- Cooperage currently has limited projection/package implementation depth relative to planned role.
- Boundaries between cooperage and bottler for transformation stages need explicit acceptance criteria per phase.
- Wikibase orchestration should continue preferring composition over new transport abstractions.
- Cross-module tests should identify failure source by layer (read, transform, payload-shape, write, orchestration).

## Handoff Summary Template (for Agent-to-Agent Continuity)

Use this concise structure when handing work from one module owner to another:

- Scope completed:
- Module touched:
- Public contracts used:
- Assumptions made:
- Open risks:
- Next owning module:
- Inputs required for next step:
