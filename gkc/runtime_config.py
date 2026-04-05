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
DEFAULT_META_WB_CONFIG_SEARCH_DIRS = ("config", "")
DEFAULT_META_WB_CONFIG_FILENAMES = (
    "meta-wikibase.yaml",
    "meta-wikibase.yml",
    "dd-wikibase.yaml",
    "dd-wikibase.yml",
)


@dataclass(frozen=True)
class SpiritSafeLayout:
    """Resolved SpiritSafe repository layout for runtime artifact lookup."""

    layout_version: int = 1
    materialized_root: Optional[str] = None
    partners_root: Optional[str] = None
    entities_path: str = "cache/entities"
    profiles_path: str = "profiles"
    value_list_queries_path: str = "queries"
    value_list_cache_path: str = "cache/queries"
    semantic_anchors_path: str = "config/semantic_anchors.json"
    logs_path: str = "cache/refresh"
    wikimedia_sites_path: str = "cache/config/wikimedia_sites.json"
    manifest_path: str = "cache/manifest.json"
    entity_index_path: str = "cache/entity_index.json"

    def _resolve(self, spiritsafe_root: str | Path, relative_path: str) -> Path:
        return Path(spiritsafe_root).expanduser().resolve() / relative_path

    def entities_dir(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.entities_path)

    def profiles_dir(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.profiles_path)

    def value_list_queries_dir(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.value_list_queries_path)

    def value_list_cache_dir(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.value_list_cache_path)

    def value_list_query_file(
        self, spiritsafe_root: str | Path, value_list_id: str
    ) -> Path:
        return self.value_list_queries_dir(spiritsafe_root) / f"{value_list_id}.sparql"

    def value_list_cache_file(
        self, spiritsafe_root: str | Path, value_list_id: str
    ) -> Path:
        return self.value_list_cache_dir(spiritsafe_root) / f"{value_list_id}.json"

    def profile_file(self, spiritsafe_root: str | Path, profile_id: str) -> Path:
        return self.profiles_dir(spiritsafe_root) / f"{profile_id}.json"

    def semantic_anchors_file(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.semantic_anchors_path)

    def logs_dir(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.logs_path)

    def wikimedia_sites_file(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.wikimedia_sites_path)

    def manifest_file(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.manifest_path)

    def entity_index_file(self, spiritsafe_root: str | Path) -> Path:
        return self._resolve(spiritsafe_root, self.entity_index_path)


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
    spiritsafe_layout: SpiritSafeLayout = SpiritSafeLayout()


class MetaWikibaseConfigValues(TypedDict):
    config_id: Optional[str]
    label: Optional[str]
    api_url: Optional[str]
    sparql_endpoint: Optional[str]
    name_identifier_property_id: Optional[str]
    internal_name_identifier_prefix: Optional[str]
    spiritsafe_layout: SpiritSafeLayout


def default_meta_wikibase_config_values() -> MetaWikibaseConfigValues:
    return {
        "config_id": None,
        "label": None,
        "api_url": None,
        "sparql_endpoint": None,
        "name_identifier_property_id": None,
        "internal_name_identifier_prefix": None,
        "spiritsafe_layout": SpiritSafeLayout(),
    }


def _read_optional_string(mapping: dict[object, object], key: str) -> Optional[str]:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise RuntimeError(f"meta-wikibase config field '{key}' must be a string")
    stripped = value.strip()
    return stripped or None


def _read_optional_int(mapping: dict[object, object], key: str) -> Optional[int]:
    value = mapping.get(key)
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raise RuntimeError(f"meta-wikibase config field '{key}' must be an integer")


def _read_optional_mapping(
    mapping: dict[object, object], key: str, *, context: str
) -> Optional[dict[object, object]]:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise RuntimeError(f"{context} field '{key}' must be a mapping")
    return value


