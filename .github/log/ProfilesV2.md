# ProfilesV2: Wikibase-First Entity Profile Architecture

Target agents: Profile Architect, Validation Agent, Wizard Engineer

Status: Pre-packet work complete. Curation Packet rework is the active milestone.

## Purpose

This brief is the active implementation guide for ProfilesV2. It captures what is done, what is now canonical, and what remains.

## Completed

### Cache and extraction substrate

- Per-entity cache refresh routes are implemented.

- SPARQL-driven cache-builder routes are implemented.

- Incremental recentchanges refresh routes are implemented.

- SpiritSafe workflow support for full and incremental cache refresh is implemented.

### JSON Entity Profile generation

- `EntityProfileJsonBuilder` is implemented in `gkc.spirit_safe`.

- JSON profile generation from `cache/entities/*.json` is implemented.

- CLI route is implemented: `gkc profile export-json`.

- Per-profile JSON output is implemented with one file per profile QID (`<output>/<QID>.json`).

- Optional profile filtering is implemented via repeatable `--profile-id`.

- API helper routes are implemented and exported: `build_entity_profile_json_documents(...)` and `export_entity_profile_json_documents(...)`.

### Value-list query extraction and hydration

- Mash primitives are implemented for reading talk-page wikitext and extracting `<sparql>` blocks.

- Value-list discovery from cache entities (`P1 -> Q7`) is implemented.

- Query export is implemented to `queries/<QID>.sparql` using the first `<sparql>` block from `Item_talk:<QID>`.

- Value-list hydration is implemented to `cache/queries/<QID>.json` with pagination and deduplication.

- CLI route is implemented: `gkc profile value-lists hydrate`.

- SpiritSafe GitHub Actions workflow is implemented and operational: `hydrate-value-lists.yml`.

### SpiritSafe repository

- All GitHub Actions workflows are operational: cache refresh, profile export, value-list hydration, profile validation, and PR auto-merge.

- Repository documentation is current: all README files are updated, `cache/queries/README.md` is added.

- Empty Python package placeholder removed.

### Current generated profile shape

The JSON profiles in `profiles/<QID>.json` currently export:

- `entity` — full Wikibase entity URI

- `identification` — prompts and guidance per language section (labels, descriptions, aliases)

- `statements` — list of statement definitions, each with `entity` URI, `io_map`, `value` (type, optional `profile`, optional `value_list_reference`, optional `value_list`), `messages`, `max_count`, `qualifiers`, and `references`

- `metadata` — label/description/alias text maps, statement count, languages, generated_at, exported_from, and two pre-built graph structures for downstream packet assembly:

  - `profile_graph` — edges to related profile entities: `entity` (URI), `label`, `via_statement` (URI), `linkage_type`

  - `value_list_graph` — edges to value-list entities: `entity` (URI), `label`, `via_statement` (URI), `cache_path`

Both graphs are already populated from real SpiritSafe data and ready for packet assembly consumption.

## Canonical Direction

### Identity

- Canonical machine identifier is `entity` URI.

- Labels are presentation only. Runtime identity, joins, and linkage resolution must not use labels.

- Profile loading entry point: QID string or full entity URI, both normalized to full URI. Filesystem derivation from URI (QID extraction) is non-authoritative and isolated.

### Runtime dependency model

- Build-time profile generation reads SpiritSafe cache entities.

- Runtime consumers load JSON profiles from `profiles/<QID>.json`; no live Wikibase access required.

- No manifest (`cache/manifest.json`) dependency for packet assembly.

### Value-list behavior

- Value-list usage is cache-first. Runtime consumers use materialized `cache/queries/<QID>.json` artifacts.

- Packet-level `value_list_routes` reference `cache_path` directly from `metadata.value_list_graph`.

## Curation Packet Contract (Frozen)

The following packet shape is the frozen contract that the Validation Agent implements and the Wizard Engineer consumes. No changes to this shape without explicit Profile Architect instruction.

