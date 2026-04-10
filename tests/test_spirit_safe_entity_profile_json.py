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


def _default_semantic_anchor_document() -> dict:
    return {
        "entities": {
            "_instance_of": {"id": "P1", "datatype": "wikibase-item"},
            "_subclass_of": {"id": "P2", "datatype": "wikibase-item"},
            "_name_identifier": {"id": "P214", "datatype": "string"},
            "_same_as": {"id": "P5", "datatype": "url"},
            "_has_statement": {"id": "P157", "datatype": "wikibase-item"},
            "_has_value": {"id": "P161", "datatype": "wikibase-item"},
            "_has_qualifier": {"id": "P158", "datatype": "wikibase-item"},
            "_has_reference": {"id": "P211", "datatype": "wikibase-item"},
            "_applies_to_profile": {"id": "P205", "datatype": "wikibase-item"},
            "_applies_to_statement": {"id": "P163", "datatype": "wikibase-item"},
            "_statement_type": {"id": "P194", "datatype": "wikibase-item"},
            "_max_count": {"id": "P182", "datatype": "quantity"},
            "_statement_prompt": {"id": "P171", "datatype": "monolingualtext"},
            "_statement_guidance": {"id": "P169", "datatype": "monolingualtext"},
            "_consequences_message": {"id": "P170", "datatype": "monolingualtext"},
            "_error_message": {"id": "P168", "datatype": "monolingualtext"},
            "_label_prompt": {"id": "P188", "datatype": "monolingualtext"},
            "_label_guidance": {"id": "P185", "datatype": "monolingualtext"},
            "_description_prompt": {"id": "P189", "datatype": "monolingualtext"},
            "_description_guidance": {"id": "P186", "datatype": "monolingualtext"},
            "_alias_prompt": {"id": "P190", "datatype": "monolingualtext"},
            "_alias_guidance": {"id": "P187", "datatype": "monolingualtext"},
            "_derives_default_value_from": {"id": "P213", "datatype": "wikibase-item"},
            "_entity": {"id": "Q1"},
            "_entity_profile": {"id": "Q3"},
            "_entity_statement": {"id": "Q5"},
            "_value_list": {"id": "Q7"},
            "_wikibase_statement_modifier": {"id": "Q58"},
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

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

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
    result = export_entity_profile_json_documents(
        cache_entities_dir,
        output_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

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

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

    assert len(docs) == 1
    value_list_graph = docs[0]["metadata"]["value_list_graph"]
    assert value_list_graph == [
        {
            "id": "https://datadistillery.wikibase.cloud/entity/Q43",
            "entity": "https://datadistillery.wikibase.cloud/entity/Q43",
            "label": "List of Tribal Jurisdictions",
            "via_statement": "https://datadistillery.wikibase.cloud/entity/Q41",
            "value_list_id": "Q43",
        },
        {
            "id": "https://datadistillery.wikibase.cloud/entity/Q28",
            "entity": "https://datadistillery.wikibase.cloud/entity/Q28",
            "label": "List of Federal Register Sources",
            "via_statement": "https://datadistillery.wikibase.cloud/entity/Q30",
            "value_list_id": "Q28",
        },
    ]


def test_linkage_index_maps_statement_property_and_target_profile(tmp_path):
    """Metadata linkage index should include statement -> property -> profile map."""

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
                                "value": {"id": "Q40"},
                            }
                        }
                    }
                ],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(
        json.dumps(profile_payload), encoding="utf-8"
    )

    statement_payloads = {
        "Q40": {
            "entity_id": "Q40",
            "entity": {
                "labels": {"mul": {"value": "office held by head of government"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P1313"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P161": [_build_entity_claim_entity_id("Q39")],
                    "P171": [_build_entity_claim_monolingual("Statement prompt")],
                },
            },
        },
        "Q39": {
            "entity_id": "Q39",
            "entity": {
                "labels": {"mul": {"value": "Office Held by Head of Government"}},
                "claims": {
                    "P1": [_build_entity_claim_entity_id("Q3")],
                    "P188": [_build_entity_claim_monolingual("Target label prompt")],
                    "P189": [
                        _build_entity_claim_monolingual("Target description prompt")
                    ],
                    "P190": [_build_entity_claim_monolingual("Target aliases prompt")],
                },
            },
        },
        "Q52": {
            "entity_id": "Q52",
            "entity": {
                "labels": {"mul": {"value": "Wikidata Entity"}},
                "claims": {},
            },
        },
    }

    for entity_id, payload in statement_payloads.items():
        (cache_entities_dir / f"{entity_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

    source_doc = next(
        doc
        for doc in docs
        if doc["id"] == "https://datadistillery.wikibase.cloud/entity/Q4"
    )
    linkage_index = source_doc["metadata"]["linkage_index"]
    assert linkage_index == {
        "outbound_by_statement": {
            "https://datadistillery.wikibase.cloud/entity/Q40": {
                "wikidata_properties": ["P1313"],
                "target_profiles": ["https://datadistillery.wikibase.cloud/entity/Q39"],
            }
        },
        "inbound_by_wikidata_property": {
            "P1313": [
                {
                    "source_profile": "https://datadistillery.wikibase.cloud/entity/Q4",
                    "source_statement": "https://datadistillery.wikibase.cloud/entity/Q40",
                    "target_profile": "https://datadistillery.wikibase.cloud/entity/Q39",
                }
            ]
        },
    }


def test_profile_statement_has_value_link_to_wikidata_entity_emits_fixed_value_list(
    tmp_path,
):
    """P161 links to Q52-typed entities should emit fixed value list entries."""

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
                        "mainsnak": {
                            "datavalue": {
                                "value": {"id": "Q16"},
                            }
                        },
                        "qualifiers": {
                            "P161": [_build_qualifier_entity_id("Q54")],
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
        "Q54": {
            "entity_id": "Q54",
            "entity": {
                "labels": {
                    "mul": {
                        "value": "federally recognized Native American tribe in the United States"
                    }
                },
                "claims": {
                    "P1": [_build_entity_claim_entity_id("Q52")],
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/Q7840353"
                        )
                    ],
                },
            },
        },
        "Q52": {
            "entity_id": "Q52",
            "entity": {
                "labels": {"mul": {"value": "Wikidata Entity"}},
                "claims": {},
            },
        },
    }

    for entity_id, payload in statement_payloads.items():
        (cache_entities_dir / f"{entity_id}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )
    value_payload = docs[0]["statements"][0]["value"]

    assert value_payload["value_list"] == [
        {
            "item": "Q7840353",
            "itemLabel": "federally recognized Native American tribe in the United States",
        }
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

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

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

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

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
                    "P5": [
                        _build_entity_claim_string("http://www.wikidata.org/entity/P31")
                    ],
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
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P1001"
                        )
                    ],
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

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )
    qualifier = docs[0]["statements"][0]["qualifiers"][0]
    assert qualifier["value"]["value_list_id"] == "Q43"


