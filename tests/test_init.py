"""Tests for package initialization."""

import gkc


def test_version():
    """Test that version is defined."""
    assert hasattr(gkc, "__version__")
    assert isinstance(gkc.__version__, str)


def test_imports():
    """Test that main classes are importable."""
    assert hasattr(gkc, "WikiverseAuth")
    assert hasattr(gkc, "OpenStreetMapAuth")
    assert hasattr(gkc, "AuthenticationError")
