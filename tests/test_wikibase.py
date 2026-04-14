"""Tests for Wikibase-specific helpers and registries."""

from copy import deepcopy

import pytest

import gkc
from gkc import bottler
from gkc.wikibase import (
    MetaWikibaseCompiledEntity,
    MetaWikibaseInitEntity,
    MetaWikibaseInitIndex,
    MetaWikibaseSeedCompilation,
    MetaWikibaseSeedPlan,
    MetaWikibaseSemanticAnchorContract,
    WikibaseDatatypeSpec,
    build_meta_wikibase_init_index,
    build_meta_wikibase_semantic_anchor_contract,
    canonicalize_wikibase_datatype,
    compile_meta_wikibase_seed,
    get_meta_wikibase_init_entity,
    get_wikibase_datatype_spec,
    is_known_wikibase_datatype,
    is_wikibase_item_datatype,
    list_wikibase_datatypes,
    load_meta_wikibase_init_document,
    load_wikibase_datatype_registry,
    load_wikibase_datatype_registry_json,
    normalize_meta_wikibase_init_document,
    plan_meta_wikibase_seed_baseline,
)


def test_load_wikibase_datatype_registry():
    """Registry loads as typed entries keyed by canonical datatype token."""
    registry = load_wikibase_datatype_registry()

    assert "wikibase-item" in registry
    assert isinstance(registry["wikibase-item"], WikibaseDatatypeSpec)
    assert registry["wikibase-item"].ontology_uri == (
        "http://wikiba.se/ontology#WikibaseItem"
    )
    assert registry["wikibase-item"].datavalue_type == "wikibase-entityid"
    assert registry["wikibase-item"].entity_value_kind == "item"


def test_get_wikibase_datatype_spec_returns_one_entry():
    """Single-entry access resolves a canonical runtime datatype token."""
    spec = get_wikibase_datatype_spec("url")

    assert spec.ontology_uri == "http://wikiba.se/ontology#Url"
    assert spec.datavalue_type == "string"
    assert spec.entity_value_kind is None


def test_get_wikibase_datatype_spec_raises_for_unknown_name():
    """Unknown datatype lookups fail loudly with the canonical token included."""
    with pytest.raises(KeyError, match="Unknown Wikibase datatype: not-a-datatype"):
        get_wikibase_datatype_spec("not-a-datatype")


def test_canonicalize_wikibase_datatype_normalizes_aliases():
    assert canonicalize_wikibase_datatype("item") == "wikibase-item"
    assert canonicalize_wikibase_datatype("globecoordinate") == "globe-coordinate"
    assert canonicalize_wikibase_datatype("WikibaseItem") == "wikibase-item"
    assert canonicalize_wikibase_datatype("http://wikiba.se/ontology#Url") == "url"
    assert canonicalize_wikibase_datatype("string") == "string"


def test_wikibase_datatype_predicates_use_registry_contract():
    assert is_known_wikibase_datatype("item") is True
    assert is_known_wikibase_datatype("external-id") is True
    assert is_known_wikibase_datatype("not-a-datatype") is False
    assert is_wikibase_item_datatype("item") is True
    assert is_wikibase_item_datatype("wikibase-item") is True
    assert is_wikibase_item_datatype("string") is False


def test_list_wikibase_datatypes_is_sorted():
    """Datatype listing is stable and sorted for deterministic use."""
    datatypes = list_wikibase_datatypes()

    assert datatypes == sorted(datatypes)
    assert "time" in datatypes
    assert "tabular-data" in datatypes


def test_load_wikibase_datatype_registry_json_round_trips_shape():
    """Raw JSON-compatible registry output preserves the package artifact shape."""
    registry = load_wikibase_datatype_registry_json()

    assert registry["globe-coordinate"]["ontology_uri"] == (
        "http://wikiba.se/ontology#Globecoordinate"
    )
    assert registry["globe-coordinate"]["datavalue_type"] == "globecoordinate"
    assert "entity_value_kind" not in registry["globe-coordinate"]


def test_load_meta_wikibase_init_document_uses_canonical_datatypes():
    document = load_meta_wikibase_init_document()

    entities = document["entities"]
    assert entities["instance_of"]["datatype"] == "wikibase-item"
    assert entities["name_identifier"]["datatype"] == "string"
    assert entities["see_also"]["datatype"] == "url"


