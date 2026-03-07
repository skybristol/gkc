"""Tests for runtime configuration helpers."""

from gkc.runtime_config import (
    DEFAULT_SPARQL_ENDPOINT,
    DEFAULT_WIKIBASE_API_URL,
    get_wikibase_runtime_config,
)


def test_runtime_config_defaults(monkeypatch):
    """Defaults are used when DD_WB_* vars are absent."""
    monkeypatch.delenv("DD_WB_API_URL", raising=False)
    monkeypatch.delenv("DD_WB_SPARQL_ENDPOINT", raising=False)
    monkeypatch.delenv("DD_WB_USERNAME", raising=False)
    monkeypatch.delenv("DD_WB_PASSWORD", raising=False)
    monkeypatch.delenv("WIKIVERSE_USERNAME", raising=False)
    monkeypatch.delenv("WIKIVERSE_PASSWORD", raising=False)

    config = get_wikibase_runtime_config()

    assert config.api_url == DEFAULT_WIKIBASE_API_URL
    assert config.sparql_endpoint == DEFAULT_SPARQL_ENDPOINT
    assert config.username is None
    assert config.password is None


def test_runtime_config_env_overrides(monkeypatch):
    """DD_WB_* variables override defaults."""
    monkeypatch.setenv("DD_WB_API_URL", "https://dd.example/w/api.php")
    monkeypatch.setenv("DD_WB_SPARQL_ENDPOINT", "https://dd.example/query/sparql")
    monkeypatch.setenv("DD_WB_USERNAME", "bot-user")
    monkeypatch.setenv("DD_WB_PASSWORD", "bot-pass")

    config = get_wikibase_runtime_config()

    assert config.api_url == "https://dd.example/w/api.php"
    assert config.sparql_endpoint == "https://dd.example/query/sparql"
    assert config.username == "bot-user"
    assert config.password == "bot-pass"


def test_runtime_config_ignores_wikiverse_credentials(monkeypatch):
    """WIKIVERSE_* credentials are ignored for Data Distillery runtime config."""
    monkeypatch.delenv("DD_WB_USERNAME", raising=False)
    monkeypatch.delenv("DD_WB_PASSWORD", raising=False)
    monkeypatch.setenv("WIKIVERSE_USERNAME", "legacy-user")
    monkeypatch.setenv("WIKIVERSE_PASSWORD", "legacy-pass")

    config = get_wikibase_runtime_config()

    assert config.username is None
    assert config.password is None
