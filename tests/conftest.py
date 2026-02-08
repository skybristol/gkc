"""
Pytest configuration and fixtures for GKC tests.

This module provides reusable fixtures for tests, including paths to
test data files and loaded test data.
"""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def shex_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to ShEx schema fixtures directory."""
    return fixtures_dir / "shex"


@pytest.fixture
def rdf_fixtures_dir(fixtures_dir: Path) -> Path:
    """Return path to RDF data fixtures directory."""
    return fixtures_dir / "rdf"


@pytest.fixture
def organism_schema_file(shex_fixtures_dir: Path) -> Path:
    """Return path to EntitySchema fixture."""
    return shex_fixtures_dir / "tribe_E502.shex"


@pytest.fixture
def valid_organism_rdf_file(rdf_fixtures_dir: Path) -> Path:
    """Return path to valid RDF fixture."""
    return rdf_fixtures_dir / "valid_Q14708404.ttl"


@pytest.fixture
def invalid_organism_rdf_file(rdf_fixtures_dir: Path) -> Path:
    """Return path to invalid RDF fixture."""
    return rdf_fixtures_dir / "invalid_Q736809.ttl"


@pytest.fixture
def organism_schema_text(organism_schema_file: Path) -> str:
    """Load and return EntitySchema content."""
    if not organism_schema_file.exists():
        return ""
    return organism_schema_file.read_text(encoding="utf-8")


@pytest.fixture
def valid_organism_rdf_text(valid_organism_rdf_file: Path) -> str:
    """Load and return valid RDF content."""
    if not valid_organism_rdf_file.exists():
        return ""
    return valid_organism_rdf_file.read_text(encoding="utf-8")


@pytest.fixture
def invalid_organism_rdf_text(invalid_organism_rdf_file: Path) -> str:
    """Load and return invalid RDF content."""
    if not invalid_organism_rdf_file.exists():
        return ""
    return invalid_organism_rdf_file.read_text(encoding="utf-8")
