# GKC Entity JSON and Curation Packet Contract

**Purpose:** Define the current JSON contracts used across the Data Distillery flow:

1. Data Distillery Wikibase semantics materialized into SpiritSafe JSON Entity Profiles.
2. JSON Entity Profiles assembled into curation packet scaffolds.
3. Curation packets charged with data, validated/coerced, and prepared for editing and eventual shipping.

## Current Contract Scope

This page documents the active packet/profile contract used by:

- `gkc.spirit_safe` for loading JSON Entity Profiles.
- `gkc.still_charger` for packet scaffold assembly and charging.
- `gkc.fermenter` for value validation/coercion and conformance notices.
- `gkc.shipper` for downstream write planning and execution.

Contract clarification:

- Wizard runtime consumes fermenter conformance outputs; it does not own validation semantics.
- Any transitional wizard-side validation helpers are implementation details pending full fermenter consolidation and are not part of the long-term module contract.

## Pipeline Overview

The current pipeline is:

1. Data Distillery Wikibase semantics are developed and documented within the working "meta-wikibase".
2. `gkc.spirit_safe` caches and updates raw Data Distillery Wikibase entity content periodically (currently a manual process while development progresses) within `SpiritSafe/cache/entities`. (reference `SpiritSafe/.github/workflows/cache-from-wikibase.yml` and `SpiritSafe/.github/workflows/cache-wikibase-and-build-profiles.yml`)
3. `gkc.spirit_safe` generates JSON Entity Profiles under `SpiritSafe/profiles/<QID>.json`. (reference `SpiritSafe/.github/workflows/cache-wikibase-and-build-profiles.yml`)
4. `gkc.still_charger.build_curation_packet_from_json_profile(...)` generates a Curation Packet scaffold and seeds default/fixed values from profile definitions.
5. `gkc.still_charger.charge_packet_from_wikidata_items(...)` retrieves data from one or more Wikidata items, builds the `data` structure within the packet with those items verbatim, and runs `fermenter` processing to evaluate the items and produce a `conformance` object with reporting details on alignment with the profiles.
6. Bottling transforms packet content to destination-specific payloads.
7. Shipping sends destination-specific payloads to Commons Partners (Wikidata, etc.).

`charge_curation_packet(...)` remains available as a legacy helper for existing integrations, but new workflows should use `charge_packet_from_wikidata_items(...)`.

## Identity Model

Curation packets use a dual-key identity model:

- `name_identifier` is the primary human-facing key for all interaction surfaces — statement slots in packet data, graph node identifiers, and the profile reference label on each entity slot.
- `id` (full entity URI) is the immutable canonical identity used for joining, provenance, and round-trip mapping to the Wikibase instance.

Neither key is optional. QIDs are convenience forms derived from URI tails and are used only where file paths require them. Labels are display content and are never used as join keys.

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

## Curation Packet Structure

All curation packets enforce a strict three-section top-level structure:

- `metadata` — the ruleset, provenance, and integrity information for this packet. This section is sealed with a SHA-256 digest at mint time and must not be modified after generation.
- `data` — the source data payload: entity values (labels, descriptions, aliases, statements) indexed by entity slot.
- `conformance` — fermenter-owned evaluation results: statement-by-statement assessment of alignment with profile rules, mapping of entities to profiles, and any notices/issues encountered during validation.

Implementation note:

- The three-section shape above is the locked contract target for #200. Runtime mutation details in current charging paths remain transitional while contract-correction refactors are completed.

### Top-Level Packet Shape

