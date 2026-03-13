"""Tests for gkc.wikibase.ontology module.

Uses mocked SPARQL responses and mocked WikibaseApiClient to avoid runtime
dependence on a live Wikibase instance.
"""

from __future__ import annotations

import json
import warnings
from unittest.mock import MagicMock, patch

import pytest

from gkc.wikibase.ontology import (
    DDOntologyIndex,
    DDProfileCacheExportResult,
    DDProfileGraph,
    _collect_internal_item_ids,
    build_discovery_sparql_query,
    build_profile_ids_sparql_query,
    export_profile_graph_to_entity_cache,
    fetch_ontology_index,
    fetch_profile_graph,
    fetch_profile_ids,
    get_label_for_language,
    get_monolingualtext_for_language,
    resolve_profile_statement_guidance,
    resolve_statement_guidance,
)

# ===========================================================================
# DDOntologyIndex and fetch_ontology_index
# ===========================================================================


@pytest.fixture
def mock_discovery_rows():
    """Mock SPARQL rows for the discovery union query (items + properties)."""
    return [
        {
            "item": {"value": "https://datadistillery.wikibase.cloud/entity/Q10"},
            "itemLabel": {"value": "Tribal Government US"},
            "class": {"value": "https://datadistillery.wikibase.cloud/entity/Q3"},
            "classLabel": {"value": "GKC Entity Profile"},
        },
        {
            "item": {"value": "https://datadistillery.wikibase.cloud/entity/Q11"},
            "itemLabel": {"value": "Whiskey Distillery"},
            "class": {"value": "https://datadistillery.wikibase.cloud/entity/Q3"},
            "classLabel": {"value": "GKC Entity Profile"},
        },
        {
            "item": {"value": "https://datadistillery.wikibase.cloud/prop/P31"},
            "itemLabel": {"value": "instance of"},
            "class": {"value": "https://datadistillery.wikibase.cloud/entity/Q49"},
            "classLabel": {"value": "GKC Entity Profile Ontology Property"},
        },
    ]


@patch("gkc.wikibase.ontology.SPARQLQuery")
def test_fetch_ontology_index_success(mock_sparql_class, mock_discovery_rows):
    """Test that fetch_ontology_index builds DDOntologyIndex correctly."""
    mock_executor = MagicMock()
    mock_executor.to_dict_list.return_value = mock_discovery_rows
    mock_sparql_class.return_value = mock_executor

    index = fetch_ontology_index(
        sparql_endpoint="https://datadistillery.wikibase.cloud/query/sparql",
    )

    assert isinstance(index, DDOntologyIndex)
    assert "Q10" in index.items
    assert "Q11" in index.items
    assert "P31" in index.properties
    assert index.items["Q10"]["label"] == "Tribal Government US"
    assert index.properties["P31"]["label"] == "instance of"
    assert "GKC Entity Profile" in index.class_index
    assert "Q10" in index.class_index["GKC Entity Profile"]
    assert "Q11" in index.class_index["GKC Entity Profile"]
    assert "GKC Entity Profile Ontology Property" in index.class_index
    assert index.fetched_at


@patch("gkc.wikibase.ontology.SPARQLQuery")
def test_fetch_ontology_index_empty(mock_sparql_class):
    """Test fetch_ontology_index with no SPARQL results."""
    mock_executor = MagicMock()
    mock_executor.to_dict_list.return_value = []
    mock_sparql_class.return_value = mock_executor

    index = fetch_ontology_index(
        sparql_endpoint="https://datadistillery.wikibase.cloud/query/sparql",
    )

    assert isinstance(index, DDOntologyIndex)
    assert index.items == {}
    assert index.properties == {}
    assert index.class_index == {}


