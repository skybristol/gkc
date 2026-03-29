from pathlib import Path

import pytest

from gkc.spirit_safe import load_profile, set_spirit_safe_source
from gkc.still_charger import (
    build_curation_packet_from_json_profile,
    charge_curation_packet,
    charge_packet_from_wikidata_items,
    create_and_charge_curation_packet,
    create_curation_packet,
    packet_entities,
    packet_entity_by_ref,
    packet_outgoing_links,
    packet_primary_profile_id,
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


def test_create_curation_packet_single_mode_is_primary_only():
    packet = create_curation_packet("Q4", operation_mode="single")

    assert packet["operation_mode"] == "single"
    assert len(packet["data"]["entities"]) == 1
    graph_edges = packet["metadata"]["graph"]["edges"]
    assert all(edge.get("relationship_type") != "P161" for edge in graph_edges)


def test_create_curation_packet_bulk_mode_expands_profile_graph():
    packet = create_curation_packet("Q4", operation_mode="bulk")

    assert packet["operation_mode"] == "bulk"
    assert len(packet["data"]["entities"]) == 2
    assert len(packet["metadata"]["graph"]["edges"]) == 2


def test_build_packet_materializes_value_list_path_on_statement_slots():
    profile_doc = load_profile("Q4")
    fixture_root = Path(__file__).resolve().parent / "fixtures" / "spiritsafe"

    packet = build_curation_packet_from_json_profile(
        profile_entity="Q4",
        json_profile_doc=profile_doc,
        source_root=fixture_root,
    )

    statement_slot = packet["data"]["entities"][0]["statements"]["Q16"]
    assert statement_slot["value-list"] == "cache/queries/Q28.json"


def test_build_packet_includes_mul_language_slots_for_identification_fields():
    profile_doc = load_profile("Q4")

    packet = build_curation_packet_from_json_profile(
        profile_entity="Q4",
        json_profile_doc=profile_doc,
    )

    entity = packet["data"]["entities"][0]
    assert entity["labels"] == {"mul": {"data-value": ""}}
    assert entity["descriptions"] == {"mul": {"data-value": ""}}
    assert entity["aliases"] == {"mul": {"data-value": ""}}


def test_build_packet_materializes_reference_and_qualifier_slots():
    profile_doc = {
        "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "name_identifier": "Q4",
        "identification": {
            "labels": {"mul": {"prompt": "label"}},
            "descriptions": {"mul": {"prompt": "description"}},
            "aliases": {"mul": {"prompt": "alias"}},
        },
        "statements": [
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q19",
                "name_identifier": "official_website",
                "value": {"type": "url"},
                "qualifiers": [
                    {
                        "entity": "https://datadistillery.wikibase.cloud/entity/Q32",
                        "name_identifier": "point_in_time",
                        "value": {"type": "time"},
                    }
                ],
                "references": [
                    {
                        "entity": "https://datadistillery.wikibase.cloud/entity/Q29",
                        "name_identifier": "reference_url",
                        "value": {"type": "url"},
                    },
                    {
                        "entity": "https://datadistillery.wikibase.cloud/entity/Q44",
                        "name_identifier": "stated_in",
                        "value": {"type": "wikibase-item"},
                    },
                ],
            }
        ],
        "metadata": {"profile_graph": [], "value_list_graph": []},
    }

    packet = build_curation_packet_from_json_profile(
        profile_entity="Q4",
        json_profile_doc=profile_doc,
    )

    statement_slot = packet["data"]["entities"][0]["statements"]["official_website"]
    assert set(statement_slot["qualifiers"].keys()) == {"point_in_time"}
    assert len(statement_slot["qualifiers"]["point_in_time"]) == 1
    qualifier = statement_slot["qualifiers"]["point_in_time"][0]
    assert qualifier["id"] == ("https://datadistillery.wikibase.cloud/entity/Q32")
    assert qualifier["data-type"] == "time"
    assert "qualifiers" not in qualifier
    assert "references" not in qualifier

    assert set(statement_slot["references"].keys()) == {"reference_url", "stated_in"}
    reference_url = statement_slot["references"]["reference_url"][0]
    stated_in = statement_slot["references"]["stated_in"][0]
    assert reference_url["id"] == "https://datadistillery.wikibase.cloud/entity/Q29"
    assert reference_url["data-type"] == "url"
    assert "qualifiers" not in reference_url
    assert "references" not in reference_url
    assert stated_in["id"] == "https://datadistillery.wikibase.cloud/entity/Q44"
    assert stated_in["data-type"] == "wikibase-item"
    assert "qualifiers" not in stated_in
    assert "references" not in stated_in


def test_build_packet_omits_qualifiers_references_when_not_specified():
    profile_doc = load_profile("Q4")

    packet = build_curation_packet_from_json_profile(
        profile_entity="Q4",
        json_profile_doc=profile_doc,
    )

    statement_slot = packet["data"]["entities"][0]["statements"]["Q16"]
    assert "qualifiers" not in statement_slot
    assert "references" not in statement_slot


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


def test_build_packet_omits_value_list_key_when_no_route():
    """Statement slots with no value-list route should not emit a value-list key."""
    profile_doc = {
        "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "name_identifier": "Q4",
        "identification": {
            "labels": {"mul": {"prompt": "label"}},
            "descriptions": {"mul": {"prompt": "description"}},
            "aliases": {"mul": {"prompt": "alias"}},
        },
        "statements": [
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q16",
                "name_identifier": "instance_of",
                "value": {"type": "wikibase-item"},
                "qualifiers": [],
                "references": [],
            }
        ],
        "metadata": {"profile_graph": [], "value_list_graph": []},
    }

    packet = build_curation_packet_from_json_profile(
        profile_entity="Q4",
        json_profile_doc=profile_doc,
    )

    slot = packet["data"]["entities"][0]["statements"]["instance_of"]
    assert "value-list" not in slot


