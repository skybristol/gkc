"""Tests for the Mash module."""

import json

import pytest

import gkc
from gkc.mash import (
    ClaimSummary,
    WikibaseEntitySchemaTemplate,
    WikibaseItemTemplate,
    WikibaseLoader,
    WikibasePropertyTemplate,
    WikibaseRecentChangesResult,
    WikipediaLoader,
    WikipediaTemplate,
    apply_item_property_filters,
    apply_template_language_filter,
    extract_first_sparql_block,
    extract_sparql_blocks,
    fetch_mediawiki_page_wikitext,
    fetch_recent_entity_changes,
    get_latest_cache_timestamp,
    refresh_entity_cache_from_recentchanges,
    strip_entity_identifiers,
)


def test_language_configuration_getter():
    """Test getting the language configuration."""
    languages = gkc.get_languages()
    assert languages == "en"


def test_language_configuration_setter():
    """Test setting the language configuration."""
    gkc.set_languages("fr")
    assert gkc.get_languages() == "fr"

    # Test with list
    gkc.set_languages(["en", "es"])
    assert gkc.get_languages() == ["en", "es"]

    # Test with "all"
    gkc.set_languages("all")
    assert gkc.get_languages() == "all"

    # Reset for other tests
    gkc.set_languages("en")


def test_wikidata_template_summary():
    """Test the summary method returns expected fields."""
    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Life, the Universe, and Everything"},
        descriptions={"en": "Answer to everything"},
        aliases={"en": ["42", "The Answer"]},
        claims=[
            ClaimSummary(
                property_id="P31", value="Q36253", qualifiers=[], references=[]
            ),
        ],
        entity_data={"id": "Q42", "labels": {}, "descriptions": {}, "claims": {}},
    )

    summary = template.summary()
    assert summary["qid"] == "Q42"
    assert summary["labels"] == {"en": "Life, the Universe, and Everything"}
    assert summary["descriptions"] == {"en": "Answer to everything"}
    assert summary["total_statements"] == 1


def test_wikidata_template_filter_properties():
    """Test filtering properties from template."""
    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
            ClaimSummary(
                property_id="P21", value="Q6581097", qualifiers=[], references=[]
            ),
        ],
        entity_data={
            "id": "Q42",
            "claims": {"P31": [{"mainsnak": {}}], "P21": [{"mainsnak": {}}]},
        },
    )

    apply_item_property_filters(
        template, include_properties=["P31", "P21"], exclude_properties=["P31"]
    )
    assert len(template.claims) == 1
    assert template.claims[0].property_id == "P21"
    assert "P31" not in template.to_dict()["claims"]


def test_wikidata_template_filter_qualifiers():
    """Test removing qualifiers from template."""
    claim = ClaimSummary(
        property_id="P31",
        value="Q5",
        qualifiers=[{"property": "P580", "count": 1}],
        references=[],
    )

    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[claim],
        entity_data={
            "id": "Q42",
            "claims": {"P31": [{"qualifiers": {"P580": [{"datavalue": {}}]}}]},
        },
    )

    template.filter_qualifiers()
    assert len(template.claims[0].qualifiers) == 0
    assert "qualifiers" not in template.to_dict()["claims"]["P31"][0]


def test_wikidata_template_filter_references():
    """Test removing references from template."""
    claim = ClaimSummary(
        property_id="P31",
        value="Q5",
        qualifiers=[],
        references=[{"count": 1}],
    )

    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[claim],
        entity_data={
            "id": "Q42",
            "claims": {"P31": [{"references": [{"snaks": {"P248": [{}]}}]}]},
        },
    )

    template.filter_references()
    assert len(template.claims[0].references) == 0
    assert "references" not in template.to_dict()["claims"]["P31"][0]


