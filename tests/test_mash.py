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

    value, metadata = WikidataLoader._snak_to_value(snak)    assert value == "Q5"
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

    value, metadata = WikidataLoader._snak_to_value(snak)    assert value == "test string"
    assert metadata is None


def test_wikidata_loader_snak_to_value_novalue():
    """Test converting novalue snak."""
    snak = {"snaktype": "novalue"}
    value, metadata = WikidataLoader._snak_to_value(snak)
    assert value == "[no value]"
    assert metadata is None

def test_wikidata_template_filter_languages_single():
    """Test filtering to a single language."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test", "fr": "Test FR", "es": "Test ES"},
        descriptions={"en": "English", "fr": "Français", "es": "Español"},
        aliases={"en": ["T"], "fr": ["T FR"], "es": ["T ES"]},
        claims=[],
    )

    template.filter_languages("en")
    assert list(template.labels.keys()) == ["en"]
    assert template.labels["en"] == "Test"
    assert list(template.descriptions.keys()) == ["en"]
    assert list(template.aliases.keys()) == ["en"]


def test_wikidata_template_filter_languages_multiple():
    """Test filtering to multiple languages."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test", "fr": "Test FR", "es": "Test ES", "de": "Test DE"},
        descriptions={"en": "English", "fr": "Français", "es": "Español"},
        aliases={"en": ["T"], "fr": ["T FR"]},
        claims=[],
    )

    template.filter_languages(["en", "fr"])
    assert set(template.labels.keys()) == {"en", "fr"}
    assert set(template.descriptions.keys()) == {"en", "fr"}
    assert set(template.aliases.keys()) == {"en", "fr"}
    # Should not have es or de
    assert "es" not in template.labels
    assert "de" not in template.labels


def test_wikidata_template_filter_languages_all():
    """Test that 'all' keeps everything."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test", "fr": "Test FR", "es": "Test ES"},
        descriptions={"en": "English", "fr": "Français"},
        aliases={"en": ["T"], "fr": ["T FR"]},
        claims=[],
    )

    template.filter_languages("all")
    # All languages should remain
    assert len(template.labels) == 3
    assert len(template.descriptions) == 2
    assert len(template.aliases) == 2


def test_wikidata_template_filter_languages_uses_package_config():
    """Test that None uses package-level configuration."""
    original_lang = gkc.get_languages()

    try:
        gkc.set_languages("fr")
        template = WikidataTemplate(
            qid="Q42",
            labels={"en": "Test", "fr": "Test FR", "es": "Test ES"},
            descriptions={"en": "English", "fr": "Français"},
            aliases={"en": ["T"], "fr": ["T FR"]},
            claims=[],
        )

        # Call without argument - should use package config
        template.filter_languages()
        assert list(template.labels.keys()) == ["fr"]
        assert list(template.descriptions.keys()) == ["fr"]
        assert list(template.aliases.keys()) == ["fr"]
    finally:
        # Reset to original
        gkc.set_languages(original_lang)


def test_wikidata_template_filter_languages_missing_language():
    """Test filtering to a language that doesn't exist in the data."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test", "fr": "Test FR"},
        descriptions={"en": "English"},
        aliases={"en": ["T"]},
        claims=[],
    )

    # Filter to a language that's not in the data
    template.filter_languages("es")
    assert len(template.labels) == 0
    assert len(template.descriptions) == 0
    assert len(template.aliases) == 0
<<<<<<< HEAD
=======
>>>>>>> Stashed changes
>>>>>>> 15c16a5 (Fix QuickStatements V1 syntax and add metadata support)
