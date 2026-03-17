---
title: SpiritSafe Integration Architecture
description: URI-keyed artifact indexing, profile graph traversal, and packet scaffolding
---

# SpiritSafe Integration Architecture

This document describes the current architecture used by `gkc.spirit_safe` for integrating SpiritSafe artifacts.

## Current State

Implemented and committed:

- JSON Entity Profiles are loaded from `profiles/<QID>.json`.
- Value-list artifacts are loaded from `cache/queries/<QID>.json`.
- Artifact manifest indexing is built from local SpiritSafe artifacts into `cache/manifest.json`.
- Profile graph traversal is QID/URI-aware and built from `metadata.profile_graph` and manifest profile entries.
- Curation packet scaffolding is manifest-independent and profile-document-driven.

## Artifact Layers

### SpiritSafe Repository Artifacts

- `profiles/<QID>.json`
- `queries/<QID>.sparql`
- `cache/entities/<QID|PID>.json`
- `cache/queries/<QID>.json`
- `cache/manifest.json`

### gkc Runtime Layers

- `load_profile()` resolves QID/URI and loads JSON profile documents.
- `load_profile_package()` loads primary plus related profiles by traversing embedded `metadata.profile_graph` edges.
- `get_profile_graph()` loads manifest and builds a graph for registry tooling.
- `create_curation_packet()` builds packet scaffolds from profile documents directly.

## Identity Model

- Canonical identity is full entity URI.
- QIDs are normalized from URI tails when needed for file resolution and graph keys.
- Labels are display fields only and are never used as join keys.

## Manifest Model

`cache/manifest.json` is a URI-keyed artifact index.

Top-level fields:

- `generated_at`
- `source`
- `profiles`
- `entities`
- `queries`
- `value_lists`

`profiles` entries summarize each profile document metadata:

- `entity`, `qid`
- `labels`, `descriptions`
- `statement_count`
- `profile_graph`
- `value_list_graph` (includes value-list routes referenced by statements and nested qualifier/reference statements)

## Profile Graph Model

`ProfileGraph` now consumes manifest profile entries where edge targets and statements are URIs.

Normalization rules:

- `target_profile` is normalized to target QID.
- `via_statement` remains URI-form.
- `relationship_type` maps from `linkage_type`.
- `cardinality` and `traversal` default to empty dict when omitted.

## Packet Scaffolding Model

`create_curation_packet()` outputs:

- `packet_id`
- `operation_mode`
- `created_at`
- `primary_profile` and `primary_profile_entity`
- `entities`
- `cross_references`
- `cardinality_constraints`
- `profile_package`

Entity scaffolds carry:

- packet-local ID (`ent-001`)
- `profile` (QID)
- `profile_entity` (URI)
- empty `data`
- `profile_structure` copied from JSON profile content

## Testing Strategy

`tests/fixtures/spiritsafe/` now mirrors the artifact-index model with minimal fixtures:

- `profiles/Q4.json`, `profiles/Q39.json`
- `cache/entities/Q4.json`
- `cache/queries/Q28.json`
- `queries/Q28.sparql`
- `cache/manifest.json`

## Theoretical Design Notes

- Shared conformance notice envelopes across charging, barreling, and validation remain planned but are not yet a finalized runtime contract.
- Wizard-facing packet consumption can move toward stricter URI-first keys and richer value-list routing metadata once downstream integration milestones land.