def test_wikidata_template_filter_languages_updates_entity_data():
    """Filter languages should update round-trip JSON output."""
    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Test", "fr": "Essai"},
        descriptions={"en": "Test", "fr": "Essai"},
        aliases={"en": ["T"], "fr": ["E"]},
        claims=[],
        entity_data={
            "id": "Q42",
            "labels": {
                "en": {"language": "en", "value": "Test"},
                "fr": {"language": "fr", "value": "Essai"},
            },
            "descriptions": {
                "en": {"language": "en", "value": "Test"},
                "fr": {"language": "fr", "value": "Essai"},
            },
            "aliases": {
                "en": [{"language": "en", "value": "T"}],
                "fr": [{"language": "fr", "value": "E"}],
            },
            "claims": {},
        },
    )

    apply_template_language_filter(template, "en")

    data = template.to_dict()
    assert template.labels == {"en": "Test"}
    assert template.descriptions == {"en": "Test"}
    assert template.aliases == {"en": ["T"]}
    assert list(data["labels"].keys()) == ["en"]
    assert list(data["descriptions"].keys()) == ["en"]
    assert list(data["aliases"].keys()) == ["en"]


def test_wikidata_template_to_dict_roundtrip():
    """Test converting template to round-trip-safe dictionary."""
    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={"en": ["T"]},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
        ],
        entity_data={
            "id": "Q42",
            "labels": {"en": {"language": "en", "value": "Test"}},
            "descriptions": {"en": {"language": "en", "value": "Test"}},
            "aliases": {"en": [{"language": "en", "value": "T"}]},
            "claims": {
                "P31": [
                    {
                        "mainsnak": {"datavalue": {"type": "wikibase-entityid"}},
                        "references": [{"snaks": {"P248": [{"datavalue": {}}]}}],
                    }
                ]
            },
        },
    )

    data = template.to_dict()
    assert data["id"] == "Q42"
    assert "P31" in data["claims"]
    assert "references" in data["claims"]["P31"][0]


def test_strip_entity_identifiers_removes_ids():
    """Strip entity and statement identifiers for new-item JSON."""
    entity_data = {
        "id": "Q42",
        "pageid": 123,
        "lastrevid": 456,
        "modified": "2024-01-01T00:00:00Z",
        "ns": 0,
        "title": "Q42",
        "labels": {"en": {"value": "Douglas Adams"}},
        "claims": {
            "P31": [
                {
                    "id": "Q42$ABC",
                    "mainsnak": {
                        "hash": "main123",
                        "datavalue": {"value": "Q5"},
                    },
                    "qualifiers": {
                        "P580": [{"hash": "abc123", "datavalue": {"value": "test"}}]
                    },
                    "references": [
                        {
                            "hash": "def456",
                            "snaks": {
                                "P248": [
                                    {"hash": "ghi789", "datavalue": {"value": "Q123"}}
                                ]
                            },
                        }
                    ],
                },
                {"mainsnak": {"datavalue": {"value": "Q215627"}}},
            ]
        },
    }

    cleaned = strip_entity_identifiers(entity_data)

    # Item-level identifiers should be removed
    assert cleaned.get("id") is None
    assert cleaned.get("pageid") is None
    assert cleaned.get("lastrevid") is None
    assert cleaned.get("modified") is None
    assert cleaned.get("ns") is None
    assert cleaned.get("title") is None

    # Statement ID should be removed
    assert cleaned["claims"]["P31"][0].get("id") is None

    # Mainsnak hash should be removed
    assert cleaned["claims"]["P31"][0]["mainsnak"].get("hash") is None

    # Qualifier hash should be removed
    assert cleaned["claims"]["P31"][0]["qualifiers"]["P580"][0].get("hash") is None

    # Reference hashes should be removed
    assert cleaned["claims"]["P31"][0]["references"][0].get("hash") is None
    ref_snaks = cleaned["claims"]["P31"][0]["references"][0]["snaks"]["P248"][0]
    assert ref_snaks.get("hash") is None

    # Original should be unchanged
    assert "id" in entity_data
    assert entity_data["claims"]["P31"][0]["id"] == "Q42$ABC"
    assert entity_data["claims"]["P31"][0]["qualifiers"]["P580"][0]["hash"] == "abc123"


class _FakeApiClient:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.api_url = "https://datadistillery.wikibase.cloud/w/api.php"

    def request(self, params):
        _ = params
        if not self.payloads:
            raise AssertionError("No more fake payloads available")
        return self.payloads.pop(0)