def test_dd_ontology_index_get_ids_for_class():
    """Test DDOntologyIndex.get_ids_for_class helper."""
    index = DDOntologyIndex(
        items={
            "Q10": {
                "label": "x",
                "class_id": "Q3",
                "class_label": "GKC Entity Profile",
                "uri": "...",
            }
        },
        class_index={"GKC Entity Profile": ["Q10"]},
    )
    assert index.get_ids_for_class("GKC Entity Profile") == ["Q10"]
    assert index.get_ids_for_class("Unknown Class") == []


def test_dd_ontology_index_frozen():
    """DDOntologyIndex is frozen."""
    index = DDOntologyIndex()
    with pytest.raises((AttributeError, TypeError)):
        index.items = {}  # type: ignore[misc]


# ===========================================================================
# fetch_profile_ids
# ===========================================================================


@patch("gkc.wikibase.ontology.SPARQLQuery")
def test_fetch_profile_ids_success(mock_sparql_class):
    """Test that fetch_profile_ids returns bare QIDs."""
    mock_executor = MagicMock()
    mock_executor.to_dict_list.return_value = [
        {"profile": {"value": "https://datadistillery.wikibase.cloud/entity/Q10"}},
        {"profile": {"value": "https://datadistillery.wikibase.cloud/entity/Q11"}},
    ]
    mock_sparql_class.return_value = mock_executor

    ids = fetch_profile_ids(
        sparql_endpoint="https://datadistillery.wikibase.cloud/query/sparql",
    )

    assert ids == ["Q10", "Q11"]


@patch("gkc.wikibase.ontology.SPARQLQuery")
def test_fetch_profile_ids_empty(mock_sparql_class):
    """Test fetch_profile_ids with no results."""
    mock_executor = MagicMock()
    mock_executor.to_dict_list.return_value = []
    mock_sparql_class.return_value = mock_executor

    ids = fetch_profile_ids(
        sparql_endpoint="https://datadistillery.wikibase.cloud/query/sparql",
    )
    assert ids == []


def test_build_profile_ids_sparql_query():
    """Test build_profile_ids_sparql_query structure."""
    query = build_profile_ids_sparql_query(
        wikibase_base_uri="https://datadistillery.wikibase.cloud",
        profile_class_id="Q3",
    )
    assert "SELECT ?profile" in query
    assert "wd:Q3" in query
    assert "wdt:P1" in query


def test_build_discovery_sparql_query():
    """Test build_discovery_sparql_query structure."""
    query = build_discovery_sparql_query(
        wikibase_base_uri="https://datadistillery.wikibase.cloud",
    )
    assert "SELECT ?item ?itemLabel ?class ?classLabel" in query
    assert "wdt:P2*" in query
    assert "UNION" in query
    assert "wikibase:directClaim" in query


# ===========================================================================
# _collect_internal_item_ids
# ===========================================================================


def test_collect_internal_item_ids_from_mainsnak():
    """Items in main snak wikibase-entityid values are collected."""
    item_json = {
        "claims": {
            "P157": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P157",
                        "datavalue": {
                            "value": {"entity-type": "item", "id": "Q200"},
                            "type": "wikibase-entityid",
                        },
                    },
                    "qualifiers": {},
                    "rank": "normal",
                }
            ]
        }
    }
    found = _collect_internal_item_ids(item_json)
    assert "Q200" in found


def test_collect_internal_item_ids_from_qualifiers():
    """Items in qualifier snaks are also collected."""
    item_json = {
        "claims": {
            "P157": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P157",
                        "datavalue": {
                            "value": {"entity-type": "item", "id": "Q200"},
                            "type": "wikibase-entityid",
                        },
                    },
                    "qualifiers": {
                        "P161": [
                            {
                                "snaktype": "value",
                                "property": "P161",
                                "datavalue": {
                                    "value": {"entity-type": "item", "id": "Q300"},
                                    "type": "wikibase-entityid",
                                },
                            }
                        ]
                    },
                    "rank": "normal",
                }
            ]
        }
    }
    found = _collect_internal_item_ids(item_json)
    assert "Q200" in found
    assert "Q300" in found


