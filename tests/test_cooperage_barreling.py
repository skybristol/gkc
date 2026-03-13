from gkc.cooperage import barrel_curation_packet_to_wikibase_plan


def _charged_packet_example():
    return {
        "packet_id": "pkt-abc123",
        "entities": [
            {
                "id": "ent-001",
                "profile": "TribalGovernmentUS",
                "profile_structure": {
                    "statements": [
                        {
                            "id": "instance_of",
                            "io_map": [{"to": "https://www.wikidata.org/entity/P31"}],
                        }
                    ]
                },
                "data": {
                    "labels": {"en": "Cherokee Nation"},
                    "descriptions": {
                        "en": "federally recognized Native American tribe based in Oklahoma"
                    },
                    "statements": {
                        "instance_of": [{"value": "Q7840353"}],
                    },
                },
            }
        ],
    }


def test_barrel_packet_to_operation_plan():
    packet = _charged_packet_example()

    operations, report = barrel_curation_packet_to_wikibase_plan(packet)

    assert report.operations_created == 1
    assert report.entities_skipped == 0
    assert len(report.issues) == 0

    op = operations[0]
    assert op["kind"] == "item"
    assert op["label"] == "Cherokee Nation"

    payload = op["payload"]
    assert payload["labels"]["en"]["value"] == "Cherokee Nation"
    assert payload["descriptions"]["en"]["language"] == "en"

    claim = payload["claims"][0]
    assert claim["mainsnak"]["property"] == "P31"
    assert claim["mainsnak"]["datavalue"]["type"] == "wikibase-entityid"
    assert claim["mainsnak"]["datavalue"]["value"]["id"] == "Q7840353"


def test_barrel_uses_global_property_map_when_statement_map_missing():
    packet = {
        "packet_id": "pkt-abc123",
        "entities": [
            {
                "id": "ent-001",
                "profile": "TribalGovernmentUS",
                "profile_structure": {"statements": []},
                "data": {
                    "labels": {"en": "Example"},
                    "statements": {"instance_of": [{"value": "Q1"}]},
                },
            }
        ],
    }

    operations, report = barrel_curation_packet_to_wikibase_plan(
        packet,
        property_id_map={"instance_of": "P31"},
    )

    assert report.operations_created == 1
    assert len(report.issues) == 0
    assert operations[0]["payload"]["claims"][0]["mainsnak"]["property"] == "P31"


def test_barrel_reports_unknown_statement_mapping():
    packet = {
        "packet_id": "pkt-abc123",
        "entities": [
            {
                "id": "ent-001",
                "profile": "TribalGovernmentUS",
                "profile_structure": {"statements": []},
                "data": {
                    "labels": {"en": "Example"},
                    "statements": {"unknown_statement": [{"value": "Q1"}]},
                },
            }
        ],
    }

    operations, report = barrel_curation_packet_to_wikibase_plan(packet)

    assert report.operations_created == 1
    assert len(report.issues) == 1
    assert report.issues[0].severity == "warning"
    assert operations[0]["payload"]["labels"]["en"]["value"] == "Example"
    assert "claims" not in operations[0]["payload"]
