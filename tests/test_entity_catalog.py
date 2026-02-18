"""Tests for EntityCatalog SPARQL handling."""

from unittest.mock import patch

import gkc
from gkc.recipe import EntityCatalog, ItemLedgerEntry, PropertyLedgerEntry


def test_entity_catalog_fetch_entities_parses_results():
    gkc.set_languages("en")
    catalog = EntityCatalog(fetch_property_details=True)

    bindings = [
        {
            "entityId": {"value": "http://www.wikidata.org/entity/P31"},
            "label": {"value": "instance of"},
            "labelLang": {"value": "en"},
            "alias": {"value": "inst of"},
            "aliasLang": {"value": "en"},
            "desc": {"value": "that class of which this subject is an instance"},
            "descLang": {"value": "en"},
            "datatype": {"value": "wikibase-item"},
            "formatterUrl": {"value": "https://example.org/$1"},
        },
        {
            "entityId": {"value": "http://www.wikidata.org/entity/Q5"},
            "label": {"value": "human"},
            "labelLang": {"value": "en"},
            "alias": {"value": "person"},
            "aliasLang": {"value": "en"},
            "desc": {"value": "human being"},
            "descLang": {"value": "en"},
        },
    ]

    with patch("gkc.recipe.execute_sparql") as mock_execute:
        mock_execute.return_value = {"results": {"bindings": bindings}}
        results = catalog.fetch_entities(["P31", "Q5"])

    assert isinstance(results["P31"], PropertyLedgerEntry)
    assert results["P31"].datatype == "wikibase-item"
    assert results["P31"].get_label("en") == "instance of"
    assert results["P31"].aliases["en"][0]["value"] == "inst of"

    assert isinstance(results["Q5"], ItemLedgerEntry)
    assert results["Q5"].get_description("en") == "human being"
    assert results["Q5"].aliases["en"][0]["value"] == "person"

    gkc.set_languages("en")


def test_entity_catalog_builds_language_filters():
    gkc.set_languages(["en", "fr"])
    catalog = EntityCatalog()

    with patch("gkc.recipe.execute_sparql") as mock_execute:
        mock_execute.return_value = {"results": {"bindings": []}}
        catalog.fetch_entities(["Q5"])
        query = mock_execute.call_args[0][0]

    assert 'FILTER(?labelLang IN ("en", "fr"))' in query
    assert 'FILTER(?aliasLang IN ("en", "fr"))' in query
    assert 'FILTER(?descLang IN ("en", "fr"))' in query

    gkc.set_languages("en")
