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
    assert packet["metadata"]["source"]["mode"] == "local"
    assert packet["metadata"]["source"]["local_root"].endswith(
        "tests/fixtures/spiritsafe"
    )


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
    assert statement_slot["value-list"] == "Q28"


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
                                    "value_list_id": "Q56",
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
    assert unit_value_slot["value-list"] == "Q56"


def test_charge_wikidata_supports_data_entities_packet_schema():
    packet = create_curation_packet("Q4", operation_mode="single")

    class _FakeMashClient:
        def load_entity_data(self, qid: str) -> dict:
            _ = qid
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

    qid_map = {entity["id"]: "Q195562" for entity in packet["data"]["entities"]}
    charged, notices = charge_packet_from_wikidata_items(
        packet,
        qid_map,
        mash_client=_FakeMashClient(),
    )

    entity_data = charged["data"]["entities"][0]
    assert "entity" in entity_data
    assert entity_data["entity"]["labels"]["en"]["value"] == "Cherokee Nation"
    assert entity_data["entity"]["aliases"]["en"][0]["value"] == "Cherokee"
    assert "metadata_digest" in charged["metadata"]["integrity"]
    assert "conformance" in charged
    assert "entity_profile_map" in charged["conformance"]
    assert "statement_evaluations" in charged["conformance"]


def test_create_and_charge_packet_single_call_api():
    class _FakeMashClient:
        def load_entity_data(self, qid: str) -> dict:
            _ = qid
            return {
                "id": "Q195562",
                "lastrevid": 123456,
                "labels": {"en": {"language": "en", "value": "Cherokee Nation"}},
                "descriptions": {},
                "aliases": {},
                "claims": {},
            }

    charged, notices = create_and_charge_curation_packet(
        "Q4",
        qid="Q195562",
        mash_client=_FakeMashClient(),
    )

    assert charged["operation_mode"] == "edit"
    assert len(charged["data"]["entities"]) == 1
    assert charged["data"]["entities"][0]["entity"]["labels"]["en"]["value"] == (
        "Cherokee Nation"
    )
    assert "conformance" in charged
    assert "entity_profile_map" in charged["conformance"]


def test_charge_wikidata_evaluates_claim_values_per_claim_with_fermenter() -> None:
    packet = {
        "packet_id": "pkt-eval-test",
        "operation_mode": "single",
        "metadata": {
            "primary_profile": {
                "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                "name_identifier": "Q4",
            },
            "profiles": [
                {
                    "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                    "name_identifier": "Q4",
                    "statements": [
                        {
                            "entity": "https://datadistillery.wikibase.cloud/entity/Q16",
                            "name_identifier": "instance_of",
                            "io_map": [{"to": "http://www.wikidata.org/entity/P31"}],
                            "value": {
                                "type": "wikibase-item",
                                "value_list": [{"item": "Q7840353"}],
                            },
                        }
                    ],
                    "metadata": {},
                }
            ],
            "graph": {"nodes": [], "edges": []},
            "mint": {},
            "source": {
                "mode": "local",
                "local_root": str(
                    Path(__file__).resolve().parent / "fixtures" / "spiritsafe"
                ),
            },
            "integrity": {},
        },
        "data": {"entities": []},
    }

    class _FakeMashClient:
        def load_entity_data(self, qid: str) -> dict:
            _ = qid
            return {
                "id": "Q14708404",
                "labels": {},
                "descriptions": {},
                "aliases": {},
                "claims": {
                    "P31": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {
                                        "id": "Q5982983",
                                        "entity-type": "item",
                                    }
                                }
                            }
                        },
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {
                                        "id": "Q7840353",
                                        "entity-type": "item",
                                    }
                                }
                            }
                        },
                    ]
                },
            }

    charged, notices = charge_packet_from_wikidata_items(
        packet,
        {"https://datadistillery.wikibase.cloud/entity/Q4": "Q14708404"},
        mash_client=_FakeMashClient(),
    )

    assert notices == []

    p31_evaluations = [
        evaluation
        for evaluation in charged["conformance"]["statement_evaluations"]
        if evaluation["entity_id"] == "Q14708404"
        and evaluation["statement_uri"]
        == "https://datadistillery.wikibase.cloud/entity/Q16"
    ]
    assert len(p31_evaluations) == 2

    first_eval = next(
        evaluation
        for evaluation in p31_evaluations
        if evaluation["json_path"] == "$.entity.claims.P31[0]"
    )
    assert first_eval["status"] == "nonconformant"
    assert first_eval["gkc_entity_statement"] == {
        "id": "instance_of",
        "uri": "https://datadistillery.wikibase.cloud/entity/Q16",
    }
    assert first_eval["statement_id"] == "instance_of"

    second_eval = next(
        evaluation
        for evaluation in p31_evaluations
        if evaluation["json_path"] == "$.entity.claims.P31[1]"
    )
    assert second_eval["status"] == "conformant"
    assert second_eval["statement_id"] == "instance_of"


