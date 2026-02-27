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


def test_spirit_safe_config_imports():
    """Test that SpiritSafe source config helpers are importable."""
    assert hasattr(gkc, "DEFAULT_SPIRIT_SAFE_GITHUB_REPO")
    assert hasattr(gkc, "SpiritSafeSourceConfig")
    assert hasattr(gkc, "get_spirit_safe_source")
    assert hasattr(gkc, "set_spirit_safe_source")
    assert hasattr(gkc, "LookupCache")
    assert hasattr(gkc, "LookupFetcher")
    assert hasattr(gkc, "hydrate_profile_lookups")


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