def test_get_latest_cache_timestamp_prefers_entity_modified(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "Q4.json").write_text(
        json.dumps(
            {
                "entity_id": "Q4",
                "entity": {"modified": "2026-03-12T20:44:37Z"},
                "metadata": {"cache_exported_at": "2026-03-12T20:44:40Z"},
            }
        ),
        encoding="utf-8",
    )
    (cache_dir / "Q39.json").write_text(
        json.dumps(
            {
                "entity_id": "Q39",
                "entity": {"modified": "2026-03-12T22:00:00Z"},
            }
        ),
        encoding="utf-8",
    )

    assert get_latest_cache_timestamp(cache_dir) == "2026-03-12T22:00:00Z"


def test_fetch_recent_entity_changes_collects_ids_and_ignores_filtered():
    client = _FakeApiClient(
        [
            {
                "query": {
                    "recentchanges": [
                        {"title": "Item:Q4", "timestamp": "2026-03-13T17:00:00Z"},
                        {"title": "Property:P192", "timestamp": "2026-03-13T17:01:00Z"},
                    ]
                },
                "continue": {"rccontinue": "next-token"},
            },
            {
                "query": {
                    "recentchanges": [
                        {"title": "Item:Q39", "timestamp": "2026-03-13T17:02:00Z"},
                        {"title": "User:Sky", "timestamp": "2026-03-13T17:03:00Z"},
                    ]
                }
            },
        ]
    )

    result = fetch_recent_entity_changes(
        client,
        since="2026-03-13T16:59:30Z",
        overlap_seconds=30,
        ignore_ids={"P192"},
    )

    assert isinstance(result, WikibaseRecentChangesResult)
    assert result.since == "2026-03-13T16:59:00Z"
    assert result.next_since == "2026-03-13T17:03:00Z"
    assert result.changed_ids == ["Q39", "Q4"]
    assert result.ignored_ids == ["P192"]


def test_refresh_entity_cache_from_recentchanges_updates_and_deletes(tmp_path):
    cache_dir = tmp_path / "entities"
    cache_dir.mkdir()
    (cache_dir / "Q4.json").write_text(
        json.dumps(
            {
                "entity_id": "Q4",
                "entity": {"id": "Q4", "modified": "2026-03-13T16:00:00Z"},
                "metadata": {"cache_exported_at": "2026-03-13T16:00:10Z"},
            }
        ),
        encoding="utf-8",
    )
    (cache_dir / "Q39.json").write_text(
        json.dumps(
            {
                "entity_id": "Q39",
                "entity": {"id": "Q39", "modified": "2026-03-13T16:00:00Z"},
            }
        ),
        encoding="utf-8",
    )

    client = _FakeApiClient(
        [
            {
                "query": {
                    "recentchanges": [
                        {"title": "Item:Q4", "timestamp": "2026-03-13T17:00:00Z"},
                        {"title": "Item:Q39", "timestamp": "2026-03-13T17:01:00Z"},
                    ]
                }
            },
            {
                "entities": {
                    "Q4": {
                        "id": "Q4",
                        "modified": "2026-03-13T17:00:00Z",
                        "labels": {},
                    },
                    "Q39": {"id": "Q39", "missing": ""},
                }
            },
        ]
    )

    result = refresh_entity_cache_from_recentchanges(
        api_client=client,
        cache_dir=cache_dir,
        since="2026-03-13T16:30:00Z",
        overlap_seconds=0,
    )

    assert result.changed_ids == ["Q39", "Q4"]
    assert result.refreshed_ids == ["Q4"]
    assert result.deleted_ids == ["Q39"]
    assert result.missing_ids == ["Q39"]

    refreshed_payload = json.loads((cache_dir / "Q4.json").read_text(encoding="utf-8"))
    assert refreshed_payload["entity_id"] == "Q4"
    assert refreshed_payload["metadata"]["workflow_mode"] == "recentchanges"
    assert not (cache_dir / "Q39.json").exists()