def test_normalize_meta_wikibase_init_document_transforms_prototype_datatypes():
    prototype = {
        "metadata": {
            "internal_name_identifier_prefix": "_",
            "languages": ["en"],
        },
        "entities": {
            "instance_of": {
                "kind": "property",
                "label_en": "instance of",
                "description_en": "type relation",
                "datatype": "WikibaseItem",
            },
            "same_as": {
                "kind": "property",
                "label_en": "same as",
                "description_en": "identity relation",
                "datatype": "http://wikiba.se/ontology#Url",
            },
            "entity": {
                "kind": "item",
                "label_en": "entity",
                "description_en": "root entity",
            },
            "error_message": {
                "kind": "property",
                "label_en": "error message",
                "description_en": "message",
                "datatype": "monolingualtext",
            },
            "wikibase-item": {
                "kind": "item",
                "label_en": "wikibase-item",
                "description_en": "type item",
                "error_message_en": "Item must be or resolve to a valid QID identifier.",
            },
        },
    }

    normalized = normalize_meta_wikibase_init_document(prototype)

    entities = normalized["entities"]
    assert entities["instance_of"]["datatype"] == "wikibase-item"
    assert entities["same_as"]["datatype"] == "url"
    assert entities["instance_of"]["kind"] == "property"
    assert entities["entity"]["kind"] == "item"
    assert (
        entities["wikibase-item"]["error_message"]
        == "Item must be or resolve to a valid QID identifier."
    )


def test_normalize_meta_wikibase_init_document_requires_authored_text():
    prototype = {
        "metadata": {"internal_name_identifier_prefix": "_", "languages": ["en"]},
        "entities": {
            "instance_of": {
                "kind": "property",
                "description_en": "type relation",
                "datatype": "wikibase-item",
            }
        },
    }

    with pytest.raises(RuntimeError, match="missing label text"):
        normalize_meta_wikibase_init_document(prototype)


def test_normalize_meta_wikibase_init_document_requires_sparql_fields():
    prototype = {
        "metadata": {"internal_name_identifier_prefix": "_", "languages": ["en"]},
        "entities": {
            "sparql_value_list": {
                "kind": "item",
                "label_en": "SPARQL-backed Value List",
                "description_en": "list",
            },
            "example_values": {
                "kind": "item",
                "instance_of": "sparql_value_list",
                "label_en": "Example values",
                "description_en": "example",
                "refresh_policy": "manual_refresh_policy",
            },
        },
    }

    with pytest.raises(RuntimeError, match="requires 'sparql_endpoint' and 'query'"):
        normalize_meta_wikibase_init_document(prototype)


def test_normalize_meta_wikibase_init_document_requires_embedded_value_list():
    prototype = {
        "metadata": {"internal_name_identifier_prefix": "_", "languages": ["en"]},
        "entities": {
            "embedded_value_list": {
                "kind": "item",
                "label_en": "Embedded Value List",
                "description_en": "list",
            },
            "example_values": {
                "kind": "item",
                "instance_of": "embedded_value_list",
                "label_en": "Example values",
                "description_en": "example",
            },
        },
    }

    with pytest.raises(RuntimeError, match="requires 'value_list'"):
        normalize_meta_wikibase_init_document(prototype)


def test_build_meta_wikibase_init_index_provides_typed_entity_access():
    index = build_meta_wikibase_init_index()

    assert isinstance(index, MetaWikibaseInitIndex)
    assert isinstance(index.properties["instance_of"], MetaWikibaseInitEntity)
    assert index.metadata.internal_name_identifier_prefix == "_"
    assert index.properties["instance_of"].internal_name_identifier == "_instance_of"
    assert index.properties["instance_of"].datatype == "wikibase-item"
    assert index.items["entity_profile"].subclass_of == "entity"
    assert index.by_internal_name_identifier["_string"].key == "string"


def test_get_meta_wikibase_init_entity_returns_one_entry():
    entity = get_meta_wikibase_init_entity("wikibase-item")

    assert entity.kind == "item"
    assert entity.instance_of == "wikibase_statement_type"
    assert entity.attributes == {
        "error_message_mul": "Item must be or resolve to a valid QID identifier."
    }


