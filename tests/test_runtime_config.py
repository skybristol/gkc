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
    assert config.spiritsafe_layout.entities_path == "still/entities"
    assert (
        config.spiritsafe_layout.semantic_anchors_path == "config/semantic_anchors.json"
    )
    assert config.spiritsafe_layout.logs_path == "still/logs"
    assert (
        config.spiritsafe_layout.wikimedia_sites_path == "partners/wikimedia_sites.json"
    )


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
spiritsafe:
    layout_version: 2
    roots:
        materialized: still
        partners: partners
    paths:
        entities: still/entities
        profiles: still/profiles
        value_list_queries: still/value_lists/queries
        value_list_cache: still/value_lists/cache
        semantic_anchors: config/semantic_anchors.json
        logs: still/logs
        wikimedia_sites: partners/wikimedia_sites.json
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
    assert config.spiritsafe_layout.layout_version == 2
    assert config.spiritsafe_layout.materialized_root == "still"
    assert config.spiritsafe_layout.partners_root == "partners"
    assert config.spiritsafe_layout.entities_path == "still/entities"
    assert config.spiritsafe_layout.profiles_path == "still/profiles"
    assert (
        config.spiritsafe_layout.value_list_queries_path == "still/value_lists/queries"
    )
    assert config.spiritsafe_layout.value_list_cache_path == "still/value_lists/cache"
    assert config.spiritsafe_layout.logs_path == "still/logs"
    assert (
        config.spiritsafe_layout.wikimedia_sites_path == "partners/wikimedia_sites.json"
    )


def test_runtime_config_autodiscovers_config_file(monkeypatch, tmp_path):
    """Runtime config auto-discovers config/dd-wikibase.yaml from parent directories."""
    root_dir = tmp_path / "SpiritSafe"
    nested_dir = root_dir / "still" / "entities"
    nested_dir.mkdir(parents=True)
    config_dir = root_dir / "config"
    config_dir.mkdir()
    config_path = config_dir / "dd-wikibase.yaml"
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


def test_runtime_config_autodiscovers_root_fallback_config(monkeypatch, tmp_path):
    """Runtime config still supports root-level dd-wikibase.yaml as a fallback."""
    root_dir = tmp_path / "SpiritSafe"
    nested_dir = root_dir / "still" / "entities"
    nested_dir.mkdir(parents=True)
    config_path = root_dir / "dd-wikibase.yaml"
    config_path.write_text(
        "api_url: https://rootfallback.example/w/api.php\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(META_WB_CONFIG_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_API_URL_ENV_VAR, raising=False)
    monkeypatch.delenv(META_WB_SPARQL_ENDPOINT_ENV_VAR, raising=False)
    monkeypatch.chdir(nested_dir)

    config = get_wikibase_runtime_config()

    assert config.config_path == str(config_path)
    assert config.api_url == "https://rootfallback.example/w/api.php"


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