def test_collect_internal_item_ids_skips_non_entityid():
    """Non wikibase-entityid datavalue types are not collected."""
    item_json = {
        "claims": {
            "P5": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P5",
                        "datavalue": {
                            "value": "P17",
                            "type": "string",
                        },
                    },
                    "qualifiers": {},
                    "rank": "normal",
                }
            ]
        }
    }
    found = _collect_internal_item_ids(item_json)
    assert found == set()


def test_collect_internal_item_ids_empty_claims():
    """Empty claims dict returns empty set."""
    assert _collect_internal_item_ids({}) == set()
    assert _collect_internal_item_ids({"claims": {}}) == set()


# ===========================================================================
# fetch_profile_graph
# ===========================================================================


def _make_item_json(qid: str, linked_qids: list[str] | None = None) -> dict:
    """Build minimal item JSON with optional wikibase-entityid claims."""
    claims = {}
    if linked_qids:
        claims["P157"] = [
            {
                "mainsnak": {
                    "snaktype": "value",
                    "property": "P157",
                    "datavalue": {
                        "value": {"entity-type": "item", "id": linked},
                        "type": "wikibase-entityid",
                    },
                },
                "qualifiers": {},
                "rank": "normal",
            }
            for linked in linked_qids
        ]
    return {
        "type": "item",
        "id": qid,
        "labels": {"en": {"language": "en", "value": f"Item {qid}"}},
        "claims": claims,
    }


def test_fetch_profile_graph_single_profile_no_links():
    """Graph fetch with a profile that has no internal links stops after one hop."""
    mock_client = MagicMock()
    mock_client.get_entities.return_value = {
        "Q10": _make_item_json("Q10"),
    }

    graph = fetch_profile_graph(["Q10"], mock_client)

    assert isinstance(graph, DDProfileGraph)
    assert "Q10" in graph.raw_items
    assert graph.profile_ids == ["Q10"]
    assert graph.traversal_log == []
    assert mock_client.get_entities.call_count == 1


def test_fetch_profile_graph_follows_internal_links():
    """Graph traversal follows wikibase-entityid links to linked items."""
    mock_client = MagicMock()

    def get_entities_side_effect(ids: list[str]) -> dict:
        results = {}
        for eid in ids:
            if eid == "Q10":
                results[eid] = _make_item_json("Q10", linked_qids=["Q50"])
            elif eid == "Q50":
                results[eid] = _make_item_json("Q50")
        return results

    mock_client.get_entities.side_effect = get_entities_side_effect

    graph = fetch_profile_graph(["Q10"], mock_client)

    assert "Q10" in graph.raw_items
    assert "Q50" in graph.raw_items
    assert mock_client.get_entities.call_count == 2


def test_fetch_profile_graph_missing_items_logged():
    """Items requested but not returned by wbgetentities are logged."""
    mock_client = MagicMock()
    mock_client.get_entities.return_value = {}  # nothing returned

    graph = fetch_profile_graph(["Q10"], mock_client)

    assert "Q10" not in graph.raw_items
    assert any("missing" in entry and "Q10" in entry for entry in graph.traversal_log)


def test_fetch_profile_graph_empty_profile_ids():
    """Empty profile list returns empty graph immediately."""
    mock_client = MagicMock()
    graph = fetch_profile_graph([], mock_client)
    assert graph.raw_items == {}
    assert graph.traversal_log == []
    mock_client.get_entities.assert_not_called()


def test_fetch_profile_graph_respects_max_hops():
    """Traversal stops at max_hops and logs the truncation."""
    mock_client = MagicMock()

    # Infinite loop: each item links to the next
    call_count = [0]

    def get_entities_side_effect(ids: list[str]) -> dict:
        call_count[0] += 1
        results = {}
        for eid in ids:
            next_id = f"Q{int(eid[1:]) + 1}"
            results[eid] = _make_item_json(eid, linked_qids=[next_id])
        return results

    mock_client.get_entities.side_effect = get_entities_side_effect

    graph = fetch_profile_graph(["Q1"], mock_client, max_hops=3)

    assert call_count[0] <= 3
    assert any("hop limit" in entry for entry in graph.traversal_log)


