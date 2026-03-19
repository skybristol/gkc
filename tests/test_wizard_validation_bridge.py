"""Tests for packet wizard validation bridge (Phase B)."""

from pathlib import Path

from gkc.profiles.forms.validation_bridge import (
    validate_entity_packet_data,
    validate_inline_value,
)


def test_validate_inline_value_coerces_wikibase_item_qid() -> None:
    normalized, notices = validate_inline_value(
        datatype="wikibase-item",
        value="Q42",
        entity_ref="ent-001",
        statement_ref="https://datadistillery.wikibase.cloud/entity/Q16",
    )

    assert isinstance(normalized, dict)
    assert normalized["id"] == "Q42"
    assert all(n.severity != "error" for n in notices)


def test_validate_entity_packet_data_reports_datatype_errors() -> None:
    statement_ref = "https://datadistillery.wikibase.cloud/entity/Q16"
    packet = {
        "value_list_routes": {},
        "entities": [
            {
                "id": "ent-001",
                "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
                "statements": [
                    {
                        "entity": statement_ref,
                        "label": "instance of",
                        "value": {"type": "wikibase-item"},
                        "max_count": 1,
                        "qualifiers": [],
                        "references": [],
                    }
                ],
                "data": {
                    "statements": {
                        statement_ref: [
                            {
                                "value": "not-a-qid",
                                "qualifiers": {},
                                "references": [],
                            }
                        ]
                    }
                },
            }
        ],
    }

    notices = validate_entity_packet_data(
        entity_slot=packet["entities"][0],
        packet=packet,
        source_root=None,
    )

    assert any(n.severity == "error" for n in notices)
    assert any(n.code == "datatype_invalid" for n in notices)


def test_validate_entity_packet_data_warns_missing_expected_reference() -> None:
    statement_ref = "https://datadistillery.wikibase.cloud/entity/Q21"
    ref_ref = "https://datadistillery.wikibase.cloud/entity/Q29"
    packet = {
        "value_list_routes": {},
        "entities": [
            {
                "id": "ent-001",
                "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
                "statements": [
                    {
                        "entity": statement_ref,
                        "label": "member count",
                        "value": {"type": "quantity"},
                        "max_count": 1,
                        "qualifiers": [],
                        "references": [
                            {
                                "entity": ref_ref,
                                "label": "reference URL",
                                "value": {"type": "url"},
                            }
                        ],
                    }
                ],
                "data": {
                    "statements": {
                        statement_ref: [
                            {
                                "value": {"amount": "+100", "unit": "1"},
                                "qualifiers": {},
                                "references": [],
                            }
                        ]
                    }
                },
            }
        ],
    }

    notices = validate_entity_packet_data(
        entity_slot=packet["entities"][0],
        packet=packet,
        source_root=Path("/tmp"),
    )

    assert any(
        n.code == "reference_missing" and n.severity == "warning" for n in notices
    )


def test_validate_entity_packet_data_accepts_statement_shaped_nested_entries() -> None:
    statement_ref = "https://datadistillery.wikibase.cloud/entity/Q19"
    qualifier_ref = "https://datadistillery.wikibase.cloud/entity/Q27"
    reference_ref = "https://datadistillery.wikibase.cloud/entity/Q29"

    packet = {
        "value_list_routes": {},
        "entities": [
            {
                "id": "ent-001",
                "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
                "statements": [
                    {
                        "entity": statement_ref,
                        "label": "official website",
                        "value": {"type": "url"},
                        "max_count": 1,
                        "qualifiers": [
                            {
                                "entity": qualifier_ref,
                                "label": "language of work or name",
                                "value": {"type": "wikibase-item"},
                                "max_count": 1,
                            }
                        ],
                        "references": [
                            {
                                "entity": reference_ref,
                                "label": "reference URL",
                                "value": {"type": "url"},
                                "max_count": 1,
                            }
                        ],
                    }
                ],
                "data": {
                    "statements": {
                        statement_ref: [
                            {
                                "value": "https://example.org",
                                "qualifiers": {
                                    qualifier_ref: [
                                        {
                                            "value": {
                                                "id": "Q1860",
                                                "item": "http://www.wikidata.org/entity/Q1860",
                                                "itemLabel": "English",
                                            }
                                        }
                                    ]
                                },
                                "references": {
                                    reference_ref: [
                                        {"value": "https://example.org/source"}
                                    ]
                                },
                            }
                        ]
                    }
                },
            }
        ],
    }

    notices = validate_entity_packet_data(
        entity_slot=packet["entities"][0],
        packet=packet,
        source_root=None,
    )

    assert not any(n.code.endswith("shape_invalid") for n in notices)
    assert not any(n.severity == "error" for n in notices)


def test_validate_entity_packet_data_reports_nested_reference_max_count() -> None:
    statement_ref = "https://datadistillery.wikibase.cloud/entity/Q21"
    reference_ref = "https://datadistillery.wikibase.cloud/entity/Q29"

    packet = {
        "value_list_routes": {},
        "entities": [
            {
                "id": "ent-001",
                "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
                "statements": [
                    {
                        "entity": statement_ref,
                        "label": "member count",
                        "value": {"type": "quantity"},
                        "max_count": 1,
                        "qualifiers": [],
                        "references": [
                            {
                                "entity": reference_ref,
                                "label": "reference URL",
                                "value": {"type": "url"},
                                "max_count": 1,
                            }
                        ],
                    }
                ],
                "data": {
                    "statements": {
                        statement_ref: [
                            {
                                "value": {"amount": "+100", "unit": "1"},
                                "qualifiers": {},
                                "references": {
                                    reference_ref: [
                                        {"value": "https://example.org/1"},
                                        {"value": "https://example.org/2"},
                                    ]
                                },
                            }
                        ]
                    }
                },
            }
        ],
    }

    notices = validate_entity_packet_data(
        entity_slot=packet["entities"][0],
        packet=packet,
        source_root=Path("/tmp"),
    )

    assert any(
        n.code == "reference_max_count_exceeded" and n.severity == "error"
        for n in notices
    )
