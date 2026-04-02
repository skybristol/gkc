# Still Charger API

## Overview

`gkc.still_charger` is the packet assembly and source charging module.

It owns:

- Building curation packet scaffolds from JSON Entity Profiles.
- Charging packet entities from source systems (currently Wikidata via `mash`).
- Producing packet-level conformance payloads by orchestrating fermenter primitives.
- Maintaining packet metadata integrity sealing after charge-time metadata mutation.

It does not own validation semantics. Fermenter owns validation outcomes and notice semantics.

## Contract Shape

Curation packets follow a strict three-section top-level shape:

- `metadata`
- `data`
- `conformance`

Source metadata for charged packets is recorded in `metadata.profiles[*]` and includes:

- `source_qid`
- `lastrevid`
- `pulled_at`

After source metadata injection, `still_charger` reseals `metadata.integrity.metadata_digest`.

## Quick Start

```python
from gkc.still_charger import create_curation_packet, charge_packet_from_wikidata_items
from gkc.spirit_safe import set_spirit_safe_source

set_spirit_safe_source(mode="local", local_root="/path/to/SpiritSafe")

packet = create_curation_packet("Q4", operation_mode="single")

qid_map = {entity["id"]: "Q195562" for entity in packet["data"]["entities"]}
charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)

print(charged_packet["metadata"]["profiles"][0].get("source_qid"))
print(charged_packet["metadata"]["integrity"]["metadata_digest_algorithm"])
print(len(notices))
```

## Public API

### create_curation_packet

Create a packet scaffold from SpiritSafe profile JSON.

```python
from gkc.still_charger import create_curation_packet

packet = create_curation_packet("Q4", operation_mode="single")
```

Arguments:

| Argument | Type | Meaning |
|---|---|---|
| `profile_id` | `str` | Profile QID or full profile URI |
| `operation_mode` | `str` | `single` for primary profile only, `bulk` for profile-graph expansion |

Returns:

- Packet scaffold with `metadata`, `data`, and empty `conformance` target surface.

### build_curation_packet_from_json_profile

Assemble a packet scaffold from a loaded JSON profile document.

```python
from pathlib import Path
from gkc.still_charger import build_curation_packet_from_json_profile

packet = build_curation_packet_from_json_profile(
    profile_entity="https://datadistillery.wikibase.cloud/entity/Q4",
    json_profile_doc=json_profile_doc,
    source_root=Path("/path/to/SpiritSafe"),
)
```

Arguments:

| Argument | Type | Meaning |
|---|---|---|
| `profile_entity` | `str` | Profile URI or QID |
| `json_profile_doc` | `dict` | Parsed JSON profile document |
| `source_root` | `Path | None` | Optional SpiritSafe local root for value-list route resolution |
| `source_config` | `dict | None` | Optional source descriptor stored under `metadata.source` |

Returns:

- Uncharged packet scaffold with sealed metadata integrity digest.

### charge_packet_from_wikidata_items

Charge a packet from Wikidata entities and emit conformance payloads.

```python
from gkc.still_charger import charge_packet_from_wikidata_items

charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)
```

Arguments:

| Argument | Type | Meaning |
|---|---|---|
| `packet` | `dict` | Packet assembled by `build_curation_packet_from_json_profile` |
| `qid_map` | `dict[str, str]` | Maps profile URI or profile `name_identifier` to Wikidata QID |
| `mash_client` | `Any | None` | Optional `WikibaseLoader`-compatible client |

Returns:

| Position | Type | Meaning |
|---|---|---|
| `0` | `dict` | Charged packet |
| `1` | `list[ConformanceNotice]` | Packet notices (currently empty placeholder list for this path) |

Charge behavior:

- Resolves linked entities via profile linkage routes.
- Loads primary and linked entity JSON from Wikidata.
- Populates packet data entities with source payloads.
- Injects source provenance fields into `metadata.profiles[*]`.
- Builds `conformance` payload from fermenter statement evaluators.
- Reseals metadata digest after metadata mutation.

Current runtime note:

- `data.entities` remains a transitional hybrid surface in current implementation (scaffold slots plus embedded raw entity payload).
- Contract direction in #200 is to eliminate hybrid slot decoration from packet `data` and keep evaluation semantics in `conformance` only.

### charge_curation_packet (Legacy)

Legacy direct-charge path from caller-provided source values.

```python
from gkc.still_charger import charge_curation_packet

charged_packet, report = charge_curation_packet(packet, source_values)
```

New workflows should prefer `charge_packet_from_wikidata_items`.

### ChargeIssue and ChargeReport

`ChargeIssue` captures a non-fatal charging issue.

`ChargeReport` summarizes charge results:

- `entities_charged`
- `entities_skipped`
- `issues`

## Metadata Integrity and Provenance

Metadata digest behavior:

1. Packet scaffolds are sealed at build time.
2. Charged packets inject source provenance into `metadata.profiles[*]`.
3. Metadata is resealed after provenance injection.

This supports packet re-presentation checks where metadata integrity and source revision context must be evaluated together.

## Conformance Output Interface

`still_charger` orchestrates conformance payload construction and delegates atomic statement evaluation to fermenter:

- `evaluate_statement_instance`
- `statement_evaluation_to_record`

Ownership split:

- `still_charger`: packet orchestration, source loading, packet mutation order.
- `fermenter`: statement-level evaluation semantics and record serialization.

## API Reference (mkdocstrings)

### ChargeIssue

::: gkc.still_charger.ChargeIssue
    options:
      show_root_heading: false
      heading_level: 4

### ChargeReport

::: gkc.still_charger.ChargeReport
    options:
      show_root_heading: false
      heading_level: 4

### create_curation_packet

::: gkc.still_charger.create_curation_packet
    options:
      show_root_heading: false
      heading_level: 4

### build_curation_packet_from_json_profile

::: gkc.still_charger.build_curation_packet_from_json_profile
    options:
      show_root_heading: false
      heading_level: 4

### charge_packet_from_wikidata_items

::: gkc.still_charger.charge_packet_from_wikidata_items
    options:
      show_root_heading: false
      heading_level: 4

### charge_curation_packet

::: gkc.still_charger.charge_curation_packet
    options:
      show_root_heading: false
      heading_level: 4

## See Also

- [Fermenter API](fermenter.md)
- [SpiritSafe API](spirit_safe.md)
- [Curation Packet Contract](../entity-json-schema.md)
