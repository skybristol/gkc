# Still Charger API

## Overview

The `gkc.still_charger` module fills curation packet scaffolds with concrete source values before cooperage transformation and shipper planning.

It supports both local-profile packet assembly (new URI-keyed contract) and specificationless charging for open-ended source data.
Validation and coercion notices are emitted as `ConformanceNotice` objects (see [Fermenter API](fermenter.md)).

## Quick Start: Build and Charge a Packet

```python
from pathlib import Path
from gkc.still_charger import (
    build_curation_packet_from_json_profile,
    charge_packet_from_wikidata_items,
)

# 1. Load a JSON profile from local SpiritSafe
import json
profile_path = Path("/path/to/SpiritSafe/profiles/Q4.json")
json_profile_doc = json.loads(profile_path.read_text())

profile_entity = "https://datadistillery.wikibase.cloud/entity/Q4"

# 2. Assemble the packet scaffold
packet = build_curation_packet_from_json_profile(
    profile_entity=profile_entity,
    json_profile_doc=json_profile_doc,
    source_root=Path("/path/to/SpiritSafe"),
)

print(packet["packet_id"])
print(len(packet["entities"]))

# 3. Charge from Wikidata (e.g., Cherokee Nation Q195562)
qid_map = {entity["id"]: "Q195562" for entity in packet["entities"]}
charged_packet, notices = charge_packet_from_wikidata_items(packet, qid_map)

for notice in notices:
    print(notice.severity, notice.code, notice.message)
```

## Public API

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

**Returns:** `dict` — The assembled packet with the frozen URI-keyed contract:

```json
{
  "packet_id": "uuid-...",
  "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
  "entities": [
    {
      "id": "uuid-...",
      "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
      "statements": [
        {"entity": "https://datadistillery.wikibase.cloud/entity/P5", "data": {}}
      ],
      "data": {}
    }
  ],
  "cross_references": [],
  "value_list_routes": {
    "https://datadistillery.wikibase.cloud/entity/P5": "/path/to/cache/queries/Q28.json"
  }
}
```

---

### `charge_packet_from_wikidata_items()`

Charge a packet scaffold with live data fetched from Wikidata.

```python
from gkc.still_charger import charge_packet_from_wikidata_items

# Map all packet entities to a single QID
qid_map = {entity["id"]: "Q195562" for entity in packet["entities"]}

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

**Returns:** `tuple[dict, list[ConformanceNotice]]`

- `dict`: The charged packet with each entity's `data` populated from Wikidata
- `list[ConformanceNotice]`: Notices emitted during charging (errors, warnings, info)

**QID resolution order for entity slots:**

1. Intra-packet UUID → exact key match in `qid_map`
2. Full entity URI → key match in `qid_map`
3. QID string → direct Wikidata lookup
4. Profile name (legacy) → backward-compatible fallback

---

### `charge_curation_packet()`

Charge a packet directly from a source-values dict. Useful for bulk operations where
data has already been fetched or transformed before packet assembly.

```python
from gkc.still_charger import charge_curation_packet

source_values = {
    "ent-001": {
        "labels": {"en": "Cherokee Nation"},
        "statements": {
            "instance_of": [{"value": "Q7840353"}],
            "official_website": [{"value": "https://www.cherokee.org"}],
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
    entity_ref="ent-001",
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

### `charge_curation_packet()`

::: gkc.still_charger.charge_curation_packet
    options:
      show_root_heading: false
      heading_level: 4

## See Also

- [Cooperage API](cooperage.md)
- [Wikibase API](wikibase.md)
- [Shipper API](shipper.md)
