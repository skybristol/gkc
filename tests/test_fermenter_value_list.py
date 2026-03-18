"""Tests for validate_value_from_list in gkc.fermenter.

Covers both SpiritSafe materialized items format and raw SPARQL bindings format,
plus all value input shapes the wizard and downstream consumers can produce.
"""

import json
from pathlib import Path

from gkc.fermenter import validate_value_from_list

# Known URIs from the Q28 fixture
URI_HIT = "http://www.wikidata.org/entity/Q137668723"
URI_HIT_LABEL = "Indian Entities Recognized and Eligible To Receive Services from the United States Bureau of Indian Affairs (April 04, 2008)"
URI_HIT_2 = "http://www.wikidata.org/entity/Q138391266"
URI_MISS = "http://www.wikidata.org/entity/Q999999999"
QID_HIT = "Q137668723"
QID_MISS = "Q999999999"

FIXTURE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "spiritsafe"
    / "cache"
    / "queries"
    / "Q28.json"
)


# ---------------------------------------------------------------------------
# items-format (SpiritSafe materialized cache) — strict match
# ---------------------------------------------------------------------------


def test_items_format_full_uri_hit():
    """Full Wikidata URI that exists in items list → valid."""
    result = validate_value_from_list(URI_HIT, FIXTURE_PATH)
    assert result.valid is True
    assert not result.errors


def test_items_format_full_uri_miss():
    """Full Wikidata URI that does not exist in items list → invalid with message."""
    result = validate_value_from_list(URI_MISS, FIXTURE_PATH)
    assert result.valid is False
    assert any(URI_MISS in err for err in result.errors)


def test_items_format_qid_string_hit():
    """Bare QID string that maps to a present URI → valid (expert-mode input)."""
    result = validate_value_from_list(QID_HIT, FIXTURE_PATH)
    assert result.valid is True
    assert not result.errors


def test_items_format_qid_string_miss():
    """Bare QID string that does not map to any cache URI → invalid."""
    result = validate_value_from_list(QID_MISS, FIXTURE_PATH)
    assert result.valid is False
    assert result.errors


def test_items_format_wizard_dict_hit():
    """Wizard-style dict with 'item' full URI → valid."""
    value = {"item": URI_HIT, "itemLabel": URI_HIT_LABEL}
    result = validate_value_from_list(value, FIXTURE_PATH)
    assert result.valid is True
    assert not result.errors


def test_items_format_wizard_dict_miss():
    """Wizard-style dict with unknown URI → invalid."""
    value = {"item": URI_MISS, "itemLabel": "Unknown Tribe"}
    result = validate_value_from_list(value, FIXTURE_PATH)
    assert result.valid is False
    assert result.errors


def test_items_format_wikibase_snakvalue_dict_hit():
    """Wikibase snakvalue dict with 'id' key → valid (QID normalised to URI)."""
    value = {"id": QID_HIT, "entity-type": "item", "numeric-id": 137668723}
    result = validate_value_from_list(value, FIXTURE_PATH)
    assert result.valid is True
    assert not result.errors


# ---------------------------------------------------------------------------
# Fuzzy label match — items format
# ---------------------------------------------------------------------------


def test_items_format_fuzzy_label_hit():
    """Fuzzy match on itemLabel in items list → valid."""
    value = {"item": URI_MISS, "itemLabel": URI_HIT_LABEL}
    result = validate_value_from_list(value, FIXTURE_PATH, match_policy="fuzzy")
    assert result.valid is True


def test_items_format_fuzzy_label_miss():
    """Fuzzy match with label not in list → invalid."""
    value = {
        "item": URI_MISS,
        "itemLabel": "Completely Unknown Tribe That Does Not Exist",
    }
    result = validate_value_from_list(value, FIXTURE_PATH, match_policy="fuzzy")
    assert result.valid is False
    assert result.errors


# ---------------------------------------------------------------------------
# Raw SPARQL bindings format (hydration pipeline intermediate)
# ---------------------------------------------------------------------------


def test_sparql_bindings_format_hit(tmp_path: Path):
    """URI present in raw SPARQL results.bindings format → valid."""
    cache_file = tmp_path / "Q99.json"
    cache_file.write_text(
        json.dumps(
            {
                "results": {
                    "bindings": [
                        {
                            "item": {"type": "uri", "value": URI_HIT},
                            "itemLabel": {"type": "literal", "value": URI_HIT_LABEL},
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    result = validate_value_from_list(URI_HIT, cache_file)
    assert result.valid is True


def test_sparql_bindings_format_miss(tmp_path: Path):
    """URI absent in raw SPARQL results.bindings format → invalid."""
    cache_file = tmp_path / "Q99.json"
    cache_file.write_text(
        json.dumps(
            {"results": {"bindings": [{"item": {"type": "uri", "value": URI_HIT}}]}}
        ),
        encoding="utf-8",
    )
    result = validate_value_from_list(URI_MISS, cache_file)
    assert result.valid is False


def test_sparql_bindings_format_fuzzy_hit(tmp_path: Path):
    """Fuzzy label match against SPARQL bindings format → valid."""
    cache_file = tmp_path / "Q99.json"
    cache_file.write_text(
        json.dumps(
            {
                "results": {
                    "bindings": [
                        {
                            "item": {"type": "uri", "value": URI_HIT},
                            "itemLabel": {"type": "literal", "value": URI_HIT_LABEL},
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    value = {"item": URI_MISS, "itemLabel": URI_HIT_LABEL}
    result = validate_value_from_list(value, cache_file, match_policy="fuzzy")
    assert result.valid is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_cache_missing(tmp_path: Path):
    """Cache file absent → error ValidationResult (offline-first)."""
    missing = tmp_path / "nonexistent.json"
    result = validate_value_from_list(URI_HIT, missing)
    assert result.valid is False
    assert any("unavailable" in err for err in result.errors)


def test_cache_corrupt(tmp_path: Path):
    """Corrupt cache file → error ValidationResult."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{not valid json", encoding="utf-8")
    result = validate_value_from_list(URI_HIT, bad_file)
    assert result.valid is False
    assert result.errors


def test_empty_none_value():
    """None input → valid with no errors (presence is enforced upstream)."""
    result = validate_value_from_list(None, FIXTURE_PATH)
    assert result.valid is True
    assert not result.errors


def test_empty_string_value():
    """Empty string input → valid with no errors (presence is enforced upstream)."""
    result = validate_value_from_list("", FIXTURE_PATH)
    assert result.valid is True
    assert not result.errors


def test_empty_dict_value():
    """Empty dict input → valid with no errors."""
    result = validate_value_from_list({}, FIXTURE_PATH)
    assert result.valid is True
    assert not result.errors


def test_unnormalizable_value():
    """Value that cannot be resolved to a URI → error ValidationResult."""
    result = validate_value_from_list(12345, FIXTURE_PATH)
    assert result.valid is False
    assert result.errors


def test_items_and_bindings_both_present(tmp_path: Path):
    """Cache with both items list and results.bindings — URI from either is accepted."""
    cache_file = tmp_path / "combo.json"
    cache_file.write_text(
        json.dumps(
            {
                "items": [{"item": URI_HIT, "itemLabel": URI_HIT_LABEL}],
                "results": {
                    "bindings": [{"item": {"type": "uri", "value": URI_HIT_2}}]
                },
            }
        ),
        encoding="utf-8",
    )
    assert validate_value_from_list(URI_HIT, cache_file).valid is True
    assert validate_value_from_list(URI_HIT_2, cache_file).valid is True
    assert validate_value_from_list(URI_MISS, cache_file).valid is False
