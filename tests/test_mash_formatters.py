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
        aliases={"en": ["T"]},
        claims=[
            ClaimSummary(property_id="P31", value="Q5", qualifiers=[], references=[]),
        ],
    )

    formatter = QSV1Formatter()
    qs_text = formatter.format(template, for_new_item=True)

    lines = qs_text.split("\n")
    assert lines[0] == "CREATE"
    assert any("en\t" in line for line in lines)
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
