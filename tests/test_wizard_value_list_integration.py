"""Tests for wizard value-list integration helpers and metadata preservation."""

from pathlib import Path

import streamlit as st

import gkc
from gkc.profiles.forms.validation_bridge import (
    _merge_wikibase_item_metadata,
    validate_inline_value,
)
from gkc.profiles.forms.wizard.steps import (
    _extract_value_list_candidates,
    _filter_value_list_candidates,
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


def test_value_list_widget_kwargs_uses_packet_route_for_nested_statement(
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
