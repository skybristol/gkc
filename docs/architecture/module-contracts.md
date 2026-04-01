# Cross-Module Contracts and Handoffs 

## Purpose

This document defines the current architectural contract between `mash`, `spirit_safe`, `still_charger`, `fermenter`, `wizard`, `bottler`, `shipper`, and `wikibase` for Data Distillery and broader GKC workflows.

It is written as a practical anti-reinvention guide for contributors and custom agents.

Infrastructure perspective for these module boundaries:

- Data Distillery Wikibase defines semantic foundation (profiles, statements, value-list semantics).
- SpiritSafe materializes those semantics as deterministic artifacts.
- `gkc` modules execute packet assembly, validation/coercion, planning, and shipping from those artifacts.

Contract clarification (active direction):

- JSON Entity Profiles materialized from DD Wikibase semantics are the only active profile runtime contract.
- YAML-era profile loading/validation/generation is superseded and retained only as temporary legacy surface pending removal.
- Runtime validation/coercion ownership is centralized in `fermenter`.
- Wizard runtime ownership is centralized in `wizard`.
- No compatibility aliasing should be introduced between `gkc.profiles.forms.*` and `gkc.wizard.*`.

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
- Publish artifact metadata needed to compare long-lived curation packets against the SpiritSafe state from which they were minted.

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

- `create_curation_packet`
- `build_curation_packet_from_json_profile`
- `charge_packet_from_wikidata_items` (active Wikidata charging path)
- `ChargeReport`
- `ChargeIssue`

Legacy surface (preserved for existing integrations; new workflows should use `charge_packet_from_wikidata_items`):

- `charge_curation_packet`

### Fermenter (`gkc.fermenter`)

Responsibility:

- Validate and coerce inbound values using profile-defined directives.
- Provide atomic datatype validators and coercion primitives.
- Enforce fixed values, value-list constraints, and full statement-shape constraints (value + qualifiers + references).
- Enforce derived-value constraints (for example, reference/qualifier values sourced from parent statement values).
- Validate packet-level compatibility and lifecycle conformance for long-lived curation packets.
- Emit shared `ConformanceNotice` records with actionable feedback.
- Serialize packet-facing statement conformance records from atomic statement evaluations.

Out of scope:

- Packet assembly and packet orchestration.
- Destination-specific payload shaping and transport execution.

Current anchor surface:

- `ConformanceNotice`
- `ConformanceOutcome` (string enum: `CONFORMANT`, `NON_CONFORMANT_MAPPABLE`, `UNCOVERED`, `MISSING_REQUIRED`)
- `StatementEvaluation`
- `EntityEvaluation`
- `ValidationResult`
- `validate_*` datatype validators
- `coerce_*` datatype coercers
- `normalize_claim_value`
- `evaluate_statement_claim`
- `evaluate_statement_instance`
- `evaluate_entity`
- `statement_evaluation_to_record`
- `conformance_notice_payloads`
- `check_packet_integrity`
- `validate_packet_inline`
- `validate_packet_from_file`

### Wizard (`gkc.wizard`)

Responsibility:

- Own interactive wizard runtime and UI orchestration.
- Render profile-driven curation flows from packet/profile artifacts.
- Consume `still_charger` packet assembly/charging outputs and `fermenter` conformance outputs.
- Manage wizard-only state and UX helpers (for example draft persistence and packet-to-view adapters).

Out of scope:

- Runtime validation/coercion rule ownership.
- Packet scaffold assembly ownership.
- SpiritSafe artifact translation/materialization ownership.

Current anchor surface:

- Top-level CLI entry `gkc wizard` (public contract).
- Streamlit app runtime and wizard step orchestration modules.

Implementation note:

- Wizard runtime is implemented under `gkc.wizard`.

### Bottler (`gkc.bottler`)

Responsibility:

- Provide canonical Wikibase JSON construction primitives for all claim/statement building.
- Transform values and mapping recipes into Wikibase payload structures (datavalues, snaks, claims).
- Build deterministic, multilingual label/description/alias blocks from profile metadata.
- Build Wikibase entity shells from profile metadata for profile-only packet generation.
- All consuming code must use bottler primitives rather than building JSON inline.

Out of scope:

- Remote API transport and authentication session management.
- Registry synchronization and semantic drift management.
- Validation and coercion logic (handled by fermenter).

Current anchor surface:

- `DataTypeTransformer` (static methods for datatype conversion)
- `SnakBuilder` (atomic snak construction with datatypes)
- `ClaimBuilder` (complete statement building with qualifiers/references)
- `LanguageBuilder` (multilingual label/description/alias block building)
- `EntityShellBuilder` (Wikibase entity shell building from profile metadata)
- `normalize_claim_datavalue` (value-to-datatype mapping utility)
- `build_claim_from_property_and_value` (convenience statement builder)
- `Distillate` (end-to-end mapping configuration container)

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

- `barrel_curation_packet_to_wikibase_plan`
- `BarrelPlanReport`
- `BarrelIssue`
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
4. `bottler` and `wikibase` orchestration shape payload structures.
5. `shipper` performs dry-run/execute writes.

### Flow 2.5: Shared Profile-to-Write Planning Pipeline (Active)