def test_fetch_profile_graph_language_warning():
    """Language warning is emitted and logged if configured language is absent."""
    mock_client = MagicMock()
    item_json = {
        "type": "item",
        "id": "Q10",
        "labels": {"es": {"language": "es", "value": "Gobierno Tribal"}},
        "claims": {},
    }
    mock_client.get_entities.return_value = {"Q10": item_json}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        graph = fetch_profile_graph(["Q10"], mock_client, default_language="en")

    assert any("Default language" in str(w.message) for w in caught)
    assert any("language_fallback" in entry for entry in graph.traversal_log)


def test_fetch_profile_graph_no_warning_for_mul():
    """No language warning is emitted when default_language is 'mul'."""
    mock_client = MagicMock()
    item_json = {
        "type": "item",
        "id": "Q10",
        "labels": {"es": {"language": "es", "value": "Gobierno Tribal"}},
        "claims": {},
    }
    mock_client.get_entities.return_value = {"Q10": item_json}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fetch_profile_graph(["Q10"], mock_client, default_language="mul")

    assert not any("Default language" in str(w.message) for w in caught)


# ===========================================================================
# Language and text resolution
# ===========================================================================


def test_get_label_for_language_found():
    """Returns label for requested language."""
    item_json = {
        "labels": {
            "en": {"language": "en", "value": "Tribal Government"},
            "mul": {"language": "mul", "value": "Tribal Government"},
        }
    }
    result = get_label_for_language(item_json, "en")
    assert result == "Tribal Government"


def test_get_label_for_language_fallback_to_mul():
    """Falls back to mul when requested language is absent."""
    item_json = {
        "labels": {
            "mul": {"language": "mul", "value": "Tribal Government MUL"},
        }
    }
    result = get_label_for_language(item_json, "es", default_language="mul")
    assert result == "Tribal Government MUL"


def test_get_label_for_language_any_available():
    """Returns any available language when neither requested nor default found."""
    item_json = {
        "labels": {
            "de": {"language": "de", "value": "Stammes Regierung"},
        }
    }
    result = get_label_for_language(item_json, "es", default_language="mul")
    assert result == "Stammes Regierung"


def test_get_label_for_language_empty():
    """Returns None for empty labels."""
    assert get_label_for_language({}, "en") is None
    assert get_label_for_language({"labels": {}}, "en") is None


def test_get_monolingualtext_for_language_found():
    """Returns text for the requested language from monolingualtext claims."""
    claims = [
        {
            "mainsnak": {
                "datavalue": {
                    "value": {"text": "Enter a label", "language": "en"},
                    "type": "monolingualtext",
                }
            }
        },
        {
            "mainsnak": {
                "datavalue": {
                    "value": {"text": "Ingrese una etiqueta", "language": "es"},
                    "type": "monolingualtext",
                }
            }
        },
    ]
    assert get_monolingualtext_for_language(claims, "en") == "Enter a label"
    assert get_monolingualtext_for_language(claims, "es") == "Ingrese una etiqueta"


def test_get_monolingualtext_for_language_fallback_to_mul():
    """Falls back to mul when requested language is absent."""
    claims = [
        {
            "mainsnak": {
                "datavalue": {
                    "value": {"text": "Enter a label", "language": "mul"},
                    "type": "monolingualtext",
                }
            }
        }
    ]
    result = get_monolingualtext_for_language(claims, "de", default_language="mul")
    assert result == "Enter a label"


def test_get_monolingualtext_for_language_empty():
    """Returns None for empty claim list."""
    assert get_monolingualtext_for_language([], "en") is None


