"""Tests for Wikibase-specific helpers and registries."""

import pytest

import gkc
from gkc.wikibase import (
    MetaWikibaseInitEntity,
    MetaWikibaseInitIndex,
    WikibaseDatatypeSpec,
    build_meta_wikibase_init_index,
    canonicalize_wikibase_datatype,
    get_meta_wikibase_init_entity,
    get_wikibase_datatype_spec,
    is_known_wikibase_datatype,
    is_wikibase_item_datatype,
    list_wikibase_datatypes,
    load_meta_wikibase_init_document,
    load_wikibase_datatype_registry,
    load_wikibase_datatype_registry_json,
    normalize_meta_wikibase_init_document,
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

    properties = document["entities"]["wikibase_entities"]["properties"]
    assert properties["instance_of"]["datatype"] == "wikibase-item"
    assert properties["name_identifier"]["datatype"] == "string"
    assert properties["see_also"]["datatype"] == "url"


def test_normalize_meta_wikibase_init_document_transforms_prototype_datatypes():
    prototype = {
        "metadata": {"internal_name_identifier_prefix": "_"},
        "entities": {
            "wikibase_entities": {
                "properties": {
                    "instance_of": {
                        "label": "instance of",
                        "description": "type relation",
                        "datatype": "WikibaseItem",
                    },
                    "same_as": {
                        "label": "same as",
                        "description": "identity relation",
                        "datatype": "http://wikiba.se/ontology#Url",
                    },
                },
                "items": {
                    "entity": {
                        "label": "entity",
                        "description": "root entity",
                    }
                },
            }
        },
    }

    normalized = normalize_meta_wikibase_init_document(prototype)

    properties = normalized["entities"]["wikibase_entities"]["properties"]
    assert properties["instance_of"]["datatype"] == "wikibase-item"
    assert properties["same_as"]["datatype"] == "url"
    assert properties["instance_of"]["kind"] == "property"
    assert normalized["entities"]["wikibase_entities"]["items"]["entity"]["kind"] == "item"


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
        "error_message": "Item must be or resolve to a valid QID identifier."
    }


def test_wikibase_helpers_are_exported_from_package_namespace():
    """Top-level gkc exports include the initial wikibase registry helpers."""
    assert hasattr(gkc, "MetaWikibaseInitEntity")
    assert hasattr(gkc, "MetaWikibaseInitIndex")
    assert hasattr(gkc, "MetaWikibaseInitMetadata")
    assert hasattr(gkc, "WikibaseDatatypeSpec")
    assert hasattr(gkc, "build_meta_wikibase_init_index")
    assert hasattr(gkc, "canonicalize_wikibase_datatype")
    assert hasattr(gkc, "get_meta_wikibase_init_entity")
    assert hasattr(gkc, "get_wikibase_datatype_spec")
    assert hasattr(gkc, "is_known_wikibase_datatype")
    assert hasattr(gkc, "is_wikibase_item_datatype")
    assert hasattr(gkc, "list_wikibase_datatypes")
    assert hasattr(gkc, "load_meta_wikibase_init_document")
    assert hasattr(gkc, "load_wikibase_datatype_registry")
    assert hasattr(gkc, "load_wikibase_datatype_registry_json")
    assert hasattr(gkc, "normalize_meta_wikibase_init_document")