1. `spirit_safe` loads and exports JSON Entity Profiles and value-list cache artifacts.
2. `still_charger` assembles curation packets from profile JSON using bottler's EntityShellBuilder to build canonical Wikibase JSON entity shells for profile-only packets.
3. `fermenter` evaluates atomic statement instances (including qualifiers/references), coerces values, and serializes packet-facing conformance records.
4. `wikibase` orchestration transforms charged packet data into `WikibaseShipper.plan_batch` operations using bottler primitives for claim/statement construction.
5. `wikibase` orchestration coordinates this flow for Data Distillery-specific workflows.
6. `shipper` computes create/update/no-op diff plans and executes writes when enabled.

### Flow 2.5a: Profile-Only Packet Wikibase JSON Shell Generation (New)

1. `still_charger` calls bottler's `EntityShellBuilder` during `build_curation_packet_from_json_profile`.
2. For each profile in the packet, bottler extracts identification metadata (labels/descriptions/aliases) and statement property IDs.
3. Bottler builds canonical Wikibase entity shells with:
   - Language-keyed labels, descriptions, aliases blocks
   - Empty claims dictionary with deterministically sorted property IDs
4. Shells are embedded in `data.entities[*].entity` for deterministic, shape-consistent packet generation.
5. Profile-only packets require no charging and can proceed directly to fermenter validation.
6. Charged packets (with Wikidata values) merge this shell with charged statement instances.

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

### Flow 2.8: Packet Re-entry and Forward Migration (Planned)

1. `still_charger` or another caller loads a previously minted curation packet.
2. `fermenter` validates packet type/shape first; structural/type failures are hard blockers.
3. `spirit_safe` provides current profile/value-list artifact metadata for compatibility comparison.
4. `wikibase` may provide current semantic revision context when network-backed comparison is available.
5. `fermenter` classifies drift (`patch_compatible`, `minor_compatible`, `migration_required`, `breaking`) and applies approved migration transforms when available.
6. `fermenter` re-validates the packet after migration and emits compatibility notices plus migration report data.
7. Downstream write-planning and shipping proceed only if the packet remains structurally valid and any required migration succeeded.

### Flow 3: Semantic Projection for Runtime Artifacts

1. `mash` retrieves semantic entities and related metadata.
2. `wikibase` orchestration applies current write-planning transformations.
3. `bottler` shapes final claim/snak structures where transport payload format is required.
4. Artifacts are validated against SpiritSafe/runtime schema contracts.
5. `wikibase` tracks projection provenance and drift metadata.

### Flow 4: Sync and Drift Management

1. `mash` reads revision/update baselines.
2. `shipper.plan_batch` computes deterministic write-operation diffs.
3. `wikibase` applies sync policy and conflict strategy.
4. `shipper` executes writes when sync direction targets remote Wikibase.
5. Reports and manifest metadata are emitted for traceability.

## Non-Negotiable Contracts

- Do not add a new generic Wikibase client under `gkc.wikibase`.
- Do not bypass `shipper` for Wikibase write execution paths.
- Keep SpiritSafe runtime contracts stable and testable.
- Preserve offline-first behavior: network-backed enhancement must not break cache-only operation.
- Preserve JSON profile export determinism (stable ordering and artifact path shape).
- Treat packet type/shape conformance as the primary hard blocker; other conformance failures should default to actionable notices unless policy explicitly escalates them.
- Do not add bridge/shim module aliases that preserve `gkc.profiles.forms.*` as a shadow wizard API.
- Do not add new runtime validation/coercion logic under `gkc.profiles.*`.

## Decision Matrix for New Work

When adding new functionality, assign ownership using this matrix:

- Need to fetch/query source entity data? -> `mash`
- Need to build/export profile JSON artifacts from SpiritSafe cache entities? -> `spirit_safe`
- Need to assemble curation packets from profile JSON and populate them with source values? -> `still_charger`
- Need atomic validation/coercion and conformance notices? -> `fermenter`
- Need to build/shape values into claim/snak/payload structures? -> `bottler`
- Need schema/specification retrieval? -> `mash`
- Need reusable charged-packet to Wikibase operation planning? -> `wikibase`
- Need to execute write operations to external APIs? -> `shipper`
- Need Data Distillery semantic orchestration, ontology conformance, or sync policy? -> `wikibase`

## Current Gaps to Revisit During Critical Analysis

- Still Charger does not yet emit per-entity source provenance (`source_qid`, `lastrevid`, `pulled_at`) in the packet.
- Boundaries between wikibase write planning and bottler transformation stages still need explicit acceptance criteria per phase.
- Cross-module tests should identify failure source by layer (read, transform, payload-shape, write, orchestration).
- Packet compatibility metadata, change classification, and forward-migration rules for long-lived offline packets remain to be implemented.

Additional active boundary cleanup:

- The old YAML-era `gkc.profiles` runtime path (`loaders`, `generators`, `validation`, and related CLI surfaces) is superseded and should be removed unless a concrete retained consumer is explicitly approved.
- `GKCEntityProfile` should be integrated with fermenter-owned validation/coercion pathways (including Pydantic-backed validation surfaces where applicable).
- Core architecture classes should remain explicit and aligned with top-level components: `GKCEntityProfile`, `GKCEntityStatement`, `GKCValueList`, and `GKCCurationPacket`.

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
