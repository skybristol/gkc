"""Tests for SPARQL-driven Wikibase cache builder."""

from __future__ import annotations

import json

from gkc.wikibase.cache import (
    build_entity_profile_identifiers_sparql_query,
    build_wikibase_cache,
    extract_entity_profile_identifiers,
)


class FakeLoader:
    """Minimal fake loader for deterministic cache build tests."""

    def __init__(self, entities: dict[str, dict]):
        self.entities = entities
        self.calls: list[list[str]] = []

    def load_entities_raw(self, entity_ids: list[str]) -> dict[str, dict]:
        self.calls.append(list(entity_ids))
        return {
            entity_id: self.entities[entity_id]
            for entity_id in entity_ids
            if entity_id in self.entities
        }


def _cache_payload(entity_id: str, entity: dict) -> dict:
    return {
        "entity_id": entity_id,
        "entity": entity,
        "metadata": {
            "source_endpoint": "https://datadistillery.wikibase.cloud/w/api.php",
            "workflow_mode": "cache-builder",
            "profile_entry_ids": [],
            "graph_fetched_at": "2026-03-01T00:00:00Z",
            "cache_exported_at": "2026-03-01T00:00:00Z",
            "extractor": "test",
            "extractor_version": "test",
        },
    }


def test_build_entity_profile_identifiers_sparql_query():
    """Query builder emits the expected traversal clauses and filters."""
    query = build_entity_profile_identifiers_sparql_query(
        wikibase_base_uri="https://datadistillery.wikibase.cloud",
        profile_class_id="Q3",
    )

    assert "SELECT ?s ?p ?o" in query
    assert "?root wdt:P1 wd:Q3" in query
    assert "(wdt:P1|wdt:P2)*" in query
    assert "FILTER(isIRI(?s) && isIRI(?p) && isIRI(?o))" in query
    assert "entity/statement/" in query


def test_extract_entity_profile_identifiers():
    """Parser keeps only local Q/P IDs and de-duplicates deterministically."""
    rows = [
        {
            "s": {"value": "https://datadistillery.wikibase.cloud/entity/Q10"},
            "p": {"value": "https://datadistillery.wikibase.cloud/prop/direct/P1"},
            "o": {"value": "https://datadistillery.wikibase.cloud/entity/Q3"},
        },
        {
            "s": {"value": "https://datadistillery.wikibase.cloud/entity/Q10"},
            "p": {"value": "https://datadistillery.wikibase.cloud/prop/P2"},
            "o": {
                "value": "https://datadistillery.wikibase.cloud/entity/statement/Q10-abc"
            },
        },
        {
            "s": {"value": "https://www.wikidata.org/entity/Q42"},
            "p": {"value": "https://www.wikidata.org/prop/direct/P31"},
            "o": {"value": "https://www.wikidata.org/entity/Q5"},
        },
    ]

    ids = extract_entity_profile_identifiers(rows)

    assert ids == ["P1", "P2", "Q10", "Q3"]


def test_build_wikibase_cache_reconciles_and_writes_summary(tmp_path, monkeypatch):
    """Cache builder upserts current IDs, deletes stale IDs, and reports diffs."""
    base_uri = "https://datadistillery.wikibase.cloud"
    cache_dir = tmp_path / "cache" / "entities"
    refresh_summary = tmp_path / "cache" / "refresh" / "last_run_summary.json"
    cache_dir.mkdir(parents=True, exist_ok=True)

    unchanged_q10 = {"id": "Q10", "type": "item", "labels": {"en": {"value": "A"}}}
    old_q11 = {"id": "Q11", "type": "item", "labels": {"en": {"value": "OLD"}}}
    stale_q99 = {"id": "Q99", "type": "item", "labels": {"en": {"value": "STALE"}}}

    (cache_dir / "Q10.json").write_text(
        json.dumps(_cache_payload("Q10", unchanged_q10), indent=2),
        encoding="utf-8",
    )
    (cache_dir / "Q11.json").write_text(
        json.dumps(_cache_payload("Q11", old_q11), indent=2),
        encoding="utf-8",
    )
    (cache_dir / "Q99.json").write_text(
        json.dumps(_cache_payload("Q99", stale_q99), indent=2),
        encoding="utf-8",
    )

    rows = [
        {
            "s": {"value": f"{base_uri}/entity/Q10"},
            "p": {"value": f"{base_uri}/prop/direct/P1"},
            "o": {"value": f"{base_uri}/entity/Q3"},
        },
        {
            "s": {"value": f"{base_uri}/entity/Q11"},
            "p": {"value": f"{base_uri}/prop/direct/P1"},
            "o": {"value": f"{base_uri}/entity/Q3"},
        },
    ]

    monkeypatch.setattr("gkc.wikibase.cache._run_sparql", lambda endpoint, query: rows)

    loader = FakeLoader(
        {
            "Q10": unchanged_q10,
            "Q11": {
                "id": "Q11",
                "type": "item",
                "labels": {"en": {"value": "UPDATED"}},
            },
            "P1": {
                "id": "P1",
                "type": "property",
                "labels": {"en": {"value": "instance of"}},
            },
            "Q3": {
                "id": "Q3",
                "type": "item",
                "labels": {"en": {"value": "GKC Entity Profile"}},
            },
        }
    )

    result = build_wikibase_cache(
        sparql_endpoint=f"{base_uri}/query/sparql",
        api_url=f"{base_uri}/w/api.php",
        cache_dir=cache_dir,
        wikibase_base_uri=base_uri,
        summary_output=refresh_summary,
        loader=loader,
    )

    assert result.new_ids == ["P1", "Q3"]
    assert result.changed_ids == ["Q11"]
    assert result.unchanged_ids == ["Q10"]
    assert result.deleted_ids == ["Q99"]
    assert result.missing_ids == []
    assert result.written_ids == ["P1", "Q10", "Q11", "Q3"]

    assert (cache_dir / "Q99.json").exists() is False
    assert (cache_dir / "P1.json").exists() is True

    summary = json.loads(refresh_summary.read_text(encoding="utf-8"))
    assert summary["summary"]["new_count"] == 2
    assert summary["summary"]["changed_count"] == 1
    assert summary["summary"]["unchanged_count"] == 1
    assert summary["summary"]["deleted_count"] == 1


def test_build_wikibase_cache_tracks_missing_ids(tmp_path, monkeypatch):
    """IDs discovered in SPARQL but missing from API are surfaced in summary."""
    base_uri = "https://datadistillery.wikibase.cloud"
    cache_dir = tmp_path / "cache" / "entities"
    cache_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        {
            "s": {"value": f"{base_uri}/entity/Q10"},
            "p": {"value": f"{base_uri}/prop/direct/P1"},
            "o": {"value": f"{base_uri}/entity/Q3"},
        }
    ]
    monkeypatch.setattr("gkc.wikibase.cache._run_sparql", lambda endpoint, query: rows)

    loader = FakeLoader(
        {
            "Q10": {"id": "Q10", "type": "item"},
        }
    )

    result = build_wikibase_cache(
        sparql_endpoint=f"{base_uri}/query/sparql",
        api_url=f"{base_uri}/w/api.php",
        cache_dir=cache_dir,
        wikibase_base_uri=base_uri,
        loader=loader,
    )

    assert result.written_ids == ["Q10"]
    assert result.missing_ids == ["P1", "Q3"]