```json
{
  "packet_id": "pkt-<uuid>",
  "operation_mode": "new",
  "metadata": {
    "primary_profile": {
      "name_identifier": "tribal_government_us",
      "id": "https://datadistillery.wikibase.cloud/entity/Q4"
    },
    "profiles": [
      {
        "id": "https://datadistillery.wikibase.cloud/entity/Q4",
        "name_identifier": "tribal_government_us",
        "identification": {},
        "statements": [],
        "metadata": {}
      }
    ],
    "graph": {
      "nodes": {
        "tribal_government_us": {
          "kind": "profile",
          "name_identifier": "tribal_government_us",
          "id": "https://datadistillery.wikibase.cloud/entity/Q4",
          "label": "Tribal Government in the United States"
        }
      },
      "edges": []
    },
    "mint": {
      "minted_at": "2026-03-26T00:00:00Z",
      "generator": "gkc.still_charger.build_curation_packet_from_json_profile",
      "gkc_version": "0.x.y"
    },
    "integrity": {
      "metadata_canonicalization": "json-sort-keys-v1",
      "metadata_digest_algorithm": "sha256",
      "metadata_digest": "<sha256 hex digest of canonical metadata JSON>"
    }
  },
  "data": {
    "entities": []
  },
  "conformance": [
    {
      "source_item": "http://www.wikidata.org/entity/Q14708404",
      "source_item_label": "Cherokee Nation",
      "statement_evaluations": []
    }
  ]
}
```

### Packet Metadata Fields

| Field | Type | Meaning |
|---|---|---|
| `packet_id` | string | UUID-based packet identifier |
| `operation_mode` | string | `new` for uncharged scaffold; `single` or `bulk` for scoped charging |
| `metadata.primary_profile.name_identifier` | string | Human-facing name identifier for the primary profile |
| `metadata.primary_profile.id` | string | Canonical URI for the primary profile |
| `metadata.profiles` | array | Full profile definitions (statements, identification, metadata) for all profiles in scope |
| `metadata.graph` | object | Unified profile and value-list graph with `nodes` (by name_identifier) and `edges` |
| `metadata.mint` | object | Mint provenance: `minted_at`, `generator`, `gkc_version` |
| `metadata.integrity` | object | SHA-256 digest of canonical metadata JSON; used as a fermenter go/no-go gate on re-entry |

### Uncharged Entity Slot Shape

Each entry in `data.entities[]` is pre-scaffolded from profile definitions with empty value slots ready to be filled:

```json
{
  "profile": "tribal_government_us",
  "id": "https://datadistillery.wikibase.cloud/entity/Q4",
  "labels": {"mul": {"data-value": ""}},
  "descriptions": {"mul": {"data-value": ""}},
  "aliases": {"mul": {"data-value": ""}},
  "statements": {
    "instance_of": {
      "id": "https://datadistillery.wikibase.cloud/entity/Q16",
      "data-type": "wikibase-item",
      "data-value": "https://www.wikidata.org/entity/Q7840353"
    },
    "official_website": {
      "id": "https://datadistillery.wikibase.cloud/entity/Q19",
      "data-type": "url",
      "data-value": null,
      "value-list": "cache/queries/Q28.json",
      "references": {
        "stated_in": [
          {
            "id": "https://datadistillery.wikibase.cloud/entity/Q30",
            "data-type": "wikibase-item",
            "data-value": null
          }
        ],
        "reference_url": [
          {
            "id": "https://datadistillery.wikibase.cloud/entity/Q29",
            "data-type": "url",
            "data-value": null
          }
        ]
      }
    }
  }
}
```

| Field | Type | Meaning |
|---|---|---|
| `profile` | string | Profile `name_identifier` for this entity slot |
| `id` | string | Profile URI — canonical entity identity for this slot |
| `labels` / `descriptions` / `aliases` | object | Language-keyed slots. Each value is `{"data-value": ""}` — no inner language tag. |
| `statements` | object | Statement slots keyed by statement `name_identifier` |

**Statement slot fields:**

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Statement entity URI |
| `data-type` | string | Wikibase data type (e.g., `wikibase-item`, `url`, `string`, `time`) |
| `data-value` | any | The value — empty string or `null` when uncharged; pre-filled for fixed/single-option defaults |
| `value-list` | string | Relative path to the value-list cache file, when applicable |
| `qualifiers` | object | Present only when the profile specifies qualifiers; same slot shape, keyed by qualifier `name_identifier` |
| `references` | object | Present only when the profile specifies references; keyed by reference statement `name_identifier`, each an array of slot objects |

