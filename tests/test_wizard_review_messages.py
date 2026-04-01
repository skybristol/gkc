"""Tests for review-stage wizard messaging semantics."""

from gkc.fermenter import ConformanceNotice
from gkc.profiles.forms.streamlit_app import (
    _collect_review_consequences,
    _conformance_evaluations_for_entity,
    _group_review_items,
    _partition_conformance_evaluations,
)


def test_collect_review_consequences_only_for_empty_statements() -> None:
    statement_missing = "https://datadistillery.wikibase.cloud/entity/Q80"
    statement_present = "https://datadistillery.wikibase.cloud/entity/Q81"

    entity_slot = {
        "id": "ent-001",
        "statements": [
            {
                "entity": statement_missing,
                "label": "native label",
                "messages": {
                    "mul": {
                        "consequences_message": "Missing this can reduce discoverability."
                    }
                },
            },
            {
                "entity": statement_present,
                "label": "headquarters location",
                "messages": {
                    "mul": {
                        "consequences_message": "Missing this can limit map linkage."
                    }
                },
            },
        ],
        "data": {
            "statements": {
                statement_missing: [],
                statement_present: [
                    {"value": "Q60", "qualifiers": {}, "references": []}
                ],
            }
        },
    }

    consequences = _collect_review_consequences(entity_slot)

    assert len(consequences) == 1
    assert statement_missing in consequences
    assert "discoverability" in consequences[statement_missing]


def test_group_review_items_groups_consequences_and_notices() -> None:
    statement_ref = "https://datadistillery.wikibase.cloud/entity/Q19"
    other_ref = "https://datadistillery.wikibase.cloud/entity/Q16"
    entity_slot = {
        "id": "ent-001",
        "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "statements": [
            {
                "entity": statement_ref,
                "label": "official website",
                "messages": {
                    "mul": {
                        "consequences_message": "Missing this weakens external linkage."
                    }
                },
            },
            {
                "entity": other_ref,
                "label": "instance of",
                "messages": {"mul": {"consequences_message": ""}},
            },
        ],
        "data": {
            "statements": {
                statement_ref: [],
                other_ref: [{"value": "Q42", "qualifiers": {}, "references": []}],
            }
        },
    }

    notices = [
        ConformanceNotice(
            severity="error",
            entity_ref="ent-001",
            statement_ref=statement_ref,
            code="datatype_invalid",
            message="Invalid URL datatype",
        ),
        ConformanceNotice(
            severity="warning",
            entity_ref="ent-999",
            statement_ref=statement_ref,
            code="statement_missing",
            message="Different entity warning",
        ),
    ]

    sections, ungrouped = _group_review_items(entity_slot=entity_slot, notices=notices)

    assert len(sections) == 1
    section = sections[0]
    assert section["statement_ref"] == statement_ref
    assert section["label"] == "official website"
    assert "external linkage" in section["consequence"]
    assert len(section["notices"]) == 1
    assert section["notices"][0].code == "datatype_invalid"
    assert len(ungrouped) == 1
    assert ungrouped[0].entity_ref == "ent-999"


def test_conformance_evaluations_for_entity_matches_qid_via_profile_map() -> None:
    entity_slot = {
        "id": "https://datadistillery.wikibase.cloud/entity/Q4",
        "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "statements": [],
        "data": {"statements": {}},
    }
    packet = {
        "conformance": {
            "entity_profile_map": {
                "Q195562": "https://datadistillery.wikibase.cloud/entity/Q4",
                "Q14708404": "https://datadistillery.wikibase.cloud/entity/Q99",
            },
            "statement_evaluations": [
                {
                    "entity_id": "Q195562",
                    "statement_uri": "https://datadistillery.wikibase.cloud/entity/Q19",
                    "status": "conformant",
                    "outcome": "conformant",
                },
                {
                    "entity_id": "Q14708404",
                    "statement_uri": "https://datadistillery.wikibase.cloud/entity/Q19",
                    "status": "nonconformant",
                    "outcome": "to_be_defined",
                },
            ],
        }
    }

    evaluations = _conformance_evaluations_for_entity(
        packet=packet, entity_slot=entity_slot
    )

    assert len(evaluations) == 1
    assert evaluations[0]["entity_id"] == "Q195562"


def test_partition_conformance_evaluations_splits_profile_and_additional() -> None:
    profile_statement = "https://datadistillery.wikibase.cloud/entity/Q19"
    uncovered_statement = "unknown/P856"

    entity_slot = {
        "id": "https://datadistillery.wikibase.cloud/entity/Q4",
        "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "statements": [
            {
                "entity": profile_statement,
                "label": "official website",
            }
        ],
    }

    evaluations = [
        {
            "entity_id": "Q195562",
            "statement_uri": profile_statement,
            "status": "conformant",
            "outcome": "conformant",
        },
        {
            "entity_id": "Q195562",
            "statement_uri": uncovered_statement,
            "status": "nonconformant",
            "outcome": "to_be_defined",
        },
    ]

    profile_aligned, additional = _partition_conformance_evaluations(
        entity_slot=entity_slot,
        evaluations=evaluations,
    )

    assert len(profile_aligned) == 1
    assert profile_aligned[0]["statement_uri"] == profile_statement
    assert len(additional) == 1
    assert additional[0]["statement_uri"] == uncovered_statement
