"""Tests for YAML profile loading and schema generation."""

from pathlib import Path

import pytest

from gkc.profiles import FormSchemaGenerator, ProfileLoader


@pytest.fixture
def profile_fixture_path() -> Path:
    return (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )


@pytest.fixture
def exemplar_fixture_path() -> Path:
    return (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "EntityProfileExemplar"
        / "profile.yaml"
    )


def test_profile_loader_reads_yaml(profile_fixture_path: Path):
    """ProfileLoader parses YAML into a ProfileDefinition."""
    loader = ProfileLoader()
    profile = loader.load_from_file(profile_fixture_path)

    assert profile.name == "Federally Recognized Tribe"
    assert len(profile.statements) >= 7

    instance_field = profile.statement_by_id("instance_of")
    assert instance_field is not None
    assert instance_field.wikidata_property == "P31"
    assert instance_field.references is not None
    assert len(instance_field.references.allowed) == 1
    allowed_items = instance_field.references.allowed[0].allowed_items
    assert allowed_items is not None
    assert allowed_items.query_ref == "queries/bia_federal_register_issues.sparql"
    assert allowed_items.query is None
    assert allowed_items.query_params["federal_register_class_qid"] == "Q121840925"


def test_form_schema_generator(profile_fixture_path: Path):
    """FormSchemaGenerator emits a structured schema."""
    loader = ProfileLoader()
    profile = loader.load_from_file(profile_fixture_path)

    schema = FormSchemaGenerator(profile).build_schema()
    assert schema["name"] == "Federally Recognized Tribe"
    assert len(schema["statements"]) >= 7
    assert schema["statements"][0]["value"]["type"] == "item"


def test_exemplar_profile_covers_datatypes_and_prompts(exemplar_fixture_path: Path):
    """Exemplar fixture should cover representative datatypes and prompt fields."""
    profile = ProfileLoader().load_from_file(exemplar_fixture_path)
    schema = FormSchemaGenerator(profile).build_schema()

    statement_ids = {statement["id"] for statement in schema["statements"]}
    assert {
        "instance_of",
        "official_website",
        "member_count",
        "native_name",
        "headquarters_location",
        "inception",
        "osm_relation_id",
        "flag_image",
    }.issubset(statement_ids)

    statement_types = {statement["value"]["type"] for statement in schema["statements"]}
    assert {
        "item",
        "url",
        "quantity",
        "monolingualtext",
        "time",
        "external-id",
        "commonsMedia",
    }.issubset(statement_types)

    assert all(statement.get("input_prompt", "") for statement in schema["statements"])

    qualifier_types = {
        qualifier["value"]["type"]
        for statement in schema["statements"]
        for qualifier in statement.get("qualifiers", [])
    }
    assert {"time", "string", "globecoordinate", "item", "monolingualtext"}.issubset(
        qualifier_types
    )
