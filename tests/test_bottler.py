"""Tests for bottler module: Wikibase JSON construction primitives."""

import json

from gkc.bottler import (
    ClaimBuilder,
    DataTypeTransformer,
    EntityShellBuilder,
    LanguageBuilder,
    SnakBuilder,
    build_claim_from_property_and_value,
    normalize_claim_datavalue,
)


class TestDataTypeTransformer:
    """Tests for DataTypeTransformer static methods."""

    def test_to_wikibase_item(self):
        result = DataTypeTransformer.to_wikibase_item("Q123")
        assert result["type"] == "wikibase-entityid"
        assert result["value"]["id"] == "Q123"
        assert result["value"]["numeric-id"] == 123
        assert result["value"]["entity-type"] == "item"

    def test_to_quantity_with_default_unit(self):
        result = DataTypeTransformer.to_quantity(42)
        assert result["type"] == "quantity"
        assert result["value"]["amount"] == "+42"
        assert result["value"]["unit"] == "1"

    def test_to_quantity_with_custom_unit(self):
        result = DataTypeTransformer.to_quantity(3.5, unit="Q11573")
        assert result["value"]["amount"] == "+3.5"
        assert result["value"]["unit"] == "Q11573"

    def test_to_time_year_only_auto_precision(self):
        result = DataTypeTransformer.to_time("2005")
        assert result["type"] == "time"
        assert result["value"]["precision"] == 9
        assert "+2005-00-00T00:00:00Z" in result["value"]["time"]

    def test_to_time_year_month_auto_precision(self):
        result = DataTypeTransformer.to_time("2005-06")
        assert result["value"]["precision"] == 10
        assert "+2005-06-00T00:00:00Z" in result["value"]["time"]

    def test_to_time_full_date_auto_precision(self):
        result = DataTypeTransformer.to_time("2005-06-15")
        assert result["value"]["precision"] == 11
        assert "+2005-06-15T00:00:00Z" in result["value"]["time"]

    def test_to_time_explicit_precision(self):
        result = DataTypeTransformer.to_time("2005-06-15", precision=10)
        assert result["value"]["precision"] == 10

    def test_to_monolingualtext(self):
        result = DataTypeTransformer.to_monolingualtext("Example", "en")
        assert result["type"] == "monolingualtext"
        assert result["value"]["text"] == "Example"
        assert result["value"]["language"] == "en"

    def test_to_globe_coordinate(self):
        result = DataTypeTransformer.to_globe_coordinate(51.5074, -0.1278)
        assert result["type"] == "globecoordinate"
        assert result["value"]["latitude"] == 51.5074
        assert result["value"]["longitude"] == -0.1278

    def test_to_url(self):
        result = DataTypeTransformer.to_url("https://example.com")
        assert result["type"] == "string"
        assert result["value"] == "https://example.com"


class TestSnakBuilder:
    """Tests for SnakBuilder."""

    def test_create_snak_wikibase_item(self):
        builder = SnakBuilder(DataTypeTransformer())
        snak = builder.create_snak("P31", "Q5", "wikibase-item")
        assert snak["property"] == "P31"
        assert snak["snaktype"] == "value"
        assert snak["datavalue"]["type"] == "wikibase-entityid"
        assert snak["datavalue"]["value"]["id"] == "Q5"

    def test_create_snak_string(self):
        builder = SnakBuilder(DataTypeTransformer())
        snak = builder.create_snak("P813", "Test string", "string")
        assert snak["datavalue"]["type"] == "string"
        assert snak["datavalue"]["value"] == "Test string"

    def test_create_snak_quantity(self):
        builder = SnakBuilder(DataTypeTransformer())
        snak = builder.create_snak(
            "P1114", 42, "quantity", transform_config={"unit": "Q1"}
        )
        assert snak["datavalue"]["type"] == "quantity"
        assert snak["datavalue"]["value"]["unit"] == "Q1"

    def test_create_snak_time(self):
        builder = SnakBuilder(DataTypeTransformer())
        snak = builder.create_snak("P580", "2005-06-15", "time")
        assert snak["datavalue"]["type"] == "time"
        assert snak["datavalue"]["value"]["precision"] == 11

    def test_create_snak_canonicalizes_item_alias(self):
        builder = SnakBuilder(DataTypeTransformer())
        snak = builder.create_snak("P31", "Q5", "item")

        assert snak["datavalue"]["type"] == "wikibase-entityid"
        assert snak["datavalue"]["value"]["id"] == "Q5"

    def test_create_snak_uses_registry_for_string_like_datatypes(self):
        builder = SnakBuilder(DataTypeTransformer())
        snak = builder.create_snak("P999", "Example external id", "external-id")

        assert snak["datavalue"]["type"] == "string"
        assert snak["datavalue"]["value"] == "Example external id"