```json
{
  "packet_id": "pkt-<uuid>",
  "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
  "operation_mode": "single",
  "entities": [
    {
      "id": "ent-001",
      "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
      "data": {},
      "statements": [
        {
          "entity": "https://datadistillery.wikibase.cloud/entity/Q16",
          "label": "instance of",
          "io_map": [{"to": "http://www.wikidata.org/entity/P31"}],
          "value": {
            "type": "wikibase-item",
            "value_list": [{"item": "Q7840353", "itemLabel": "federally recognized Native American tribe in the United States"}]
          },
          "fixed": true,
          "max_count": null,
          "qualifiers": [],
          "references": []
        }
      ]
    }
  ],
  "cross_references": [
    {
      "from_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
      "to_entity": "https://datadistillery.wikibase.cloud/entity/Q39",
      "via_statement": "https://datadistillery.wikibase.cloud/entity/Q40",
      "linkage_type": "P161"
    }
  ],
  "value_list_routes": {
    "https://datadistillery.wikibase.cloud/entity/Q28": {
      "label": "List of Federal Register Sources",
      "cache_path": "cache/queries/Q28.json",
      "item_count": 47
    }
  }
}
```

### Frozen design decisions

- `profile_entity` uses full URI throughout. No profile-name string keys anywhere in the packet.

- `cross_references` are sourced from `metadata.profile_graph` of the loaded JSON profile. No manifest required.

- `value_list_routes` are sourced from `metadata.value_list_graph`. `item_count` is loaded at assembly time from the referenced cache file if it exists; `null` if the file is absent.

- `max_count: null` is the exclusive unlimited encoding. This applies profile → packet → validation path with no other representation.

- `fixed: true` on a statement means the value is pre-populated from the profile (sourced from `value.value_list` entries). Fixed values should not be user-edited. `fixed: null` or absent means curator-supplied.

- `data` is an empty dict at assembly time. `charge_curation_packet()` fills it.

- Entity scaffolds carry `profile_entity` (URI) on each entity slot; the `id` field (`ent-001`) is a stable intra-packet reference.

## Remaining Work: Curation Packet Generation

> **Tracked:** gkc#143 — Curation packet rework: align packet assembly, charge, and barrel pipeline with frozen URI-keyed contract

### 1) `build_curation_packet_from_json_profile()`

Responsibility: Validation Agent

Inputs:

- `profile_entity` — QID string or full entity URI (normalize to full URI internally)

- `json_profile_doc` — loaded JSON profile document (dict from `profiles/<QID>.json`)

- Optional `source_root` — path to SpiritSafe root, used to hydrate `item_count` in `value_list_routes`

Output: packet dict matching the frozen contract above.

Steps:

1. Normalize `profile_entity` to full URI; derive QID for filesystem access.

2. Build `entities` list: one entity slot per profile entity, `data` empty, `statements` copied from `json_profile_doc["statements"]` with `fixed` flag derived from `value.value_list` presence.

3. Build `cross_references` from `json_profile_doc["metadata"]["profile_graph"]`.

4. Build `value_list_routes` from `json_profile_doc["metadata"]["value_list_graph"]`, optionally hydrating `item_count` from the cache file.

5. Generate `packet_id` as `pkt-<uuid4>`.

Deliverables: implementation in `gkc.spirit_safe`, tests covering single-profile packet, cross-references populated from profile_graph, value_list_routes with and without item_count, and fixed-value detection.

### 2) URI-keyed lookup in `charge_curation_packet()`

Responsibility: Validation Agent

Current `_entity_payload_for()` matches source_values by `entity.get("id")` (intra-packet UUID) or `entity.get("profile")` (profile name string). Neither matches URI keys.

Required: source_values must support keys that are full entity URIs or QID strings. Resolution order: exact URI match first, then QID-only fallback.