def test_build_packet_includes_nested_children_for_q58_modifier_qualifier():
    """A qualifier with Q58 entity class should expand its own qualifiers."""
    profile_doc = {
        "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "name_identifier": "Q4",
        "identification": {
            "labels": {"mul": {"prompt": "label"}},
            "descriptions": {"mul": {"prompt": "description"}},
            "aliases": {"mul": {"prompt": "alias"}},
        },
        "statements": [
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q21",
                "name_identifier": "member_count",
                "value": {"type": "quantity"},
                "qualifiers": [
                    {
                        "entity": "https://datadistillery.wikibase.cloud/entity/Q57",
                        "name_identifier": "units",
                        "entity_classes": ["Q5", "Q58"],
                        "value": {"type": "wikibase-item"},
                        "qualifiers": [
                            {
                                "entity": "https://datadistillery.wikibase.cloud/entity/Q56",
                                "name_identifier": "unit_value",
                                "value": {
                                    "type": "wikibase-item",
                                    "value_list_reference": "cache/queries/Q56.json",
                                },
                                "qualifiers": [],
                                "references": [],
                            }
                        ],
                        "references": [],
                    }
                ],
                "references": [],
            }
        ],
        "metadata": {"profile_graph": [], "value_list_graph": []},
    }

    packet = build_curation_packet_from_json_profile(
        profile_entity="Q4",
        json_profile_doc=profile_doc,
    )

    statement_slot = packet["data"]["entities"][0]["statements"]["member_count"]
    assert "qualifiers" in statement_slot
    units_slot = statement_slot["qualifiers"]["units"][0]
    assert units_slot["id"] == "https://datadistillery.wikibase.cloud/entity/Q57"
    assert "qualifiers" in units_slot
    unit_value_slot = units_slot["qualifiers"]["unit_value"][0]
    assert unit_value_slot["id"] == "https://datadistillery.wikibase.cloud/entity/Q56"
    assert unit_value_slot["value-list"] == "cache/queries/Q56.json"


def test_charge_wikidata_supports_data_entities_packet_schema():
    packet = create_curation_packet("Q4", operation_mode="single")

    class _FakeTemplate:
        def to_dict(self):
            return {
                "id": "Q195562",
                "lastrevid": 123456,
                "labels": {"en": {"language": "en", "value": "Cherokee Nation"}},
                "descriptions": {
                    "en": {
                        "language": "en",
                        "value": "federally recognized Native American tribe",
                    }
                },
                "aliases": {"en": [{"language": "en", "value": "Cherokee"}]},
                "claims": {},
            }

    class _FakeMashClient:
        def load_item(self, qid: str):
            _ = qid
            return _FakeTemplate()

    qid_map = {entity["id"]: "Q195562" for entity in packet["data"]["entities"]}
    charged, notices = charge_packet_from_wikidata_items(
        packet,
        qid_map,
        mash_client=_FakeMashClient(),
    )

    entity_data = charged["data"]["entities"][0]
    assert "labels" in entity_data
    assert entity_data["labels"]["en"]["data-value"] == "Cherokee Nation"
    assert entity_data["aliases"]["en"]["data-value"] == ["Cherokee"]
    assert "conformance_summary" in charged["metadata"]
    assert charged["metadata"]["conformance_summary"]["missing"] >= 1
    assert "metadata_digest" in charged["metadata"]["integrity"]
    assert any(n.code == "statement_missing" for n in notices)


def test_create_and_charge_packet_single_call_api():
    class _FakeTemplate:
        def to_dict(self):
            return {
                "id": "Q195562",
                "lastrevid": 123456,
                "labels": {"en": {"language": "en", "value": "Cherokee Nation"}},
                "descriptions": {},
                "aliases": {},
                "claims": {},
            }

    class _FakeMashClient:
        def load_item(self, qid: str):
            _ = qid
            return _FakeTemplate()

    charged, notices = create_and_charge_curation_packet(
        "Q4",
        qid="Q195562",
        mash_client=_FakeMashClient(),
    )

    assert charged["operation_mode"] == "single"
    assert len(charged["data"]["entities"]) == 1
    assert charged["data"]["entities"][0]["labels"]["en"]["data-value"] == (
        "Cherokee Nation"
    )
    assert any(n.code == "statement_missing" for n in notices)


def test_packet_helpers_resolve_entities_and_primary_profile() -> None:
    packet = create_curation_packet("Q4", operation_mode="bulk")

    entities = packet_entities(packet)
    assert len(entities) == 2

    primary_id = packet_primary_profile_id(packet)
    assert primary_id == "https://datadistillery.wikibase.cloud/entity/Q4"

    by_profile = packet_entity_by_ref(packet, "Q4")
    assert by_profile is not None
    assert by_profile["id"] == "https://datadistillery.wikibase.cloud/entity/Q4"

    by_id = packet_entity_by_ref(
        packet,
        "https://datadistillery.wikibase.cloud/entity/Q39",
    )
    assert by_id is not None
    assert by_id["profile"] == "Q39"


def test_packet_outgoing_links_attach_target_entities() -> None:
    packet = create_curation_packet("Q4", operation_mode="bulk")

    links = packet_outgoing_links(packet, "Q4")

    assert len(links) == 1
    link = links[0]
    assert link["from"] == "Q4"
    assert link["to"] == "Q39"
    assert link["relationship_type"] == "P161"
    assert isinstance(link["target_entity"], dict)
    assert link["target_entity"]["profile"] == "Q39"
