"""Tests for Mash formatters."""

import json

from gkc.mash import ClaimSummary, MashTemplate
from gkc.mash_formatters import JSONFormatter, QSV1Formatter


def test_qsv1_formatter_new_item():
    """Format template for new item creation."""
    template = MashTemplate(
        qid="Q42",
        labels={"en": "Test Item", "fr": "Élément de Test"},
        descriptions={"en": "A test item"},
        aliases={"en": ["T", "Test"]},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
        ],
    )

    formatter = QSV1Formatter()
    qs_text = formatter.format(template, for_new_item=True)

    lines = qs_text.split("\n")
    assert lines[0] == "CREATE"
    # Check for labels with L prefix
    assert any("Len\t" in line for line in lines)
    # Check for descriptions with D prefix
    assert any("Den\t" in line for line in lines)
    # Check for aliases with A prefix
    assert any("Aen\t" in line for line in lines)
    assert any("P31\tQ5" in line for line in lines)


def test_qsv1_formatter_exclude_properties():
    """Exclude properties from QS output."""
    template = MashTemplate(
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

    formatter = QSV1Formatter(exclude_properties=["P31"])
    qs_text = formatter.format(template, for_new_item=True)

    assert "P31" not in qs_text
    assert "P21" in qs_text


def test_json_formatter_basic():
    """Format template as JSON."""
    template = MashTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
        ],
    )

    formatter = JSONFormatter()
    json_text = formatter.format(template)

    data = json.loads(json_text)
    assert data["qid"] == "Q42"
    assert len(data["claims"]) == 1


def test_json_formatter_exclude_properties():
    """Exclude properties from JSON output."""
    template = MashTemplate(
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

    formatter = JSONFormatter()
    json_text = formatter.format(template, exclude_properties=["P31"])

    data = json.loads(json_text)
    assert len(data["claims"]) == 1
    assert data["claims"][0]["property_id"] == "P21"


def test_qsv1_formatter_with_entity_labels():
    """Format QS output with entity labels in comments."""
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

    entity_labels = {
        "P31": "instance of",
        "Q5": "human",
        "P21": "sex or gender",
        "Q6581097": "male",
    }

    formatter = QSV1Formatter(entity_labels=entity_labels)
    qs_text = formatter.format(template, for_new_item=True)

    lines = qs_text.split("\n")

    # Find the P31 claim line
    p31_line = [line for line in lines if line.startswith("LAST\tP31\t")]
    assert len(p31_line) == 1
    assert "/* instance of is human */" in p31_line[0]

    # Find the P21 claim line
    p21_line = [line for line in lines if line.startswith("LAST\tP21\t")]
    assert len(p21_line) == 1
    assert "/* sex or gender is male */" in p21_line[0]


def test_qsv1_formatter_with_qualifiers_and_labels():
    """Format QS output with qualifiers and labels in comments."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(
                property_id="P50",
                value="Q1010563",
                qualifiers=[
                    {"property": "P1545", "value": "1"},
                ],
                references=[],
            ),
        ],
    )

    entity_labels = {
        "P50": "author",
        "Q1010563": "Bureau of Indian Affairs",
        "P1545": "series ordinal",
    }

    formatter = QSV1Formatter(entity_labels=entity_labels)
    qs_text = formatter.format(template, for_new_item=True)

    lines = qs_text.split("\n")

    # Find the P50 claim line with qualifier
    p50_line = [line for line in lines if line.startswith("LAST\tP50\t")]
    assert len(p50_line) == 1

    # Check that the line has the qualifier values
    assert "P1545" in p50_line[0]
    assert "1" in p50_line[0]

    # Check the comment includes both main claim and qualifier
    expected = "/* author is Bureau of Indian Affairs; series ordinal is 1 */"
    assert expected in p50_line[0]


def test_qsv1_formatter_without_entity_labels():
    """Format QS output without entity labels (no comments)."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
        ],
    )

    # No entity_labels provided
    formatter = QSV1Formatter()
    qs_text = formatter.format(template, for_new_item=True)

    lines = qs_text.split("\n")

    # Find the P31 claim line
    p31_line = [line for line in lines if line.startswith("LAST\tP31\t")]
    assert len(p31_line) == 1
    # Should not have any comment
    assert "/*" not in p31_line[0]


