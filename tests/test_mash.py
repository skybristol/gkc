"""Tests for the Mash module."""

import gkc
from gkc.mash import (
    ClaimSummary,
    WikidataLoader,
    WikidataTemplate,
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
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Life, the Universe, and Everything"},
        descriptions={"en": "Answer to everything"},
        aliases={"en": ["42", "The Answer"]},
        claims=[
            ClaimSummary(
                property_id="P31", value="Q36253", qualifiers=[], references=[]
            ),
        ],
    )

    summary = template.summary()
    assert summary["qid"] == "Q42"
    assert summary["labels"] == {"en": "Life, the Universe, and Everything"}
    assert summary["descriptions"] == {"en": "Answer to everything"}
    assert summary["total_statements"] == 1


def test_wikidata_template_filter_properties():
    """Test filtering properties from template."""
    template = WikidataTemplate(
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
    )

    template.filter_properties(["P31"])
    assert len(template.claims) == 1
    assert template.claims[0].property_id == "P21"


def test_wikidata_template_filter_qualifiers():
    """Test removing qualifiers from template."""
    claim = ClaimSummary(
        property_id="P31",
        value="Q5",
        qualifiers=[{"property": "P580", "count": 1}],
        references=[],
    )

    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[claim],
    )

    template.filter_qualifiers()
    assert len(template.claims[0].qualifiers) == 0


def test_wikidata_template_filter_references():
    """Test removing references from template."""
    claim = ClaimSummary(
        property_id="P31",
        value="Q5",
        qualifiers=[],
        references=[{"count": 1}],
    )

    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[claim],
    )

    template.filter_references()
    assert len(template.claims[0].references) == 0


def test_wikidata_template_to_dict():
    """Test converting template to dictionary."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={"en": ["T"]},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
        ],
    )

    data = template.to_dict()
    assert data["qid"] == "Q42"
    assert len(data["claims"]) == 1
    assert data["claims"][0]["property_id"] == "P31"


def test_strip_entity_identifiers_removes_ids():
    """Strip entity and statement identifiers for new-item JSON."""
    entity_data = {
        "id": "Q42",
        "pageid": 123,
        "lastrevid": 456,
        "modified": "2024-01-01T00:00:00Z",
        "ns": 0,
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
    # ns should be preserved
    assert cleaned.get("ns") == 0

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


def test_wikidata_loader_snak_to_value_entity():
    """Test converting entity snak to value."""
    snak = {
        "snaktype": "value",
        "datavalue": {
            "type": "wikibase-entityid",
            "value": {"id": "Q5"},
        },
    }

    value, metadata = WikidataLoader._snak_to_value(snak)
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

    value, metadata = WikidataLoader._snak_to_value(snak)
    assert value == "test string"
    assert metadata is None


def test_wikidata_loader_snak_to_value_novalue():
    """Test converting novalue snak."""
    snak = {"snaktype": "novalue"}
    value, metadata = WikidataLoader._snak_to_value(snak)
    assert value == "[no value]"
    assert metadata is None
