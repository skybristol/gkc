# Still Charger API

## Overview

The `gkc.still_charger` module assembles curation packet scaffolds from JSON Entity Profiles and fills them with concrete source values before Wikibase write planning.

All packets enforce a strict `metadata` / `data` split. The `metadata` section carries the full profile ruleset, unified graph, mint provenance, and an integrity digest. The `data` section contains fillable entity slots keyed by statement `name_identifier`.

Validation and coercion notices are emitted as `ConformanceNotice` objects (see [Fermenter API](fermenter.md)).

## Quick Start: Build and Charge a Packet

```python
from pathlib import Path
from gkc.still_charger import (
    create_curation_packet,
    charge_packet_from_wikidata_items,
)
from gkc.spirit_safe import set_spirit_safe_source

set_spirit_safe_source(mode="local", local_root="/path/to/SpiritSafe")

# 1. Create uncharged scaffold from profile QID (canonical entrypoint)
packet = create_curation_packet("Q4", operation_mode="single")

print(packet["packet_id"])
# Entity slots are keyed by name_identifier in data.entities
for entity in packet["data"]["entities"]:
    print(entity["profile"], list(entity["statements"].keys()))

# 2. Charge from Wikidata (Cherokee Nation Q195562)
# qid_map accepts profile entity URI or name_identifier as keys
qid_map = {entity["id"]: "Q195562" for entity in packet["data"]["entities"]}
charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)

for notice in notices:
    print(notice.severity, notice.code, notice.message)
```

## Public API

### `create_curation_packet()`

Create a packet scaffold from SpiritSafe by profile identifier.

```python
from gkc.still_charger import create_curation_packet

packet = create_curation_packet("Q4", operation_mode="single")
```

**Arguments:**

| Argument | Type | Description |
|---|---|---|
| `profile_id` | `str` | Profile QID or full profile URI |
| `operation_mode` | `str` | `single` for primary-only scaffold or `bulk` for profile-graph expansion |

**Returns:** `dict` — Packet scaffold in the dual-key packet contract (`name_identifier` for human-facing keys and `id` URI for canonical identity).

---

### `build_curation_packet_from_json_profile()`

Assemble a curation packet scaffold from a JSON Entity Profile document.

```python
from pathlib import Path
from gkc.still_charger import build_curation_packet_from_json_profile

packet = build_curation_packet_from_json_profile(
    profile_entity="https://datadistillery.wikibase.cloud/entity/Q4",
    json_profile_doc=json_profile_doc,
    source_root=Path("/path/to/SpiritSafe"),
)
```

**Arguments:**

| Argument | Type | Description |
|---|---|---|
| `profile_entity` | `str` | Full URI for the entity profile (e.g., `https://datadistillery.wikibase.cloud/entity/Q4`) |
| `json_profile_doc` | `dict` | Parsed JSON Entity Profile document |
| `source_root` | `Path \| None` | Local SpiritSafe root for value-list route resolution (optional) |

**Returns:** `dict` — The assembled packet with the two-section contract:

```json
{
  "packet_id": "pkt-...",
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
    "graph": {"nodes": {}, "edges": []},
    "mint": {"minted_at": "...", "generator": "...", "gkc_version": "..."},
    "integrity": {"metadata_digest": "..."}
  },
  "data": {
    "entities": [
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
          }
        }
      }
    ]
  }
}
```

### `charge_packet_from_wikidata_items()`

Charge a packet scaffold with live data fetched from Wikidata.

```python
from gkc.still_charger import charge_packet_from_wikidata_items

# Map all packet entities to a single QID
qid_map = {entity["id"]: "Q195562" for entity in packet["data"]["entities"]}

charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)

errors = [n for n in notices if n.severity == "error"]
warnings = [n for n in notices if n.severity == "warning"]
```

**Arguments:**

| Argument | Type | Description |
|---|---|---|
| `packet` | `dict` | Assembled packet from `build_curation_packet_from_json_profile()` |
| `qid_map` | `dict[str, str]` | Maps entity IDs or profile entity URIs to Wikidata QIDs |
| `mash_client` | `Any \| None` | Optional pre-configured mash client; creates a new one if not supplied |

**QID resolution order for entity slots:**

1. Full profile entity URI — exact key match in `qid_map`
2. Profile `name_identifier` — key match in `qid_map`
3. Profile entity URI tail QID — direct Wikidata lookup fallback

**Returns:** `tuple[dict, list[ConformanceNotice]]`

- `dict`: Charged packet with `data-value` fields populated in each entity slot. Statements are partitioned into conformant, non_conformant (with `non_conformant: true` and `notices`), and uncovered (under `entity.uncovered_statements`). Missing-required statements remain with `data-value: null` and attached notices.
- `list[ConformanceNotice]`: All conformance notices from the charging pass.

---

### `charge_curation_packet()` (Legacy)

Charge a packet directly from a source-values dict. This is a legacy path for bulk operations where data has already been fetched and transformed before packet assembly. New workflows should use `charge_packet_from_wikidata_items()` instead.

```python
from gkc.still_charger import charge_curation_packet

source_values = {
    "https://datadistillery.wikibase.cloud/entity/Q4": {
        "labels": {"mul": {"data-value": "Cherokee Nation"}},
        "statements": {
            "instance_of": [{"data-value": "https://www.wikidata.org/entity/Q7840353"}],
        },
    }
}

charged_packet, report = charge_curation_packet(packet, source_values)

print(report.entities_charged)
print(report.entities_skipped)
print([issue.message for issue in report.issues])
```

---

### `ChargeIssue` and `ChargeReport`

```python
from gkc.still_charger import ChargeIssue, ChargeReport

issue = ChargeIssue(
    severity="warning",
  entity_ref="https://datadistillery.wikibase.cloud/entity/Q4",
    code="specificationless_charge",
    message="Specificationless charging accepted unknown statements",
)

report = ChargeReport(entities_charged=1, entities_skipped=0, issues=[issue])
print(report.entities_charged, report.issues[0].severity)
```

`ChargeIssue` is an alias for `ConformanceNotice` (see [Fermenter API](fermenter.md)).


## API Reference (mkdocstrings)

### `ChargeIssue`

::: gkc.still_charger.ChargeIssue
    options:
      show_root_heading: false
      heading_level: 4

### `ChargeReport`

::: gkc.still_charger.ChargeReport
    options:
      show_root_heading: false
      heading_level: 4

### `create_curation_packet()`

::: gkc.still_charger.create_curation_packet
    options:
      show_root_heading: false
      heading_level: 4

### `build_curation_packet_from_json_profile()`

::: gkc.still_charger.build_curation_packet_from_json_profile
    options:
      show_root_heading: false
      heading_level: 4

### `charge_curation_packet()`

::: gkc.still_charger.charge_curation_packet
    options:
      show_root_heading: false
      heading_level: 4

## See Also

- [Wikibase API](wikibase.md)
- [Shipper API](shipper.md)
