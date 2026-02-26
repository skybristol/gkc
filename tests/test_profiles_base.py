"""Tests for profile base classes.

This module tests the foundational profile classes to ensure they have proper
structure, type hints, and can be instantiated correctly.
"""

from typing import Any

import pytest

from gkc.profiles.base import (
    BarrelProfile,
    EntityProfile,
    ModulationProfile,
    PropertyDefinition,
)


class ConcreteEntityProfile(EntityProfile):
    """Concrete implementation for testing."""

    profile_name = "test_entity"
    profile_version = "1.0"
    description = "Test entity profile"


class ConcreteBarrelProfile(BarrelProfile):
    """Concrete implementation for testing."""

    platform = "test_platform"

    def transform(self, entity: EntityProfile) -> dict[str, Any]:
        """Test implementation."""
        return {"test": "data"}

    def ship(self, payload: dict[str, Any]) -> Any:
        """Test implementation."""
        return {"status": "shipped"}


def test_entity_profile_creation():
    """Test that EntityProfile can be instantiated with required fields."""
    profile = ConcreteEntityProfile(
        labels={"en": "Test Entity"},
        descriptions={"en": "A test entity"},
        aliases={"en": ["Test", "Entity"]},
    )

    assert profile.labels == {"en": "Test Entity"}
    assert profile.descriptions == {"en": "A test entity"}
    assert profile.aliases == {"en": ["Test", "Entity"]}
    assert profile.profile_name == "test_entity"
    assert profile.profile_version == "1.0"


def test_entity_profile_defaults():
    """Test that EntityProfile has sensible defaults."""
    profile = ConcreteEntityProfile()

    assert profile.labels == {}
    assert profile.descriptions == {}
    assert profile.aliases == {}
    assert profile.source_id is None
    assert profile.provenance == {}


def test_entity_profile_to_dict():
    """Test EntityProfile serialization."""
    profile = ConcreteEntityProfile(
        labels={"en": "Test"},
        source_id="Q12345",
    )

    data = profile.to_dict()
    assert data["labels"] == {"en": "Test"}
    assert data["source_id"] == "Q12345"


def test_entity_profile_abstract_methods():
    """Test that abstract methods raise NotImplementedError."""
    profile = ConcreteEntityProfile()

    with pytest.raises(NotImplementedError):
        profile.to_modulation_profile()

    with pytest.raises(NotImplementedError):
        profile.to_barrel_profile("wikidata")

    with pytest.raises(NotImplementedError):
        ConcreteEntityProfile.from_raw({})


def test_modulation_profile_creation():
    """Test that ModulationProfile can be instantiated."""
    modulation = ModulationProfile(
        name="test_workflow",
        description="Test data workflow",
        entity_types=["test_entity"],
    )

    assert modulation.name == "test_workflow"
    assert modulation.description == "Test data workflow"
    assert modulation.entity_types == ["test_entity"]
    assert modulation.field_specs == {}


def test_modulation_profile_field_specs():
    """Test ModulationProfile with field specifications."""
    modulation = ModulationProfile(
        name="test_workflow",
        field_specs={
            "test_entity.name": {
                "type": "string",
                "required": True,
                "help_text": "Entity name",
            }
        },
    )

    assert "test_entity.name" in modulation.field_specs
    assert modulation.field_specs["test_entity.name"]["required"] is True


def test_modulation_profile_validate_inputs():
    """Test input validation returns inputs as-is in base implementation."""
    modulation = ModulationProfile(name="test")
    inputs = {"field1": "value1"}

    validated = modulation.validate_inputs(inputs)
    assert validated == inputs


def test_modulation_profile_abstract_methods():
    """Test that abstract methods raise NotImplementedError."""
    modulation = ModulationProfile(name="test")

    with pytest.raises(NotImplementedError):
        modulation.to_barrel_profiles()


def test_barrel_profile_creation():
    """Test that BarrelProfile can be instantiated."""
    barrel = ConcreteBarrelProfile()

    assert barrel.platform == "test_platform"


def test_barrel_profile_transform():
    """Test BarrelProfile transform method."""
    barrel = ConcreteBarrelProfile()
    entity = ConcreteEntityProfile(labels={"en": "Test"})

    payload = barrel.transform(entity)
    assert payload == {"test": "data"}


def test_barrel_profile_ship():
    """Test BarrelProfile ship method."""
    barrel = ConcreteBarrelProfile()
    payload = {"test": "data"}

    result = barrel.ship(payload)
    assert result == {"status": "shipped"}


def test_barrel_profile_validate_payload():
    """Test BarrelProfile payload validation."""
    barrel = ConcreteBarrelProfile()
    payload = {"test": "data"}

    assert barrel.validate_payload(payload) is True


def test_barrel_profile_to_dict():
    """Test BarrelProfile serialization."""
    barrel = ConcreteBarrelProfile()

    data = barrel.to_dict()
    assert data["platform"] == "test_platform"
    assert data["class"] == "ConcreteBarrelProfile"


def test_property_definition_creation():
    """Test that PropertyDefinition can be instantiated."""
    prop = PropertyDefinition(
        property_id="P31",
        label="instance of",
        datatype="wikibase-item",
    )

    assert prop.property_id == "P31"
    assert prop.label == "instance of"
    assert prop.datatype == "wikibase-item"
    assert prop.platform == "wikidata"  # default


def test_property_definition_with_qualifiers():
    """Test PropertyDefinition with qualifier requirements."""
    prop = PropertyDefinition(
        property_id="P31",
        label="instance of",
        required_qualifiers=["P580"],
        optional_qualifiers=["P582"],
    )

    assert prop.required_qualifiers == ["P580"]
    assert prop.optional_qualifiers == ["P582"]


def test_property_definition_to_dict():
    """Test PropertyDefinition serialization."""
    prop = PropertyDefinition(
        property_id="P31",
        label="instance of",
        platform="wikidata",
    )

    data = prop.to_dict()
    assert data["property_id"] == "P31"
    assert data["label"] == "instance of"
    assert data["platform"] == "wikidata"


def test_property_definition_validate_value():
    """Test PropertyDefinition value validation."""
    prop = PropertyDefinition(property_id="P31")

    # Base implementation always returns True
    assert prop.validate_value("Q5") is True
    assert prop.validate_value(12345) is True
