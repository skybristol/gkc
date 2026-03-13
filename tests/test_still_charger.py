from gkc.still_charger import charge_curation_packet


def _minimal_packet():
    return {
        "packet_id": "pkt-test",
        "operation_mode": "single",
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


def test_charge_packet_by_profile_id():
    packet = _minimal_packet()
    values = {
        "TribalGovernmentUS": {
            "labels": {"en": "Cherokee Nation"},
            "statements": {
                "instance_of": [{"value": "Q7840353"}],
                "official_website": [{"value": "https://www.cherokee.org"}],
            },
        }
    }

    charged, report = charge_curation_packet(packet, values)

    assert report.entities_charged == 1
    assert report.entities_skipped == 0
    entity_data = charged["entities"][0]["data"]
    assert entity_data["labels"]["en"] == "Cherokee Nation"
    assert "instance_of" in entity_data["statements"]


def test_charge_packet_reject_unknown_statements_without_specificationless():
    packet = _minimal_packet()
    values = {
        "ent-001": {
            "statements": {
                "unknown_statement": [{"value": "Q1"}],
            }
        }
    }

    charged, report = charge_curation_packet(
        packet,
        values,
        specificationless=False,
    )

    assert report.entities_charged == 0
    assert report.entities_skipped == 1
    assert len(report.issues) == 1
    assert report.issues[0].severity == "error"
    assert charged["entities"][0]["data"] == {}


def test_charge_packet_allows_unknown_statements_with_specificationless():
    packet = _minimal_packet()
    values = {
        "ent-001": {
            "statements": {
                "unknown_statement": [{"value": "Q1"}],
            }
        }
    }

    charged, report = charge_curation_packet(
        packet,
        values,
        specificationless=True,
    )

    assert report.entities_charged == 1
    assert report.entities_skipped == 0
    assert len(report.issues) == 1
    assert report.issues[0].severity == "warning"
    assert "unknown_statement" in charged["entities"][0]["data"]["statements"]
