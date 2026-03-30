"""Tests for wizard adaptation to packet-native still_charger structures."""

from gkc.profiles.forms.streamlit_app import (
    _adapt_packet_to_wizard_view,
    _qid_map_for_primary_entity,
)


def test_adapt_packet_to_wizard_view_maps_slot_values_and_filters_statements() -> None:
    statement_q16 = "https://datadistillery.wikibase.cloud/entity/Q16"
    statement_q19 = "https://datadistillery.wikibase.cloud/entity/Q19"

    packet = {
        "packet_id": "pkt-test",
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
                            "entity": statement_q16,
                            "label": "instance of",
                        },
                        {
                            "entity": statement_q19,
                            "label": "official website",
                        },
                    ],
                }
            ],
        },
        "data": {
            "entities": [
                {
                    "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                    "profile": "Q4",
                    "labels": {"mul": {"data-value": "Cherokee Nation"}},
                    "descriptions": {
                        "mul": {"data-value": "federally recognized tribe"}
                    },
                    "aliases": {"mul": {"data-value": ["Cherokee"]}},
                    "statements": {
                        "Q16": {"id": statement_q16, "data-value": {"id": "Q7840353"}},
                        "Q19": {
                            "id": statement_q19,
                            "data-value": "https://www.cherokee.org",
                        },
                        "Q999": {
                            "id": "https://datadistillery.wikibase.cloud/entity/Q999",
                            "data-value": "should not render",
                        },
                    },
                }
            ]
        },
    }

    adapted = _adapt_packet_to_wizard_view(packet)

    assert "entities" in adapted
    assert len(adapted["entities"]) == 1

    entity_slot = adapted["entities"][0]
    assert (
        entity_slot["profile_entity"]
        == "https://datadistillery.wikibase.cloud/entity/Q4"
    )
    assert entity_slot["data"]["labels"]["mul"] == "Cherokee Nation"
    assert entity_slot["data"]["aliases"]["mul"] == ["Cherokee"]

    assert set(entity_slot["data"]["statements"].keys()) == {
        statement_q16,
        statement_q19,
    }
    assert entity_slot["data"]["statements"][statement_q16][0]["value"] == {
        "id": "Q7840353"
    }
    assert (
        entity_slot["data"]["statements"][statement_q19][0]["value"]
        == "https://www.cherokee.org"
    )


def test_qid_map_for_primary_entity_includes_primary_identifiers() -> None:
    packet = {
        "metadata": {
            "primary_profile": {
                "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                "name_identifier": "Q4",
            }
        },
        "data": {
            "entities": [
                {
                    "id": "https://datadistillery.wikibase.cloud/entity/Q4",
                    "profile": "Q4",
                }
            ]
        },
    }

    qid_map = _qid_map_for_primary_entity(packet, "Q195562")

    assert qid_map["https://datadistillery.wikibase.cloud/entity/Q4"] == "Q195562"
    assert qid_map["Q4"] == "Q195562"