def test_build_meta_wikibase_semantic_anchor_contract_uses_active_prefix():
    contract = build_meta_wikibase_semantic_anchor_contract(
        internal_name_identifier_prefix="__"
    )

    assert isinstance(contract, MetaWikibaseSemanticAnchorContract)
    assert contract.internal_name_identifier_prefix == "__"
    assert contract.requirements["__entity"].kind == "item"
    assert contract.requirements["__has_statement"].datatype == "wikibase-item"


def test_compile_meta_wikibase_seed_builds_symbolic_payloads():
    compilation = compile_meta_wikibase_seed()

    assert isinstance(compilation, MetaWikibaseSeedCompilation)
    assert isinstance(compilation.entities["instance_of"], MetaWikibaseCompiledEntity)

    property_payload = compilation.entities["instance_of"].payload
    assert property_payload["type"] == "property"
    assert property_payload["datatype"] == "wikibase-item"
    assert property_payload["labels"]["en"]["value"] == "instance of"
    assert (
        property_payload["claims"]["_name_identifier"][0]["mainsnak"]["datavalue"][
            "value"
        ]
        == "_instance_of"
    )

    item_payload = compilation.entities["entity_profile"].payload
    assert item_payload["type"] == "item"
    assert "datatype" not in item_payload
    assert (
        item_payload["claims"]["_subclass_of"][0]["mainsnak"]["datavalue"]["value"][
            "id"
        ]
        == "_entity"
    )
    assert (
        "numeric-id"
        not in item_payload["claims"]["_subclass_of"][0]["mainsnak"]["datavalue"][
            "value"
        ]
    )

    wikibase_item_claims = compilation.entities["wikibase-item"].payload["claims"]
    assert sorted(wikibase_item_claims.keys()) == [
        "_instance_of",
        "_name_identifier",
    ]

    data_size_max_count = compilation.entities["data_size"].payload["claims"][
        "_max_count"
    ][0]
    assert data_size_max_count["mainsnak"]["snaktype"] == "novalue"
    assert "datavalue" not in data_size_max_count["mainsnak"]


def test_compile_meta_wikibase_seed_uses_package_language_for_display_text(
    monkeypatch,
):
    monkeypatch.setattr(gkc, "get_languages", lambda: "fr")

    compilation = compile_meta_wikibase_seed()

    payload = compilation.entities["instance_of"].payload
    assert payload["labels"]["fr"]["value"] == "instance of"
    assert payload["descriptions"]["fr"]["value"] == (
        "type to which this subject belongs or corresponds"
    )


