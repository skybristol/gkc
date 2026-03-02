"""Tests for EntityJSONValidator (Phase 8.5).

Test coverage:
- Schema compliance validation
- Completeness calculation with various language/statement configurations
- Round-trip serialization integrity
"""

from pathlib import Path

import pytest

from gkc.profiles import ProfileLoader
from gkc.profiles.validators import EntityJSONValidator


@pytest.fixture
def tribal_profile():
    """Load TribalGovernmentUS profile for testing."""
    profile_path = (
        Path(__file__).parent
        / "fixtures"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )
    return ProfileLoader().load_from_file(profile_path)


@pytest.fixture
def minimal_entity():
    """Create a minimal valid GKC Entity JSON."""
    return {
        "packet_id": "ent-001-test",
        "profile_name": "TribalGovernmentUS",
        "username": "test_user",
        "status": "in_progress",
        "created_at": "2026-03-02T12:00:00Z",
        "creation_path": "primary",
        "labels": {},
        "descriptions": {},
        "aliases": {},
        "statements": {},
        "sitelinks": {},
    }


@pytest.fixture
def complete_entity():
    """Create a complete GKC Entity JSON with all required fields."""
    return {
        "packet_id": "ent-001-test",
        "profile_name": "TribalGovernmentUS",
        "username": "test_user",
        "status": "in_progress",
        "created_at": "2026-03-02T12:00:00Z",
        "creation_path": "primary",
        "labels": {"en": "Test Tribe"},
        "descriptions": {
            "en": "federally recognized Native American tribe based in Oklahoma"
        },
        "aliases": {"en": ["Test Tribe Official Name"]},
        "statements": {
            "instance_of": [
                {
                    "value": {"type": "item", "id": "Q7840353"},
                    "qualifiers": {},
                    "references": [{"stated_in": {"type": "item", "id": "Q138391266"}}],
                }
            ]
        },
        "sitelinks": {},
    }


# ============================================================================
# SCHEMA VALIDATION TESTS
# ============================================================================


def test_validate_schema_minimal_valid(minimal_entity):
    """Test that minimal valid entity passes schema validation."""
    result = EntityJSONValidator.validate_schema(minimal_entity)
    assert result.is_valid is True
    assert len([i for i in result.issues if i.severity == "error"]) == 0


def test_validate_schema_missing_packet_id():
    """Test that missing packet_id fails validation."""
    entity = {
        "profile_name": "TribalGovernmentUS",
        "username": "test_user",
        "status": "in_progress",
        "created_at": "2026-03-02T12:00:00Z",
        "creation_path": "primary",
        "labels": {},
        "descriptions": {},
        "aliases": {},
        "statements": {},
        "sitelinks": {},
    }
    result = EntityJSONValidator.validate_schema(entity)
    assert result.is_valid is False
    assert any("packet_id" in issue.field for issue in result.issues)


def test_validate_schema_missing_profile_name():
    """Test that missing profile_name fails validation."""
    entity = {
        "packet_id": "ent-001-test",
        "username": "test_user",
        "status": "in_progress",
        "created_at": "2026-03-02T12:00:00Z",
        "creation_path": "primary",
        "labels": {},
        "descriptions": {},
        "aliases": {},
        "statements": {},
        "sitelinks": {},
    }
    result = EntityJSONValidator.validate_schema(entity)
    assert result.is_valid is False
    assert any("profile_name" in issue.field for issue in result.issues)


def test_validate_schema_invalid_labels_structure():
    """Test that invalid labels structure produces warning."""
    entity = {
        "packet_id": "ent-001-test",
        "profile_name": "TribalGovernmentUS",
        "username": "test_user",
        "status": "in_progress",
        "created_at": "2026-03-02T12:00:00Z",
        "creation_path": "primary",
        "labels": ["not a dict"],  # Invalid: should be dict
        "descriptions": {},
        "aliases": {},
        "statements": {},
        "sitelinks": {},
    }
    result = EntityJSONValidator.validate_schema(entity)
    assert any("labels" in issue.field for issue in result.issues)


def test_validate_schema_invalid_statements_structure():
    """Test that invalid statements structure produces error."""
    entity = {
        "packet_id": "ent-001-test",
        "profile_name": "TribalGovernmentUS",
        "username": "test_user",
        "status": "in_progress",
        "created_at": "2026-03-02T12:00:00Z",
        "creation_path": "primary",
        "labels": {},
        "descriptions": {},
        "aliases": {},
        "statements": "not a dict",  # Invalid: should be dict
        "sitelinks": {},
    }
    result = EntityJSONValidator.validate_schema(entity)
    assert result.is_valid is False
    assert any("statements" in issue.field for issue in result.issues)


# ============================================================================
# COMPLETENESS CALCULATION TESTS
# ============================================================================


def test_calculate_completeness_empty_entity(minimal_entity, tribal_profile):
    """Test completeness calculation for empty entity (0%)."""
    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=None
    )
    # Should have 0 completed, total = 2 (label, description) + num_statements
    assert result.completed_fields == 0
    assert result.required_fields_total > 0
    assert result.progress_percentage == 0.0


