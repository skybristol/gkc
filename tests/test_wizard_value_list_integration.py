"""Tests for wizard value-list integration helpers and metadata preservation."""

from pathlib import Path

import streamlit as st

import gkc
from gkc.fermenter import validate_inline_value
from gkc.wizard.steps import (
    _coerce_nested_statement_map,
    _extract_value_list_candidates,
    _filter_value_list_candidates,
    _fixed_value_widget_kwargs,
    _initial_fixed_value,
    _materialize_value_list_cache,
    _value_list_widget_kwargs,
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


def test_materialize_value_list_cache_from_local_source(
    monkeypatch, tmp_path: Path
) -> None:
    spirit_safe_root = tmp_path / "SpiritSafe"
    source_file = spirit_safe_root / "cache" / "queries" / "Q28.json"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(
        '{"items": [{"item": "http://www.wikidata.org/entity/Q42", "itemLabel": "Douglas Adams"}]}',
        encoding="utf-8",
    )

    original_source = gkc.get_spirit_safe_source()
    gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

    try:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        local_path, error = _materialize_value_list_cache("cache/queries/Q28.json")

        assert error is None
        assert local_path is not None
        assert local_path.exists()
        assert "Douglas Adams" in local_path.read_text(encoding="utf-8")
    finally:
        gkc.set_spirit_safe_source(
            mode=original_source.mode,
            github_repo=original_source.github_repo,
            github_ref=original_source.github_ref,
            local_root=original_source.local_root,
        )


def test_value_list_widget_kwargs_uses_statement_local_value_list_reference(
    monkeypatch, tmp_path: Path
) -> None:
    spirit_safe_root = tmp_path / "SpiritSafe"
    source_file = spirit_safe_root / "cache" / "queries" / "Q28.json"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(
        '{"items": [{"item": "http://www.wikidata.org/entity/Q1", "itemLabel": "Universe"}]}',
        encoding="utf-8",
    )

    original_source = gkc.get_spirit_safe_source()
    original_session = dict(st.session_state)
    gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

    try:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        st.session_state.clear()
        st.session_state["packet"] = {
            "value_list_routes": {
                "https://datadistillery.wikibase.cloud/entity/Q30": {
                    "cache_path": "cache/queries/Q28.json"
                }
            }
        }
        st.session_state["source_root"] = str(spirit_safe_root)

        widget_kwargs = _value_list_widget_kwargs(
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q30",
                "label": "stated in",
                "value": {
                    "type": "wikibase-item",
                    "value_list_reference": "cache/queries/Q28.json",
                },
            }
        )

        assert widget_kwargs["all_item_options_count"] == 1
        assert (
            widget_kwargs["item_options"][0]["item"]
            == "http://www.wikidata.org/entity/Q1"
        )
        assert widget_kwargs["item_options"][0]["itemLabel"] == "Universe"
    finally:
        st.session_state.clear()
        st.session_state.update(original_session)
        gkc.set_spirit_safe_source(
            mode=original_source.mode,
            github_repo=original_source.github_repo,
            github_ref=original_source.github_ref,
            local_root=original_source.local_root,
        )


def test_value_list_widget_kwargs_does_not_fallback_to_route_only(
    monkeypatch, tmp_path: Path
) -> None:
    spirit_safe_root = tmp_path / "SpiritSafe"
    source_file = spirit_safe_root / "cache" / "queries" / "Q28.json"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text(
        '{"items": [{"item": "http://www.wikidata.org/entity/Q1", "itemLabel": "Universe"}]}',
        encoding="utf-8",
    )

    original_source = gkc.get_spirit_safe_source()
    original_session = dict(st.session_state)
    gkc.set_spirit_safe_source(mode="local", local_root=spirit_safe_root)

    try:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        st.session_state.clear()
        st.session_state["packet"] = {
            "value_list_routes": {
                "https://datadistillery.wikibase.cloud/entity/Q30": {
                    "cache_path": "cache/queries/Q28.json"
                }
            }
        }
        st.session_state["source_root"] = str(spirit_safe_root)

        widget_kwargs = _value_list_widget_kwargs(
            {
                "entity": "https://datadistillery.wikibase.cloud/entity/Q30",
                "label": "stated in",
                "value": {"type": "wikibase-item"},
            }
        )

        assert widget_kwargs == {}
    finally:
        st.session_state.clear()
        st.session_state.update(original_session)
        gkc.set_spirit_safe_source(
            mode=original_source.mode,
            github_repo=original_source.github_repo,
            github_ref=original_source.github_ref,
            local_root=original_source.local_root,
        )


def test_initial_fixed_value_preserves_item_metadata_for_single_value_list() -> None:
    fixed_value = _initial_fixed_value(
        {
            "value": {
                "type": "wikibase-item",
                "value_list": [
                    {
                        "item": "Q7840353",
                        "itemLabel": "federally recognized Native American tribe in the United States",
                    }
                ],
            }
        }
    )

    assert fixed_value == {
        "item": "Q7840353",
        "id": "Q7840353",
        "itemLabel": "federally recognized Native American tribe in the United States",
    }


def test_fixed_value_widget_kwargs_support_inline_item_value_list() -> None:
    widget_kwargs = _fixed_value_widget_kwargs(
        {
            "value": {
                "type": "wikibase-item",
                "value_list": [
                    {
                        "item": "Q7840353",
                        "itemLabel": "federally recognized Native American tribe in the United States",
                    }
                ],
            }
        }
    )

    assert widget_kwargs == {
        "item_options": [
            {
                "item": "Q7840353",
                "itemLabel": "federally recognized Native American tribe in the United States",
            }
        ],
        "all_item_options_count": 1,
    }


def test_coerce_nested_statement_map_from_legacy_reference_list() -> None:
    statement_ref = "https://datadistillery.wikibase.cloud/entity/Q29"

    normalized = _coerce_nested_statement_map(
        [
            {"property": statement_ref, "value": "https://example.org/source"},
            {"property": statement_ref, "value": "https://example.org/backup"},
        ]
    )

    assert list(normalized.keys()) == [statement_ref]
    assert [entry["value"] for entry in normalized[statement_ref]] == [
        "https://example.org/source",
        "https://example.org/backup",
    ]


def test_coerce_nested_statement_map_from_legacy_qualifier_scalar_map() -> None:
    statement_ref = "https://datadistillery.wikibase.cloud/entity/Q27"

    normalized = _coerce_nested_statement_map(
        {
            statement_ref: {
                "id": "Q1860",
                "item": "http://www.wikidata.org/entity/Q1860",
                "itemLabel": "English",
            }
        }
    )

    assert list(normalized.keys()) == [statement_ref]
    assert normalized[statement_ref][0]["value"]["id"] == "Q1860"