def test_get_monolingualtext_skips_non_monolingualtext():
    """Non-monolingualtext claims are skipped."""
    claims = [
        {
            "mainsnak": {
                "datavalue": {
                    "value": "P17",
                    "type": "string",
                }
            }
        }
    ]
    assert get_monolingualtext_for_language(claims, "en") is None


# ===========================================================================
# resolve_statement_guidance
# ===========================================================================


def _make_graph_with_items(item_map: dict) -> DDProfileGraph:
    graph = DDProfileGraph(profile_ids=["Q10"])
    graph.raw_items.update(item_map)
    return graph


def _mono_claim(text: str, lang: str) -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": {"text": text, "language": lang},
                "type": "monolingualtext",
            }
        }
    }


def test_resolve_statement_guidance_from_statement_item():
    """Returns guidance from statement item when present."""
    statement_item = {"claims": {"P169": [_mono_claim("Provide a value", "mul")]}}
    graph = _make_graph_with_items({"Q50": statement_item})
    result = resolve_statement_guidance(graph, "Q50", "P169", language="mul")
    assert result == "Provide a value"


def test_resolve_statement_guidance_fallback_to_primitive():
    """Falls back to primitive item when statement item has no matching guidance."""
    statement_item = {"claims": {}}
    primitive_item = {
        "claims": {"P169": [_mono_claim("Default guidance from primitive", "mul")]}
    }
    graph = _make_graph_with_items({"Q50": statement_item, "Q99": primitive_item})
    result = resolve_statement_guidance(
        graph, "Q50", "P169", language="mul", primitive_item_id="Q99"
    )
    assert result == "Default guidance from primitive"


def test_resolve_statement_guidance_returns_none_when_not_found():
    """Returns None when guidance is absent from all levels."""
    graph = _make_graph_with_items({"Q50": {"claims": {}}})
    result = resolve_statement_guidance(graph, "Q50", "P169")
    assert result is None


def test_resolve_statement_guidance_missing_items_returns_none():
    """Returns None gracefully when item IDs are not in the graph."""
    graph = _make_graph_with_items({})
    result = resolve_statement_guidance(graph, "Q50", "P169", primitive_item_id="Q99")
    assert result is None


def _p157_claim_for_statement(
    statement_item_id: str,
    qualifier_pid: str,
    text: str,
    language: str = "mul",
) -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": {"entity-type": "item", "id": statement_item_id},
                "type": "wikibase-entityid",
            }
        },
        "qualifiers": {
            qualifier_pid: [
                {
                    "datavalue": {
                        "value": {"text": text, "language": language},
                        "type": "monolingualtext",
                    }
                }
            ]
        },
    }


def test_resolve_profile_statement_guidance_prefers_profile_qualifier():
    profile_item = {
        "claims": {
            "P157": [
                _p157_claim_for_statement(
                    statement_item_id="Q50",
                    qualifier_pid="P171",
                    text="Qualifier prompt",
                    language="mul",
                )
            ]
        }
    }
    statement_item = {"claims": {"P171": [_mono_claim("Statement prompt", "mul")]}}
    graph = _make_graph_with_items({"Q10": profile_item, "Q50": statement_item})

    result = resolve_profile_statement_guidance(
        graph=graph,
        profile_item_id="Q10",
        statement_item_id="Q50",
        guidance_prop_id="P171",
        language="mul",
    )
    assert result == "Qualifier prompt"


def test_resolve_profile_statement_guidance_falls_back_to_statement_item():
    profile_item = {
        "claims": {
            "P157": [
                {
                    "mainsnak": {
                        "datavalue": {
                            "value": {"entity-type": "item", "id": "Q50"},
                            "type": "wikibase-entityid",
                        }
                    },
                    "qualifiers": {},
                }
            ]
        }
    }
    statement_item = {
        "claims": {"P170": [_mono_claim("Statement consequences", "mul")]}
    }
    graph = _make_graph_with_items({"Q10": profile_item, "Q50": statement_item})

    result = resolve_profile_statement_guidance(
        graph=graph,
        profile_item_id="Q10",
        statement_item_id="Q50",
        guidance_prop_id="P170",
        language="mul",
    )
    assert result == "Statement consequences"