Qualifiers and references are omitted entirely when the profile does not specify them. When a statement is used as a reference or qualifier, it does not carry its own nested `references` or `qualifiers`.

## Charged Entity Slot Shape

Charging populates each entity slot's `data-value` fields with values from source data (Wikidata, curated input, defaults). The entity slot structure mirrors the uncharged shape:

Implementation note:

- Current runtime charged packets still include transitional hybrid payload details while #200 contract-correction refactors are in progress.

```json
{
  "profile": "tribal_government_us",
  "id": "https://datadistillery.wikibase.cloud/entity/Q4",
  "labels": {"mul": {"data-value": "Cherokee Nation"}},
  "descriptions": {"mul": {"data-value": "federally recognized Native American tribe"}},
  "aliases": {"mul": {"data-value": ""}},
  "statements": {
    "instance_of": {
      "id": "https://datadistillery.wikibase.cloud/entity/Q16",
      "data-type": "wikibase-item",
      "data-value": "https://www.wikidata.org/entity/Q7840353"
    },
    "official_website": {
      "id": "https://datadistillery.wikibase.cloud/entity/Q19",
      "data-type": "url",
      "data-value": "https://www.cherokee.org",
      "value-list": "cache/queries/Q28.json"
    },
    "population": {
      "id": "https://datadistillery.wikibase.cloud/entity/Q21",
      "data-type": "quantity",
      "data-value": null
    }
  }
}
```

**Target invariant:** The `data` section preserves the **source payload only**. Evaluation results, notices, and conformance status are never stored in `data`. All such metadata flows into the `conformance` section.

## Conformance Section

The `conformance` section is produced by `gkc.fermenter` during packet charging and contains all evaluation results. It is an array of per-entity evaluation groups, each covering one source item.

Implementation note:

- Current runtime charge output is still transitioning toward this grouped conformance shape as contract work in #200 proceeds.

### Conformance Top-Level Shape

```json
{
  "conformance": [
    {
      "source_item": "http://www.wikidata.org/entity/Q14708404",
      "source_item_label": "Cherokee Nation",
      "statement_evaluations": [
        { /* ... */ }
      ]
    }
  ]
}
```

`source_item_label` is the best available single-language label for the entity, resolved in preference order: `en` → `mul` → first available language. This matches the active GKC language setting (currently defaulting to `en`).

### Statement Evaluation Records

Each entry in `statement_evaluations` covers one claim from the source Wikidata entity. Records are produced by the fermenter primitive `evaluate_statement_instance(profile_statement, raw_claim)` and serialized by `statement_evaluation_to_record()`.

```json
{
  "json_path": "$.entity.claims.P856[0]",
  "gkc_entity_statement": {
    "id": "official_website",
    "uri": "https://datadistillery.wikibase.cloud/entity/Q19"
  },
  "conformant": true,
  "outcome": "conformant",
  "normalized_value": "https://www.cherokee.org",
  "qualifiers": [],
  "references": [
    {
      "json_path": "$.entity.claims.P856[0].references.P854",
      "gkc_entity_statement": {
        "id": "reference_url",
        "uri": "https://datadistillery.wikibase.cloud/entity/Q29"
      },
      "conformant": true,
      "outcome": "conformant",
      "normalized_value": "https://www.cherokee.org"
    }
  ]
}
```

**For claims not mapped to any profile statement**, `gkc_entity_statement` is `null` and `outcome` is omitted. The claim still appears in the evaluations so curators can see what source data the profile does not cover.

```json
{
  "json_path": "$.entity.claims.P18[0]",
  "gkc_entity_statement": null,
  "conformant": false,
  "normalized_value": "Cherokee_Nation_Capitol.jpg"
}
```

### Statement Evaluation Record Fields

