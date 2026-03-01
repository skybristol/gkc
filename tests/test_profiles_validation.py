"""Tests for profile validation against Wikidata JSON."""

from pathlib import Path

import pytest

from gkc.profiles import ProfileLoader, ProfileValidator


@pytest.fixture
def profile_fixture_path() -> Path:
    return (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )


def _minimal_wikidata_item() -> dict:
    return {
        "id": "Q123",
        "claims": {
            "P31": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "datatype": "wikibase-item",
                        "datavalue": {
                            "type": "wikibase-entityid",
                            "value": {"id": "Q7840353"},
                        },
                    },
                    "references": [
                        {
                            "snaks": {
                                "P248": [
                                    {
                                        "snaktype": "value",
                                        "datatype": "wikibase-item",
                                        "datavalue": {
                                            "type": "wikibase-entityid",
                                            "value": {"id": "Q138391266"},
                                        },
                                    }
                                ]
                            }
                        }
                    ],
                }
            ],
            "P856": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "datatype": "url",
                        "datavalue": {"type": "string", "value": "https://example.org"},
                    },
                    "qualifiers": {
                        "P407": [
                            {
                                "snaktype": "value",
                                "datatype": "wikibase-item",
                                "datavalue": {
                                    "type": "wikibase-entityid",
                                    "value": {"id": "Q1860"},
                                },
                            }
                        ]
                    },
                    "references": [
                        {
                            "snaks": {
                                "P854": [
                                    {
                                        "snaktype": "value",
                                        "datatype": "url",
                                        "datavalue": {
                                            "type": "string",
                                            "value": "https://example.org",
                                        },
                                    }
                                ]
                            }
                        }
                    ],
                }
            ],
            "P2124": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "datatype": "quantity",
                        "datavalue": {
                            "type": "quantity",
                            "value": {"amount": "+12.5"},
                        },
                    },
                    "qualifiers": {
                        "P585": [
                            {
                                "snaktype": "value",
                                "datatype": "time",
                                "datavalue": {
                                    "type": "time",
                                    "value": {"time": "+2020-01-01T00:00:00Z"},
                                },
                            }
                        ]
                    },
                    "references": [
                        {
                            "snaks": {
                                "P854": [
                                    {
                                        "snaktype": "value",
                                        "datatype": "url",
                                        "datavalue": {
                                            "type": "string",
                                            "value": "https://example.org/source",
                                        },
                                    }
                                ]
                            }
                        }
                    ],
                }
            ],
        },
    }


def test_lenient_validation_warns_on_integer_only(profile_fixture_path: Path):
    """Lenient validation issues warnings for nonconforming fields."""
    profile = ProfileLoader().load_from_file(profile_fixture_path)
    validator = ProfileValidator(profile)

    result = validator.validate_item(_minimal_wikidata_item(), policy="lenient")
    assert result.ok is True
    assert any("integer_only" in issue.message for issue in result.warnings)


def test_strict_validation_errors_on_integer_only(profile_fixture_path: Path):
    """Strict validation errors on integer_only violations."""
    profile = ProfileLoader().load_from_file(profile_fixture_path)
    validator = ProfileValidator(profile)

    result = validator.validate_item(_minimal_wikidata_item(), policy="strict")
    assert result.ok is False
    assert any("integer_only" in issue.message for issue in result.errors)