def test_qsv1_formatter_with_string_values():
    """Format QS output with string values (not entity IDs)."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(
                property_id="P1476", value='"Test Title"', qualifiers=[], references=[]
            ),
        ],
    )

    entity_labels = {
        "P1476": "title",
    }

    formatter = QSV1Formatter(entity_labels=entity_labels)
    qs_text = formatter.format(template, for_new_item=True)

    lines = qs_text.split("\n")

    # Find the P1476 claim line
    p1476_line = [line for line in lines if line.startswith("LAST\tP1476\t")]
    assert len(p1476_line) == 1
    # Comment should show the property label and the actual string value
    assert '/* title is "Test Title" */' in p1476_line[0]


def test_qsv1_formatter_existing_item():
    """Format QS output for updating an existing item."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
        ],
    )

    entity_labels = {
        "P31": "instance of",
        "Q5": "human",
    }

    formatter = QSV1Formatter(entity_labels=entity_labels)
    qs_text = formatter.format(template, for_new_item=False)

    lines = qs_text.split("\n")

    # Should not have CREATE
    assert "CREATE" not in qs_text

    # Should use Q42 instead of LAST
    p31_line = [line for line in lines if line.startswith("Q42\tP31\t")]
    assert len(p31_line) == 1
    assert "/* instance of is human */" in p31_line[0]


def test_qsv1_formatter_with_date_precision():
    """Format QS output with date values that include precision."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(
                property_id="P577",
                value="+2001-01-15T00:00:00Z",
                qualifiers=[],
                references=[],
                value_metadata={"precision": 11},
            ),
        ],
    )

    entity_labels = {
        "P577": "publication date",
    }

    formatter = QSV1Formatter(entity_labels=entity_labels)
    qs_text = formatter.format(template, for_new_item=True)

    lines = qs_text.split("\n")

    # Find the P577 claim line
    p577_line = [line for line in lines if line.startswith("LAST\tP577\t")]
    assert len(p577_line) == 1
    # Date should include precision suffix
    assert "+2001-01-15T00:00:00Z/11" in p577_line[0]
    # Comment should show the property label and date
    assert "/* publication date is +2001-01-15T00:00:00Z */" in p577_line[0]


def test_qsv1_formatter_with_qualifier_date_precision():
    """Format QS output with date qualifiers that include precision."""
    template = WikidataTemplate(
        qid="Q42",
        labels={"en": "Test"},
        descriptions={"en": "Test"},
        aliases={},
        claims=[
            ClaimSummary(
                property_id="P39",
                value="Q5",
                qualifiers=[
                    {
                        "property": "P580",
                        "value": "+1990-01-01T00:00:00Z",
                        "metadata": {"precision": 9},
                    },
                ],
                references=[],
            ),
        ],
    )

    entity_labels = {
        "P39": "position held",
        "Q5": "human",
        "P580": "start time",
    }

    formatter = QSV1Formatter(entity_labels=entity_labels)
    qs_text = formatter.format(template, for_new_item=True)

    lines = qs_text.split("\n")

    # Find the P39 claim line with qualifier
    p39_line = [line for line in lines if line.startswith("LAST\tP39\t")]
    assert len(p39_line) == 1

    # Check that the qualifier has precision
    assert "P580" in p39_line[0]
    assert "+1990-01-01T00:00:00Z/9" in p39_line[0]

    # Check the comment includes both main claim and qualifier
    assert "position held is human" in p39_line[0]
    assert "start time is +1990-01-01T00:00:00Z" in p39_line[0]