class TestClaimBuilder:
    """Tests for ClaimBuilder."""

    def test_create_claim_simple(self):
        transformer = DataTypeTransformer()
        snak_builder = SnakBuilder(transformer)
        claim_builder = ClaimBuilder(snak_builder)

        claim = claim_builder.create_claim("P31", "Q5", "wikibase-item")
        assert claim["type"] == "statement"
        assert claim["rank"] == "normal"
        assert claim["mainsnak"]["property"] == "P31"

    def test_create_claim_with_qualifiers(self):
        transformer = DataTypeTransformer()
        snak_builder = SnakBuilder(transformer)
        claim_builder = ClaimBuilder(snak_builder)

        qualifiers = [{"property": "P585", "value": "2005-06-15", "datatype": "time"}]

        claim = claim_builder.create_claim(
            "P580", "2005-06-15", "time", qualifiers=qualifiers
        )
        assert "qualifiers" in claim
        assert "P585" in claim["qualifiers"]
        assert "qualifiers-order" in claim

    def test_create_claim_with_references(self):
        transformer = DataTypeTransformer()
        snak_builder = SnakBuilder(transformer)
        claim_builder = ClaimBuilder(snak_builder)

        references = [
            {
                "P248": {"value": "Q5", "datatype": "wikibase-item"},
                "P813": {"value": "2005-06-15", "datatype": "time"},
            }
        ]

        claim = claim_builder.create_claim(
            "P31", "Q5", "wikibase-item", references=references
        )
        assert "references" in claim
        assert len(claim["references"]) == 1
        assert "P248" in claim["references"][0]["snaks"]

    def test_create_claim_with_rank(self):
        transformer = DataTypeTransformer()
        snak_builder = SnakBuilder(transformer)
        claim_builder = ClaimBuilder(snak_builder)

        claim = claim_builder.create_claim(
            "P31", "Q5", "wikibase-item", rank="preferred"
        )
        assert claim["rank"] == "preferred"


class TestLanguageBuilder:
    """Tests for LanguageBuilder."""

    def test_build_label_block_simple(self):
        result = LanguageBuilder.build_label_block({"en": "English", "de": "German"})
        assert "en" in result
        assert "de" in result
        assert result["en"]["value"] == "English"
        assert result["en"]["language"] == "en"

    def test_build_label_block_empty(self):
        result = LanguageBuilder.build_label_block({})
        assert result == {}

    def test_build_label_block_filters_empty_values(self):
        result = LanguageBuilder.build_label_block(
            {"en": "English", "de": "", "fr": None}
        )
        assert "en" in result
        assert "de" not in result
        assert "fr" not in result

    def test_build_description_block(self):
        result = LanguageBuilder.build_description_block(
            {"en": "Description", "mul": "Generic"}
        )
        assert "en" in result
        assert "mul" in result
        assert result["mul"]["value"] == "Generic"

    def test_build_alias_block_single_values(self):
        result = LanguageBuilder.build_alias_block({"en": "Alias", "de": "Andere"})
        assert "en" in result
        assert isinstance(result["en"], list)
        assert len(result["en"]) == 1
        assert result["en"][0]["value"] == "Alias"

    def test_build_alias_block_multiple_values(self):
        result = LanguageBuilder.build_alias_block(
            {"en": ["Alias1", "Alias2"], "de": ["Andere1", "Andere2"]}
        )
        assert len(result["en"]) == 2
        assert result["en"][0]["value"] == "Alias1"
        assert result["en"][1]["value"] == "Alias2"


