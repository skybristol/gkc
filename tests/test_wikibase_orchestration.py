from gkc.wikibase.orchestration import build_wikibase_write_plan


class _FakeShipper:
    def __init__(self):
        self.calls = []

    def plan_batch(self, operations, language="en"):
        self.calls.append({"operations": operations, "language": language})
        return {
            "summary": {"total": len(operations)},
            "operations": operations,
            "language": language,
        }


def test_build_wikibase_write_plan_pipeline_without_shipper(monkeypatch):
    packet = {
        "packet_id": "pkt-1",
        "entities": [
            {
                "id": "ent-001",
                "profile": "TribalGovernmentUS",
                "data": {},
                "profile_structure": {
                    "statements": [
                        {
                            "id": "instance_of",
                            "io_map": [{"to": "https://www.wikidata.org/entity/P31"}],
                        }
                    ]
                },
            }
        ],
    }

    def _fake_create_curation_packet(*args, **kwargs):
        _ = args, kwargs
        return packet

    monkeypatch.setattr(
        "gkc.wikibase.orchestration.create_curation_packet",
        _fake_create_curation_packet,
    )

    result = build_wikibase_write_plan(
        "TribalGovernmentUS",
        source_values={
            "ent-001": {
                "labels": {"en": "Cherokee Nation"},
                "statements": {"instance_of": [{"value": "Q7840353"}]},
            }
        },
    )

    assert result.packet["packet_id"] == "pkt-1"
    assert result.charge_report.entities_charged == 1
    assert result.barrel_report.operations_created == 1
    assert len(result.operations) == 1
    assert result.diff_plan is None


def test_build_wikibase_write_plan_pipeline_with_shipper(monkeypatch):
    packet = {
        "packet_id": "pkt-2",
        "entities": [
            {
                "id": "ent-001",
                "profile": "TribalGovernmentUS",
                "data": {},
                "profile_structure": {
                    "statements": [
                        {
                            "id": "instance_of",
                            "io_map": [{"to": "https://www.wikidata.org/entity/P31"}],
                        }
                    ]
                },
            }
        ],
    }

    def _fake_create_curation_packet(*args, **kwargs):
        _ = args, kwargs
        return packet

    monkeypatch.setattr(
        "gkc.wikibase.orchestration.create_curation_packet",
        _fake_create_curation_packet,
    )

    shipper = _FakeShipper()
    result = build_wikibase_write_plan(
        "TribalGovernmentUS",
        source_values={
            "ent-001": {
                "labels": {"en": "Cherokee Nation"},
                "statements": {"instance_of": [{"value": "Q7840353"}]},
            }
        },
        shipper=shipper,
        language="en",
    )

    assert len(shipper.calls) == 1
    assert shipper.calls[0]["language"] == "en"
    assert result.diff_plan is not None
    assert result.diff_plan["summary"]["total"] == 1
