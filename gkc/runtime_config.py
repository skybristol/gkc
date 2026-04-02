"""Runtime configuration helpers for GKC integrations.

Plain meaning: Read read-only integration defaults in one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TypedDict

import yaml

DEFAULT_WIKIBASE_API_URL = "https://datadistillery.wikibase.cloud/w/api.php"
DEFAULT_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
DEFAULT_USER_AGENT = "GKC/1.0 (https://github.com/skybristol/gkc; data integration)"
META_WB_CONFIG_ENV_VAR = "META_WB_CONFIG"
META_WB_API_URL_ENV_VAR = "META_WB_API_URL"
META_WB_SPARQL_ENDPOINT_ENV_VAR = "META_WB_SPARQL_ENDPOINT"
DEFAULT_META_WB_CONFIG_FILENAMES = (
    "meta-wikibase.yaml",
    "meta-wikibase.yml",
    "dd-wikibase.yaml",
    "dd-wikibase.yml",
)


@dataclass(frozen=True)
class WikibaseRuntimeConfig:
    """Read-only Wikibase integration settings resolved from environment."""

    api_url: str
    sparql_endpoint: Optional[str]
    config_path: Optional[str] = None
    config_id: Optional[str] = None
    label: Optional[str] = None
    name_identifier_property_id: Optional[str] = None
    internal_name_identifier_prefix: Optional[str] = None


class MetaWikibaseConfigValues(TypedDict):
    config_id: Optional[str]
    label: Optional[str]
    api_url: Optional[str]
    sparql_endpoint: Optional[str]
    name_identifier_property_id: Optional[str]
    internal_name_identifier_prefix: Optional[str]


def _read_optional_string(mapping: dict[object, object], key: str) -> Optional[str]:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise RuntimeError(f"meta-wikibase config field '{key}' must be a string")
    stripped = value.strip()
    return stripped or None


def _discover_meta_wikibase_config_path() -> Optional[Path]:
    explicit_path = os.environ.get(META_WB_CONFIG_ENV_VAR)
    if explicit_path:
        candidate = Path(explicit_path).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if not candidate.is_file():
            raise RuntimeError(f"META_WB_CONFIG points to a missing file: {candidate}")
        return candidate

    for directory in (Path.cwd(), *Path.cwd().parents):
        for filename in DEFAULT_META_WB_CONFIG_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return candidate

    return None


def _load_meta_wikibase_config(path: Path) -> MetaWikibaseConfigValues:
    try:
        raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read meta-wikibase config {path}: {exc}"
        ) from exc

    if raw_config is None:
        return {
            "config_id": None,
            "label": None,
            "api_url": None,
            "sparql_endpoint": None,
            "name_identifier_property_id": None,
            "internal_name_identifier_prefix": None,
        }
    if not isinstance(raw_config, dict):
        raise RuntimeError(
            f"Meta-wikibase config {path} must contain a top-level mapping"
        )

    meta_config = raw_config.get("meta_wikibase", raw_config)
    if not isinstance(meta_config, dict):
        raise RuntimeError(
            f"Meta-wikibase config {path} field 'meta_wikibase' must be a mapping"
        )

    semantic_conventions = meta_config.get("semantic_conventions")
    if semantic_conventions is None:
        semantic_conventions = {}
    if not isinstance(semantic_conventions, dict):
        raise RuntimeError(
            f"Meta-wikibase config {path} field 'semantic_conventions' must be a mapping"
        )

    return {
        "config_id": _read_optional_string(meta_config, "id"),
        "label": _read_optional_string(meta_config, "label"),
        "api_url": _read_optional_string(meta_config, "api_url"),
        "sparql_endpoint": _read_optional_string(meta_config, "sparql_endpoint"),
        "name_identifier_property_id": _read_optional_string(
            semantic_conventions, "name_identifier_property_id"
        ),
        "internal_name_identifier_prefix": _read_optional_string(
            semantic_conventions, "internal_name_identifier_prefix"
        ),
    }


def get_wikibase_runtime_config() -> WikibaseRuntimeConfig:
    """Return resolved Wikibase runtime settings.

    Resolution order:
      - Config file path from META_WB_CONFIG, when set explicitly
      - Auto-discovered config file in current/parent directories
      - API URL override: META_WB_API_URL or config file value or default
      - SPARQL endpoint override: META_WB_SPARQL_ENDPOINT or config file value
        or default Wikidata QS endpoint

    Authentication is intentionally out of scope here. Generic MediaWiki
    authentication continues to flow through ``WikiverseAuth`` and the
    ``WIKIVERSE_*`` environment variables or explicit parameters.
    """

    config_path = _discover_meta_wikibase_config_path()
    config_values: MetaWikibaseConfigValues
    if config_path:
        config_values = _load_meta_wikibase_config(config_path)
    else:
        config_values = {
            "config_id": None,
            "label": None,
            "api_url": None,
            "sparql_endpoint": None,
            "name_identifier_property_id": None,
            "internal_name_identifier_prefix": None,
        }

    api_url = (
        os.environ.get(META_WB_API_URL_ENV_VAR)
        or config_values.get("api_url")
        or DEFAULT_WIKIBASE_API_URL
    )
    sparql_endpoint = (
        os.environ.get(META_WB_SPARQL_ENDPOINT_ENV_VAR)
        or config_values.get("sparql_endpoint")
        or DEFAULT_SPARQL_ENDPOINT
    )

    return WikibaseRuntimeConfig(
        api_url=api_url,
        sparql_endpoint=sparql_endpoint,
        config_path=str(config_path) if config_path else None,
        config_id=config_values.get("config_id"),
        label=config_values.get("label"),
        name_identifier_property_id=config_values.get("name_identifier_property_id"),
        internal_name_identifier_prefix=config_values.get(
            "internal_name_identifier_prefix"
        ),
    )
