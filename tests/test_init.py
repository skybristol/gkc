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


def test_spirit_safe_imports():
    """Test that Spirit Safe classes are importable (new and legacy names)."""
    # New names
    assert hasattr(gkc, "SpiritSafeValidator")
    assert hasattr(gkc, "SpiritSafeValidationError")
    # Backwards compatibility aliases
    assert hasattr(gkc, "ShExValidator")
    assert hasattr(gkc, "ShExValidationError")
    # Verify aliases point to same classes
    assert gkc.ShExValidator is gkc.SpiritSafeValidator
    assert gkc.ShExValidationError is gkc.SpiritSafeValidationError


def test_cooperage_imports():
    """Test that Cooperage functions are importable (new and legacy names)."""
    # New names
    assert hasattr(gkc, "CooperageError")
    assert hasattr(gkc, "fetch_schema_specification")
    assert hasattr(gkc, "validate_entity_reference")
    # Backwards compatibility aliases
    assert hasattr(gkc, "WikidataFetchError")
    assert hasattr(gkc, "fetch_entity_schema")
    assert hasattr(gkc, "validate_entity_id")
    # Verify aliases
    assert gkc.WikidataFetchError is gkc.CooperageError
    assert gkc.fetch_entity_schema is gkc.fetch_schema_specification
    assert gkc.validate_entity_id is gkc.validate_entity_reference


def test_recipe_imports():
    """Test that Recipe Builder classes are importable (new and legacy names)."""
    # New names
    assert hasattr(gkc, "RecipeBuilder")
    assert hasattr(gkc, "PropertyProfile")
    assert hasattr(gkc, "PropertyCatalog")
    assert hasattr(gkc, "SpecificationExtractor")
    # Backwards compatibility aliases
    assert hasattr(gkc, "ClaimsMapBuilder")
    assert hasattr(gkc, "PropertyInfo")
    assert hasattr(gkc, "WikidataPropertyFetcher")
    assert hasattr(gkc, "ShExPropertyExtractor")
    # Verify aliases
    assert gkc.ClaimsMapBuilder is gkc.RecipeBuilder
    assert gkc.PropertyInfo is gkc.PropertyProfile
    assert gkc.WikidataPropertyFetcher is gkc.PropertyCatalog
    assert gkc.ShExPropertyExtractor is gkc.SpecificationExtractor
