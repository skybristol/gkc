"""Tests for value-list query export and hydration workflows."""

import json

import gkc


def _claim_entity_id(entity_id: str) -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": {
                    "id": entity_id,
                }
            }
        }
    }


def test_hydrate_value_lists_from_cache_writes_query_and_cache(monkeypatch, tmp_path):
    cache_entities_dir = tmp_path / "cache" / "entities"
    queries_dir = tmp_path / "queries"
    cache_queries_dir = tmp_path / "cache" / "queries"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    (cache_entities_dir / "Q4.json").write_text(
        json.dumps(
            {
                "entity_id": "Q4",
                "entity": {
                    "claims": {
                        "P1": [_claim_entity_id("Q7")],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "gkc.spirit_safe.fetch_mediawiki_page_wikitext",
        lambda api_client, title: (
            "<sparql>SELECT ?item ?itemLabel ?domain WHERE { ?item ?p ?o }</sparql>"
            "<sparql>SELECT ?ignored WHERE { ?ignored ?p ?o }</sparql>"
        ),
    )

    monkeypatch.setattr(
        "gkc.spirit_safe.paginate_query",
        lambda **kwargs: [
            {
                "item": "http://www.wikidata.org/entity/Q2",
                "itemLabel": "Beta",
                "domain": "de.wikipedia.org",
            },
            {
                "item": "http://www.wikidata.org/entity/Q1",
                "itemLabel": "Alpha",
                "domain": "en.wikipedia.org",
            },
            {
                "item": "http://www.wikidata.org/entity/Q1",
                "itemLabel": "Alpha",
                "domain": "en.wikipedia.org",
            },
        ],
    )

    result = gkc.hydrate_value_lists_from_cache(
        cache_entities_dir=cache_entities_dir,
        queries_dir=queries_dir,
        cache_queries_dir=cache_queries_dir,
        api_url="https://datadistillery.wikibase.cloud/w/api.php",
        endpoint="https://datadistillery.wikibase.cloud/query/sparql",
        fail_on_hydration_error=True,
    )

    assert result.discovered_ids == ["Q4"]
    assert result.hydrated_ids == ["Q4"]
    assert result.failures == []

    query_file = queries_dir / "Q4.sparql"
    assert query_file.exists()
    assert "?item ?itemLabel" in query_file.read_text(encoding="utf-8")
    assert "?ignored" not in query_file.read_text(encoding="utf-8")

    cache_file = cache_queries_dir / "Q4.json"
    assert cache_file.exists()
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    assert payload["metadata"]["query"] == "queries/Q4.sparql"
    assert payload["metadata"]["source"].endswith("/wiki/Item_talk:Q4")
    assert payload["metadata"]["count"] == 2
    assert payload["metadata"]["columns"] == ["domain", "item", "itemLabel"]
    assert payload["items"] == [
        {
            "domain": "en.wikipedia.org",
            "item": "http://www.wikidata.org/entity/Q1",
            "itemLabel": "Alpha",
        },
        {
            "domain": "de.wikipedia.org",
            "item": "http://www.wikidata.org/entity/Q2",
            "itemLabel": "Beta",
        },
    ]


def test_hydrate_value_lists_keeps_existing_cache_on_failure(monkeypatch, tmp_path):
    cache_entities_dir = tmp_path / "cache" / "entities"
    queries_dir = tmp_path / "queries"
    cache_queries_dir = tmp_path / "cache" / "queries"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)
    cache_queries_dir.mkdir(parents=True, exist_ok=True)

    (cache_entities_dir / "Q4.json").write_text(
        json.dumps(
            {
                "entity_id": "Q4",
                "entity": {
                    "claims": {
                        "P1": [_claim_entity_id("Q7")],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    existing_payload = {
        "metadata": {"entity": "https://datadistillery.wikibase.cloud/entity/Q4"},
        "items": [{"item": "http://www.wikidata.org/entity/Q999", "itemLabel": "Old"}],
    }
    (cache_queries_dir / "Q4.json").write_text(
        json.dumps(existing_payload, indent=2),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "gkc.spirit_safe.fetch_mediawiki_page_wikitext",
        lambda api_client, title: "<sparql>SELECT ?item ?itemLabel WHERE { ?item ?p ?o }</sparql>",
    )
    monkeypatch.setattr(
        "gkc.spirit_safe.paginate_query",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("Query failed")),
    )

    result = gkc.hydrate_value_lists_from_cache(
        cache_entities_dir=cache_entities_dir,
        queries_dir=queries_dir,
        cache_queries_dir=cache_queries_dir,
        api_url="https://datadistillery.wikibase.cloud/w/api.php",
        endpoint="https://datadistillery.wikibase.cloud/query/sparql",
        fail_on_hydration_error=False,
    )

    assert result.discovered_ids == ["Q4"]
    assert result.hydrated_ids == []
    assert len(result.failures) == 1

    payload = json.loads((cache_queries_dir / "Q4.json").read_text(encoding="utf-8"))
    assert payload == existing_payload


def test_hydrate_value_lists_fails_on_duplicate_non_core_conflict(
    monkeypatch, tmp_path
):
    cache_entities_dir = tmp_path / "cache" / "entities"
    queries_dir = tmp_path / "queries"
    cache_queries_dir = tmp_path / "cache" / "queries"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)
    cache_queries_dir.mkdir(parents=True, exist_ok=True)

    (cache_entities_dir / "Q4.json").write_text(
        json.dumps(
            {
                "entity_id": "Q4",
                "entity": {
                    "claims": {
                        "P1": [_claim_entity_id("Q7")],
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    existing_payload = {
        "metadata": {
            "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
            "query": "queries/Q4.sparql",
        },
        "items": [{"item": "http://www.wikidata.org/entity/Q999", "itemLabel": "Old"}],
    }
    (cache_queries_dir / "Q4.json").write_text(
        json.dumps(existing_payload, indent=2),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "gkc.spirit_safe.fetch_mediawiki_page_wikitext",
        lambda api_client, title: "<sparql>SELECT ?item ?itemLabel ?domain WHERE { ?item ?p ?o }</sparql>",
    )
    monkeypatch.setattr(
        "gkc.spirit_safe.paginate_query",
        lambda **kwargs: [
            {
                "item": "http://www.wikidata.org/entity/Q1",
                "itemLabel": "Alpha",
                "domain": "en.wikipedia.org",
            },
            {
                "item": "http://www.wikidata.org/entity/Q1",
                "itemLabel": "Alpha",
                "domain": "fr.wikipedia.org",
            },
        ],
    )

    result = gkc.hydrate_value_lists_from_cache(
        cache_entities_dir=cache_entities_dir,
        queries_dir=queries_dir,
        cache_queries_dir=cache_queries_dir,
        api_url="https://datadistillery.wikibase.cloud/w/api.php",
        endpoint="https://datadistillery.wikibase.cloud/query/sparql",
        fail_on_hydration_error=False,
    )

    assert result.discovered_ids == ["Q4"]
    assert result.hydrated_ids == []
    assert len(result.failures) == 1
    assert "Duplicate value-list row conflict" in result.failures[0]["error"]

    payload = json.loads((cache_queries_dir / "Q4.json").read_text(encoding="utf-8"))
    assert payload == existing_payload
