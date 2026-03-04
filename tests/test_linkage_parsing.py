"""
Test linkage metadata parsing from SpiritSafe profiles.

Validates that ProfileDefinition correctly parses statement-level linkage
metadata and provides helper methods for multi-entity workflows.
"""

from pathlib import Path

import pytest

from gkc.profiles.loaders.yaml_loader import ProfileLoader
from gkc.profiles.models import (
    LinkageCardinality,
    LinkageRelationship,
    LinkageTraversal,
    LinkageWorkflowPolicy,
    ProfileDefinition,
    StatementLinkage,
)


@pytest.fixture
def tribal_government_profile() -> ProfileDefinition:
    """Load the TribalGovernmentUS test fixture profile.

    Returns:
        Parsed ProfileDefinition with linkage metadata.
    """
    fixture_path = (
        Path(__file__).parent
        / "fixtures"
        / "spiritsafe"
        / "profiles"
        / "TribalGovernmentUS"
        / "profile.yaml"
    )
    assert fixture_path.exists(), f"Fixture not found: {fixture_path}"

    loader = ProfileLoader()
    profile = loader.load_from_file(str(fixture_path))
    return profile


def test_linkage_metadata_parsed(tribal_government_profile):
    """Test that linkage metadata is correctly parsed from YAML."""
    # Find the office_held_by_head_of_state statement
    stmt = tribal_government_profile.statement_by_id("office_held_by_head_of_state")
    assert stmt is not None, "Statement office_held_by_head_of_state should exist"

    # Verify linkage metadata exists
    assert stmt.linkage is not None, "Statement should have linkage metadata"
    assert isinstance(stmt.linkage, StatementLinkage)

    # Verify target profile
    assert stmt.linkage.target_profile == "OfficeHeldByHeadOfState"

    # Verify relationship
    assert isinstance(stmt.linkage.relationship, LinkageRelationship)
    assert stmt.linkage.relationship.type == "office_of_head_of_state"
    assert stmt.linkage.relationship.direction == "bidirectional"
    assert stmt.linkage.relationship.reverse_statement_hint == "applies_to_jurisdiction"

    # Verify cardinality
    assert isinstance(stmt.linkage.cardinality, LinkageCardinality)
    assert stmt.linkage.cardinality.min == 0
    assert stmt.linkage.cardinality.max == 1

    # Verify workflow policy
    assert isinstance(stmt.linkage.workflow_policy, LinkageWorkflowPolicy)
    assert stmt.linkage.workflow_policy.create is True
    assert stmt.linkage.workflow_policy.select_existing is True

    # Verify traversal
    assert isinstance(stmt.linkage.traversal, LinkageTraversal)
    assert stmt.linkage.traversal.max_depth == 1


def test_entity_profile_field_parsed(tribal_government_profile):
    """Test that entity_profile field is correctly parsed."""
    stmt = tribal_government_profile.statement_by_id("office_held_by_head_of_state")
    assert stmt is not None
    assert stmt.entity_profile == "OfficeHeldByHeadOfState"


def test_guidance_field_parsed(tribal_government_profile):
    """Test that guidance field is correctly parsed."""
    stmt = tribal_government_profile.statement_by_id("office_held_by_head_of_state")
    assert stmt is not None
    assert stmt.guidance != ""
    assert "office itself" in stmt.guidance.lower()


def test_get_statement_linkages(tribal_government_profile):
    """Test ProfileDefinition.get_statement_linkages() helper method."""
    linked_statements = tribal_government_profile.get_statement_linkages()

    # Should find at least one linked statement
    assert len(linked_statements) >= 1

    # All returned statements should have linkage
    for stmt in linked_statements:
        assert stmt.linkage is not None

    # Verify office_held_by_head_of_state is in the list
    stmt_ids = {stmt.id for stmt in linked_statements}
    assert "office_held_by_head_of_state" in stmt_ids


def test_get_linked_profile_names(tribal_government_profile):
    """Test ProfileDefinition.get_linked_profile_names() helper method."""
    linked_names = tribal_government_profile.get_linked_profile_names()

    # Should find OfficeHeldByHeadOfState
    assert "OfficeHeldByHeadOfState" in linked_names

    # Should be sorted and unique
    assert linked_names == sorted(set(linked_names))


def test_get_link_definition(tribal_government_profile):
    """Test ProfileDefinition.get_link_definition() helper method."""
    # Get linkage for known profile
    linkage = tribal_government_profile.get_link_definition("OfficeHeldByHeadOfState")
    assert linkage is not None
    assert isinstance(linkage, StatementLinkage)
    assert linkage.target_profile == "OfficeHeldByHeadOfState"
    assert linkage.cardinality.max == 1

    # Try to get linkage for non-existent profile
    missing = tribal_government_profile.get_link_definition("NonExistentProfile")
    assert missing is None


def test_cardinality_validation():
    """Test that LinkageCardinality validates min/max constraints."""
    # Valid cardinality
    valid = LinkageCardinality(min=0, max=1)
    assert valid.min == 0
    assert valid.max == 1

    # Invalid: min > max should raise error
    with pytest.raises(ValueError, match="min.*cannot exceed max"):
        LinkageCardinality(min=5, max=1)

    # Invalid: negative min should raise error
    with pytest.raises(ValueError):
        LinkageCardinality(min=-1, max=1)


def test_workflow_policy_alias():
    """Test that LinkageWorkflowPolicy accepts 'allowed'/'disallowed' string values."""
    # Test with explicit boolean values
    policy1 = LinkageWorkflowPolicy(create=True, select_existing=False)
    assert policy1.create is True
    assert policy1.select_existing is False

    # Test with 'allowed' string values (as seen in YAML files)
    policy2 = LinkageWorkflowPolicy.model_validate(
        {"create": "allowed", "select_existing": "allowed"}
    )
    assert policy2.create is True
    assert policy2.select_existing is True

    # Test with 'disallowed' string value
    policy3 = LinkageWorkflowPolicy.model_validate(
        {"create": "disallowed", "select_existing": "allowed"}
    )
    assert policy3.create is False
    assert policy3.select_existing is True


def test_statements_without_linkage(tribal_government_profile):
    """Test that statements without linkage metadata don't break parsing."""
    # instance_of should not have linkage
    stmt = tribal_government_profile.statement_by_id("instance_of")
    assert stmt is not None
    assert stmt.linkage is None
    assert stmt.entity_profile is None
