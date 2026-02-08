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
    """Test that ShEx classes are importable."""
    assert hasattr(gkc, "ShExValidator")
    assert hasattr(gkc, "ShExValidationError")


def test_wd_imports():
    """Test that Wikidata utilities are importable."""
    assert hasattr(gkc, "WikidataFetchError")
    assert hasattr(gkc, "fetch_entity_rdf")
    assert hasattr(gkc, "fetch_entity_schema")
