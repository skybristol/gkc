"""Tests for package initialization."""

import gkc


def test_version():
    """Test that version is defined."""
    assert hasattr(gkc, "__version__")
    assert isinstance(gkc.__version__, str)


def test_auth_imports():
    """Test that auth classes are importable."""
    assert hasattr(gkc, "WikiverseAuth")
    assert hasattr(gkc, "OpenStreetMapAuth")
    assert hasattr(gkc, "AuthenticationError")


def test_shex_imports():
    """Test that ShEx validation classes are importable."""
    assert hasattr(gkc, "ShexValidator")
    assert hasattr(gkc, "ShexValidationError")


def test_cooperage_imports():
    """Test that Cooperage functions are importable."""
    assert hasattr(gkc, "CooperageError")
    assert hasattr(gkc, "fetch_schema_specification")
    assert hasattr(gkc, "validate_entity_reference")


def test_recipe_imports():
    """Test that Recipe Builder classes are importable."""
    assert hasattr(gkc, "RecipeBuilder")
    assert hasattr(gkc, "PropertyLedgerEntry")
    assert hasattr(gkc, "SpecificationExtractor")