def test_charge_wikidata_includes_nested_reference_conformance_records() -> None:
    packet = {
        "packet_id": "pkt-ref-test",
        "operation_mode": "single",
        "metadata": {
            "primary_profile": {
                "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                "name_identifier": "Q4",
            },
            "profiles": [
                {
                    "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                    "name_identifier": "Q4",
                    "statements": [
                        {
                            "entity": "https://datadistillery.wikibase.cloud/entity/Q19",
                            "name_identifier": "official_website",
                            "io_map": [{"to": "http://www.wikidata.org/entity/P856"}],
                            "value": {"type": "url"},
                            "references": [
                                {
                                    "entity": "https://datadistillery.wikibase.cloud/entity/Q29",
                                    "name_identifier": "reference_url",
                                    "io_map": [
                                        {"to": "http://www.wikidata.org/entity/P854"}
                                    ],
                                    "value": {"type": "url"},
                                },
                                {
                                    "entity": "https://datadistillery.wikibase.cloud/entity/Q44",
                                    "name_identifier": "stated_in",
                                    "io_map": [
                                        {"to": "http://www.wikidata.org/entity/P248"}
                                    ],
                                    "value": {"type": "wikibase-item"},
                                },
                            ],
                        }
                    ],
                    "metadata": {},
                }
            ],
            "graph": {"nodes": [], "edges": []},
            "mint": {},
            "source": {},
            "integrity": {},
        },
        "data": {"entities": []},
    }

    class _FakeMashClient:
        def load_entity_data(self, qid: str) -> dict:
            _ = qid
            return {
                "id": "Q14708404",
                "labels": {},
                "descriptions": {},
                "aliases": {},
                "claims": {
                    "P856": [
                        {
                            "mainsnak": {
                                "snaktype": "value",
                                "datavalue": {"value": "https://example.org"},
                            },
                            "references": [
                                {
                                    "snaks": {
                                        "P854": [
                                            {
                                                "snaktype": "value",
                                                "datavalue": {
                                                    "value": "https://example.org/source"
                                                },
                                            }
                                        ]
                                    }
                                }
                            ],
                        }
                    ]
                },
            }

    charged, notices = charge_packet_from_wikidata_items(
        packet,
        {"https://datadistillery.wikibase.cloud/entity/Q4": "Q14708404"},
        mash_client=_FakeMashClient(),
    )

    assert notices == []

    website_eval = next(
        evaluation
        for evaluation in charged["conformance"]["statement_evaluations"]
        if evaluation["statement_uri"]
        == "https://datadistillery.wikibase.cloud/entity/Q19"
    )
    assert website_eval["status"] == "conformant"
    assert website_eval["gkc_entity_statement"] == {
        "id": "official_website",
        "uri": "https://datadistillery.wikibase.cloud/entity/Q19",
    }
    assert website_eval["statement_id"] == "official_website"
    assert len(website_eval["references"]) == 2

    refs_by_id = {
        reference["statement_id"]: reference for reference in website_eval["references"]
    }
    assert refs_by_id["reference_url"]["status"] == "conformant"
    assert refs_by_id["stated_in"]["status"] == "nonconformant"
    assert refs_by_id["stated_in"]["outcome"] == "missing"


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


