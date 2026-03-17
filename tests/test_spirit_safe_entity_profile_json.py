"""Tests for SpiritSafe JSON entity profile builder/export utilities."""

import json

from gkc.spirit_safe import (
    build_entity_profile_json_documents,
    export_entity_profile_json_documents,
)


def _build_entity_claim_entity_id(entity_id: str) -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": {
                    "id": entity_id,
                }
            }
        }
    }


def _build_qualifier_entity_id(entity_id: str) -> dict:
    return {
        "datavalue": {
            "value": {
                "id": entity_id,
            }
        }
    }


def _build_entity_claim_string(value: str) -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": value,
            }
        }
    }


def test_build_entity_profile_json_documents_from_cache_entities(tmp_path):
    """Build returns JSON entity profile docs for cache entities typed as Q3."""
    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"en": {"value": "Tribal Government in the United States"}},
            "descriptions": {"en": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(json.dumps(payload), encoding="utf-8")

    docs = build_entity_profile_json_documents(cache_entities_dir)

    assert len(docs) == 1
    assert docs[0]["entity"].endswith("/Q4")
    assert docs[0]["metadata"]["statement_count"] == 0


def test_export_entity_profile_json_documents_writes_qid_files(tmp_path):
    """Export writes one JSON file per built profile document."""
    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"en": {"value": "Tribal Government in the United States"}},
            "descriptions": {"en": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(json.dumps(payload), encoding="utf-8")

    output_dir = tmp_path / "profiles"
    result = export_entity_profile_json_documents(cache_entities_dir, output_dir)

    assert result.output_dir == str(output_dir.resolve())
    assert result.written_ids == ["Q4"]

    profile_path = output_dir / "Q4.json"
    assert profile_path.exists()
    profile_payload = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile_payload["entity"].endswith("/Q4")


def test_value_list_graph_includes_reference_and_qualifier_routes(tmp_path):
    """Metadata graph should include value-list routes from nested statements."""

    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    profile_payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"mul": {"value": "Tribal Government in the United States"}},
            "descriptions": {"mul": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
                "P157": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"id": "Q16"},
                            }
                        },
                        "qualifiers": {
                            "P211": [_build_qualifier_entity_id("Q30")],
                            "P158": [_build_qualifier_entity_id("Q41")],
                        },
                    }
                ],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(
        json.dumps(profile_payload), encoding="utf-8"
    )

    statement_payloads = {
        "Q16": {
            "entity_id": "Q16",
            "entity": {
                "labels": {"mul": {"value": "instance of"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string("http://www.wikidata.org/entity/P31")
                    ],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                },
            },
        },
        "Q30": {
            "entity_id": "Q30",
            "entity": {
                "labels": {"mul": {"value": "stated in"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P248"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P161": [_build_entity_claim_entity_id("Q28")],
                },
            },
        },
        "Q41": {
            "entity_id": "Q41",
            "entity": {
                "labels": {"mul": {"value": "applies to jurisdiction"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P1001"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P161": [_build_entity_claim_entity_id("Q43")],
                },
            },
        },
        "Q28": {
            "entity_id": "Q28",
            "entity": {
                "labels": {"mul": {"value": "List of Federal Register Sources"}},
                "claims": {
                    "P1": [_build_entity_claim_entity_id("Q7")],
                },
            },
        },
        "Q43": {
            "entity_id": "Q43",
            "entity": {
                "labels": {"mul": {"value": "List of Tribal Jurisdictions"}},
                "claims": {
                    "P1": [_build_entity_claim_entity_id("Q7")],
                },
            },
        },
    }

    for entity_id, payload in statement_payloads.items():
        (cache_entities_dir / f"{entity_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    docs = build_entity_profile_json_documents(cache_entities_dir)

    assert len(docs) == 1
    value_list_graph = docs[0]["metadata"]["value_list_graph"]
    assert value_list_graph == [
        {
            "entity": "https://datadistillery.wikibase.cloud/entity/Q43",
            "label": "List of Tribal Jurisdictions",
            "via_statement": "https://datadistillery.wikibase.cloud/entity/Q41",
            "cache_path": "cache/queries/Q43.json",
        },
        {
            "entity": "https://datadistillery.wikibase.cloud/entity/Q28",
            "label": "List of Federal Register Sources",
            "via_statement": "https://datadistillery.wikibase.cloud/entity/Q30",
            "cache_path": "cache/queries/Q28.json",
        },
    ]
