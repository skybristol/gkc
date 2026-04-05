# Still Charger Architecture

## Purpose

`still_charger` is the runtime boundary between profile materialization and packet validation.

It is responsible for:

- Packet scaffold assembly from JSON Entity Profiles.
- Source charging orchestration for primary and linked entities.
- Packet mutation sequencing for metadata, data, and conformance sections.
- Preserving packet metadata integrity by resealing digest after metadata changes.

It is not responsible for validation semantics or notice interpretation. Those belong to `fermenter`.

## Inputs and Outputs

Inputs:

- Primary profile JSON document from `spirit_safe`.
- Related profile metadata from profile graph traversal.
- Source entities from `mash` (Wikidata/Wikibase JSON).
- Optional value-list cache context from SpiritSafe local source metadata.

Outputs:

- Curation packet scaffold (`metadata`, `data`, `conformance`).
- Charged packet with source payloads and conformance evaluation records.
- Charging report/notices surface for caller workflows.

## Ownership Boundary

Owns:

- Packet assembly API surface (`create_curation_packet`, `build_curation_packet_from_json_profile`).
- Charge orchestration API surface (`charge_packet_from_wikidata_items`, legacy `charge_curation_packet`).
- Linked-entity resolution routing from profile linkage metadata.
- Source provenance injection into packet metadata.
- Metadata digest resealing after provenance mutation.

Does not own:

- Datatype validation/coercion semantics.
- Conformance outcome policy definitions.
- Destination payload shaping and remote write transport.
- Wizard-specific view state or adapter structures.

## Packet Lifecycle

### Stage 1. Scaffold Assembly

- Normalize primary profile identity (URI and profile name identifier).
- Load linked profile documents from profile graph metadata.
- Build packet metadata section:
  - `primary_profile`
  - `profiles`
  - `graph`
  - `mint`
  - `source`
  - `integrity`
- Build packet data scaffold entities from profile statements.

### Stage 2. Source Charging

- Resolve primary source QID from caller-provided mapping.
- Resolve linked entities referenced by linkage routes.
- Load source entity JSON from `mash`.
- Inject source provenance in `metadata.profiles[*]`:
  - `source_qid`
  - `lastrevid`
  - `pulled_at`
- Populate packet data entities with source payloads.

### Stage 3. Conformance Assembly

- Evaluate claim instances via fermenter statement primitives.
- Serialize statement evaluation records into packet conformance section.
- Preserve ownership separation: orchestration in `still_charger`, semantics in `fermenter`.

### Stage 4. Integrity Reseal

- Reseal metadata digest after charge-time metadata mutation.
- Ensure packet re-presentation can verify metadata/actionability together.

## Dependency Contracts

### With SpiritSafe

Consumes:

- JSON profile artifacts.
- Profile graph and linkage metadata.
- Source mode/local root metadata for cache context.

Contract note:

- Packet assembly is profile-document driven and does not require manifest-based orchestration.

### With Mash

Consumes:

- Raw entity retrieval for primary and linked QIDs.

Contract note:

- `still_charger` owns retrieval order and mapping to packet entities.
- `mash` owns API retrieval mechanics and response normalization.

### With Fermenter

Consumes:

- Atomic statement evaluation and packet-facing record serialization.

Contract note:

- `still_charger` should not patch or reinterpret fermenter output semantics.
- If additional fields are required in packet conformance records, they should be emitted by fermenter serialization contract.

### With Wizard

Provides:

- Packet surfaces consumed by wizard adapters.

Contract note:

- Wizard runtime structures are downstream and must not redefine packet contract shape.

## Current State vs Target Direction

Current state:

- Charged packet data surface is still transitional and hybrid in current runtime implementation (scaffold slots plus embedded raw entity payload).
- Conformance remains packet-level and is generated during charging.

Target direction under #200:

- Lock strict packet contract with clear section boundaries.
- Keep source payload in packet data without duplicated evaluation semantics.
- Keep all evaluation status/outcome semantics in packet conformance.
- Keep packet metadata as canonical machine contract with integrity and provenance.

## Known Prerequisites and Gaps

- Eliminate residual coupling where still_charger patches fields onto fermenter records.
- Finalize conformance record shape migration to grouped entity evaluations and current outcome contract.
- Align tests and fixtures to fail on reintroduction of hybrid packet semantics once contract lock is complete.

## Related Docs

- [Curation Packet Contract](../gkc/entity-json-schema.md)
- [Cross-Module Contracts](module-contracts.md)
- [Validation Architecture](validation-architecture.md)
- [SpiritSafe Registry](SpiritSafe/index.md)
