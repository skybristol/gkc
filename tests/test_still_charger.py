from pathlib import Path

import pytest

from gkc.spirit_safe import load_profile, set_spirit_safe_source
from gkc.still_charger import (
    build_curation_packet_from_json_profile,
    charge_curation_packet,
)


@pytest.fixture(autouse=True)
def setup_local_source() -> None:
    fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"
    set_spirit_safe_source(mode="local", local_root=str(fixture_root))
    yield
    set_spirit_safe_source(mode="github")


def _minimal_packet():
    return {
        "packet_id": "pkt-test",
        "operation_mode": "single",
        "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "entities": [
            {
                "id": "ent-001",
                "profile": "TribalGovernmentUS",
                "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
                "data": {},
                "statements": [
                    {"entity": "https://datadistillery.wikibase.cloud/entity/Q16"},
                    {"entity": "https://datadistillery.wikibase.cloud/entity/Q40"},
                ],
                "profile_structure": {
                    "statements": [
                        {"id": "instance_of"},
                        {"id": "official_website"},
                    ]
                },
            }
        ],
    }


def test_build_packet_expands_linked_profiles_from_graph():
    profile_doc = load_profile("Q4")
    fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"

    packet = build_curation_packet_from_json_profile(
        profile_entity="Q4",
        json_profile_doc=profile_doc,
        source_root=fixture_root,
    )

    assert packet["metadata"]["primary_profile"]["id"] == (
        "https://datadistillery.wikibase.cloud/entity/Q4"
    )
    assert len(packet["data"]["entities"]) == 2
    assert {entity["id"] for entity in packet["data"]["entities"]} == {
        "https://datadistillery.wikibase.cloud/entity/Q4",
        "https://datadistillery.wikibase.cloud/entity/Q39",
    }
    edge_types = {
        edge["relationship_type"] for edge in packet["metadata"]["graph"]["edges"]
    }
    assert "P161" in edge_types


def test_build_packet_value_list_routes_use_statement_uris_and_item_counts():
    profile_doc = load_profile("Q4")
    fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"

    packet = build_curation_packet_from_json_profile(
        profile_entity="Q4",
        json_profile_doc=profile_doc,
        source_root=fixture_root,
    )

    value_list_edges = [
        edge
        for edge in packet["metadata"]["graph"]["edges"]
        if edge.get("relationship_type") == "value_list_link"
    ]
    assert any(
        edge.get("via_statement") == "https://datadistillery.wikibase.cloud/entity/Q16"
        and edge.get("cache_path") == "cache/queries/Q28.json"
        and edge.get("item_count") == 2
        for edge in value_list_edges
    )


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