def test_plan_meta_wikibase_seed_baseline_compares_live_state_and_requires_mul():
    current_entities = {
        "_wikibase-item": {
            "id": "Q50",
            "type": "item",
            "labels": {"en": {"language": "en", "value": "wikibase-item"}},
            "descriptions": {
                "en": {
                    "language": "en",
                    "value": "wikibase item property template used to set a data type for a statement, reference, or qualifier and any additional specifications",
                }
            },
            "aliases": {
                "en": [
                    {
                        "language": "en",
                        "value": "_wikibase-item",
                    }
                ]
            },
            "claims": {
                "P1": [
                    {
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P1",
                            "datavalue": {
                                "type": "wikibase-entityid",
                                "value": {
                                    "entity-type": "item",
                                    "id": "Q99",
                                    "numeric-id": 99,
                                },
                            },
                        },
                        "type": "statement",
                        "rank": "normal",
                    }
                ],
                "P214": [
                    {
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P214",
                            "datavalue": {
                                "type": "string",
                                "value": "_wikibase-item",
                            },
                        },
                        "type": "statement",
                        "rank": "normal",
                    }
                ],
                "P168": [
                    {
                        "mainsnak": {
                            "snaktype": "value",
                            "property": "P168",
                            "datavalue": {
                                "type": "monolingualtext",
                                "value": {
                                    "language": "mul",
                                    "text": "Item must be or resolve to a valid QID identifier.",
                                },
                            },
                        },
                        "type": "statement",
                        "rank": "normal",
                    }
                ],
            },
        }
    }
    entity_id_to_internal_name_identifier = {
        "P1": "_instance_of",
        "P168": "_error_message",
        "P214": "_name_identifier",
        "Q99": "_wikibase_statement_type",
    }

    plan = plan_meta_wikibase_seed_baseline(
        current_entities_by_internal_name_identifier=current_entities,
        entity_id_to_internal_name_identifier=entity_id_to_internal_name_identifier,
    )

    matching_entry = next(
        operation
        for operation in plan.operations
        if operation.internal_name_identifier == "_wikibase-item"
    )
    assert matching_entry.action == "skip"
    assert matching_entry.current_entity_id == "Q50"

    data_size_entity = {
        "id": "Q91",
        "type": "item",
        "labels": {"en": {"language": "en", "value": "data size"}},
        "descriptions": {
            "en": {
                "language": "en",
                "value": "size of a software, dataset, neural network, or individual file",
            }
        },
        "claims": {
            "P1": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P1",
                        "datavalue": {
                            "type": "wikibase-entityid",
                            "value": {
                                "entity-type": "item",
                                "id": "Q5",
                                "numeric-id": 5,
                            },
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
            "P214": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P214",
                        "datavalue": {
                            "type": "string",
                            "value": "_data_size",
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
            "P215": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P215",
                        "datavalue": {
                            "type": "wikibase-entityid",
                            "value": {
                                "entity-type": "item",
                                "id": "Q71",
                                "numeric-id": 71,
                            },
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
            "P182": [
                {
                    "mainsnak": {
                        "snaktype": "novalue",
                        "property": "P182",
                        "datatype": "quantity",
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
            "P158": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P158",
                        "datavalue": {
                            "type": "wikibase-entityid",
                            "value": {
                                "entity-type": "item",
                                "id": "Q90",
                                "numeric-id": 90,
                            },
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
            "P171": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P171",
                        "datavalue": {
                            "type": "monolingualtext",
                            "value": {
                                "language": "mul",
                                "text": "enter a value for total size of the data item",
                            },
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
            "P169": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P169",
                        "datavalue": {
                            "type": "monolingualtext",
                            "value": {
                                "language": "mul",
                                "text": "Enter a value for the data size of the subject and specify an appropriate unit of measure",
                            },
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
            "P168": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P168",
                        "datavalue": {
                            "type": "monolingualtext",
                            "value": {
                                "language": "mul",
                                "text": "Failure to provide a data size with the appropriate unit of measure may result in a reduced ability to determine appropriate use of the information",
                            },
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
            "P5": [
                {
                    "mainsnak": {
                        "snaktype": "value",
                        "property": "P5",
                        "datavalue": {
                            "type": "string",
                            "value": "http://www.wikidata.org/entity/P3575",
                        },
                    },
                    "type": "statement",
                    "rank": "normal",
                }
            ],
        },
    }
    novalue_entities = dict(current_entities)
    novalue_entities["_data_size"] = data_size_entity
    novalue_entity_id_to_internal_name_identifier = {
        **entity_id_to_internal_name_identifier,
        "P5": "_same_as",
        "P158": "_has_qualifier",
        "P168": "_error_message",
        "P169": "_statement_guidance",
        "P171": "_statement_prompt",
        "P182": "_max_count",
        "P215": "_statement_type",
        "Q5": "_entity_statement",
        "Q71": "_quantity",
        "Q90": "_data_size_units",
    }
    novalue_plan = plan_meta_wikibase_seed_baseline(
        current_entities_by_internal_name_identifier=novalue_entities,
        entity_id_to_internal_name_identifier=novalue_entity_id_to_internal_name_identifier,
    )
    novalue_entry = next(
        operation
        for operation in novalue_plan.operations
        if operation.internal_name_identifier == "_data_size"
    )
    assert novalue_entry.action == "skip"

    invalid_claim_entities = deepcopy(current_entities)
    invalid_claim_entities["_wikibase-item"]["claims"]["P1"][0]["mainsnak"][
        "datavalue"
    ]["value"]["id"] = "Q100"

    invalid_claim_plan = plan_meta_wikibase_seed_baseline(
        current_entities_by_internal_name_identifier=invalid_claim_entities,
        entity_id_to_internal_name_identifier=entity_id_to_internal_name_identifier,
    )
    invalid_claim_entry = next(
        operation
        for operation in invalid_claim_plan.operations
        if operation.internal_name_identifier == "_wikibase-item"
    )
    assert invalid_claim_entry.action == "update"
    assert "claims._instance_of" in (invalid_claim_entry.changed_fields or [])


def test_compile_meta_wikibase_seed_uses_bottler_primitives(monkeypatch):
    call_counts = {"shell": 0, "claim": 0, "claim_from_datavalue": 0}

    original_build_entity_shell = bottler.EntityShellBuilder.build_entity_shell
    original_create_claim = bottler.ClaimBuilder.create_claim
    original_create_claim_from_datavalue = (
        bottler.ClaimBuilder.create_claim_from_datavalue
    )

    def counting_build_entity_shell(self, entity_metadata):
        call_counts["shell"] += 1
        return original_build_entity_shell(self, entity_metadata)

    def counting_create_claim(
        self,
        property_id,
        value,
        datatype,
        transform_config=None,
        qualifiers=None,
        references=None,
        rank="normal",
    ):
        call_counts["claim"] += 1
        return original_create_claim(
            self,
            property_id,
            value,
            datatype,
            transform_config,
            qualifiers,
            references,
            rank,
        )

    def counting_create_claim_from_datavalue(
        self, property_id, datavalue, qualifiers=None, references=None, rank="normal"
    ):
        call_counts["claim_from_datavalue"] += 1
        return original_create_claim_from_datavalue(
            self,
            property_id,
            datavalue,
            qualifiers=qualifiers,
            references=references,
            rank=rank,
        )

    monkeypatch.setattr(
        bottler.EntityShellBuilder,
        "build_entity_shell",
        counting_build_entity_shell,
    )
    monkeypatch.setattr(
        bottler.ClaimBuilder,
        "create_claim",
        counting_create_claim,
    )
    monkeypatch.setattr(
        bottler.ClaimBuilder,
        "create_claim_from_datavalue",
        counting_create_claim_from_datavalue,
    )

    compilation = compile_meta_wikibase_seed()

    assert len(compilation.entities) > 0
    assert call_counts["shell"] == len(compilation.entities)
    assert call_counts["claim"] > 0
    assert call_counts["claim_from_datavalue"] > 0


def test_plan_meta_wikibase_seed_baseline_returns_dry_run_operations():
    plan = plan_meta_wikibase_seed_baseline()

    assert isinstance(plan, MetaWikibaseSeedPlan)
    assert len(plan.operations) > 0
    assert all(operation.action == "create" for operation in plan.operations)
    assert plan.operations == sorted(
        plan.operations,
        key=lambda operation: operation.internal_name_identifier,
    )
    assert plan.operations[0].payload["type"] in {"item", "property"}


def test_wikibase_helpers_are_exported_from_package_namespace():
    """Top-level gkc exports include the initial wikibase registry helpers."""
    assert hasattr(gkc, "MetaWikibaseCompiledEntity")
    assert hasattr(gkc, "MetaWikibaseInitEntity")
    assert hasattr(gkc, "MetaWikibaseInitIndex")
    assert hasattr(gkc, "MetaWikibaseInitMetadata")
    assert hasattr(gkc, "MetaWikibaseSemanticAnchorContract")
    assert hasattr(gkc, "WikibaseDatatypeSpec")
    assert hasattr(gkc, "MetaWikibaseSeedCompilation")
    assert hasattr(gkc, "MetaWikibaseSeedPlan")
    assert hasattr(gkc, "build_meta_wikibase_init_index")
    assert hasattr(gkc, "build_meta_wikibase_semantic_anchor_contract")
    assert hasattr(gkc, "canonicalize_wikibase_datatype")
    assert hasattr(gkc, "compile_meta_wikibase_seed")
    assert hasattr(gkc, "get_meta_wikibase_init_entity")
    assert hasattr(gkc, "get_wikibase_datatype_spec")
    assert hasattr(gkc, "is_known_wikibase_datatype")
    assert hasattr(gkc, "is_wikibase_item_datatype")
    assert hasattr(gkc, "list_wikibase_datatypes")
    assert hasattr(gkc, "load_meta_wikibase_init_document")
    assert hasattr(gkc, "load_wikibase_datatype_registry")
    assert hasattr(gkc, "load_wikibase_datatype_registry_json")
    assert hasattr(gkc, "normalize_meta_wikibase_init_document")
    assert hasattr(gkc, "plan_meta_wikibase_seed_baseline")