def test_extract_sparql_blocks_returns_blocks_in_order():
    wikitext = """
== Query ==
<sparql>
SELECT ?item ?itemLabel WHERE {
  ?item ?p ?o .
}
</sparql>

<sparql class=\"secondary\">
SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }
</sparql>
""".strip()

    blocks = extract_sparql_blocks(wikitext)
    assert len(blocks) == 2
    assert blocks[0].startswith("SELECT ?item ?itemLabel")
    assert blocks[1].startswith("SELECT ?item WHERE")


def test_extract_first_sparql_block_raises_without_block():
    with pytest.raises(RuntimeError, match="No <sparql> block"):
        extract_first_sparql_block("No query markup here")


def test_fetch_mediawiki_page_wikitext_from_revision_slots():
    client = _FakeApiClient(
        [
            {
                "query": {
                    "pages": [
                        {
                            "title": "Item_talk:Q4",
                            "revisions": [
                                {
                                    "slots": {
                                        "main": {
                                            "content": "<sparql>SELECT * WHERE { ?s ?p ?o }</sparql>"
                                        }
                                    }
                                }
                            ],
                        }
                    ]
                }
            }
        ]
    )

    text = fetch_mediawiki_page_wikitext(client, "Item_talk:Q4")
    assert "SELECT * WHERE" in text


def test_wikidata_loader_snak_to_value_entity():
    """Test converting entity snak to value."""
    snak = {
        "snaktype": "value",
        "datavalue": {
            "type": "wikibase-entityid",
            "value": {"id": "Q5"},
        },
    }

    value, metadata = WikibaseLoader._snak_to_value(snak)
    assert value == "Q5"
    assert metadata is None


def test_wikidata_loader_snak_to_value_string():
    """Test converting string snak to value."""
    snak = {
        "snaktype": "value",
        "datavalue": {
            "type": "string",
            "value": "test string",
        },
    }

    value, metadata = WikibaseLoader._snak_to_value(snak)
    assert value == "test string"
    assert metadata is None


def test_wikidata_loader_snak_to_value_novalue():
    """Test converting novalue snak."""
    snak = {"snaktype": "novalue"}
    value, metadata = WikibaseLoader._snak_to_value(snak)
    assert value == "[no value]"
    assert metadata is None


def test_wikidata_template_to_shell():
    """Test converting template to shell format."""
    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[],
        entity_data={
            "id": "Q42",
            "pageid": 123,
            "lastrevid": 456,
            "modified": "2024-01-01T00:00:00Z",
            "ns": 0,
            "title": "Q42",
            "labels": {"en": {"value": "Test"}},
            "claims": {},
        },
    )

    shell = template.to_shell()
    assert shell.get("id") is None
    assert shell.get("pageid") is None
    assert shell.get("ns") is None
    assert shell.get("title") is None
    assert "labels" in shell


def test_wikidata_template_to_qsv1():
    """Test converting template to QuickStatements V1 format."""
    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
        ],
        entity_data={
            "id": "Q42",
            "labels": {"en": {"value": "Test"}},
            "claims": {"P31": [{"mainsnak": {}}]},
        },
    )

    qs_text = template.to_qsv1(for_new_item=False)
    assert "Q42" in qs_text
    assert "P31" in qs_text

    qs_new = template.to_qsv1(for_new_item=True)
    assert "CREATE" in qs_new
    assert "LAST" in qs_new


def test_wikidata_template_to_gkc_entity_profile_not_implemented():
    """Test that to_gkc_entity_profile raises NotImplementedError."""
    template = WikibaseItemTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[],
        entity_data={"id": "Q42"},
    )

    try:
        template.to_gkc_entity_profile()
        assert False, "Should have raised NotImplementedError"
    except NotImplementedError as e:
        assert "not yet implemented" in str(e)


def test_wikidata_property_template_summary():
    """Test WikibasePropertyTemplate summary method."""
    template = WikibasePropertyTemplate(
        pid="P31",
        labels={"en": "instance of"},
        descriptions={"en": "that class of which this subject is a particular example"},
        aliases={},
        datatype="wikibase-item",
        formatter_url=None,
        entity_data={"id": "P31", "datatype": "wikibase-item"},
    )

    summary = template.summary()
    assert summary["pid"] == "P31"
    assert summary["labels"]["en"] == "instance of"
    assert summary["datatype"] == "wikibase-item"