def test_charge_wikidata_uses_linkage_index_for_linked_profiles() -> None:
    packet = {
        "packet_id": "pkt-test",
        "operation_mode": "single",
        "metadata": {
            "primary_profile": {
                "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                "name_identifier": "Q4",
            },
            "profiles": [
                {
                    "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                    "name_identifier": "Q4",
                    "statements": [
                        {
                            "entity": "https://datadistillery.wikibase.cloud/entity/Q40",
                            "io_map": [{"to": "http://www.wikidata.org/entity/P1313"}],
                            "value": {
                                "type": "wikibase-item",
                                "profile": {
                                    "entity": "https://datadistillery.wikibase.cloud/entity/Q39"
                                },
                            },
                        }
                    ],
                    "metadata": {
                        "linkage_index": {
                            "outbound_by_statement": {
                                "https://datadistillery.wikibase.cloud/entity/Q40": {
                                    "wikidata_properties": ["P1313"],
                                    "target_profiles": [
                                        "https://datadistillery.wikibase.cloud/entity/Q39"
                                    ],
                                }
                            },
                            "inbound_by_wikidata_property": {
                                "P1313": [
                                    {
                                        "source_profile": "https://datadistillery.wikibase.cloud/entity/Q4",
                                        "source_statement": "https://datadistillery.wikibase.cloud/entity/Q40",
                                        "target_profile": "https://datadistillery.wikibase.cloud/entity/Q39",
                                    }
                                ]
                            },
                        }
                    },
                },
                {
                    "id": "https://datadistillery.wikibase.cloud/entity/Q39",
                    "name_identifier": "Q39",
                    "statements": [
                        {
                            "entity": "https://datadistillery.wikibase.cloud/entity/Q50",
                            "io_map": [{"to": "http://www.wikidata.org/entity/P279"}],
                            "value": {"type": "wikibase-item"},
                        }
                    ],
                    "metadata": {
                        "linkage_index": {
                            "outbound_by_statement": {
                                "https://datadistillery.wikibase.cloud/entity/Q50": {
                                    "wikidata_properties": ["P279"],
                                    "target_profiles": [],
                                }
                            },
                            "inbound_by_wikidata_property": {
                                "P279": [
                                    {
                                        "source_profile": "https://datadistillery.wikibase.cloud/entity/Q39",
                                        "source_statement": "https://datadistillery.wikibase.cloud/entity/Q50",
                                    }
                                ]
                            },
                        }
                    },
                },
            ],
            "graph": {"nodes": [], "edges": []},
            "mint": {},
            "integrity": {},
        },
        "data": {"entities": []},
    }

    class _FakeMashClient:
        def load_entity_data(self, qid: str) -> dict:
            if qid == "Q14708404":
                return {
                    "id": "Q14708404",
                    "labels": {"en": {"value": "Cherokee Nation"}},
                    "descriptions": {},
                    "aliases": {},
                    "claims": {
                        "P1313": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {
                                            "id": "Q999001",
                                            "entity-type": "item",
                                        }
                                    }
                                }
                            }
                        ]
                    },
                }
            if qid == "Q999001":
                return {
                    "id": "Q999001",
                    "labels": {"en": {"value": "Principal Chief"}},
                    "descriptions": {},
                    "aliases": {},
                    "claims": {
                        "P279": [
                            {
                                "mainsnak": {
                                    "datavalue": {
                                        "value": {
                                            "id": "Q123",
                                            "entity-type": "item",
                                        }
                                    }
                                }
                            }
                        ]
                    },
                }
            raise AssertionError(f"Unexpected entity lookup: {qid}")

    charged, notices = charge_packet_from_wikidata_items(
        packet,
        {"https://datadistillery.wikibase.cloud/entity/Q4": "Q14708404"},
        mash_client=_FakeMashClient(),
    )

    assert notices == []
    assert [entity["id"] for entity in charged["data"]["entities"]] == [
        "Q14708404",
        "Q999001",
    ]
    assert charged["conformance"]["entity_profile_map"]["Q999001"] == (
        "https://datadistillery.wikibase.cloud/entity/Q39"
    )

    p1313_eval = next(
        evaluation
        for evaluation in charged["conformance"]["statement_evaluations"]
        if evaluation["entity_id"] == "Q14708404"
        and evaluation["json_path"] == "$.entity.claims.P1313[0]"
    )
    assert p1313_eval["status"] == "conformant"
    assert p1313_eval["statement_uri"] == (
        "https://datadistillery.wikibase.cloud/entity/Q40"
    )