def test_profile_level_p158_claim_supersedes_statement_level_defaults(tmp_path):
    """Profile-level P158 claim should fully supersede all statement-level qualifier defaults.

    When a profile carries P158 (has qualifier) claims targeting a specific statement
    via P163 (applies to statement), those override claims replace the entire set of
    qualifier defaults from the underlying statement entity — not just the same-entity
    entries.  Statement-level defaults that lack a profile counterpart are dropped.
    """

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
                            "P171": [
                                _build_qualifier_monolingual(
                                    "Override qualifier prompt"
                                )
                            ],
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
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P1001"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q52")],
                    "P171": [
                        _build_entity_claim_monolingual("Default qualifier prompt")
                    ],
                },
            },
        },
        "Q42": {
            "entity_id": "Q42",
            "entity": {
                "labels": {"mul": {"value": "point in time"}},
                "claims": {
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P585"
                        )
                    ],
                    "P194": [_build_entity_claim_entity_id("Q55")],
                    "P171": [
                        _build_entity_claim_monolingual("Untouched qualifier prompt")
                    ],
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

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )
    qualifiers = docs[0]["statements"][0]["qualifiers"]
    by_entity = {entry["entity"].rsplit("/", 1)[-1]: entry for entry in qualifiers}

    # Profile override (Q41) is present; statement-default Q42 is dropped entirely.
    assert set(by_entity.keys()) == {"Q41"}
    assert by_entity["Q41"]["messages"]["mul"]["prompt"] == "Override qualifier prompt"


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
                    "P5": [
                        _build_entity_claim_string("http://www.wikidata.org/entity/P31")
                    ],
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
                    "P5": [
                        _build_entity_claim_string(
                            "http://www.wikidata.org/entity/P361"
                        )
                    ],
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

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )
    by_entity = {
        entry["entity"].rsplit("/", 1)[-1]: entry for entry in docs[0]["statements"]
    }

    assert by_entity["Q16"]["max_count"] == 1
    assert by_entity["Q17"]["max_count"] == 2