def test_wikidata_property_template_filter_languages():
    """Test filtering languages on property template."""
    template = WikibasePropertyTemplate(
        pid="P31",
        labels={"en": "instance of", "fr": "nature de l'élément"},
        descriptions={"en": "test", "fr": "test"},
        aliases={},
        datatype="wikibase-item",
        formatter_url=None,
        entity_data={
            "id": "P31",
            "labels": {
                "en": {"value": "instance of"},
                "fr": {"value": "nature de l'élément"},
            },
            "descriptions": {"en": {"value": "test"}, "fr": {"value": "test"}},
        },
    )

    apply_template_language_filter(template, "en")
    assert len(template.labels) == 1
    assert "en" in template.labels
    assert "fr" not in template.labels


def test_wikidata_property_template_to_shell():
    """Test converting property template to shell format."""
    template = WikibasePropertyTemplate(
        pid="P31",
        labels={"en": "instance of"},
        descriptions={},
        aliases={},
        datatype="wikibase-item",
        formatter_url=None,
        entity_data={
            "id": "P31",
            "pageid": 123,
            "ns": 120,
            "title": "Property:P31",
            "datatype": "wikibase-item",
        },
    )

    shell = template.to_shell()
    assert shell.get("id") is None
    assert shell.get("pageid") is None
    assert shell.get("ns") is None
    assert shell.get("title") is None


def test_wikidata_entity_schema_template_summary():
    """Test WikibaseEntitySchemaTemplate summary method."""
    template = WikibaseEntitySchemaTemplate(
        eid="E502",
        labels={"en": "Tribe"},
        descriptions={"en": "An ethnic group"},
        schema_text="PREFIX : <http://www.wikidata.org/entity/>",
        entity_data={"id": "E502"},
    )

    summary = template.summary()
    assert summary["eid"] == "E502"
    assert summary["labels"]["en"] == "Tribe"
    assert summary["schema_text_length"] > 0


def test_wikidata_entity_schema_template_filter_languages():
    """Test filtering languages on entity schema template."""
    template = WikibaseEntitySchemaTemplate(
        eid="E502",
        labels={"en": "Tribe", "fr": "Tribu"},
        descriptions={"en": "test", "fr": "test"},
        schema_text="test",
        entity_data={
            "id": "E502",
            "labels": {"en": {"value": "Tribe"}, "fr": {"value": "Tribu"}},
            "descriptions": {"en": {"value": "test"}, "fr": {"value": "test"}},
        },
    )

    apply_template_language_filter(template, "en")
    assert len(template.labels) == 1
    assert "en" in template.labels
    assert "fr" not in template.labels


def test_wikidata_loader_load_items_empty():
    """Test loading empty list of items."""
    loader = WikibaseLoader()
    result = loader.load_items([])
    assert result == {}


def test_wikibase_loader_default_batch_size_without_auth():
    """WikibaseLoader defaults to a batch size of 50 when no auth is provided."""
    loader = WikibaseLoader()
    assert loader.entity_batch_size == 50


def test_wikibase_loader_default_batch_size_with_no_high_limits():
    """WikibaseLoader stays at 50 when auth is present but apihighlimits is absent."""
    fake_auth = type("FakeAuth", (), {"has_api_high_limits": lambda self: False})()
    loader = WikibaseLoader(auth=fake_auth)
    assert loader.entity_batch_size == 50


def test_wikibase_loader_high_batch_size_with_apihighlimits():
    """WikibaseLoader uses 500 when auth reports apihighlimits is present."""
    fake_auth = type("FakeAuth", (), {"has_api_high_limits": lambda self: True})()
    loader = WikibaseLoader(auth=fake_auth)
    assert loader.entity_batch_size == 500


def test_wikibase_loader_batch_size_safe_with_auth_none_method():
    """WikibaseLoader falls back to 50 when auth object lacks has_api_high_limits."""

    class NoMethodAuth:
        pass

    loader = WikibaseLoader(auth=NoMethodAuth())
    assert loader.entity_batch_size == 50


