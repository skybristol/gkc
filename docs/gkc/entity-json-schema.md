# GKC Entity JSON and Curation Packet Contract

**Purpose:** Define the current JSON contracts used across the Data Distillery flow:

1. Data Distillery Wikibase semantics materialized into SpiritSafe JSON Entity Profiles.
2. JSON Entity Profiles assembled into curation packet scaffolds.
3. Curation packets charged with data, validated/coerced, and prepared for shipping.

This document replaces older profile-name and YAML-era schema language where it no longer matches runtime behavior.

## Current Contract Scope

This page documents the active packet/profile contract used by:

- `gkc.spirit_safe` for loading JSON Entity Profiles.
- `gkc.still_charger` for packet scaffold assembly and charging.
- `gkc.fermenter` and wizard validation bridge for value conformance.
- `gkc.wikibase` and `gkc.shipper` for downstream write planning and execution.

## Pipeline Overview

The current pipeline is:

1. Data Distillery Wikibase semantics are captured in SpiritSafe cache artifacts.
2. `gkc.spirit_safe` exports JSON Entity Profiles under `profiles/<QID>.json`.
3. `gkc.still_charger.build_curation_packet_from_json_profile(...)` builds a packet scaffold.
4. `gkc.still_charger.charge_curation_packet(...)` and related flows fill packet entity data.
5. Validation/coercion runs on packet values and emits conformance notices.
6. Bottling transforms packet content to destination-specific payloads.
7. Shipping sends destination-specific payloads to Commons Partners (Wikidata, etc.).

## Canonical Identity Rules

- Canonical profile and statement identity is URI-first.
- QIDs are convenience forms derived from URI tails.
- Labels are display content and are not join keys.
- Cross-entity references inside packets use packet-local entity IDs until shipping resolves external IDs.

## JSON Entity Profile Contract

A JSON Entity Profile document (for example `profiles/Q4.json`) includes:

- `entity`: profile URI.
- `identification`: label/description/alias prompts and guidance by language.
- `statements`: statement specifications used to scaffold packet entities.
- `metadata`: profile graph, value-list graph, export metadata, and descriptive fields.

### Statement Specification Shape

Each entry in `statements[]` typically includes:

| Field | Type | Meaning |
|---|---|---|
| `entity` | string | Statement URI |
| `label` | string | Human-readable statement label |
| `io_map` | array | Mapping to destination properties (for example Wikidata PID URI) |
| `value` | object | Value contract including datatype and optional value-list/profile linkage |
| `messages` | object | Prompt/guidance/error messaging payload |
| `max_count` | number | Upper-bound cardinality target |
| `qualifiers` | array | Nested statement specs for qualifiers |
| `references` | array | Nested statement specs for references |

Within `value`, profiles may include derived-default hints for nested statements:

- `value_source: statement_value`
- `value_source_statement: <parent statement URI>`

These are consumed by downstream wizard/validation paths and are not UI-only fields.

## Curation Packet Scaffold Contract

The active scaffold contract produced by `build_curation_packet_from_json_profile(...)` is:

```json
{
  "packet_id": "pkt-<uuid>",
  "operation_mode": "new",
  "metadata": {
    "primary_profile": {
      "name_identifier": "Q4",
      "id": "https://datadistillery.wikibase.cloud/entity/Q4"
    },
    "profiles": [],
    "graph": {
      "nodes": [],
      "edges": []
    }
  },
  "data": {
    "entities": []
  }
}
```

### Packet Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `packet_id` | string | Yes | Packet-local identifier |
| `operation_mode` | string | Yes | Current mode (`new` in scaffold builder) |
| `metadata.primary_profile.id` | string | Yes | Primary profile URI used to mint packet |
| `metadata.profiles` | array | Yes | Profile metadata and statement definitions in packet scope |
| `metadata.graph.edges` | array | Yes | URI-aware profile graph edges |
| `data.entities` | array | Yes | Entity slots in this packet |
| `minted_from` | object | No (recommended) | Provenance and compatibility metadata |
| `compatibility_status` | string | No | Re-entry compatibility outcome |
| `migration_report` | object | No | Migration actions and warnings |

### Entity Slot Scaffold Shape

Each entry in `data.entities[]` includes:

