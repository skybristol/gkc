# Still Charger API

## Overview

The `gkc.still_charger` module fills curation packet scaffolds with concrete source values before cooperage transformation and shipper planning.

It supports bootstrap-friendly specificationless charging and emits structured charge reports for warnings and errors.

## Quick Start

```python
from gkc.still_charger import charge_curation_packet

packet = {
    "packet_id": "pkt-demo",
    "entities": [
        {
            "id": "ent-001",
            "profile": "TribalGovernmentUS",
            "data": {},
            "profile_structure": {
                "statements": [
                    {"id": "instance_of"},
                    {"id": "official_website"},
                ]
            },
        }
    ],
}

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
print(charged_packet["entities"][0]["data"]["labels"]["en"])
```

## Public API Quick Starts

### `charge_curation_packet()`

```python
from gkc.still_charger import charge_curation_packet

charged, report = charge_curation_packet(
    packet,
    source_values,
    specificationless=True,
)

print(report.entities_charged)
print(report.entities_skipped)
print([issue.message for issue in report.issues])
```

### `ChargeIssue` and `ChargeReport`

```python
from gkc.still_charger import ChargeIssue, ChargeReport

issue = ChargeIssue(
    severity="warning",
    entity_id="ent-001",
    field="statements",
    message="Specificationless charging accepted unknown statements",
)

report = ChargeReport(entities_charged=1, entities_skipped=0, issues=[issue])
print(report.entities_charged, report.issues[0].severity)
```

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
