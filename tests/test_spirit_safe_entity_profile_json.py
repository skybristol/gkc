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


def _build_entity_claim_quantity(amount: str) -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": {
                    "amount": amount,
                }
            }
        }
    }


def _build_entity_claim_monolingual(text: str, language: str = "mul") -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": {
                    "text": text,
                    "language": language,
                }
            }
        }
    }


def _build_qualifier_monolingual(text: str, language: str = "mul") -> dict:
    return {
        "datavalue": {
            "value": {
                "text": text,
                "language": language,
            }
        }
    }


def _build_qualifier_quantity(amount: str) -> dict:
    return {
        "datavalue": {
            "value": {
                "amount": amount,
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
            "labels": {
                "mul": {"value": "Tribal Government in the United States"},
                "en": {"value": "Tribal Government in the United States"},
            },
            "descriptions": {"en": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                "P190": [_build_entity_claim_monolingual("Enter aliases")],
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
            "labels": {
                "mul": {"value": "Tribal Government in the United States"},
                "en": {"value": "Tribal Government in the United States"},
            },
            "descriptions": {"en": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                "P190": [_build_entity_claim_monolingual("Enter aliases")],
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
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                "P190": [_build_entity_claim_monolingual("Enter aliases")],
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
                    "P171": [_build_entity_claim_monolingual("Statement prompt")],
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
                    "P171": [_build_entity_claim_monolingual("Reference prompt")],
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
                    "P171": [_build_entity_claim_monolingual("Qualifier prompt")],
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


def test_reference_statement_derives_value_from_parent_statement(tmp_path):
    """Nested reference should expose statement_value source when P213 matches parent."""

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
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                "P190": [_build_entity_claim_monolingual("Enter aliases")],
                "P157": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"id": "Q19"},
                            }
                        },
                        "qualifiers": {
                            "P211": [_build_qualifier_entity_id("Q29")],
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
        "Q19": {
            "entity_id": "Q19",
            "entity": {
                "labels": {"mul": {"value": "official website"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P856"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q54")],
                    "P171": [
                        _build_entity_claim_monolingual("Official website prompt")
                    ],
                },
            },
        },
        "Q29": {
            "entity_id": "Q29",
            "entity": {
                "labels": {"mul": {"value": "reference URL"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P854"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q54")],
                    "P213": [_build_entity_claim_entity_id("Q19")],
                    "P171": [_build_entity_claim_monolingual("Reference URL prompt")],
                },
            },
        },
        "Q54": {
            "entity_id": "Q54",
            "entity": {
                "labels": {"mul": {"value": "url"}},
                "claims": {
                    "P1": [_build_entity_claim_entity_id("Q44")],
                },
            },
        },
    }

    for entity_id, payload in statement_payloads.items():
        (cache_entities_dir / f"{entity_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    docs = build_entity_profile_json_documents(cache_entities_dir)

    references = docs[0]["statements"][0]["references"]
    assert len(references) == 1
    assert references[0]["value"]["value_source"] == "statement_value"
    assert references[0]["value"]["value_source_statement"] == (
        "https://datadistillery.wikibase.cloud/entity/Q19"
    )


def test_reference_statement_derived_value_respects_profile_scope(tmp_path):
    """P205 profile scoping should prevent derived value source outside scope."""

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
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                "P190": [_build_entity_claim_monolingual("Enter aliases")],
                "P157": [
                    {
                        "mainsnak": {
                            "datavalue": {
                                "value": {"id": "Q19"},
                            }
                        },
                        "qualifiers": {
                            "P211": [_build_qualifier_entity_id("Q29")],
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
        "Q19": {
            "entity_id": "Q19",
            "entity": {
                "labels": {"mul": {"value": "official website"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P856"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q54")],
                    "P171": [
                        _build_entity_claim_monolingual("Official website prompt")
                    ],
                },
            },
        },
        "Q29": {
            "entity_id": "Q29",
            "entity": {
                "labels": {"mul": {"value": "reference URL"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P854"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q54")],
                    "P213": [
                        {
                            "mainsnak": {
                                "datavalue": {
                                    "value": {"id": "Q19"},
                                }
                            },
                            "qualifiers": {
                                "P205": [_build_qualifier_entity_id("Q39")],
                            },
                        }
                    ],
                    "P171": [_build_entity_claim_monolingual("Reference URL prompt")],
                },
            },
        },
        "Q54": {
            "entity_id": "Q54",
            "entity": {
                "labels": {"mul": {"value": "url"}},
                "claims": {
                    "P1": [_build_entity_claim_entity_id("Q44")],
                },
            },
        },
    }

    for entity_id, payload in statement_payloads.items():
        (cache_entities_dir / f"{entity_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    docs = build_entity_profile_json_documents(cache_entities_dir)

    references = docs[0]["statements"][0]["references"]
    assert len(references) == 1
    assert "value_source" not in references[0]["value"]
    assert "value_source_statement" not in references[0]["value"]


def test_statement_level_value_claim_respects_p163_parent_scope(tmp_path):
    """Statement-level P161 with P163 should apply only when parent statement matches."""

    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    profile_payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"mul": {"value": "Example profile"}},
            "descriptions": {"mul": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                "P190": [_build_entity_claim_monolingual("Enter aliases")],
                "P157": [
                    {
                        "mainsnak": {"datavalue": {"value": {"id": "Q16"}}},
                        "qualifiers": {
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
                    "P5": [_build_entity_claim_string("http://www.wikidata.org/entity/P31")],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P171": [_build_entity_claim_monolingual("Statement prompt")],
                },
            },
        },
        "Q41": {
            "entity_id": "Q41",
            "entity": {
                "labels": {"mul": {"value": "applies to jurisdiction"}},
                "claims": {
                    "P5": [_build_entity_claim_string("http://www.wikidata.org/entity/P1001")],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P171": [_build_entity_claim_monolingual("Qualifier prompt")],
                    "P161": [
                        {
                            "mainsnak": {"datavalue": {"value": {"id": "Q43"}}},
                            "qualifiers": {
                                "P163": [_build_qualifier_entity_id("Q16")],
                            },
                        }
                    ],
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
        "Q52": {
            "entity_id": "Q52",
            "entity": {
                "labels": {"mul": {"value": "wikibase-item"}},
                "claims": {"P1": [_build_entity_claim_entity_id("Q44")]},
            },
        },
        "Q54": {
            "entity_id": "Q54",
            "entity": {
                "labels": {"mul": {"value": "url"}},
                "claims": {"P1": [_build_entity_claim_entity_id("Q44")]},
            },
        },
        "Q7": {
            "entity_id": "Q7",
            "entity": {
                "labels": {"mul": {"value": "GKC Value List"}},
                "claims": {"P1": [_build_entity_claim_entity_id("Q1")]},
            },
        },
        "Q1": {
            "entity_id": "Q1",
            "entity": {
                "labels": {"mul": {"value": "Root class"}},
                "claims": {},
            },
        },
    }

    for entity_id, payload in statement_payloads.items():
        (cache_entities_dir / f"{entity_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    docs = build_entity_profile_json_documents(cache_entities_dir)
    qualifier = docs[0]["statements"][0]["qualifiers"][0]
    assert qualifier["value"]["value_list_reference"] == "cache/queries/Q43.json"


def test_profile_level_p158_claim_overrides_targeted_nested_statement_only(tmp_path):
    """Profile-level P158 claim should override only the targeted nested statement spec."""

    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    profile_payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"mul": {"value": "Example profile"}},
            "descriptions": {"mul": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                "P190": [_build_entity_claim_monolingual("Enter aliases")],
                "P157": [
                    {
                        "mainsnak": {"datavalue": {"value": {"id": "Q16"}}},
                    }
                ],
                "P158": [
                    {
                        "mainsnak": {"datavalue": {"value": {"id": "Q41"}}},
                        "qualifiers": {
                            "P163": [_build_qualifier_entity_id("Q16")],
                            "P171": [_build_qualifier_monolingual("Override qualifier prompt")],
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
                    "P5": [_build_entity_claim_string("http://www.wikidata.org/entity/P31")],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P171": [_build_entity_claim_monolingual("Statement prompt")],
                    "P158": [
                        _build_entity_claim_entity_id("Q41"),
                        _build_entity_claim_entity_id("Q42"),
                    ],
                },
            },
        },
        "Q41": {
            "entity_id": "Q41",
            "entity": {
                "labels": {"mul": {"value": "applies to jurisdiction"}},
                "claims": {
                    "P5": [_build_entity_claim_string("http://www.wikidata.org/entity/P1001")],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P171": [_build_entity_claim_monolingual("Default qualifier prompt")],
                },
            },
        },
        "Q42": {
            "entity_id": "Q42",
            "entity": {
                "labels": {"mul": {"value": "point in time"}},
                "claims": {
                    "P5": [_build_entity_claim_string("http://www.wikidata.org/entity/P585")],
                    "P194": [_build_entity_claim_entity_id("Q55")],
                    "P171": [_build_entity_claim_monolingual("Untouched qualifier prompt")],
                },
            },
        },
        "Q52": {
            "entity_id": "Q52",
            "entity": {
                "labels": {"mul": {"value": "wikibase-item"}},
                "claims": {"P1": [_build_entity_claim_entity_id("Q44")]},
            },
        },
        "Q55": {
            "entity_id": "Q55",
            "entity": {
                "labels": {"mul": {"value": "time"}},
                "claims": {"P1": [_build_entity_claim_entity_id("Q44")]},
            },
        },
    }

    for entity_id, payload in statement_payloads.items():
        (cache_entities_dir / f"{entity_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    docs = build_entity_profile_json_documents(cache_entities_dir)
    qualifiers = docs[0]["statements"][0]["qualifiers"]
    by_entity = {entry["entity"].rsplit("/", 1)[-1]: entry for entry in qualifiers}

    assert set(by_entity.keys()) == {"Q41", "Q42"}
    assert by_entity["Q41"]["messages"]["mul"]["prompt"] == "Override qualifier prompt"
    assert by_entity["Q42"]["messages"]["mul"]["prompt"] == "Untouched qualifier prompt"


def test_profile_level_max_count_overrides_statement_level_baseline(tmp_path):
    """Statement baseline max_count should be replaced only when P157 qualifier sets P182."""

    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    profile_payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"mul": {"value": "Example profile"}},
            "descriptions": {"mul": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                "P190": [_build_entity_claim_monolingual("Enter aliases")],
                "P157": [
                    {
                        "mainsnak": {"datavalue": {"value": {"id": "Q16"}}},
                        "qualifiers": {
                            "P182": [_build_qualifier_quantity("+1")],
                        },
                    },
                    {
                        "mainsnak": {"datavalue": {"value": {"id": "Q17"}}},
                    },
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
                    "P5": [_build_entity_claim_string("http://www.wikidata.org/entity/P31")],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P171": [_build_entity_claim_monolingual("Statement prompt")],
                    "P182": [_build_entity_claim_quantity("+3")],
                },
            },
        },
        "Q17": {
            "entity_id": "Q17",
            "entity": {
                "labels": {"mul": {"value": "part of"}},
                "claims": {
                    "P5": [_build_entity_claim_string("http://www.wikidata.org/entity/P361")],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P171": [_build_entity_claim_monolingual("Statement prompt")],
                    "P182": [_build_entity_claim_quantity("+2")],
                },
            },
        },
        "Q52": {
            "entity_id": "Q52",
            "entity": {
                "labels": {"mul": {"value": "wikibase-item"}},
                "claims": {"P1": [_build_entity_claim_entity_id("Q44")]},
            },
        },
    }

    for entity_id, payload in statement_payloads.items():
        (cache_entities_dir / f"{entity_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    docs = build_entity_profile_json_documents(cache_entities_dir)
    by_entity = {
        entry["entity"].rsplit("/", 1)[-1]: entry for entry in docs[0]["statements"]
    }

    assert by_entity["Q16"]["max_count"] == 1
    assert by_entity["Q17"]["max_count"] == 2


def test_export_json_skips_profile_when_mul_language_coverage_fails(tmp_path):
    """Invalid mul coverage should skip writing profile and report failure."""

    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {"mul": {"value": "Tribal Government in the United States"}},
            "descriptions": {"en": {"value": "Example profile"}},
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
                "P188": [_build_entity_claim_monolingual("Enter label")],
                "P189": [_build_entity_claim_monolingual("Enter description")],
                # Intentionally missing P190 mul prompt.
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(json.dumps(payload), encoding="utf-8")

    output_dir = tmp_path / "profiles"
    result = export_entity_profile_json_documents(cache_entities_dir, output_dir)

    assert result.written_ids == []
    assert result.skipped_ids == ["Q4"]
    assert len(result.failures) == 1
    assert result.failures[0]["profile_id"] == "Q4"
    assert "identification.aliases.mul.prompt" in result.failures[0]["missing_paths"]
    assert not (output_dir / "Q4.json").exists()


def test_export_json_filters_incomplete_non_mul_language(tmp_path):
    """Incomplete non-mul languages should be excluded from written JSON profile."""

    cache_entities_dir = tmp_path / "cache" / "entities"
    cache_entities_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "entity_id": "Q4",
        "entity": {
            "labels": {
                "mul": {"value": "Tribal Government in the United States"},
                "es": {"value": "Gobierno tribal en los Estados Unidos"},
            },
            "descriptions": {
                "en": {"value": "Example profile"},
                "es": {"value": "Perfil de ejemplo"},
            },
            "aliases": {},
            "claims": {
                "P1": [_build_entity_claim_entity_id("Q3")],
                "P188": [
                    _build_entity_claim_monolingual("Enter label", "mul"),
                    _build_entity_claim_monolingual("Ingrese etiqueta", "es"),
                ],
                "P189": [
                    _build_entity_claim_monolingual("Enter description", "mul"),
                    _build_entity_claim_monolingual("Ingrese descripcion", "es"),
                ],
                # Include only mul alias prompt so es is filtered as incomplete.
                "P190": [_build_entity_claim_monolingual("Enter aliases", "mul")],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(json.dumps(payload), encoding="utf-8")

    output_dir = tmp_path / "profiles"
    result = export_entity_profile_json_documents(cache_entities_dir, output_dir)

    assert result.written_ids == ["Q4"]
    assert result.skipped_ids == []
    assert len(result.language_filtering) == 1
    assert result.language_filtering[0]["profile_id"] == "Q4"
    excluded = {
        entry["language"]
        for entry in result.language_filtering[0]["excluded_languages"]
    }
    assert "es" in excluded

    written = json.loads((output_dir / "Q4.json").read_text(encoding="utf-8"))
    assert written["metadata"]["languages"] == ["mul"]
    assert "es" not in written["identification"]["labels"]
    assert "es" not in written["metadata"]["labels"]
