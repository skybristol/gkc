---
title: SpiritSafe Integration Architecture
description: Profile graph traversal and packet scaffolding
---

# SpiritSafe Integration Architecture

This document describes the current architecture used by `gkc.spirit_safe` for integrating SpiritSafe artifacts.

## Current State

Implemented and committed:

- JSON Entity Profiles are loaded from `still/profiles/<QID>.json`.
- Value-list artifacts are loaded from `still/value_lists/cache/<QID>.json`.
- Profile graph traversal is QID/URI-aware and built from embedded `metadata.profile_graph` entries.
- Curation packet scaffolding is profile-document-driven.

## Artifact Layers

### SpiritSafe Repository Artifacts

- `still/profiles/<QID>.json`
- `still/value_lists/queries/<QID>.sparql`
- `still/entities/<QID|PID>.json`
- `still/value_lists/cache/<QID>.json`

### gkc Runtime Layers

- `load_profile()` resolves QID/URI and loads JSON profile documents.
- `load_profile_package()` loads primary plus related profiles by traversing embedded `metadata.profile_graph` edges.
- `still_charger.create_curation_packet()` builds packet scaffolds from profile documents loaded via SpiritSafe.

## Identity Model

SpiritSafe artifacts and curation packets use a dual-key identity model:

- `name_identifier` — primary human-facing key, derived from the DD Wikibase `name_identifier` property (P214). Used as statement slot keys in packet data, graph node identifiers, and profile reference labels.
- Full entity URI — immutable canonical identity for joining, provenance, and round-trip mapping to the Wikibase instance. Stored in the `id` field throughout.

QIDs are normalized from URI tails only where file path resolution requires them. Labels are display-only and are never used as join keys.

## Registry Metadata Model

Registry discovery reads metadata directly from each JSON profile document.

Relevant metadata fields include:

- `entity`
- `metadata.labels`
- `metadata.descriptions`
- `metadata.statement_count`
- `metadata.profile_graph`
- `metadata.value_list_graph`

## Profile Graph Model

`ProfileGraph` consumes embedded profile metadata where edge targets and statements are URIs.

Normalization rules:

- `target_profile` is normalized to target QID.
- `via_statement` remains URI-form.
- `relationship_type` maps from `linkage_type`.
- `cardinality` and `traversal` default to empty dict when omitted.

## Packet Scaffolding Model

`still_charger.create_curation_packet()` and `still_charger.build_curation_packet_from_json_profile()` produce a two-section packet:

- `metadata` — the complete profile ruleset, unified graph, mint provenance, and SHA-256 integrity digest.
- `data` — fillable entity slots.

Top-level packet fields:

- `packet_id` — UUID-based identifier
- `operation_mode` — `new`, `single`, or `bulk`
- `metadata.primary_profile` — `name_identifier` and `id` (URI) for the primary profile
- `metadata.profiles` — array of full profile definitions (statements, identification, metadata) for all profiles in packet scope
- `metadata.graph` — unified graph with `nodes` keyed by `name_identifier` and `edges` encoding both profile-to-profile and profile-to-value-list relationships
- `metadata.mint` — `minted_at`, `generator`, `gkc_version`
- `metadata.integrity` — SHA-256 digest of canonical metadata JSON; used as fermenter go/no-go gate on re-entry
- `data.entities` — array of entity slots

Entity slots in `data.entities` carry:

- `profile` — profile `name_identifier`
- `id` — profile URI (canonical entity identity for this slot)
- Language-keyed `labels`, `descriptions`, `aliases` slots — each value is `{"data-value": ""}`; no inner language tag
- `statements` — object keyed by statement `name_identifier`, each slot including `id` (statement URI), `data-type`, `data-value`, and optionally `value-list`, `qualifiers`, and `references`

Qualifiers and references are omitted when the profile does not specify them. When used as a reference or qualifier, a statement does not carry its own nested references or qualifiers.

Derived-value hints from SpiritSafe JSON (P213 semantics) appear within statement `value` objects:

- `value_source: statement_value`
- `value_source_statement: <parent statement URI>`

These are derived from DD Wikibase statement-level semantics and are intended for downstream wizard/validation consumers.

## Testing Strategy

`tests/fixtures/spiritsafe/` now mirrors the current SpiritSafe layout with minimal fixtures:

- `still/profiles/Q4.json`, `still/profiles/Q39.json`
- `still/entities/Q4.json`
- `still/value_lists/cache/Q28.json`
- `still/value_lists/queries/Q28.sparql`

## Theoretical Design Notes

**Packet migration tooling** — When a long-lived packet returns after SpiritSafe state has changed, a forward migration utility will classify drift and apply approved transforms before re-validation. The `metadata.mint` fields provide the provenance anchor. Change classification categories (`patch_compatible`, `minor_compatible`, `migration_required`, `breaking`) and a migration report are the planned output. Not yet implemented.

**Fermenter-driven charged packet integration** — The `charge_packet_from_wikidata_items` path in `still_charger` does not yet use the fermenter evaluator (`evaluate_entity`) to partition charged statements into conformant/non_conformant/uncovered/missing_required buckets. This is the next implementation step; the fermenter evaluator API is ready. See [Cross-Module Contracts](../module-contracts.md) for current gap notes.
