"""Tests for wizard value-list integration helpers and metadata preservation."""

from gkc.profiles.forms.validation_bridge import (
    _merge_wikibase_item_metadata,
    validate_inline_value,
)
from gkc.profiles.forms.wizard.steps import (
    _extract_value_list_candidates,
    _filter_value_list_candidates,
)


def test_extract_value_list_candidates_supports_items_and_bindings() -> None:
    payload = {
        "items": [
            {
                "item": "http://www.wikidata.org/entity/Q42",
                "itemLabel": "Douglas Adams",
            }
        ],
        "results": {
            "bindings": [
                {
                    "item": {"value": "http://www.wikidata.org/entity/Q1"},
                    "itemLabel": {"value": "Universe"},
                }
            ]
        },
    }

    candidates = _extract_value_list_candidates(payload)

    assert len(candidates) == 2
    assert candidates[0]["item"] == "http://www.wikidata.org/entity/Q42"
    assert candidates[0]["itemLabel"] == "Douglas Adams"
    assert candidates[1]["item"] == "http://www.wikidata.org/entity/Q1"
    assert candidates[1]["itemLabel"] == "Universe"


def test_filter_value_list_candidates_matches_label_qid_and_uri() -> None:
    candidates = [
        {
            "item": "http://www.wikidata.org/entity/Q42",
            "itemLabel": "Douglas Adams",
        },
        {
            "item": "http://www.wikidata.org/entity/Q1",
            "itemLabel": "Universe",
        },
    ]

    assert len(_filter_value_list_candidates(candidates, "doug")) == 1
    assert len(_filter_value_list_candidates(candidates, "Q1")) == 1
    assert (
        len(_filter_value_list_candidates(candidates, "wikidata.org/entity/q42")) == 1
    )


def test_merge_wikibase_item_metadata_preserves_uri_and_label() -> None:
    original = {
        "id": "Q42",
        "item": "http://www.wikidata.org/entity/Q42",
        "itemLabel": "Douglas Adams",
    }
    normalized = {
        "entity-type": "item",
        "numeric-id": 42,
        "id": "Q42",
    }

    merged = _merge_wikibase_item_metadata(original, normalized)

    assert merged["id"] == "Q42"
    assert merged["item"] == "http://www.wikidata.org/entity/Q42"
    assert merged["itemLabel"] == "Douglas Adams"


def test_validate_inline_value_keeps_item_metadata() -> None:
    value = {
        "id": "Q42",
        "item": "http://www.wikidata.org/entity/Q42",
        "itemLabel": "Douglas Adams",
    }

    normalized, notices = validate_inline_value(
        datatype="wikibase-item",
        value=value,
        entity_ref="ent-001",
        statement_ref="https://datadistillery.wikibase.cloud/entity/Q16",
    )

    assert not any(n.severity == "error" for n in notices)
    assert normalized["id"] == "Q42"
    assert normalized["item"] == "http://www.wikidata.org/entity/Q42"
    assert normalized["itemLabel"] == "Douglas Adams"