Deliverables: updated `_entity_payload_for()` with URI-keyed resolution; tests covering URI-keyed and QID-keyed source_values.

### 3) Shared `ConformanceNotice` envelope

Responsibility: Validation Agent

Required: replace the current `ChargeIssue` / `ChargeReport` / `BarrelIssue` / `BarrelPlanReport` split with a single `ConformanceNotice` dataclass. All charging, barreling, and validation surfaces emit it. CLI and Wizard consume it without adapting locally.

Fields: `severity`, `entity_ref` (URI or intra-packet ID), `statement_ref` (URI or None), `code`, `message`.

Deliverables: shared type in `gkc.still_charger` or a new `gkc.notices` module; charging and barreling emit it; existing `ChargeIssue` and `BarrelIssue` become aliases or are deprecated.

### 4) `gkc packet build` CLI route

Responsibility: Validation Agent

Required: `gkc packet build --profile Q4 [--source local --local-root ...]` outputs a JSON packet to stdout or a file.

Deliverables: CLI route consuming `build_curation_packet_from_json_profile()`; tests covering defaults and `--source local`.

### 5) Wizard packet integration

Responsibility: Wizard Engineer — begins after items (1)–(4) are complete.

- No local packet assembly logic in the Wizard layer.

- Value-list routes consumed directly from `packet["value_list_routes"]`.

- Conformance notices rendered from the shared envelope with no local coercion policy.

## Immediate Agent Sequence

### Profile Architect

The frozen packet contract above is the handoff. No further Profile Architect input is needed before implementation begins.

### Validation Agent

Implement items (1)–(4) above against the frozen contract. Validate against test fixtures in `tests/fixtures/profiles/`. Produce a handoff summary for the Wizard Engineer when complete.

### Wizard Engineer

After the packet milestone is delivered, integrate directly against the frozen packet shape. No local packet assembly or value-list policy forks.

## Acceptance Criteria For Packet Milestone

- `build_curation_packet_from_json_profile()` produces packets with URI identity throughout.

- `cross_references` are deterministic and sourced from `metadata.profile_graph`.

- `value_list_routes` are populated at assembly time; consumers use them directly.

- `max_count: null` is the single unlimited encoding end-to-end.

- `ConformanceNotice` is emitted consistently across charging, barreling, and validation surfaces.

- Packets are round-trippable through charge and barrel without loss of identity.

- Tests cover packet assembly, URI-keyed charging, notice emission, and CLI output.

## Out Of Scope For Packet Milestone

> **Tracked:** gkc#142 — SpiritSafe manifest: replace old design with URI-keyed artifact index and cleanup legacy manifest infrastructure
> **Tracked:** gkc#144 — Wizard V2: dynamic form generation from SpiritSafe JSON profiles (begins after gkc#143 delivers)

- Sitelink profile contract.

- Interface-specific policy engines separate from shared validation and charging behavior.

- Live runtime SPARQL execution as a substitute for materialized value-list artifacts.

- Manifest (`cache/manifest.json`) generation — not required for packet assembly.

- Deprecation or removal of the old `create_curation_packet()` — deferred until the Wizard migration is complete.

## Practical Commands (Current)

Build and export JSON profiles from cache entities:

```bash
poetry run gkc --json profile export-json \
  --cache-entities-dir /Users/sky/code/SpiritSafe/cache/entities \
  --output /Users/sky/code/SpiritSafe/profiles
```

Hydrate value-list queries and cache artifacts:

```bash
poetry run gkc --json profile value-lists hydrate \
  --source local \
  --local-root /Users/sky/code/SpiritSafe
```

Filter export to selected profiles:

```bash
poetry run gkc --json profile export-json \
  --cache-entities-dir /Users/sky/code/SpiritSafe/cache/entities \
  --profile-id Q4 \
  --profile-id Q39 \
  --output /Users/sky/code/SpiritSafe/profiles
```
