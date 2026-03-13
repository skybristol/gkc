# Cross-Module Contracts and Handoffs 

## Purpose

This document defines the current architectural contract between `mash`, `still_charger`, `cooperage`, `bottler`, `shipper`, and `wikibase` for Data Distillery and broader GKC workflows.

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

### Still Charger (`gkc.still_charger`)

Responsibility:

- Fill curation packet entity scaffolds with concrete source values.
- Support bootstrap-friendly charging behavior when specifications are still emerging.
- Emit a structured charge report (charged/skipped entities and warnings/errors).

Out of scope:

- Target payload shaping for any specific destination API.
- API transport execution.

Current anchor surface:

- `charge_curation_packet`
- `ChargeReport`
- `ChargeIssue`

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

1. `spirit_safe` creates curation packet scaffolds from profile definitions.
2. `still_charger` fills packet entities with real input values.
3. `cooperage` transforms charged packet data into `WikibaseShipper.plan_batch` operations.
4. `wikibase` orchestration coordinates this flow for Data Distillery-specific workflows.
5. `shipper` computes create/update/no-op diff plans and executes writes when enabled.

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
- Need to populate curation packet scaffolds with concrete values? -> `still_charger`
- Need to build/shape values into claim/snak/payload structures? -> `bottler`
- Need schema/specification retrieval or reusable projection logic? -> `cooperage`
- Need to execute write operations to external APIs? -> `shipper`
- Need Data Distillery semantic orchestration, ontology conformance, or sync policy? -> `wikibase`

## Current Gaps to Revisit During Critical Analysis

- Still Charger currently supports specificationless charging for bootstrap workflows; strict charging contracts need additional profile-spec alignment.
- Cooperage currently provides packet-to-Wikibase operation planning; additional target transformers still need explicit acceptance criteria per phase.
- Boundaries between cooperage and bottler for transformation stages still need explicit acceptance criteria per phase.
- Wikibase orchestration should continue preferring composition over new transport abstractions.
- Cross-module tests should identify failure source by layer (read, transform, payload-shape, write, orchestration).

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
