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


def test_mash_and_utilities_imports():
    """Test that mash and utilities functions are importable via gkc namespace."""
    assert hasattr(gkc, "fetch_schema_specification")
    assert hasattr(gkc, "validate_entity_reference")
    assert hasattr(gkc, "fetch_entity_rdf")
    assert hasattr(gkc, "get_entity_uri")


def test_wikibase_registry_imports():
    """Test that wikibase registry helpers are importable via gkc namespace."""
    assert hasattr(gkc, "WikibaseDatatypeSpec")
    assert hasattr(gkc, "canonicalize_wikibase_datatype")
    assert hasattr(gkc, "get_wikibase_datatype_spec")
    assert hasattr(gkc, "is_known_wikibase_datatype")
    assert hasattr(gkc, "is_wikibase_item_datatype")
    assert hasattr(gkc, "list_wikibase_datatypes")
    assert hasattr(gkc, "load_wikibase_datatype_registry")
    assert hasattr(gkc, "load_wikibase_datatype_registry_json")


def test_mash_adapter_contract_imports():
    """Test that mash adapter contracts are importable from the mash package."""
    import gkc.mash as mash

    assert hasattr(mash, "MashSourceAdapter")
    assert hasattr(mash, "WikibaseMashSourceAdapter")
    assert hasattr(mash, "WikipediaMashSourceAdapter")