def test_export_json_skips_profile_when_mul_label_prompt_coverage_fails(tmp_path):
    """Missing mul label prompt should skip writing a profile."""

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
                "P189": [_build_entity_claim_monolingual("Enter description")],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(json.dumps(payload), encoding="utf-8")

    output_dir = tmp_path / "profiles"
    result = export_entity_profile_json_documents(
        cache_entities_dir,
        output_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

    assert result.written_ids == []
    assert result.skipped_ids == ["Q4"]
    assert len(result.failures) == 1
    assert result.failures[0]["profile_id"] == "Q4"
    assert "identification.labels.mul.prompt" in result.failures[0]["missing_paths"]
    assert not (output_dir / "Q4.json").exists()


def test_export_json_filters_languages_missing_label_prompt(tmp_path):
    """Languages without label prompts should be excluded from written JSON profile."""

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
                    _build_entity_claim_monolingual("Enter label", "en"),
                ],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(json.dumps(payload), encoding="utf-8")

    output_dir = tmp_path / "profiles"
    result = export_entity_profile_json_documents(
        cache_entities_dir,
        output_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

    assert result.written_ids == ["Q4"]
    assert result.skipped_ids == []
    assert len(result.language_filtering) == 1
    assert result.language_filtering[0]["profile_id"] == "Q4"
    excluded = {
        entry["language"]
        for entry in result.language_filtering[0]["excluded_languages"]
    }
    assert excluded == {"en", "es"}

    written = json.loads((output_dir / "Q4.json").read_text(encoding="utf-8"))
    assert written["metadata"]["languages"] == ["mul"]
    assert "es" not in written["identification"]["labels"]
    assert "es" not in written["metadata"]["labels"]


def test_statement_node_emits_entity_classes_from_p1(tmp_path):
    """Built statement nodes should include entity_classes derived from P1 claims."""

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
                        "mainsnak": {
                            "datavalue": {"value": {"id": "Q57"}},
                        }
                    }
                ],
            },
        },
    }
    (cache_entities_dir / "Q4.json").write_text(
        json.dumps(profile_payload), encoding="utf-8"
    )

    statement_payload = {
        "entity_id": "Q57",
        "entity": {
            "labels": {"mul": {"value": "units"}},
            "claims": {
                "P1": [
                    _build_entity_claim_entity_id("Q5"),
                    _build_entity_claim_entity_id("Q58"),
                ],
                "P194": [_build_entity_claim_entity_id("Q16")],
                "P171": [_build_entity_claim_monolingual("Select units")],
            },
        },
    }
    (cache_entities_dir / "Q57.json").write_text(
        json.dumps(statement_payload), encoding="utf-8"
    )

    value_type_payload = {
        "entity_id": "Q16",
        "entity": {
            "labels": {"mul": {"value": "wikibase-item"}},
            "claims": {},
        },
    }
    (cache_entities_dir / "Q16.json").write_text(
        json.dumps(value_type_payload), encoding="utf-8"
    )

    docs = build_entity_profile_json_documents(
        cache_entities_dir,
        semantic_anchor_document=_default_semantic_anchor_document(),
    )

    assert len(docs) == 1
    assert len(docs[0]["statements"]) == 1
    statement_node = docs[0]["statements"][0]
    assert "entity_classes" in statement_node
    assert set(statement_node["entity_classes"]) == {"Q5", "Q58"}