def test_wikibase_loader_load_items_respects_batch_size(monkeypatch):
    """load_items batches calls according to entity_batch_size."""
    from unittest.mock import MagicMock

    fake_auth = type("FakeAuth", (), {"has_api_high_limits": lambda self: True})()
    loader = WikibaseLoader(auth=fake_auth)
    assert loader.entity_batch_size == 500

    calls = []

    def fake_fetch(entity_ids):
        calls.append(len(entity_ids))
        return {
            eid: {"id": eid, "labels": {}, "claims": {}, "type": "item"}
            for eid in entity_ids
        }

    monkeypatch.setattr(loader, "_fetch_entities_batch", fake_fetch)
    monkeypatch.setattr(loader, "_build_template", lambda qid, data: MagicMock())

    qids = [f"Q{i}" for i in range(600)]
    loader.load_items(qids)

    # With batch_size=500, 600 items should produce two batches: 500 and 100
    assert len(calls) == 2
    assert calls[0] == 500
    assert calls[1] == 100


def test_wikibase_loader_load_entities_raw_respects_batch_size(monkeypatch):
    """load_entities_raw batches requests and returns merged raw entity JSON."""
    fake_auth = type("FakeAuth", (), {"has_api_high_limits": lambda self: True})()
    loader = WikibaseLoader(auth=fake_auth)

    calls = []

    def fake_fetch(entity_ids):
        calls.append(len(entity_ids))
        return {eid: {"id": eid, "type": "item"} for eid in entity_ids}

    monkeypatch.setattr(loader, "_fetch_entities_batch", fake_fetch)

    entity_ids = [f"Q{i}" for i in range(600)]
    result = loader.load_entities_raw(entity_ids)

    assert len(calls) == 2
    assert calls[0] == 500
    assert calls[1] == 100
    assert len(result) == 600


def test_wikipedia_template_initialization():
    """Test creating a Wikipedia template."""
    template = WikipediaTemplate(
        title="Infobox settlement",
        description="An infobox for settlements",
        params={"name": {"label": "Name"}, "image": {"label": "Image"}},
        param_order=["name", "image"],
        raw_data={"title": "Infobox settlement", "params": {}},
    )

    assert template.title == "Infobox settlement"
    assert template.description == "An infobox for settlements"
    assert len(template.params) == 2
    assert template.param_order == ["name", "image"]


def test_wikipedia_template_summary():
    """Test the summary method returns expected fields."""
    template = WikipediaTemplate(
        title="Infobox settlement",
        description="An infobox for settlements",
        params={
            "name": {"label": "Name"},
            "image": {"label": "Image"},
            "population": {"label": "Population"},
        },
        param_order=["name", "image", "population"],
        raw_data={},
    )

    summary = template.summary()
    assert summary["title"] == "Infobox settlement"
    assert summary["description"] == "An infobox for settlements"
    assert summary["param_count"] == 3


def test_wikipedia_template_to_dict():
    """Test serializing template to dict."""
    params = {"name": {"label": "Name"}, "image": {"label": "Image"}}
    param_order = ["name", "image"]
    template = WikipediaTemplate(
        title="Infobox settlement",
        description="An infobox for settlements",
        params=params,
        param_order=param_order,
        raw_data={},
    )

    result = template.to_dict()
    assert result["title"] == "Infobox settlement"
    assert result["description"] == "An infobox for settlements"
    assert result["params"] == params
    assert result["paramOrder"] == param_order


def test_wikipedia_loader_initialization():
    """Test initializing a Wikipedia loader."""
    loader = WikipediaLoader()
    expected_agents = "GKC/1.0 (https://github.com/skybristol/gkc; data integration)"
    assert loader.user_agent == expected_agents
    assert loader.base_url == "https://en.wikipedia.org/w/api.php"


def test_wikipedia_loader_custom_user_agent():
    """Test initializing a Wikipedia loader with custom user agent."""
    loader = WikipediaLoader(user_agent="CustomBot/1.0")
    assert loader.user_agent == "CustomBot/1.0"