```json
{
  "profile": "Q4",
  "id": "https://datadistillery.wikibase.cloud/entity/Q4",
  "labels": {"mul": {"data-value": ""}},
  "descriptions": {"mul": {"data-value": ""}},
  "aliases": {"mul": {"data-value": ""}},
  "statements": {
    "Q16": {
      "id": "https://datadistillery.wikibase.cloud/entity/Q16",
      "data-type": "item",
      "data-value": ""
    }
  }
}
```

| Field | Type | Required | Meaning |
|---|---|---|---|
| `profile` | string | Yes | Profile name identifier for this entity slot |
| `id` | string | Yes | Entity URI for this slot |
| `labels/descriptions/aliases` | object | Yes | Identification field slots |
| `statements` | object | Yes | Statement slot map keyed by statement identifier |

## Charged Entity Data Contract

After charging, `entity.data` is populated with normalized content.

Common fields:

- `labels`
- `descriptions`
- `aliases`
- `statements`

`data.statements` is keyed by statement URI, not by display label.

Example:

```json
{
  "data": {
    "labels": {
      "en": "Cherokee Nation"
    },
    "descriptions": {},
    "aliases": {},
    "statements": {
      "https://datadistillery.wikibase.cloud/entity/Q16": [
        {
          "value": {"id": "Q7840353"},
          "qualifiers": {},
          "references": []
        }
      ]
    }
  }
}
```

### Nested Qualifier and Reference Shape

Nested qualifiers and references may appear in statement-shaped map form keyed by nested statement URI.

Typical nested shape:

- `qualifiers`: object keyed by statement URI with list values.
- `references`: object keyed by statement URI with list values, or an empty list where no references are provided.

Validation/coercion layers should normalize accepted nested forms and report shape violations as conformance notices.

## Conformance and Blocking Policy

Conformance is target-state oriented, not strict all-fields-must-be-present enforcement.

Current policy direction:

- Type/shape conformance failures are hard blockers.
- Missing expected statements, qualifiers, or references are usually notice-driven unless policy explicitly escalates.
- `max_count` is an upper-bound target; effective lower bound is zero unless explicit minimum policy is introduced.
- Derived-value and fixed/list constraints are enforced according to profile directives and resolver context.

## Packet Re-entry, Compatibility, and Migration

Long-lived packets may return after SpiritSafe/Wikibase state has changed.

To support deterministic handling, packets should carry `minted_from` metadata.

### Recommended `minted_from` Fields

| Field | Type | Meaning |
|---|---|---|
| `packet_contract_version` | string | Version of packet compatibility contract |
| `spiritsafe_commit` | string | SpiritSafe git commit used at mint time |
| `dd_revision` | string | Data Distillery revision watermark or snapshot ID |
| `profiles` | array | Per-profile records used to mint packet |
| `value_lists` | array | Value-list snapshot records used to mint packet |
| `minted_at` | string | Mint timestamp (ISO 8601) |

Per-profile metadata should include profile URI/QID and profile/statement digests.

Per-value-list metadata should include value-list ID plus cache digest and refresh timestamp.

### Compatibility Status Values

Suggested runtime values:

- `compatible`
- `migration_available`
- `manual_review_required`
- `incompatible`

### Change Classification

Suggested drift classes:

- `patch_compatible`
- `minor_compatible`
- `migration_required`
- `breaking`

### Re-entry Sequence

1. Validate packet type and shape.
2. Compare `minted_from` metadata to current SpiritSafe and DD state.
3. Classify drift.
4. Apply approved forward migrations when available.
5. Re-run conformance validation/coercion.
6. Emit compatibility and migration reporting.
7. Proceed to shipping only when packet is structurally valid and required migrations succeeded.

## Transition Notes

Some legacy packet/documentation surfaces still reference older fields such as `profile_name`, profile-name keyed statement maps, or YAML-first assumptions.

Current architecture direction is URI-first JSON profile and packet contracts, with compatibility shims preserved only where required during migration.

## Related Documentation

- [Data Distillery Wikibase Architecture](../architecture/DataDistillery-Wikibase.md)
- [Cross-Module Contracts](../architecture/module-contracts.md)
- [SpiritSafe Integration Architecture](../architecture/spirit_safe_models.md)
- [Profiles and Graph Linkage](./profiles.md)
- [Wizard Workflows](./wizard.md)
