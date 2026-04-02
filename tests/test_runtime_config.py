"""Tests for runtime configuration helpers."""

from gkc.runtime_config import (
    DEFAULT_SPARQL_ENDPOINT,
    DEFAULT_WIKIBASE_API_URL,
    META_WB_API_URL_ENV_VAR,
    META_WB_CONFIG_ENV_VAR,
    META_WB_SPARQL_ENDPOINT_ENV_VAR,
    get_wikibase_runtime_config,
)


def test_runtime_config_defaults(monkeypatch):
    """Defaults are used when META_WB_* vars and config files are absent."""
    monkeypatch.delenv(META_WB_CONFIG_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_API_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_SPARQL_ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.delenv("WIKIVERSE_USERNAME", raising=False)
    monkeypatch.delenv("WIKIVERSE_PASSWORD", raising=False)

    config = get_wikibase_runtime_config()

    assert config.api_url == DEFAULT_WIKIBASE_API_URL
    assert config.sparql_endpoint == DEFAULT_SPARQL_ENDPOINT
    assert config.config_path is None


def test_runtime_config_env_overrides(monkeypatch):
    """META_WB_* variables override defaults."""
    monkeypatch.setenv(META_WB_API_URL_ENV_VAR, "https://dd.example/w/api.php")
    monkeypatch.setenv(
        META_WB_SPARQL_ENDPOINT_ENV_VAR, "https://dd.example/query/sparql"
    )

    config = get_wikibase_runtime_config()

    assert config.api_url == "https://dd.example/w/api.php"
    assert config.sparql_endpoint == "https://dd.example/query/sparql"


def test_runtime_config_ignores_wikiverse_credentials(monkeypatch):
    """WIKIVERSE_* credentials do not affect read-only runtime config."""
    monkeypatch.delenv(META_WB_CONFIG_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_API_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_SPARQL_ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.setenv("WIKIVERSE_USERNAME", "legacy-user")
    monkeypatch.setenv("WIKIVERSE_PASSWORD", "legacy-pass")

    config = get_wikibase_runtime_config()

    assert config.api_url == DEFAULT_WIKIBASE_API_URL
    assert config.sparql_endpoint == DEFAULT_SPARQL_ENDPOINT


def test_runtime_config_loads_config_file(monkeypatch, tmp_path):
    """Runtime config loads endpoint settings from a tracked config file."""
    config_path = tmp_path / "dd-wikibase.yaml"
    config_path.write_text(
        """
meta_wikibase:
  id: datadistillery-wikibase
  label: Data Distillery Wikibase
  api_url: https://config.example/w/api.php
  sparql_endpoint: https://config.example/query/sparql
  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(META_WB_CONFIG_ENV_VAR, str(config_path))
    monkeypatch.delenv(META_WB_API_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_SPARQL_ENDPOINT_ENV_VAR, raising=False)

    config = get_wikibase_runtime_config()

    assert config.config_path == str(config_path)
    assert config.config_id == "datadistillery-wikibase"
    assert config.label == "Data Distillery Wikibase"
    assert config.api_url == "https://config.example/w/api.php"
    assert config.sparql_endpoint == "https://config.example/query/sparql"
    assert config.name_identifier_property_id == "P214"
    assert config.internal_name_identifier_prefix == "_"


def test_runtime_config_autodiscovers_config_file(monkeypatch, tmp_path):
    """Runtime config auto-discovers dd-wikibase.yaml from parent directories."""
    root_dir = tmp_path / "SpiritSafe"
    nested_dir = root_dir / "cache" / "entities"
    nested_dir.mkdir(parents=True)
    config_path = root_dir / "dd-wikibase.yaml"
    config_path.write_text(
        "api_url: https://autodiscovery.example/w/api.php\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(META_WB_CONFIG_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_API_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_SPARQL_ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(nested_dir)

    config = get_wikibase_runtime_config()

    assert config.config_path == str(config_path)
    assert config.api_url == "https://autodiscovery.example/w/api.php"
    assert config.sparql_endpoint == DEFAULT_SPARQL_ENDPOINT


def test_runtime_config_env_overrides_config_file(monkeypatch, tmp_path):
    """META_WB_* overrides win over config file values."""
    config_path = tmp_path / "dd-wikibase.yaml"
    config_path.write_text(
        """
api_url: https://config.example/w/api.php
sparql_endpoint: https://config.example/query/sparql
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(META_WB_CONFIG_ENV_VAR, str(config_path))
    monkeypatch.setenv(META_WB_API_URL_ENV_VAR, "https://env.example/w/api.php")
    monkeypatch.setenv(
        META_WB_SPARQL_ENDPOINT_ENV_VAR, "https://env.example/query/sparql"
    )

    config = get_wikibase_runtime_config()

    assert config.api_url == "https://env.example/w/api.php"
    assert config.sparql_endpoint == "https://env.example/query/sparql"
