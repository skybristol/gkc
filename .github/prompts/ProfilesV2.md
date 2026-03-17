# ProfilesV2: Wikibase-First Entity Profile Architecture

Target agents: Profile Architect, Validation Agent, Wizard Engineer

Status: In progress. JSON Entity Profile export is now implemented in gkc.

## Purpose

This brief is the active implementation guide for ProfilesV2. It captures what is done, what is now canonical, and what remains.

## Completed

### Cache and extraction substrate

- Per-entity cache refresh routes are implemented.

- SPARQL-driven cache-builder routes are implemented.

- Incremental recentchanges refresh routes are implemented.

- SpiritSafe workflow support for full and incremental cache refresh is implemented.

### JSON Entity Profile generation in gkc

- `EntityProfileJsonBuilder` is implemented in `gkc.spirit_safe`.

- JSON profile generation from `cache/entities/*.json` is implemented.

- CLI route is implemented: `gkc profile export-json`.

- Per-profile JSON output is implemented with one file per profile QID (`<output>/<QID>.json`).

- Optional profile filtering is implemented via repeatable `--profile-id`.

- API helper routes are implemented and exported:

  - `build_entity_profile_json_documents(...)`

  - `export_entity_profile_json_documents(...)`

### Current generated profile shape

Current export generates:

- `entity`

- `identification`

- `statements`

- `metadata`

And currently supports:

- cache-linked statement expansion

- qualifier and reference statement expansion with terminal behavior on nested qualifier/reference statements

- value semantics with `value.profile`, `value.value_list_reference`, and optional `value.value_list`

- strict language-key collection from language-bearing sections

## Canonical Direction Right Now

### Identity

- Canonical machine identifier is `entity` URI.

- Labels are presentation only.

- Runtime identity, joins, and linkage resolution must not use labels.

### Runtime dependency model

- Build-time profile generation reads SpiritSafe cache entities.

- Runtime consumers should not require live DD Wikibase access for profile execution paths.

### Value-list behavior

- Value-list usage is cache-first.

- Runtime consumers use materialized artifacts, not live SPARQL execution.

## Remaining Work: Curation Packet Generation (Next Priority)

The next milestone is packet migration to JSON-first and entity-URI-first behavior.

### 1) Packet identity migration

Current packet code paths still rely on profile-name keys in multiple places.

Required:

- move packet-level profile identity to entity-URI-first usage

- keep temporary URI-to-filesystem derivation isolated and non-authoritative

Deliverable:

- packet schema and packet assembly routes using URI identity across cross-references and profile package content

### 2) Cross-reference assembly alignment

Required:

- use manifest graph edges for traversal and profile loading order

- use statement-level linkage content as canonical semantic source

- include explicit `via_statement` context on packet cross-references

Deliverable:

- deterministic packet cross-reference assembly contract and implementation

### 3) Cardinality consistency

Required:

- select a single unlimited encoding and apply it profile -> packet -> validation path

Deliverable:

- one consistent unlimited representation with tests

### 4) Fixed and default value charging semantics

Required:

- fixed values are additive and non-destructive

- defaults pre-populate only when field is empty

- extra values generate structured notices rather than silent mutation

Deliverable:

- shared conformance notice envelope consumed by Wizard, CLI, and bulk routes

### 5) Value-list routing in packet

Required packet route metadata per value-list entity:

- cache path

- item count

- inlineability metadata

Deliverable:

- packet-level `value_list_routes` populated at packet assembly time

### 6) Loader-path convergence

Current dict-vs-model split remains a fragility point.

Required:

- one canonical typed loading path for packet assembly and packet validation paths

Deliverable:

- packet routes and validators use shared typed contract

## Immediate Agent Sequence

### Profile Architect

- freeze packet-facing profile assumptions for URI identity, linkage metadata, and value-list routes

### Validation Agent

- implement packet generation and conformance validation changes against frozen contract

- produce stable notice envelope and validation surfaces

### Wizard Engineer

- integrate directly against frozen packet contract with no local policy forks

## Acceptance Criteria For Next Milestone

- packet generation is JSON-first and URI-identity-safe

- packet cross-references are deterministic and include `via_statement`

- packet contains value-list routes and consumers use them directly

- conformance notices are emitted consistently across interfaces

- tests cover packet generation, charging notices, and consumer integration

## Out Of Scope For Immediate Packet Milestone

- sitelink profile contract reintroduction

- interface-specific policy engines separate from shared validation and charging behavior

- live runtime SPARQL execution as a substitute for materialized value-list artifacts

## Practical Commands (Current)

Build and export JSON profiles from cache entities:

```bash
poetry run gkc --json profile export-json \
  --cache-entities-dir /Users/sky/code/SpiritSafe/cache/entities \
  --output /Users/sky/code/SpiritSafe/profiles
```

Filter export to selected profiles:

```bash
poetry run gkc --json profile export-json \
  --cache-entities-dir /Users/sky/code/SpiritSafe/cache/entities \
  --profile-id Q4 \
  --profile-id Q39 \
  --output /Users/sky/code/SpiritSafe/profiles
```