| Field | Type | Meaning |
|---|---|---|
| `json_path` | string | JSONPath to the claim in source Wikidata entity JSON (e.g., `$.entity.claims.P856[0]`) |
| `gkc_entity_statement` | object or null | Profile statement identity: `id` (name_identifier) and `uri` (canonical DD Wikibase URI). `null` when the claim is not covered by the profile. |
| `conformant` | boolean | `true` only when this record and all nested qualifiers and references are conformant. `false` for any failure or uncovered claim. |
| `outcome` | string | Evaluation outcome code (see below). Omitted when `gkc_entity_statement` is null. |
| `normalized_value` | any | Normalized, curator-facing value. For `wikibase-item` types this is a full resolvable URI (e.g., `http://www.wikidata.org/entity/Q12345`). |
| `qualifiers` | array | Nested qualifier evaluation records using the same shape. |
| `references` | array | Nested reference evaluation records using the same shape. |

### Outcome Values

`outcome` is set only when `gkc_entity_statement` is non-null. All outcome messaging for curator display is drawn from `error message` statements in the corresponding DD Wikibase entity profile items (accessible via `metadata.profiles` in the packet), enabling multilingual rendering without embedding text strings in the conformance record.

| Outcome | Meaning | Curator action |
|---|---|---|
| `conformant` | Value matches all profile constraints | None |
| `missing` | Profile expects this statement; none found in source | Add the statement |
| `value_error` | Value is present but malformed or wrong datatype | Fix the value; see statement-type `error message` in profile |
| `value_not_in_allowed_set` | Value is the right type but not in the required list or fixed value | Choose from allowed values; see list `error message` in profile |

**Note:** fixed-value constraints are modeled as a list of one item in the profile. `value_not_in_allowed_set` covers both list and fixed-value mismatches.

**Note on nesting:** Qualifiers and references use the same record shape recursively. `conformant` on the parent statement is `true` only when the parent value and all nested records are individually `conformant: true`.


### Source Provenance (per entity, in metadata)

When charging from Wikidata, each entity's source metadata is recorded under `metadata.profiles[i]` alongside the profile definition:

```json
{
  "source_qid": "Q195562",
  "lastrevid": 1234567890,
  "pulled_at": "2026-03-26T10:00:00Z"
}
```

`lastrevid` is used when a charged packet reaches the bottling/shipping stage to detect whether the Wikidata item has changed since the packet was minted. It is also used when a Curation Packet is re-presented for validation.

## Conformance and Blocking Policy

Conformance is target-state oriented, not strict all-fields-must-be-present enforcement.

Current policy direction:

- Type/shape conformance failures are hard blockers.
- Missing expected statements, qualifiers, or references are usually notice-driven unless policy explicitly escalates.
- `max_count` is an upper-bound target; effective lower bound is zero unless explicit minimum policy is introduced.
- Derived-value and fixed/list constraints are enforced according to profile directives and resolver context.

## Packet Re-entry and Integrity

Curation packets carry a SHA-256 digest of their canonical metadata at mint time (`metadata.integrity.metadata_digest`). When a packet is presented back to the fermenter for validation, this digest is recomputed and compared. A digest mismatch is a hard failure — no data validation proceeds until integrity is confirmed. This ensures that the ruleset embedded in the packet has not drifted from the one used during curation.

For long-lived packets that return after SpiritSafe or Data Distillery state has changed, the `metadata.mint` provenance fields (`minted_at`, `gkc_version`) provide a basis for drift classification. Formal packet migration tooling — including change classification (`patch_compatible`, `minor_compatible`, `migration_required`, `breaking`) and a migration report — is planned but not yet implemented.

### Theoretical Design Notes

**Packet migration tooling** — When a packet created from an older SpiritSafe state is re-presented, a forward migration utility will classify drift and apply approved transforms before re-validation. The `metadata.mint` fields provide the provenance anchor for this. Not yet implemented.

## Related Documentation

- [Data Distillery Wikibase Architecture](../architecture/DataDistillery-Wikibase.md)
- [Cross-Module Contracts](../architecture/module-contracts.md)
- [SpiritSafe Integration Architecture](../architecture/spirit_safe_models.md)
- [Profiles and Graph Linkage](./profiles.md)
- [Wizard Workflows](./wizard.md)