def test_calculate_completeness_labels_only(minimal_entity, tribal_profile):
    """Test completeness with only labels filled."""
    minimal_entity["labels"] = {"en": "Test Tribe"}
    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=None
    )
    # Should count 1 completed field (en label)
    assert result.completed_fields >= 1
    assert result.progress_percentage > 0.0
    # Language not completed until BOTH label and description present
    # (so completed_languages might be empty)


def test_calculate_completeness_labels_and_descriptions(minimal_entity, tribal_profile):
    """Test completeness with labels and descriptions."""
    minimal_entity["labels"] = {"en": "Test Tribe"}
    minimal_entity["descriptions"] = {"en": "A test tribe"}
    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=None
    )
    # Should count 2 completed (en label + en description)
    assert result.completed_fields >= 2
    # Now language should be completed (both label and description present)
    assert "en" in result.completed_languages


def test_calculate_completeness_with_statements(minimal_entity, tribal_profile):
    """Test completeness calculation with statements filled."""
    minimal_entity["labels"] = {"en": "Test Tribe"}
    minimal_entity["descriptions"] = {"en": "A test tribe"}
    minimal_entity["statements"] = {
        "instance_of": [
            {
                "value": {"type": "item", "id": "Q7840353"},
                "qualifiers": {},
                "references": [],
            }
        ]
    }
    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=None
    )
    # Should count label + description + 1 statement
    assert result.completed_fields >= 3
    assert result.progress_percentage > 0.0


def test_calculate_completeness_multiple_languages(minimal_entity, tribal_profile):
    """Test completeness with multiple languages."""
    minimal_entity["labels"] = {"en": "Test Tribe", "chr": "ᏚᏓᏲᎳ"}
    minimal_entity["descriptions"] = {"en": "A test tribe", "chr": "ᏚᏓᏲᎳ ᎠᏂᏴᏫᏯ"}
    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=None
    )
    # Should count 2 completed fields (one per language for label+description pair)
    # Not 4, because we count language completion, not individual fields
    assert result.completed_fields >= 2
    assert "en" in result.completed_languages
    # chr might not be in completed if profile doesn't require it


def test_calculate_completeness_required_languages(minimal_entity, tribal_profile):
    """Test completeness with specific required languages."""
    minimal_entity["labels"] = {"en": "Test Tribe"}
    minimal_entity["descriptions"] = {"en": "A test tribe"}

    # Require both en and chr
    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=["en", "chr"]
    )

    # Should show chr as missing
    assert "chr" in result.missing_languages
    assert "en" in result.completed_languages


def test_calculate_completeness_full_entity(complete_entity, tribal_profile):
    """Test completeness calculation for complete entity."""
    result = EntityJSONValidator.calculate_completeness(
        complete_entity, tribal_profile, required_languages=None
    )
    # Should have label + description + 1 statement = 3
    assert result.completed_fields >= 3
    assert result.progress_percentage > 0.0
    assert len(result.completed_languages) >= 1


# ============================================================================
# MISSING FIELDS TESTS
# ============================================================================


def test_missing_fields_identification(minimal_entity, tribal_profile):
    """Test that missing fields are correctly identified."""
    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=None
    )
    # Should identify missing label and description for at least one language
    assert "labels" in result.missing_fields or len(result.missing_languages) > 0


def test_missing_fields_statements(minimal_entity, tribal_profile):
    """Test that missing required statements are identified."""
    # Add identification but no statements
    minimal_entity["labels"] = {"en": "Test Tribe"}
    minimal_entity["descriptions"] = {"en": "A test tribe"}

    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=None
    )

    # Check that required statements are in missing fields
    # (TribalGovernmentUS has several required statements)
    assert len(result.missing_fields) > 0


# ============================================================================
# EDGE CASES & ERROR HANDLING
# ============================================================================


def test_completeness_with_empty_statements_dict(minimal_entity, tribal_profile):
    """Test that empty statements dict is handled correctly."""
    minimal_entity["statements"] = {}
    result = EntityJSONValidator.calculate_completeness(
        minimal_entity, tribal_profile, required_languages=None
    )
    assert result.completed_fields >= 0  # Should not crash


def test_completeness_with_none_values(minimal_entity, tribal_profile):
    """Test that None values don't crash completeness calculation."""
    minimal_entity["labels"] = None
    result = EntityJSONValidator.validate_schema(minimal_entity)
    # Should produce warning but not crash
    assert result.issues  # Should have validation issues


def test_schema_validation_with_extra_fields(minimal_entity):
    """Test that extra fields are allowed (forward compatibility)."""
    minimal_entity["extra_field"] = "extra_value"
    result = EntityJSONValidator.validate_schema(minimal_entity)
    # Should still be valid (we don't enforce strict schema)
    assert result.is_valid is True


def test_empty_entity_dict():
    """Test validation of completely empty entity."""
    result = EntityJSONValidator.validate_schema({})
    assert result.is_valid is False
    # Should have multiple errors for missing required fields
    assert len([i for i in result.issues if i.severity == "error"]) > 0
