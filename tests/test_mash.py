"""Tests for the Mash module."""

import gkc
from gkc.mash import (
    ClaimSummary,
    WikidataLoader,
    WikidataTemplate,
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


def test_wikidata_loader_snak_to_value_entity():
    """Test converting entity snak to value."""
    snak = {
        "snaktype": "value",
        "datavalue": {
            "type": "wikibase-entityid",
            "value": {"id": "Q5"},
        },
    }

    value, metadata = MashLoader._snak_to_value(snak)
    assert value == "Q5"    assert metadata is None


def test_wikidata_loader_snak_to_value_string():
    """Test converting string snak to value."""
    snak = {
        "snaktype": "value",
        "datavalue": {
            "type": "string",
            "value": "test string",
        },
    }

    value, metadata = MashLoader._snak_to_value(snak)
    assert value == "test string"    assert metadata is None


def test_wikidata_loader_snak_to_value_novalue():
    """Test converting novalue snak."""
    snak = {"snaktype": "novalue"}
    value, metadata = MashLoader._snak_to_value(snak)
    assert value == "[no value]"
    assert metadata is None
>>>>>>> Stashed changes=======
>>>>>>> 3988fbc (Fix class name references after merge conflict resolution)