def test_resolve_profile_statement_guidance_falls_back_to_primitive_item():
    profile_item = {
        "claims": {
            "P157": [
                {
                    "mainsnak": {
                        "datavalue": {
                            "value": {"entity-type": "item", "id": "Q50"},
                            "type": "wikibase-entityid",
                        }
                    },
                    "qualifiers": {},
                }
            ]
        }
    }
    statement_item = {"claims": {}}
    primitive_item = {"claims": {"P168": [_mono_claim("Template error text", "mul")]}}
    graph = _make_graph_with_items(
        {"Q10": profile_item, "Q50": statement_item, "Q99": primitive_item}
    )

    result = resolve_profile_statement_guidance(
        graph=graph,
        profile_item_id="Q10",
        statement_item_id="Q50",
        guidance_prop_id="P168",
        primitive_item_id="Q99",
        language="mul",
    )
    assert result == "Template error text"


def test_export_profile_graph_to_entity_cache_writes_entity_files(tmp_path):
    """Export writes one deterministic cache file per fetched entity ID."""
    mock_client = MagicMock()

    def get_entities_side_effect(ids: list[str]) -> dict:
        results = {}
        for eid in ids:
            if eid == "Q10":
                results[eid] = _make_item_json("Q10", linked_qids=["Q50"])
            elif eid == "Q50":
                results[eid] = _make_item_json("Q50")
        return results

    mock_client.api_url = "https://datadistillery.wikibase.cloud/w/api.php"
    mock_client.get_entities.side_effect = get_entities_side_effect

    out_dir = tmp_path / "entity-cache"
    result = export_profile_graph_to_entity_cache(
        profile_ids=["Q10"],
        api_client=mock_client,
        cache_dir=out_dir,
        source_endpoint="https://datadistillery.wikibase.cloud/query/sparql",
        workflow_mode="profile-entry",
    )

    assert isinstance(result, DDProfileCacheExportResult)
    assert result.written_ids == ["Q10", "Q50"]
    assert result.skipped_ids == []

    q10_file = out_dir / "Q10.json"
    q50_file = out_dir / "Q50.json"
    assert q10_file.exists()
    assert q50_file.exists()

    q10_payload = json.loads(q10_file.read_text(encoding="utf-8"))
    assert q10_payload["entity_id"] == "Q10"
    assert q10_payload["metadata"]["workflow_mode"] == "profile-entry"
    assert (
        q10_payload["metadata"]["source_endpoint"]
        == "https://datadistillery.wikibase.cloud/query/sparql"
    )
    assert "extractor_version" in q10_payload["metadata"]
    assert "source_branch" in q10_payload["metadata"]
    assert "source_commit" in q10_payload["metadata"]


def test_export_profile_graph_to_entity_cache_honors_ignore_ids(tmp_path):
    """Export skips IDs in ignore list and does not write files for them."""
    mock_client = MagicMock()
    mock_client.api_url = "https://datadistillery.wikibase.cloud/w/api.php"
    mock_client.get_entities.return_value = {
        "Q10": _make_item_json("Q10"),
        "Q1": _make_item_json("Q1"),
    }

    out_dir = tmp_path / "entity-cache"
    result = export_profile_graph_to_entity_cache(
        profile_ids=["Q10", "Q1"],
        api_client=mock_client,
        cache_dir=out_dir,
        ignore_ids={"Q1"},
    )

    assert result.written_ids == ["Q10"]
    assert result.skipped_ids == ["Q1"]
    assert (out_dir / "Q10.json").exists()
    assert not (out_dir / "Q1.json").exists()