def _load_spiritsafe_layout(raw_config: dict[object, object]) -> SpiritSafeLayout:
    spiritsafe_config = raw_config.get("spiritsafe")
    if spiritsafe_config is None:
        return SpiritSafeLayout()
    if not isinstance(spiritsafe_config, dict):
        raise RuntimeError("Meta-wikibase config field 'spiritsafe' must be a mapping")

    roots = (
        _read_optional_mapping(
            spiritsafe_config,
            "roots",
            context="Meta-wikibase config field 'spiritsafe'",
        )
        or {}
    )
    paths = (
        _read_optional_mapping(
            spiritsafe_config,
            "paths",
            context="Meta-wikibase config field 'spiritsafe'",
        )
        or {}
    )

    default_layout = SpiritSafeLayout()
    return SpiritSafeLayout(
        layout_version=(
            _read_optional_int(spiritsafe_config, "layout_version")
            or default_layout.layout_version
        ),
        materialized_root=(
            _read_optional_string(roots, "materialized")
            or default_layout.materialized_root
        ),
        partners_root=(
            _read_optional_string(roots, "partners") or default_layout.partners_root
        ),
        entities_path=(
            _read_optional_string(paths, "entities") or default_layout.entities_path
        ),
        profiles_path=(
            _read_optional_string(paths, "profiles") or default_layout.profiles_path
        ),
        value_list_queries_path=(
            _read_optional_string(paths, "value_list_queries")
            or default_layout.value_list_queries_path
        ),
        value_list_cache_path=(
            _read_optional_string(paths, "value_list_cache")
            or default_layout.value_list_cache_path
        ),
        semantic_anchors_path=(
            _read_optional_string(paths, "semantic_anchors")
            or default_layout.semantic_anchors_path
        ),
        logs_path=(_read_optional_string(paths, "logs") or default_layout.logs_path),
        wikimedia_sites_path=(
            _read_optional_string(paths, "wikimedia_sites")
            or default_layout.wikimedia_sites_path
        ),
        manifest_path=(
            _read_optional_string(paths, "manifest") or default_layout.manifest_path
        ),
        entity_index_path=(
            _read_optional_string(paths, "entity_index")
            or default_layout.entity_index_path
        ),
    )


def discover_meta_wikibase_config_path(
    *,
    start_dir: Optional[Path] = None,
    explicit_path: Optional[str] = None,
) -> Optional[Path]:
    explicit_path = explicit_path or os.environ.get(META_WB_CONFIG_ENV_VAR)
    if explicit_path:
        candidate = Path(explicit_path).expanduser()
        if not candidate.is_absolute():
            candidate = (Path.cwd() / candidate).resolve()
        if not candidate.is_file():
            raise RuntimeError(f"META_WB_CONFIG points to a missing file: {candidate}")
        return candidate

    search_root = start_dir or Path.cwd()

    for directory in (search_root, *search_root.parents):
        for subdir in DEFAULT_META_WB_CONFIG_SEARCH_DIRS:
            for filename in DEFAULT_META_WB_CONFIG_FILENAMES:
                candidate = (
                    directory / subdir / filename if subdir else directory / filename
                )
                if candidate.is_file():
                    return candidate

    return None


def load_meta_wikibase_config(path: Path) -> MetaWikibaseConfigValues:
    try:
        raw_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read meta-wikibase config {path}: {exc}"
        ) from exc

    if raw_config is None:
        return default_meta_wikibase_config_values()
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
        "spiritsafe_layout": _load_spiritsafe_layout(raw_config),
    }


def resolve_spiritsafe_layout_for_root(spiritsafe_root: str | Path) -> SpiritSafeLayout:
    """Resolve the authored SpiritSafe layout contract for a local checkout root."""

    root = Path(spiritsafe_root).expanduser().resolve()
    config_path = discover_meta_wikibase_config_path(start_dir=root)
    if config_path is None:
        return SpiritSafeLayout()

    config_values = load_meta_wikibase_config(config_path)
    return config_values.get("spiritsafe_layout", SpiritSafeLayout())


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

    config_path = discover_meta_wikibase_config_path()
    config_values: MetaWikibaseConfigValues
    if config_path:
        config_values = load_meta_wikibase_config(config_path)
    else:
        config_values = default_meta_wikibase_config_values()

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
        spiritsafe_layout=config_values.get("spiritsafe_layout", SpiritSafeLayout()),
    )