class TestEntityShellBuilder:
    """Tests for EntityShellBuilder."""

    def test_build_entity_shell_minimal(self):
        builder = EntityShellBuilder()
        shell = builder.build_entity_shell({})
        assert isinstance(shell, dict)

    def test_build_entity_shell_with_labels_descriptions(self):
        metadata = {
            "labels": {"en": "Example"},
            "descriptions": {"en": "An example item"},
            "statement_pids": ["P31", "P17"],
        }
        builder = EntityShellBuilder()
        shell = builder.build_entity_shell(metadata)

        assert "labels" in shell
        assert shell["labels"]["en"]["value"] == "Example"
        assert "descriptions" in shell
        assert shell["descriptions"]["en"]["value"] == "An example item"

    def test_build_entity_shell_with_properties(self):
        metadata = {"statement_pids": ["P31", "P17", "P625"]}
        builder = EntityShellBuilder()
        shell = builder.build_entity_shell(metadata)

        assert "claims" in shell
        assert "P17" in shell["claims"]
        assert "P31" in shell["claims"]
        assert "P625" in shell["claims"]
        # Claims should be empty lists
        assert shell["claims"]["P31"] == []

    def test_build_entity_shell_deterministic_property_order(self):
        metadata = {"statement_pids": ["P625", "P31", "P17"]}
        builder = EntityShellBuilder()
        shell = builder.build_entity_shell(metadata)

        # Properties should be sorted alphabetically
        properties = list(shell["claims"].keys())
        assert properties == sorted(properties)

    def test_build_entity_shell_with_aliases(self):
        metadata = {
            "labels": {"en": "Main", "de": "Haupt"},
            "aliases": {"en": ["Alt1", "Alt2"]},
            "statement_pids": ["P31"],
        }
        builder = EntityShellBuilder()
        shell = builder.build_entity_shell(metadata)

        assert "aliases" in shell
        assert len(shell["aliases"]["en"]) == 2
        assert shell["aliases"]["en"][0]["value"] == "Alt1"


class TestClaimUtilities:
    """Tests for standalone claim utility functions."""

    def test_normalize_claim_datavalue_qid(self):
        dtype, value = normalize_claim_datavalue("Q5")
        assert dtype == "wikibase-entityid"
        assert value["id"] == "Q5"
        assert value["entity-type"] == "item"

    def test_normalize_claim_datavalue_property(self):
        dtype, value = normalize_claim_datavalue("P31")
        assert dtype == "wikibase-entityid"
        assert value["id"] == "P31"
        assert value["entity-type"] == "property"

    def test_normalize_claim_datavalue_string(self):
        dtype, value = normalize_claim_datavalue("Some text")
        assert dtype == "string"
        assert value == "Some text"

    def test_normalize_claim_datavalue_boolean(self):
        dtype, value = normalize_claim_datavalue(True)
        assert dtype == "boolean"
        assert value is True

    def test_normalize_claim_datavalue_integer(self):
        dtype, value = normalize_claim_datavalue(42)
        assert dtype == "quantity"
        assert value["amount"] == "42"

    def test_normalize_claim_datavalue_dict_with_id(self):
        dtype, value = normalize_claim_datavalue({"id": "Q100"})
        assert dtype == "wikibase-entityid"
        assert value["id"] == "Q100"

    def test_normalize_claim_datavalue_dict_with_value(self):
        dtype, value = normalize_claim_datavalue({"value": "Q200"})
        assert dtype == "wikibase-entityid"
        assert value["id"] == "Q200"

    def test_normalize_claim_datavalue_none(self):
        result = normalize_claim_datavalue(object())
        assert result is None

    def test_build_claim_from_property_and_value(self):
        claim = build_claim_from_property_and_value("P31", "Q5")
        assert claim is not None
        assert claim["type"] == "statement"
        assert claim["rank"] == "normal"
        assert claim["mainsnak"]["property"] == "P31"
        assert claim["mainsnak"]["datavalue"]["value"]["id"] == "Q5"

    def test_build_claim_from_invalid_value(self):
        claim = build_claim_from_property_and_value("P31", object())
        assert claim is None


class TestBottlerRoundtrip:
    """Integration tests for bottler primitives."""

    def test_roundtrip_entity_shell_to_json(self):
        """Verify entity shells can be serialized to JSON without error."""
        metadata = {
            "labels": {"en": "Test", "de": "Test"},
            "descriptions": {"en": "A test"},
            "aliases": {"en": ["Alt"]},
            "statement_pids": ["P31", "P17"],
        }
        builder = EntityShellBuilder()
        shell = builder.build_entity_shell(metadata)

        # Should serialize without error
        json_str = json.dumps(shell, sort_keys=True)
        assert json_str is not None

        # Should deserialize back
        restored = json.loads(json_str)
        assert restored["labels"]["en"]["value"] == "Test"

    def test_deterministic_entity_shell_multiple_builds(self):
        """Verify same metadata produces identical JSON across multiple builds."""
        metadata = {
            "labels": {"en": "Test", "de": "Test"},
            "descriptions": {"en": "A test"},
            "aliases": {"en": ["Alt"]},
            "statement_pids": ["P31", "P17", "P625"],
        }
        builder = EntityShellBuilder()

        shell1 = builder.build_entity_shell(metadata)
        shell2 = builder.build_entity_shell(metadata)

        json1 = json.dumps(shell1, sort_keys=True)
        json2 = json.dumps(shell2, sort_keys=True)

        assert json1 == json2
