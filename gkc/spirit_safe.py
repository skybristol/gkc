"""
SpiritSafe utilities for profile-based data management.

This module provides infrastructure for managing YAML profiles, including
SPARQL-backed choice list fetching, caching, and result normalization.

Named after the locked cabinet in traditional distilleries where the master
distiller inspects and approves the product before it's sent to barrel aging
or bottling.

Plain meaning: Tools for working with SpiritSafe profiles and their data sources.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, Optional, Union
from urllib.parse import urlparse

import requests

from gkc.mash import (
    WikibaseApiClient,
    extract_first_sparql_block,
    fetch_mediawiki_page_wikitext,
)
from gkc.runtime_config import (
    DEFAULT_META_WB_CONFIG_FILENAMES,
    DEFAULT_META_WB_CONFIG_SEARCH_DIRS,
    MetaWikibaseConfigValues,
    default_meta_wikibase_config_values,
    load_meta_wikibase_config,
)
from gkc.sparql import SPARQLQuery, paginate_query, read_sparql_query_file

RefreshPolicy = Literal["manual", "daily", "weekly", "on_release"]
SpiritSafeSourceMode = Literal["github", "local"]

DEFAULT_SPIRIT_SAFE_GITHUB_REPO = "skybristol/SpiritSafe"


@dataclass(frozen=True)
class SpiritSafeSourceConfig:
    """Package-level configuration for SpiritSafe source location.

    Args:
        mode: Source mode ("github" or "local")
        github_repo: GitHub repository slug for SpiritSafe assets
        github_ref: Git ref used for GitHub raw file resolution
        local_root: Local SpiritSafe clone root when mode is "local"

    Plain meaning: Decide whether SpiritSafe assets come from GitHub or local disk.
    """

    mode: SpiritSafeSourceMode = "github"
    github_repo: str = DEFAULT_SPIRIT_SAFE_GITHUB_REPO
    github_ref: str = "main"
    local_root: Optional[Path] = None

    def resolve_cache_dir(self) -> Path:
        """Resolve default cache directory for the configured source.

        Returns:
            Filesystem path to cache directory.
        """
        if self.mode == "local" and self.local_root is not None:
            return self.local_root / "cache"

        repo_slug = self.github_repo.replace("/", "_")
        return Path.home() / ".cache" / "gkc" / "spiritsafe" / repo_slug / "cache"

    def resolve_relative(self, relative_path: str) -> Union[Path, str]:
        """Resolve a SpiritSafe-relative path to local path or GitHub raw URL.

        Args:
            relative_path: Relative path inside SpiritSafe repository.

        Returns:
            Local filesystem path (local mode) or GitHub raw URL (github mode).
        """
        normalized = relative_path.lstrip("/")
        if self.mode == "local":
            if self.local_root is None:
                raise ValueError("local_root is required when mode='local'")
            return self.local_root / normalized

        return (
            f"https://raw.githubusercontent.com/{self.github_repo}/"
            f"{self.github_ref}/{normalized}"
        )


_SPIRIT_SAFE_SOURCE_CONFIG = SpiritSafeSourceConfig()


def set_spirit_safe_source(
    mode: SpiritSafeSourceMode = "github",
    github_repo: str = DEFAULT_SPIRIT_SAFE_GITHUB_REPO,
    github_ref: str = "main",
    local_root: Optional[Union[str, Path]] = None,
) -> None:
    """Set package-wide SpiritSafe source location.

    Args:
        mode: Source mode ("github" or "local").
        github_repo: GitHub repository slug for SpiritSafe assets.
        github_ref: Git ref used for GitHub raw file resolution.
        local_root: Local SpiritSafe clone root when mode is "local".

    Raises:
        ValueError: If local mode is requested without local_root.

    Plain meaning: Configure where SpiritSafe profiles/queries/caches are resolved.
    """
    global _SPIRIT_SAFE_SOURCE_CONFIG

    normalized_local_root: Optional[Path] = None
    if mode == "local":
        if local_root is None:
            raise ValueError("local_root is required when mode='local'")
        normalized_local_root = Path(local_root).expanduser().resolve()

    _SPIRIT_SAFE_SOURCE_CONFIG = SpiritSafeSourceConfig(
        mode=mode,
        github_repo=github_repo,
        github_ref=github_ref,
        local_root=normalized_local_root,
    )


def get_spirit_safe_source() -> SpiritSafeSourceConfig:
    """Get current package-wide SpiritSafe source configuration.

    Returns:
        Active SpiritSafe source configuration.

    Plain meaning: See where SpiritSafe data is configured to come from.
    """
    return _SPIRIT_SAFE_SOURCE_CONFIG


# ============================================================================
# Profile Registry Abstraction
# ============================================================================


def _read_text_from_resolved_path(resolved: Union[Path, str]) -> str:
    """Read text content from a resolved path or URL.

    Args:
        resolved: Local Path or GitHub raw URL

    Returns:
        Text content of the file

    Raises:
        FileNotFoundError: If file/URL cannot be read
    """
    if isinstance(resolved, Path):
        return resolved.read_text(encoding="utf-8")
    # GitHub URL
    response = requests.get(str(resolved), timeout=10)
    response.raise_for_status()
    return response.text


def list_profiles() -> list[str]:
    """List all available profile IDs in the configured SpiritSafe source.

    Returns:
        List of profile identifiers (directory names under profiles/)

    Example:
        >>> profiles = list_profiles()
        >>> print(profiles)
        ['TribalGovernmentUS', 'OfficeHeldByHeadOfState']

    Note:
        For GitHub mode, this requires an API call to list directory contents.
        For local mode, this scans the local profiles/ directory.

        **Design Question**: Should we maintain a central registry.yaml file
        in SpiritSafe to avoid GitHub API calls and provide additional metadata
        like profile categories, deprecation warnings, or featured profiles?

    Plain meaning: See what entity profiles are available.
    """
    source = get_spirit_safe_source()

    if source.mode == "local":
        if source.local_root is None:
            raise ValueError("local_root required for local mode")
        profiles_dir = source.local_root / "profiles"
        if not profiles_dir.exists():
            return []
        # List directories only
        return sorted(
            [
                item.name
                for item in profiles_dir.iterdir()
                if item.is_dir() and not item.name.startswith(".")
            ]
        )

    # GitHub mode: use GitHub API to list directory contents
    api_url = (
        f"https://api.github.com/repos/{source.github_repo}/"
        f"contents/profiles?ref={source.github_ref}"
    )
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        contents = response.json()
        # Filter for directories only
        return sorted([item["name"] for item in contents if item["type"] == "dir"])
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to list profiles from {source.github_repo}: {exc}"
        ) from exc


def profile_exists(profile_id: str) -> bool:
    """Check if a profile exists in the configured SpiritSafe source.

    Args:
        profile_id: Profile identifier to check

    Returns:
        True if profile exists, False otherwise

    Example:
        >>> if profile_exists("TribalGovernmentUS"):
        ...     print("Profile found")

    Plain meaning: Check if a specific entity profile is available.
    """
    try:
        # Attempt to resolve the profile path
        profile_path = f"profiles/{profile_id}/profile.yaml"
        source = get_spirit_safe_source()
        resolved = source.resolve_relative(profile_path)
        _read_text_from_resolved_path(resolved)
        return True
    except Exception:
        return False


class LookupCache:
    """Manage cached SPARQL lookup results.

    Args:
        cache_dir: Directory for cache storage (default from active SpiritSafe source)

    Example:
        >>> cache = LookupCache()
        >>> cache.get("query_hash")

    Plain meaning: Store and retrieve SPARQL query results from disk.
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize cache manager.

        Args:
            cache_dir: Cache storage directory (default from active SpiritSafe source)
        """
        if cache_dir is None:
            cache_dir = get_spirit_safe_source().resolve_cache_dir()

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _query_hash(self, query: str) -> str:
        """Generate a hash for a query string.

        Args:
            query: SPARQL query string

        Returns:
            SHA256 hash of the query
        """
        return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]

    def _cache_path(self, query: str) -> Path:
        """Get cache file path for a query.

        Args:
            query: SPARQL query string

        Returns:
            Path to cache file
        """
        query_hash = self._query_hash(query)
        return self.cache_dir / f"{query_hash}.json"

    def get(self, query: str) -> Optional[dict[str, Any]]:
        """Retrieve cached results for a query.

        Args:
            query: SPARQL query string

        Returns:
            Cached data dict or None if not found

        Example:
            >>> cache = LookupCache()
            >>> data = cache.get("SELECT ?item WHERE { ... }")
        """
        cache_path = self._cache_path(query)
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def set(
        self,
        query: str,
        results: list[dict[str, Any]],
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Cache results for a query.

        Args:
            query: SPARQL query string
            results: Query results to cache
            metadata: Optional metadata to store with results

        Example:
            >>> cache = LookupCache()
            >>> cache.set("SELECT ...", [{"item": "Q123"}])
        """
        cache_path = self._cache_path(query)

        cache_data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "metadata": metadata or {},
        }

        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)

    def is_fresh(self, query: str, refresh_policy: RefreshPolicy = "manual") -> bool:
        """Check if cached results are still fresh.

        Args:
            query: SPARQL query string
            refresh_policy: Refresh policy to check against

        Returns:
            True if cache is fresh, False otherwise

        Example:
            >>> cache = LookupCache()
            >>> if not cache.is_fresh(query, "daily"):
            ...     # Refresh cache
        """
        if refresh_policy == "manual":
            # Manual refresh: always consider fresh if exists
            return self.get(query) is not None

        cached = self.get(query)
        if cached is None:
            return False

        # Parse timestamp
        try:
            cached_time = datetime.fromisoformat(cached["timestamp"])
        except (KeyError, ValueError):
            return False

        # Check freshness based on policy
        now = datetime.now()
        if refresh_policy == "daily":
            return (now - cached_time) < timedelta(days=1)
        elif refresh_policy == "weekly":
            return (now - cached_time) < timedelta(weeks=1)
        # on_release would need version comparison (not implemented yet)
        return False

    def invalidate(self, query: str) -> bool:
        """Invalidate cache for a specific query.

        Args:
            query: SPARQL query string

        Returns:
            True if cache was invalidated, False if not found

        Example:
            >>> cache = LookupCache()
            >>> cache.invalidate("SELECT ...")
        """
        cache_path = self._cache_path(query)
        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear_all(self) -> int:
        """Clear all cached queries.

        Returns:
            Number of cache files deleted

        Example:
            >>> cache = LookupCache()
            >>> count = cache.clear_all()
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            count += 1
        return count


class LookupFetcher:
    """Fetch and cache SPARQL-backed choice lists.

    Args:
        cache: Optional LookupCache instance
        endpoint: SPARQL endpoint URL

    Example:
        >>> fetcher = LookupFetcher()
        >>> results = fetcher.fetch(query, refresh_policy="daily")

    Plain meaning: Execute SPARQL queries for choice lists with caching.
    """

    def __init__(
        self,
        cache: Optional[LookupCache] = None,
        endpoint: str = "https://query.wikidata.org/sparql",
    ):
        """Initialize lookup fetcher.

        Args:
            cache: LookupCache instance (creates default if None)
            endpoint: SPARQL endpoint URL
        """
        self.cache = cache or LookupCache()
        self.endpoint = endpoint
        self.sparql = SPARQLQuery(endpoint=endpoint)

    def _dedupe_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate results based on unique identifier.

        Handles query result redundancy from SPARQL endpoints or pagination
        artifacts by tracking seen items and keeping only first occurrence.
        Uses the "item" field as the unique identifier (standard for Wikidata).

        Args:
            results: Raw results from SPARQL query execution.

        Returns:
            Deduplicated results list preserving order of first occurrence.

        Plain meaning: Remove duplicate rows from query results.
        """
        seen_items: set[str] = set()
        deduplicated: list[dict[str, Any]] = []

        for result in results:
            # Use "item" field as unique identifier (Wikidata convention)
            # If no item field, use entire result as dict key (as string)
            if "item" in result:
                item_key = result["item"]
            else:
                # Fallback: use string representation of the entire row
                # This handles cases with multiple identifier fields
                item_key = tuple(sorted(result.items())).__str__()

            if item_key not in seen_items:
                seen_items.add(item_key)
                deduplicated.append(result)

        return deduplicated

    def fetch(
        self,
        query: str,
        refresh_policy: RefreshPolicy = "manual",
        force_refresh: bool = False,
        page_size: int = 1000,
        max_results: Optional[int] = None,
    ) -> list[dict[str, str]]:
        """Fetch lookup results with caching.

        Args:
            query: SPARQL query string
            refresh_policy: Cache refresh policy
            force_refresh: Force cache refresh even if fresh
            page_size: Results per page for pagination
            max_results: Maximum total results to fetch

        Returns:
            List of result dictionaries

        Raises:
            SPARQLError: If query execution fails

        Example:
            >>> fetcher = LookupFetcher()
            >>> results = fetcher.fetch(
            ...     "SELECT ?item ?itemLabel WHERE { ... }",
            ...     refresh_policy="daily"
            ... )

        Plain meaning: Get lookup data from cache or query endpoint.
        """
        # Check cache first
        if not force_refresh and self.cache.is_fresh(query, refresh_policy):
            cached = self.cache.get(query)
            if cached is not None:
                return cached["results"]

        # Execute query with pagination
        results = paginate_query(
            query,
            page_size=page_size,
            endpoint=self.endpoint,
            max_results=max_results,
        )

        # Deduplicate results to handle redundant query results
        # (can occur with certain SPARQL patterns or pagination artifacts)
        results = self._dedupe_results(results)

        # Cache results
        self.cache.set(
            query,
            results,
            metadata={
                "refresh_policy": refresh_policy,
                "result_count": len(results),
            },
        )

        return results

    def fetch_choice_list(
        self,
        query: str,
        id_var: str = "item",
        label_var: str = "itemLabel",
        extra_vars: Optional[list[str]] = None,
        refresh_policy: RefreshPolicy = "manual",
        force_refresh: bool = False,
    ) -> list[dict[str, str]]:
        """Fetch a choice list with normalized structure.

        Normalizes SPARQL results to a consistent choice list format
        with id, label, and optional extra fields.

        Args:
            query: SPARQL query string
            id_var: Variable name for item ID (default: "item")
            label_var: Variable name for label (default: "itemLabel")
            extra_vars: Optional list of extra variable names to include
            refresh_policy: Cache refresh policy
            force_refresh: Force cache refresh

        Returns:
            List of choice items with normalized structure

        Example:
            >>> fetcher = LookupFetcher()
            >>> choices = fetcher.fetch_choice_list(
            ...     query,
            ...     id_var="item",
            ...     label_var="itemLabel",
            ...     extra_vars=["languageCode"]
            ... )
            >>> # Returns: [{"id": "Q123", "label": "Example", "languageCode": "en"}]

        Plain meaning: Get normalized choice data for forms and validation.
        """
        raw_results = self.fetch(query, refresh_policy, force_refresh)

        # Normalize to choice list format
        choices = []
        for row in raw_results:
            choice: dict[str, str] = {}

            # Extract ID (handle URLs with entity IDs)
            id_value = row.get(id_var, "")
            if "/" in id_value:
                # Extract QID from URL
                # (e.g., http://www.wikidata.org/entity/Q123 -> Q123)
                id_value = id_value.split("/")[-1]
            choice["id"] = id_value

            # Extract label
            choice["label"] = row.get(label_var, "")

            # Extract extra fields if specified
            if extra_vars:
                for var in extra_vars:
                    if var in row:
                        choice[var] = row[var]

            choices.append(choice)

        return choices


def resolve_profile_path(profile_ref: Union[str, Path]) -> Union[str, Path]:
    """Resolve a profile reference to a path within SpiritSafe structure.

    Handles profile name resolution (with or without .yaml extension) to the
    registrant package path (`profiles/<ProfileName>/profile.yaml`) and preserves
    explicit paths as-is.

    Args:
        profile_ref: Profile name (e.g., "TribalGovernmentUS",
                "TribalGovernmentUS.yaml") or explicit path
                (e.g., "profiles/TribalGovernmentUS/profile.yaml").

    Returns:
        Resolved path suitable for ``resolve_query_ref``.
    """
    ref_str = str(profile_ref)

    # If it's already a path with directory separators, use as-is
    if "/" in ref_str or "\\" in ref_str:
        return profile_ref

    # If it looks like an absolute path, use as-is
    path_obj = Path(profile_ref)
    if path_obj.is_absolute():
        return profile_ref

    # Simple profile name: resolve to registrant package path
    # Allow both "ProfileName" and "ProfileName.yaml" inputs
    profile_name = ref_str.removesuffix(".yaml")
    return f"profiles/{profile_name}/profile.yaml"


def resolve_query_ref(
    query_ref: str, profile_path: Union[str, Path]
) -> Union[Path, str]:
    """Resolve a query reference relative to profile location with root fallback.

    Resolution strategy:
    1. Try profile-relative first (profiles/<Name>/queries/file.sparql)
    2. Fall back to root-relative (queries/file.sparql)

    Args:
        query_ref: Query reference path from profile (e.g., "queries/file.sparql")
        profile_path: Path to the profile file that references the query

    Returns:
        Resolved path (local Path or GitHub URL depending on source mode)

    Raises:
        FileNotFoundError: If query cannot be found in either location

    Example:
        >>> # For profile "profiles/TribalGovernmentUS/profile.yaml"
        >>> # and query_ref "queries/file.sparql"
        >>> resolve_query_ref(
        ...     "queries/file.sparql",
        ...     "profiles/TribalGovernmentUS/profile.yaml",
        ... )
        # tries: profiles/TribalGovernmentUS/queries/file.sparql
        # then:  queries/file.sparql

    Plain meaning: Find query file near profile first, then in global queries directory.
    """
    source = get_spirit_safe_source()
    profile_path_str = str(profile_path)

    # Extract profile directory for registrant-style profiles
    # profiles/Foo/profile.yaml -> profiles/Foo/
    profile_dir: Optional[str] = None
    if "/" in profile_path_str or "\\" in profile_path_str:
        profile_parent = str(Path(profile_path_str).parent)
        # Only treat as profile directory if it looks like a registrant path
        if profile_parent.startswith("profiles/") and profile_parent != "profiles":
            profile_dir = profile_parent

    candidates: list[str] = []

    # Strategy 1: profile-relative (only if we have a profile directory)
    if profile_dir:
        profile_relative = f"{profile_dir}/{query_ref}".replace("//", "/")
        candidates.append(profile_relative)

    # Strategy 2: root-relative fallback
    candidates.append(query_ref)

    last_error: Optional[Exception] = None
    for candidate in candidates:
        try:
            resolved = source.resolve_relative(candidate)
            # Verify the path exists before returning it
            _read_text_from_resolved_path(resolved)
            return resolved
        except Exception as exc:
            last_error = exc

    # Build helpful error message
    tried_paths = ", ".join(candidates)
    if last_error is not None:
        raise FileNotFoundError(
            f"Query not found: {query_ref} (tried: {tried_paths})"
        ) from last_error

    raise FileNotFoundError(f"Query not found: {query_ref} (tried: {tried_paths})")


@dataclass(frozen=True)
class ValueListHydrationResult:
    """Summary of value-list query export and hydration operations."""

    queries_dir: str
    cache_queries_dir: str
    discovered_ids: list[str] = field(default_factory=list)
    hydrated_ids: list[str] = field(default_factory=list)
    query_files_written: list[str] = field(default_factory=list)
    cache_files_written: list[str] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)


def discover_value_list_ids(
    cache_entities_dir: Union[str, Path],
    *,
    value_list_class_id: str = "Q7",
) -> list[str]:
    """Discover all value-list entity IDs from SpiritSafe cache entities.

    Value lists are identified by `P1 -> Q7` classification in cached entity claims.
    """
    cache_dir = Path(cache_entities_dir)
    discovered: list[str] = []

    for path in sorted(cache_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        entity_id = payload.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id:
            continue

        claims = payload.get("entity", {}).get("claims", {})
        p1_claims = claims.get("P1", []) if isinstance(claims, dict) else []
        if _claims_include_entity_id(p1_claims, value_list_class_id):
            discovered.append(entity_id)

    return sorted(discovered)


def export_value_list_sparql_queries(
    *,
    cache_entities_dir: Union[str, Path],
    queries_dir: Union[str, Path],
    api_url: str,
    value_list_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Export first `<sparql>` talk-page blocks into SpiritSafe query files.

    Writes one file per value-list ID as `<queries_dir>/<QID>.sparql`.
    """
    selected_ids = sorted(
        set(value_list_ids or discover_value_list_ids(cache_entities_dir))
    )
    out_dir = Path(queries_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    api_client = WikibaseApiClient(api_url=api_url)
    written_files: list[str] = []
    failures: list[dict[str, Any]] = []

    for entity_id in selected_ids:
        title = f"Item_talk:{entity_id}"
        try:
            wikitext = fetch_mediawiki_page_wikitext(api_client=api_client, title=title)
            query_text = extract_first_sparql_block(wikitext)
            output_path = out_dir / f"{entity_id}.sparql"
            output_path.write_text(query_text.strip() + "\n", encoding="utf-8")
            written_files.append(str(output_path.resolve()))
        except Exception as exc:
            failures.append(
                {
                    "value_list_id": entity_id,
                    "source_title": title,
                    "error": str(exc),
                }
            )

    return {
        "value_list_ids": selected_ids,
        "queries_dir": str(out_dir.resolve()),
        "query_files_written": sorted(written_files),
        "failures": failures,
    }


def hydrate_value_list_query_caches(
    *,
    value_list_ids: list[str],
    queries_dir: Union[str, Path],
    cache_queries_dir: Union[str, Path],
    endpoint: str,
    page_size: int = 1000,
    max_results: Optional[int] = None,
    wikibase_api_url: str = "https://datadistillery.wikibase.cloud/w/api.php",
) -> dict[str, Any]:
    """Hydrate value-list JSON cache artifacts from local `.sparql` files.

    Existing cache files are preserved if hydration fails for an item.
    """
    query_root = Path(queries_dir)
    cache_root = Path(cache_queries_dir)
    cache_root.mkdir(parents=True, exist_ok=True)

    base_uri = _wikibase_base_uri_from_api_url(wikibase_api_url)

    hydrated_ids: list[str] = []
    written_files: list[str] = []
    failures: list[dict[str, Any]] = []

    for entity_id in value_list_ids:
        query_file = query_root / f"{entity_id}.sparql"
        output_file = cache_root / f"{entity_id}.json"
        try:
            query_text = read_sparql_query_file(query_file)
            rows = paginate_query(
                query=query_text,
                page_size=page_size,
                endpoint=endpoint,
                max_results=max_results,
            )
            items = _normalize_value_list_items(rows)
            columns = sorted({key for item in items for key in item.keys()})
            payload = {
                "metadata": {
                    "entity": f"{base_uri}/entity/{entity_id}",
                    "source": f"{base_uri}/wiki/Item_talk:{entity_id}",
                    "query": f"queries/{entity_id}.sparql",
                    "updated": datetime.now(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "count": len(items),
                    "columns": columns,
                },
                "items": items,
            }
            output_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            hydrated_ids.append(entity_id)
            written_files.append(str(output_file.resolve()))
        except Exception as exc:
            failures.append(
                {
                    "value_list_id": entity_id,
                    "query_file": str(query_file),
                    "cache_file": str(output_file),
                    "error": str(exc),
                }
            )

    return {
        "value_list_ids": value_list_ids,
        "cache_queries_dir": str(cache_root.resolve()),
        "hydrated_ids": sorted(hydrated_ids),
        "cache_files_written": sorted(written_files),
        "failures": failures,
    }


def hydrate_value_lists_from_cache(
    *,
    cache_entities_dir: Union[str, Path],
    queries_dir: Union[str, Path],
    cache_queries_dir: Union[str, Path],
    api_url: str,
    endpoint: str,
    value_list_ids: Optional[list[str]] = None,
    page_size: int = 1000,
    max_results: Optional[int] = None,
    fail_on_hydration_error: bool = True,
) -> ValueListHydrationResult:
    """Export value-list SPARQL files and hydrate value-list cache artifacts."""
    export_summary = export_value_list_sparql_queries(
        cache_entities_dir=cache_entities_dir,
        queries_dir=queries_dir,
        api_url=api_url,
        value_list_ids=value_list_ids,
    )

    export_failures = list(export_summary.get("failures", []))
    if export_failures and fail_on_hydration_error:
        first = export_failures[0]
        raise RuntimeError(
            "Failed to export value-list SPARQL query "
            f"for {first.get('value_list_id')}: {first.get('error')}"
        )

    eligible_ids = [
        value_list_id
        for value_list_id in export_summary["value_list_ids"]
        if value_list_id not in {f.get("value_list_id") for f in export_failures}
    ]

    hydrate_summary = hydrate_value_list_query_caches(
        value_list_ids=eligible_ids,
        queries_dir=queries_dir,
        cache_queries_dir=cache_queries_dir,
        endpoint=endpoint,
        page_size=page_size,
        max_results=max_results,
        wikibase_api_url=api_url,
    )

    failures = export_failures + list(hydrate_summary.get("failures", []))
    if failures and fail_on_hydration_error:
        first = failures[0]
        raise RuntimeError(
            "Value-list hydration failed "
            f"for {first.get('value_list_id')}: {first.get('error')}"
        )

    return ValueListHydrationResult(
        queries_dir=export_summary["queries_dir"],
        cache_queries_dir=hydrate_summary["cache_queries_dir"],
        discovered_ids=sorted(export_summary["value_list_ids"]),
        hydrated_ids=sorted(hydrate_summary["hydrated_ids"]),
        query_files_written=sorted(export_summary["query_files_written"]),
        cache_files_written=sorted(hydrate_summary["cache_files_written"]),
        failures=failures,
    )


def _claims_include_entity_id(claims: Any, expected_id: str) -> bool:
    if not isinstance(claims, list):
        return False

    for claim in claims:
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if isinstance(value, dict) and value.get("id") == expected_id:
            return True
    return False


def _wikibase_base_uri_from_api_url(api_url: str) -> str:
    parsed = urlparse(api_url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    raise ValueError(f"Invalid Wikibase API URL: {api_url}")


def _normalize_value_list_items(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped_by_item: dict[str, dict[str, str]] = {}

    for row in rows:
        item = row.get("item")
        item_label = row.get("itemLabel")
        if not item or not item_label:
            continue

        normalized_row: dict[str, str] = {"item": item, "itemLabel": item_label}
        for key, value in row.items():
            if key in {"item", "itemLabel"}:
                continue
            if isinstance(value, str) and value:
                normalized_row[key] = value

        existing = deduped_by_item.get(item)
        if existing is None:
            deduped_by_item[item] = normalized_row
            continue

        # Duplicate rows are allowed only if non-core fields are identical.
        existing_extra = {
            key: value
            for key, value in existing.items()
            if key not in {"item", "itemLabel"}
        }
        candidate_extra = {
            key: value
            for key, value in normalized_row.items()
            if key not in {"item", "itemLabel"}
        }
        if existing_extra != candidate_extra:
            raise ValueError(
                "Duplicate value-list row conflict for item "
                f"{item}: non-core fields differ between rows"
            )

    return sorted(
        deduped_by_item.values(),
        key=lambda entry: (entry["itemLabel"].casefold(), entry["item"]),
    )


class EntityProfileJsonBuilder:
    """Build JSON entity profiles from SpiritSafe per-entity cache files.

    Plain meaning: Convert profile-linked cache entities into JSON profile docs.
    """

    PROFILE_CLASS_ID = "Q3"

    PROFILE_STATEMENT = "P157"
    HAS_QUALIFIER = "P158"
    HAS_VALUE = "P161"
    VALUE_TYPE = "P194"
    IO_MAP = "P5"
    PROMPT = "P171"
    GUIDANCE = "P169"
    CONSEQUENCES = "P170"
    ERROR_MESSAGE = "P168"
    MAX_COUNT = "P182"
    HAS_REFERENCE = "P211"
    APPLIES_TO_PROFILE = "P205"
    APPLIES_TO_STATEMENT = "P163"
    DERIVES_DEFAULT_VALUE_FROM = "P213"

    LABEL_PROMPT = "P188"
    LABEL_GUIDANCE = "P185"
    DESCRIPTION_PROMPT = "P189"
    DESCRIPTION_GUIDANCE = "P186"
    ALIAS_PROMPT = "P190"
    ALIAS_GUIDANCE = "P187"

    NAME_IDENTIFIER = "P214"
    SAME_AS = "P5"
    WIKIDATA_ENTITY_URL = "P5"
    GKC_ENTITY_PROFILE_CLASS = "Q3"
    GKC_VALUE_LIST_CLASS = "Q7"
    WIKIDATA_ENTITY_CLASS = "Q52"
    STATEMENT_MODIFIER_CLASS = "Q58"

    LANGUAGE_KEY_PATTERN = re.compile(
        r"^(mul|[a-z]{2,3}(?:-[a-z0-9]+)*)$", re.IGNORECASE
    )

    MESSAGE_FIELD_BY_PROP = {
        PROMPT: "prompt",
        GUIDANCE: "guidance",
        CONSEQUENCES: "consequences_message",
        ERROR_MESSAGE: "error_message",
    }

    def __init__(
        self,
        cache_entities_dir: Union[str, Path],
        entity_prefix: str = "https://datadistillery.wikibase.cloud/entity/",
        label_language_order: tuple[str, ...] = ("mul", "en"),
        description_language_order: tuple[str, ...] = ("en", "mul"),
    ) -> None:
        self.cache_entities_dir = Path(cache_entities_dir)
        self.entity_prefix = entity_prefix.rstrip("/") + "/"
        self.label_language_order = label_language_order
        self.description_language_order = description_language_order
        self._cache_index = self._load_cache_index()

    def build_all(self) -> list[dict[str, Any]]:
        """Build JSON documents for every cache entity typed as a profile."""
        return self.build_all_with_report()["documents"]

    def build_all_with_report(self) -> dict[str, Any]:
        """Build JSON profile documents and collect language-policy diagnostics."""
        results: list[dict[str, Any]] = []
        skipped_profiles: list[dict[str, Any]] = []
        language_filtering: list[dict[str, Any]] = []

        for doc in self._cache_index.values():
            if self._is_profile_item(doc):
                try:
                    built, filtering_report = self._build_one_with_language_policy(doc)
                    results.append(built)
                    if filtering_report.get("excluded_languages"):
                        language_filtering.append(filtering_report)
                except EntityProfileLanguageCoverageError as exc:
                    skipped_profiles.append(
                        {
                            "profile_id": exc.profile_id,
                            "code": "mul_language_coverage_failed",
                            "message": str(exc),
                            "missing_paths": exc.missing_paths,
                        }
                    )

        return {
            "documents": results,
            "skipped_profiles": skipped_profiles,
            "language_filtering": language_filtering,
        }

    def build_one(self, wikibase_item: dict[str, Any]) -> dict[str, Any]:
        """Build one JSON profile document from a single cache entity."""
        built, _ = self._build_one_with_language_policy(wikibase_item)
        return built

    def _build_one_with_language_policy(
        self, wikibase_item: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Build one JSON profile and enforce profile language completeness policy."""
        entity_uri = f"{self.entity_prefix}{wikibase_item.get('entity_id', '')}"
        name_identifier = self._entity_name_identifier(wikibase_item)

        identification = {
            "labels": self._build_language_section(
                wikibase_item, self.LABEL_PROMPT, self.LABEL_GUIDANCE
            ),
            "descriptions": self._build_language_section(
                wikibase_item, self.DESCRIPTION_PROMPT, self.DESCRIPTION_GUIDANCE
            ),
            "aliases": self._build_language_section(
                wikibase_item, self.ALIAS_PROMPT, self.ALIAS_GUIDANCE
            ),
        }

        statements = self._build_profile_statements(wikibase_item)
        metadata = self._build_profile_metadata(
            wikibase_item,
            identification=identification,
            statements=statements,
            entity_uri=entity_uri,
        )

        profile_doc = {
            "id": entity_uri,
            "name_identifier": name_identifier,
            "entity": entity_uri,
            "identification": identification,
            "statements": statements,
            "metadata": metadata,
        }

        return self._apply_language_completeness_policy(profile_doc)

    def _apply_language_completeness_policy(
        self, profile_doc: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        profile_id = str(profile_doc.get("entity", "")).rstrip("/").split("/")[-1]
        candidates = set(self._collect_languages(profile_doc))
        candidates.add("mul")

        missing_by_language: dict[str, list[str]] = {}
        for language in sorted(candidates):
            missing = self._missing_language_coverage(profile_doc, language)
            if missing:
                missing_by_language[language] = missing

        mul_missing = missing_by_language.get("mul", [])
        if mul_missing:
            raise EntityProfileLanguageCoverageError(
                profile_id=profile_id or "<unknown>",
                missing_paths=mul_missing,
            )

        allowed_languages = {"mul"}
        excluded_languages: list[dict[str, Any]] = []
        for language in sorted(candidates):
            if language == "mul":
                continue
            missing = missing_by_language.get(language, [])
            if missing:
                excluded_languages.append(
                    {
                        "language": language,
                        "missing_paths": missing,
                    }
                )
                continue
            allowed_languages.add(language)

        self._prune_profile_languages(profile_doc, allowed_languages)
        self._recompute_profile_languages(profile_doc)

        return profile_doc, {
            "profile_id": profile_id,
            "excluded_languages": excluded_languages,
        }

    def _missing_language_coverage(
        self, profile_doc: dict[str, Any], language: str
    ) -> list[str]:
        missing: list[str] = []

        metadata = profile_doc.get("metadata", {})
        identification = profile_doc.get("identification", {})

        labels = metadata.get("labels", {}) if isinstance(metadata, dict) else {}
        descriptions = (
            metadata.get("descriptions", {}) if isinstance(metadata, dict) else {}
        )
        aliases = metadata.get("aliases", {}) if isinstance(metadata, dict) else {}

        if not self._metadata_has_label(labels, language):
            missing.append(f"metadata.labels.{language}")

        if not self._metadata_has_description(descriptions, language):
            if language == "mul":
                missing.append("metadata.descriptions.mul_or_en")
            else:
                missing.append(f"metadata.descriptions.{language}")

        if aliases and not self._metadata_has_alias(aliases, language):
            missing.append(f"metadata.aliases.{language}")

        if not self._identification_has_prompt(identification, "labels", language):
            missing.append(f"identification.labels.{language}.prompt")

        if not self._identification_has_prompt(
            identification, "descriptions", language
        ):
            missing.append(f"identification.descriptions.{language}.prompt")

        if not self._identification_has_prompt(identification, "aliases", language):
            missing.append(f"identification.aliases.{language}.prompt")

        statements = profile_doc.get("statements", [])
        for statement in self._iter_statement_nodes(statements):
            entity = statement.get("entity", "<unknown>")
            messages = statement.get("messages", {})
            if not isinstance(messages, dict):
                missing.append(f"statement:{entity}.messages.{language}.prompt")
                continue
            prompt = messages.get(language, {}).get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                missing.append(f"statement:{entity}.messages.{language}.prompt")

        return sorted(set(missing))

    def _metadata_has_label(self, labels: Any, language: str) -> bool:
        return isinstance(labels, dict) and isinstance(labels.get(language), str)

    def _metadata_has_description(self, descriptions: Any, language: str) -> bool:
        if not isinstance(descriptions, dict):
            return False
        if language == "mul":
            mul_value = descriptions.get("mul")
            en_value = descriptions.get("en")
            return isinstance(mul_value, str) or isinstance(en_value, str)
        return isinstance(descriptions.get(language), str)

    def _metadata_has_alias(self, aliases: Any, language: str) -> bool:
        if not isinstance(aliases, dict):
            return False
        values = aliases.get(language)
        return isinstance(values, list) and any(
            isinstance(value, str) and value.strip() for value in values
        )

    def _identification_has_prompt(
        self, identification: Any, section_name: str, language: str
    ) -> bool:
        if not isinstance(identification, dict):
            return False
        section = identification.get(section_name, {})
        if not isinstance(section, dict):
            return False
        payload = section.get(language, {})
        if not isinstance(payload, dict):
            return False
        prompt = payload.get("prompt")
        return isinstance(prompt, str) and bool(prompt.strip())

    def _prune_profile_languages(
        self, profile_doc: dict[str, Any], allowed_languages: set[str]
    ) -> None:
        identification = profile_doc.get("identification", {})
        if isinstance(identification, dict):
            for field_name in ("labels", "descriptions", "aliases"):
                section = identification.get(field_name)
                if isinstance(section, dict):
                    for language in list(section.keys()):
                        if language not in allowed_languages:
                            section.pop(language, None)

        metadata = profile_doc.get("metadata", {})
        if isinstance(metadata, dict):
            for field_name in ("labels", "descriptions", "aliases"):
                section = metadata.get(field_name)
                if isinstance(section, dict):
                    for language in list(section.keys()):
                        if language not in allowed_languages:
                            section.pop(language, None)

        statements = profile_doc.get("statements", [])
        for statement in self._iter_statement_nodes(statements):
            messages = statement.get("messages")
            if isinstance(messages, dict):
                for language in list(messages.keys()):
                    if language not in allowed_languages:
                        messages.pop(language, None)

    def _recompute_profile_languages(self, profile_doc: dict[str, Any]) -> None:
        metadata = profile_doc.get("metadata", {})
        if not isinstance(metadata, dict):
            return
        metadata["languages"] = self._collect_languages(
            {
                "identification": profile_doc.get("identification", {}),
                "statements": profile_doc.get("statements", []),
                "metadata": {
                    "labels": metadata.get("labels", {}),
                    "descriptions": metadata.get("descriptions", {}),
                    "aliases": metadata.get("aliases", {}),
                },
            }
        )

    def _build_profile_metadata(
        self,
        wikibase_item: dict[str, Any],
        *,
        identification: dict[str, Any],
        statements: list[dict[str, Any]],
        entity_uri: str,
    ) -> dict[str, Any]:
        profile_graph = self._build_profile_graph(wikibase_item)
        metadata = {
            "labels": self._localized_text_map(wikibase_item, "labels"),
            "descriptions": self._localized_text_map(wikibase_item, "descriptions"),
            "aliases": self._alias_text_map(wikibase_item),
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "languages": [],
            "statement_count": len(statements),
            "profile_graph": profile_graph,
            "value_list_graph": self._build_value_list_graph(statements),
            "linkage_index": self._build_linkage_index(
                statements,
                source_profile_uri=entity_uri,
                profile_graph=profile_graph,
            ),
            "exported_from": entity_uri,
        }

        metadata["languages"] = self._collect_languages(
            {
                "identification": identification,
                "statements": statements,
                "metadata": {
                    "labels": metadata["labels"],
                    "descriptions": metadata["descriptions"],
                    "aliases": metadata["aliases"],
                },
            }
        )
        return metadata

    def _build_linkage_index(
        self,
        statements: list[dict[str, Any]],
        *,
        source_profile_uri: str,
        profile_graph: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build deterministic linkage index for statement/property/profile routing."""
        outbound_by_statement: dict[str, dict[str, list[str]]] = {}
        targets_by_statement: dict[str, set[str]] = {}

        for edge in profile_graph:
            if not isinstance(edge, dict):
                continue
            via_statement = edge.get("via_statement")
            target_profile = edge.get("entity") or edge.get("id")
            if not isinstance(via_statement, str) or not via_statement:
                continue
            if not isinstance(target_profile, str) or not target_profile:
                continue
            targets_by_statement.setdefault(via_statement, set()).add(target_profile)

        for statement in self._iter_statement_nodes(statements):
            if not isinstance(statement, dict):
                continue

            statement_uri = statement.get("entity")
            if not isinstance(statement_uri, str) or not statement_uri:
                continue

            property_ids = self._statement_wikidata_property_ids(statement)
            target_profiles = self._statement_target_profile_uris(statement)
            if statement_uri in targets_by_statement:
                target_profiles = sorted(
                    set(target_profiles).union(targets_by_statement[statement_uri])
                )

            if not property_ids and not target_profiles:
                continue

            outbound_by_statement[statement_uri] = {
                "wikidata_properties": property_ids,
                "target_profiles": target_profiles,
            }

        inbound_by_wikidata_property: dict[str, list[dict[str, str]]] = {}
        for statement_uri in sorted(outbound_by_statement.keys()):
            outbound = outbound_by_statement[statement_uri]
            property_ids = outbound.get("wikidata_properties", [])
            target_profiles = outbound.get("target_profiles", [])

            for property_id in property_ids:
                records = inbound_by_wikidata_property.setdefault(property_id, [])
                if target_profiles:
                    for target_profile in target_profiles:
                        records.append(
                            {
                                "source_profile": source_profile_uri,
                                "source_statement": statement_uri,
                                "target_profile": target_profile,
                            }
                        )
                else:
                    records.append(
                        {
                            "source_profile": source_profile_uri,
                            "source_statement": statement_uri,
                        }
                    )

        for records in inbound_by_wikidata_property.values():
            records.sort(
                key=lambda record: (
                    str(record.get("source_profile", "")),
                    str(record.get("source_statement", "")),
                    str(record.get("target_profile", "")),
                )
            )

        return {
            "outbound_by_statement": {
                statement_uri: outbound_by_statement[statement_uri]
                for statement_uri in sorted(outbound_by_statement.keys())
            },
            "inbound_by_wikidata_property": {
                property_id: inbound_by_wikidata_property[property_id]
                for property_id in sorted(inbound_by_wikidata_property.keys())
            },
        }

    def _statement_wikidata_property_ids(self, statement: dict[str, Any]) -> list[str]:
        io_map = statement.get("io_map")
        if not isinstance(io_map, list):
            return []

        property_ids: list[str] = []
        for route in io_map:
            if not isinstance(route, dict):
                continue
            target = route.get("to")
            if not isinstance(target, str) or not target:
                continue
            property_id = self._extract_wikidata_property_id(target)
            if property_id:
                property_ids.append(property_id)

        return self._dedupe_preserve_order(property_ids)

    def _statement_target_profile_uris(self, statement: dict[str, Any]) -> list[str]:
        value_payload = statement.get("value")
        if not isinstance(value_payload, dict):
            return []

        profile_payload = value_payload.get("profile")
        if not isinstance(profile_payload, dict):
            return []

        target = profile_payload.get("entity")
        if isinstance(target, str) and target:
            return [target]

        return []

    def _extract_wikidata_property_id(self, target: str) -> Optional[str]:
        if target.startswith("P") and target[1:].isdigit():
            return target

        candidate = target.rstrip("/").split("/")[-1]
        if candidate.startswith("P") and candidate[1:].isdigit():
            return candidate

        return None

    def _build_profile_graph(
        self, wikibase_item: dict[str, Any]
    ) -> list[dict[str, Optional[str]]]:
        graph: list[dict[str, Optional[str]]] = []
        seen: set[tuple[str, str]] = set()
        for statement_id, linked_value_ids in self._iter_statement_value_linkages(
            wikibase_item
        ):
            for target_id in linked_value_ids:
                type_ids = self._entity_type_ids(self._cache_index.get(target_id))
                if self.GKC_ENTITY_PROFILE_CLASS not in type_ids:
                    continue
                key = (statement_id, target_id)
                if key in seen:
                    continue
                seen.add(key)
                target_name_identifier = self._entity_name_identifier(
                    self._cache_index.get(target_id)
                )
                entry: dict[str, Optional[str]] = {
                    "id": f"{self.entity_prefix}{target_id}",
                    "entity": f"{self.entity_prefix}{target_id}",
                    "label": self._entity_label(target_id),
                    "via_statement": f"{self.entity_prefix}{statement_id}",
                    "linkage_type": self.HAS_VALUE,
                }
                if target_name_identifier:
                    entry["name_identifier"] = target_name_identifier
                graph.append(entry)
        return graph

    def _build_value_list_graph(
        self, statements: list[dict[str, Any]]
    ) -> list[dict[str, Optional[str]]]:
        graph: list[dict[str, Optional[str]]] = []
        seen: set[tuple[str, str]] = set()

        for statement in self._iter_statement_nodes(statements):
            if not isinstance(statement, dict):
                continue

            statement_entity = statement.get("entity")
            if not isinstance(statement_entity, str) or not statement_entity:
                continue

            value_payload = statement.get("value")
            if not isinstance(value_payload, dict):
                continue

            cache_path = value_payload.get("value_list_reference")
            if not isinstance(cache_path, str) or not cache_path:
                continue

            target_id = self._qid_from_cache_path(cache_path)
            if not target_id:
                continue

            type_ids = self._entity_type_ids(self._cache_index.get(target_id))
            if type_ids and self.GKC_VALUE_LIST_CLASS not in type_ids:
                continue

            key = (statement_entity, cache_path)
            if key in seen:
                continue
            seen.add(key)

            target_name_identifier = self._entity_name_identifier(
                self._cache_index.get(target_id)
            )
            entry: dict[str, Optional[str]] = {
                "id": f"{self.entity_prefix}{target_id}",
                "entity": f"{self.entity_prefix}{target_id}",
                "label": self._entity_label(target_id),
                "via_statement": statement_entity,
                "cache_path": cache_path,
            }
            if target_name_identifier:
                entry["name_identifier"] = target_name_identifier

            graph.append(entry)
        return graph

    def _iter_statement_nodes(
        self, statements: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []

        def _walk(statement_list: list[dict[str, Any]]) -> None:
            for statement in statement_list:
                if not isinstance(statement, dict):
                    continue
                nodes.append(statement)
                for key in ("qualifiers", "references"):
                    nested = statement.get(key)
                    if isinstance(nested, list):
                        _walk(nested)

        _walk(statements)
        return nodes

    def _qid_from_cache_path(self, cache_path: str) -> Optional[str]:
        candidate = Path(cache_path).stem.upper()
        if candidate.startswith("Q") and candidate[1:].isdigit():
            return candidate
        return None

    def _iter_statement_value_linkages(
        self, wikibase_item: dict[str, Any]
    ) -> list[tuple[str, list[str]]]:
        linkages: list[tuple[str, list[str]]] = []
        claims = wikibase_item.get("entity", {}).get("claims", {})
        current_profile_id = wikibase_item.get("entity_id")
        for claim in claims.get(self.PROFILE_STATEMENT, []):
            statement_id = self._claim_entity_id(claim)
            if not statement_id:
                continue
            statement_doc = self._cache_index.get(statement_id)
            statement_claims = (
                statement_doc.get("entity", {}).get("claims", {})
                if statement_doc
                else {}
            )
            intrinsic = self._claim_entity_values(
                self._applicable_claims(
                    statement_claims.get(self.HAS_VALUE, []),
                    current_profile_id=current_profile_id,
                    parent_statement_id=None,
                )
            )
            overlay = self._qualifier_entity_ids(
                claim.get("qualifiers", {}), self.HAS_VALUE
            )
            effective = overlay if overlay else intrinsic
            linkages.append((statement_id, self._dedupe_preserve_order(effective)))
        return linkages

    def _build_profile_statements(
        self, wikibase_item: dict[str, Any]
    ) -> list[dict[str, Any]]:
        statements: list[dict[str, Any]] = []
        claims = wikibase_item.get("entity", {}).get("claims", {})
        root_id = wikibase_item.get("entity_id")
        profile_spec_index = self._build_profile_statement_spec_index(
            wikibase_item, current_profile_id=root_id
        )
        for claim in claims.get(self.PROFILE_STATEMENT, []):
            statement_id = self._claim_entity_id(claim)
            if not statement_id:
                continue
            built = self._build_statement_from_cache_id(
                statement_id,
                role="statement",
                overlay_qualifiers=claim.get("qualifiers", {}),
                visited={root_id} if root_id else set(),
                current_profile_id=root_id,
                profile_spec_index=profile_spec_index,
            )
            if built:
                statements.append(built)
        return statements

    def _build_profile_statement_spec_index(
        self,
        profile_item: dict[str, Any],
        *,
        current_profile_id: Optional[str],
    ) -> dict[str, dict[str, list[dict[str, Any]]]]:
        """Index profile-level P158/P211 claims by targeted statement (P163)."""
        index: dict[str, dict[str, list[dict[str, Any]]]] = {}
        claims = profile_item.get("entity", {}).get("claims", {})

        for prop_id in (self.HAS_QUALIFIER, self.HAS_REFERENCE):
            for claim in claims.get(prop_id, []):
                target_statement_ids = self._qualifier_entity_ids(
                    claim.get("qualifiers", {}), self.APPLIES_TO_STATEMENT
                )
                if not target_statement_ids:
                    continue

                for target_statement_id in target_statement_ids:
                    if not self._claim_applies_in_context(
                        claim,
                        current_profile_id=current_profile_id,
                        parent_statement_id=target_statement_id,
                    ):
                        continue

                    index.setdefault(target_statement_id, {}).setdefault(
                        prop_id, []
                    ).append(claim)

        return index

    def _build_statement_from_cache_id(
        self,
        entity_id: str,
        *,
        role: str,
        overlay_qualifiers: Optional[dict[str, list[dict[str, Any]]]] = None,
        visited: Optional[set[str]] = None,
        current_profile_id: Optional[str] = None,
        parent_statement_id: Optional[str] = None,
        profile_spec_index: Optional[dict[str, dict[str, list[dict[str, Any]]]]] = None,
    ) -> Optional[dict[str, Any]]:
        if visited is None:
            visited = set()
        if entity_id in visited:
            return None
        if profile_spec_index is None:
            profile_spec_index = {}

        statement_item = self._cache_index.get(entity_id)
        if not statement_item:
            return None

        next_visited = set(visited)
        next_visited.add(entity_id)

        statement_json = self._build_statement_from_item(
            statement_item,
            current_profile_id=current_profile_id,
            parent_statement_id=parent_statement_id,
        )

        qualifiers = overlay_qualifiers or {}
        overlay_value_ids = self._qualifier_entity_ids(qualifiers, self.HAS_VALUE)
        if overlay_value_ids:
            combined_value_ids = self._dedupe_preserve_order(overlay_value_ids)
        else:
            combined_value_ids = statement_json["value"]["linked_entity_ids"]
        statement_json["value"] = self._build_value_payload(
            statement_json["value"]["type"], combined_value_ids
        )

        source_statement_id = self._derived_value_source_statement_id(
            statement_item=statement_item,
            role=role,
            parent_statement_id=parent_statement_id,
            current_profile_id=current_profile_id,
        )
        if source_statement_id:
            statement_json["value"]["value_source"] = "statement_value"
            statement_json["value"][
                "value_source_statement"
            ] = f"{self.entity_prefix}{source_statement_id}"

        if qualifiers:
            statement_json["messages"] = self._merge_messages(
                statement_json.get("messages", {}),
                self._build_messages_from_qualifiers(qualifiers),
            )
            if self.MAX_COUNT in qualifiers:
                statement_json["max_count"] = self._qualifier_first_quantity_int(
                    qualifiers, self.MAX_COUNT
                )

        if role == "statement":
            statement_claims = statement_item.get("entity", {}).get("claims", {})
            profile_overrides = profile_spec_index.get(entity_id, {})

            qualifier_specs = self._resolve_statement_spec_entries(
                statement_claims=statement_claims.get(self.HAS_QUALIFIER, []),
                claim_level_overlay_ids=self._qualifier_entity_ids(
                    qualifiers, self.HAS_QUALIFIER
                ),
                profile_override_claims=profile_overrides.get(self.HAS_QUALIFIER, []),
                current_profile_id=current_profile_id,
                parent_statement_id=parent_statement_id,
            )
            reference_specs = self._resolve_statement_spec_entries(
                statement_claims=statement_claims.get(self.HAS_REFERENCE, []),
                claim_level_overlay_ids=self._qualifier_entity_ids(
                    qualifiers, self.HAS_REFERENCE
                ),
                profile_override_claims=profile_overrides.get(self.HAS_REFERENCE, []),
                current_profile_id=current_profile_id,
                parent_statement_id=parent_statement_id,
            )

            statement_json["qualifiers"] = self._resolve_linked_statements(
                qualifier_specs,
                role="qualifier",
                visited=next_visited,
                current_profile_id=current_profile_id,
                parent_statement_id=entity_id,
                profile_spec_index=profile_spec_index,
            )
            statement_json["references"] = self._resolve_linked_statements(
                reference_specs,
                role="reference",
                visited=next_visited,
                current_profile_id=current_profile_id,
                parent_statement_id=entity_id,
                profile_spec_index=profile_spec_index,
            )

        if role in {"qualifier", "reference"}:
            statement_json.pop("qualifiers", None)
            statement_json.pop("references", None)

        return statement_json

    def _resolve_linked_statements(
        self,
        statement_specs: list[dict[str, Any]],
        *,
        role: str,
        visited: set[str],
        current_profile_id: Optional[str],
        parent_statement_id: str,
        profile_spec_index: dict[str, dict[str, list[dict[str, Any]]]],
    ) -> list[dict[str, Any]]:
        resolved: list[dict[str, Any]] = []
        for spec in statement_specs:
            entity_id = str(spec.get("entity_id", "")).strip()
            if not entity_id:
                continue
            nested = self._build_statement_from_cache_id(
                entity_id,
                role=role,
                overlay_qualifiers=spec.get("overlay_qualifiers", {}),
                visited=visited,
                current_profile_id=current_profile_id,
                parent_statement_id=parent_statement_id,
                profile_spec_index=profile_spec_index,
            )
            if nested:
                resolved.append(nested)
        return resolved

    def _resolve_statement_spec_entries(
        self,
        *,
        statement_claims: list[dict[str, Any]],
        claim_level_overlay_ids: list[str],
        profile_override_claims: list[dict[str, Any]],
        current_profile_id: Optional[str],
        parent_statement_id: Optional[str],
    ) -> list[dict[str, Any]]:
        """Resolve nested statement specs with profile-level supersede semantics.

        When profile-level override claims (P158/P211 with P163) are present for a
        statement, they fully supersede the underlying statement entity's defaults.
        Statement-level defaults are only used when no profile-level overrides exist.
        """

        candidates: list[dict[str, Any]] = []
        order = 0

        if not profile_override_claims:
            for claim in statement_claims:
                if not self._claim_applies_in_context(
                    claim,
                    current_profile_id=current_profile_id,
                    parent_statement_id=parent_statement_id,
                ):
                    continue
                entity_id = self._claim_entity_id(claim)
                if not entity_id:
                    continue
                candidates.append(
                    {
                        "entity_id": entity_id,
                        "overlay_qualifiers": claim.get("qualifiers", {}),
                        "source_rank": 1,
                        "scope_rank": self._claim_scope_rank(claim),
                        "order": order,
                    }
                )
                order += 1

        for entity_id in claim_level_overlay_ids:
            candidates.append(
                {
                    "entity_id": entity_id,
                    "overlay_qualifiers": {},
                    "source_rank": 2,
                    "scope_rank": 0,
                    "order": order,
                }
            )
            order += 1

        for claim in profile_override_claims:
            entity_id = self._claim_entity_id(claim)
            if not entity_id:
                continue
            candidates.append(
                {
                    "entity_id": entity_id,
                    "overlay_qualifiers": claim.get("qualifiers", {}),
                    "source_rank": 3,
                    "scope_rank": self._claim_scope_rank(claim),
                    "order": order,
                }
            )
            order += 1

        winners: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            entity_id = candidate["entity_id"]
            existing = winners.get(entity_id)
            if not existing:
                winners[entity_id] = candidate
                continue

            better_source = candidate["source_rank"] > existing["source_rank"]
            better_scope = candidate["scope_rank"] > existing["scope_rank"]
            if better_source or (
                candidate["source_rank"] == existing["source_rank"] and better_scope
            ):
                winners[entity_id] = candidate

        selected = sorted(winners.values(), key=lambda entry: entry["order"])
        return [
            {
                "entity_id": entry["entity_id"],
                "overlay_qualifiers": entry["overlay_qualifiers"],
            }
            for entry in selected
        ]

    def _build_statement_from_item(
        self,
        statement_item: dict[str, Any],
        *,
        current_profile_id: Optional[str],
        parent_statement_id: Optional[str],
    ) -> dict[str, Any]:
        entity_id = statement_item.get("entity_id")
        label = self._get_localized_text(
            statement_item,
            section="labels",
            language_order=self.label_language_order,
            required=False,
        )

        claims = statement_item.get("entity", {}).get("claims", {})
        io_targets = self._claim_string_values(claims.get(self.IO_MAP, []))

        value_type: Optional[str] = None
        type_refs = self._claim_entity_values(claims.get(self.VALUE_TYPE, []))
        if type_refs:
            value_type = self._entity_label(type_refs[0]) or type_refs[0]

        intrinsic_value_ids = self._claim_entity_values(
            self._applicable_claims(
                claims.get(self.HAS_VALUE, []),
                current_profile_id=current_profile_id,
                parent_statement_id=parent_statement_id,
            )
        )

        max_count = self._claim_first_quantity_int(
            self._applicable_claims(
                claims.get(self.MAX_COUNT, []),
                current_profile_id=current_profile_id,
                parent_statement_id=parent_statement_id,
            )
        )

        return {
            "id": f"{self.entity_prefix}{entity_id}",
            "name_identifier": self._entity_name_identifier(statement_item),
            "entity": f"{self.entity_prefix}{entity_id}",
            "label": label,
            "entity_classes": self._entity_type_ids(statement_item),
            "io_map": [{"to": target} for target in io_targets],
            "value": {
                "type": value_type,
                "linked_entity_ids": intrinsic_value_ids,
            },
            "messages": self._build_messages_from_claims(claims),
            "max_count": max_count,
            "qualifiers": [],
            "references": [],
        }

    def _claim_scope_rank(self, claim: dict[str, Any]) -> int:
        qualifiers = claim.get("qualifiers", {})
        if not isinstance(qualifiers, dict):
            return 0

        has_profile_scope = bool(
            self._qualifier_entity_ids(qualifiers, self.APPLIES_TO_PROFILE)
        )
        has_statement_scope = bool(
            self._qualifier_entity_ids(qualifiers, self.APPLIES_TO_STATEMENT)
        )

        if has_profile_scope and has_statement_scope:
            return 3
        if has_profile_scope:
            return 2
        if has_statement_scope:
            return 1
        return 0

    def _applicable_claims(
        self,
        claims: list[dict[str, Any]],
        *,
        current_profile_id: Optional[str],
        parent_statement_id: Optional[str],
    ) -> list[dict[str, Any]]:
        applicable: list[dict[str, Any]] = []
        for claim in claims:
            if self._claim_applies_in_context(
                claim,
                current_profile_id=current_profile_id,
                parent_statement_id=parent_statement_id,
            ):
                applicable.append(claim)
        return applicable

    def _claim_first_quantity_int(
        self,
        claims: list[dict[str, Any]],
    ) -> Optional[int]:
        for claim in claims:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if not isinstance(value, dict):
                continue
            amount = value.get("amount")
            if isinstance(amount, str):
                try:
                    return int(float(amount))
                except ValueError:
                    return None
        return None

    def _build_value_payload(
        self, value_type: Optional[str], target_ids: list[str]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": value_type}
        value_list: list[dict[str, Optional[str]]] = []

        for target_id in target_ids:
            target_doc = self._cache_index.get(target_id)
            type_ids = self._entity_type_ids(target_doc)
            target_label = self._entity_label(target_id)
            target_entity = f"{self.entity_prefix}{target_id}"

            if self.GKC_ENTITY_PROFILE_CLASS in type_ids and "profile" not in payload:
                payload["profile"] = {"entity": target_entity, "label": target_label}

            if (
                self.GKC_VALUE_LIST_CLASS in type_ids
                and "value_list_reference" not in payload
            ):
                payload["value_list_reference"] = f"cache/queries/{target_id}.json"

            if self.WIKIDATA_ENTITY_CLASS in type_ids:
                wikidata_urls = self._dedupe_preserve_order(
                    self._entity_string_claim_values(target_doc, self.SAME_AS)
                    + self._entity_string_claim_values(
                        target_doc, self.WIKIDATA_ENTITY_URL
                    )
                )
                for url in wikidata_urls:
                    qid = self._extract_wikidata_qid_from_url(url)
                    if qid:
                        value_list.append({"item": qid, "itemLabel": target_label})

        if value_list:
            payload["value_list"] = value_list

        return payload

    def _build_messages_from_claims(
        self, claims: dict[str, list[dict[str, Any]]]
    ) -> dict[str, dict[str, str]]:
        messages: dict[str, dict[str, str]] = {}
        for prop_id, field_name in self.MESSAGE_FIELD_BY_PROP.items():
            by_lang = self._monolingual_claims_by_language(claims.get(prop_id, []))
            for language, text in by_lang.items():
                messages.setdefault(language, {})[field_name] = text
        return messages

    def _build_messages_from_qualifiers(
        self, qualifiers: dict[str, list[dict[str, Any]]]
    ) -> dict[str, dict[str, str]]:
        messages: dict[str, dict[str, str]] = {}
        for prop_id, field_name in self.MESSAGE_FIELD_BY_PROP.items():
            by_lang = self._monolingual_qualifiers_by_language(
                qualifiers.get(prop_id, [])
            )
            for language, text in by_lang.items():
                messages.setdefault(language, {})[field_name] = text
        return messages

    def _merge_messages(
        self,
        base_messages: dict[str, dict[str, str]],
        overlay_messages: dict[str, dict[str, str]],
    ) -> dict[str, dict[str, str]]:
        merged = {language: fields.copy() for language, fields in base_messages.items()}
        for language, fields in overlay_messages.items():
            merged.setdefault(language, {}).update(fields)
        return merged

    def _build_language_section(
        self,
        wikibase_item: dict[str, Any],
        prompt_claim_id: str,
        guidance_claim_id: str,
    ) -> dict[str, dict[str, str]]:
        prompt_by_language = self._extract_monolingual_by_language(
            wikibase_item, prompt_claim_id
        )
        guidance_by_language = self._extract_monolingual_by_language(
            wikibase_item, guidance_claim_id
        )

        languages = sorted(set(prompt_by_language) | set(guidance_by_language))
        section: dict[str, dict[str, str]] = {}

        for language in languages:
            entry: dict[str, str] = {}
            prompts = prompt_by_language.get(language, [])
            guidances = guidance_by_language.get(language, [])
            if prompts:
                entry["prompt"] = prompts[0]
            if guidances:
                entry["guidance"] = guidances[0]
            if entry:
                section[language] = entry

        return section

    def _extract_monolingual_by_language(
        self,
        wikibase_item: dict[str, Any],
        claim_id: str,
    ) -> dict[str, list[str]]:
        claims = wikibase_item.get("entity", {}).get("claims", {}).get(claim_id, [])
        by_language: dict[str, list[str]] = {}
        for claim in claims:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if not isinstance(value, dict):
                continue
            language = value.get("language")
            text = value.get("text")
            if language and text:
                by_language.setdefault(language, []).append(text)
        return by_language

    def _localized_text_map(
        self, wikibase_item: dict[str, Any], section: str
    ) -> dict[str, str]:
        mapped: dict[str, str] = {}
        values = wikibase_item.get("entity", {}).get(section, {})
        for language, payload in values.items():
            if isinstance(payload, dict) and payload.get("value"):
                mapped[language] = payload["value"]
        return mapped

    def _alias_text_map(self, wikibase_item: dict[str, Any]) -> dict[str, list[str]]:
        alias_map: dict[str, list[str]] = {}
        aliases = wikibase_item.get("entity", {}).get("aliases", {})
        for language, values in aliases.items():
            texts = [
                value.get("value")
                for value in values
                if isinstance(value, dict) and value.get("value")
            ]
            if texts:
                alias_map[language] = texts
        return alias_map

    def _collect_languages(self, value: Any) -> list[str]:
        found: set[str] = set()

        identification = (
            value.get("identification", {}) if isinstance(value, dict) else {}
        )
        statements = value.get("statements", []) if isinstance(value, dict) else []
        metadata = value.get("metadata", {}) if isinstance(value, dict) else {}

        self._collect_language_keys_from_identification(identification, found)
        self._collect_language_keys_from_statements(statements, found)
        self._collect_language_keys_from_metadata(metadata, found)

        return sorted(found)

    def _collect_language_keys_from_identification(
        self, identification: dict[str, Any], out: set[str]
    ) -> None:
        for field_name in ("labels", "descriptions", "aliases"):
            language_map = identification.get(field_name, {})
            if isinstance(language_map, dict):
                out.update(self._valid_language_keys(language_map.keys()))

    def _collect_language_keys_from_statements(
        self, statements: list[dict[str, Any]], out: set[str]
    ) -> None:
        for statement in statements:
            if not isinstance(statement, dict):
                continue

            messages = statement.get("messages", {})
            if isinstance(messages, dict):
                out.update(self._valid_language_keys(messages.keys()))

            for nested_field in ("qualifiers", "references"):
                nested = statement.get(nested_field, [])
                if isinstance(nested, list):
                    self._collect_language_keys_from_statements(nested, out)

    def _collect_language_keys_from_metadata(
        self, metadata: dict[str, Any], out: set[str]
    ) -> None:
        for field_name in ("labels", "descriptions", "aliases"):
            language_map = metadata.get(field_name, {})
            if isinstance(language_map, dict):
                out.update(self._valid_language_keys(language_map.keys()))

    def _valid_language_keys(self, keys: Any) -> set[str]:
        valid: set[str] = set()
        for key in keys:
            if isinstance(key, str) and self.LANGUAGE_KEY_PATTERN.fullmatch(key):
                valid.add(key)
        return valid

    def _is_profile_item(self, wikibase_item: dict[str, Any]) -> bool:
        claims_p1 = wikibase_item.get("entity", {}).get("claims", {}).get("P1", [])
        for claim in claims_p1:
            if self._claim_entity_id(claim) == self.PROFILE_CLASS_ID:
                return True
        return False

    def _load_cache_index(self) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for json_file in sorted(self.cache_entities_dir.glob("*.json")):
            with json_file.open("r", encoding="utf-8") as handle:
                doc = json.load(handle)
            entity_id = doc.get("entity_id")
            if entity_id:
                index[entity_id] = doc
        return index

    def _get_localized_text(
        self,
        wikibase_item: dict[str, Any],
        *,
        section: str,
        language_order: tuple[str, ...],
        required: bool,
    ) -> Optional[str]:
        values = wikibase_item.get("entity", {}).get(section, {})
        for language in language_order:
            text = values.get(language, {}).get("value")
            if text:
                return text
        for payload in values.values():
            if isinstance(payload, dict) and payload.get("value"):
                return payload["value"]
        if required:
            raise ValueError(
                f"{section} missing for {wikibase_item.get('entity_id', '<unknown>')}"
            )
        return None

    def _monolingual_claims_by_language(
        self, claims: list[dict[str, Any]]
    ) -> dict[str, str]:
        by_language: dict[str, str] = {}
        for claim in claims:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if not isinstance(value, dict):
                continue
            language = value.get("language")
            text = value.get("text")
            if language and text and language not in by_language:
                by_language[language] = text
        return by_language

    def _monolingual_qualifiers_by_language(
        self, qualifiers: list[dict[str, Any]]
    ) -> dict[str, str]:
        by_language: dict[str, str] = {}
        for qualifier in qualifiers:
            value = qualifier.get("datavalue", {}).get("value", {})
            if not isinstance(value, dict):
                continue
            language = value.get("language")
            text = value.get("text")
            if language and text and language not in by_language:
                by_language[language] = text
        return by_language

    def _claim_entity_id(self, claim: dict[str, Any]) -> Optional[str]:
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        return value.get("id") if isinstance(value, dict) else None

    def _claim_entity_values(self, claims: list[dict[str, Any]]) -> list[str]:
        values: list[str] = []
        for claim in claims:
            entity_id = self._claim_entity_id(claim)
            if entity_id:
                values.append(entity_id)
        return values

    def _derived_value_source_statement_id(
        self,
        *,
        statement_item: dict[str, Any],
        role: str,
        parent_statement_id: Optional[str],
        current_profile_id: Optional[str],
    ) -> Optional[str]:
        if role not in {"qualifier", "reference"}:
            return None
        if not parent_statement_id:
            return None

        claims = statement_item.get("entity", {}).get("claims", {})
        derives_claims = claims.get(self.DERIVES_DEFAULT_VALUE_FROM, [])
        for claim in derives_claims:
            source_statement_id = self._claim_entity_id(claim)
            if not source_statement_id or source_statement_id != parent_statement_id:
                continue
            if self._claim_applies_in_context(
                claim,
                current_profile_id=current_profile_id,
                parent_statement_id=parent_statement_id,
            ):
                return source_statement_id
        return None

    def _claim_applies_to_profile(
        self,
        claim: dict[str, Any],
        current_profile_id: Optional[str],
    ) -> bool:
        return self._claim_applies_in_context(
            claim,
            current_profile_id=current_profile_id,
            parent_statement_id=None,
        )

    def _claim_applies_in_context(
        self,
        claim: dict[str, Any],
        *,
        current_profile_id: Optional[str],
        parent_statement_id: Optional[str],
    ) -> bool:
        qualifiers = claim.get("qualifiers", {})
        if not isinstance(qualifiers, dict):
            return True

        applies_to_profiles = self._qualifier_entity_ids(
            qualifiers, self.APPLIES_TO_PROFILE
        )
        applies_to_statements = self._qualifier_entity_ids(
            qualifiers, self.APPLIES_TO_STATEMENT
        )

        profile_matches = not applies_to_profiles or (
            current_profile_id is not None and current_profile_id in applies_to_profiles
        )
        statement_matches = not applies_to_statements or (
            parent_statement_id is not None
            and parent_statement_id in applies_to_statements
        )
        return profile_matches and statement_matches

    def _claim_string_values(self, claims: list[dict[str, Any]]) -> list[str]:
        values: list[str] = []
        for claim in claims:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
            if isinstance(value, str):
                values.append(value)
        return values

    def _qualifier_entity_ids(
        self, qualifiers: dict[str, list[dict[str, Any]]], prop_id: str
    ) -> list[str]:
        values: list[str] = []
        for qualifier in qualifiers.get(prop_id, []):
            value = qualifier.get("datavalue", {}).get("value", {})
            if isinstance(value, dict) and value.get("id"):
                values.append(value["id"])
        return values

    def _qualifier_first_quantity_int(
        self,
        qualifiers: dict[str, list[dict[str, Any]]],
        prop_id: str,
    ) -> Optional[int]:
        for qualifier in qualifiers.get(prop_id, []):
            value = qualifier.get("datavalue", {}).get("value", {})
            if not isinstance(value, dict):
                continue
            amount = value.get("amount")
            if isinstance(amount, str):
                try:
                    return int(float(amount))
                except ValueError:
                    return None
        return None

    def _entity_type_ids(self, entity_doc: Optional[dict[str, Any]]) -> list[str]:
        if not entity_doc:
            return []
        claims = entity_doc.get("entity", {}).get("claims", {})
        return self._claim_entity_values(claims.get("P1", []))

    def _entity_string_claim_values(
        self, entity_doc: Optional[dict[str, Any]], prop_id: str
    ) -> list[str]:
        if not entity_doc:
            return []
        claims = entity_doc.get("entity", {}).get("claims", {})
        return self._claim_string_values(claims.get(prop_id, []))

    def _extract_wikidata_qid_from_url(self, url: str) -> Optional[str]:
        if "/entity/Q" not in url:
            return None
        candidate = url.rstrip("/").split("/")[-1]
        if candidate.startswith("Q") and candidate[1:].isdigit():
            return candidate
        return None

    def _dedupe_preserve_order(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            deduped.append(value)
        return deduped

    def _entity_label(self, entity_id: str) -> Optional[str]:
        doc = self._cache_index.get(entity_id)
        if not doc:
            return None
        return self._get_localized_text(
            doc,
            section="labels",
            language_order=self.label_language_order,
            required=False,
        )

    def _entity_name_identifier(
        self, entity_doc: Optional[dict[str, Any]]
    ) -> Optional[str]:
        if not entity_doc:
            return None
        claims = entity_doc.get("entity", {}).get("claims", {})
        values = self._claim_string_values(claims.get(self.NAME_IDENTIFIER, []))
        if values:
            return values[0]
        return None


class EntityProfileLanguageCoverageError(ValueError):
    """Raised when a profile fails required language completeness coverage."""

    def __init__(self, profile_id: str, missing_paths: list[str]) -> None:
        self.profile_id = profile_id
        self.missing_paths = sorted(set(missing_paths))
        super().__init__(
            f"Profile '{profile_id}' failed required mul language coverage: "
            + ", ".join(self.missing_paths)
        )


@dataclass(frozen=True)
class EntityProfileJsonExportResult:
    """Summary of JSON entity profile export writes."""

    output_dir: str
    written_ids: list[str]
    skipped_ids: list[str] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    language_filtering: list[dict[str, Any]] = field(default_factory=list)


def build_entity_profile_json_documents(
    cache_entities_dir: Union[str, Path],
    *,
    entity_prefix: str = "https://datadistillery.wikibase.cloud/entity/",
) -> list[dict[str, Any]]:
    """Build JSON entity profile documents from cache entities.

    Args:
        cache_entities_dir: Directory containing SpiritSafe cache entity JSON files.
        entity_prefix: URI prefix for entity references.

    Returns:
        List of JSON profile documents.
    """
    builder = EntityProfileJsonBuilder(
        cache_entities_dir=cache_entities_dir,
        entity_prefix=entity_prefix,
    )
    return builder.build_all()


def export_entity_profile_json_documents(
    cache_entities_dir: Union[str, Path],
    output_dir: Union[str, Path],
    *,
    entity_prefix: str = "https://datadistillery.wikibase.cloud/entity/",
    profile_ids: Optional[list[str]] = None,
) -> EntityProfileJsonExportResult:
    """Build and export JSON entity profile documents as one file per profile.

    Files are written as `<output_dir>/<QID>.json`.

    Args:
        cache_entities_dir: Directory containing SpiritSafe cache entity JSON files.
        output_dir: Output directory for generated JSON profile files.
        entity_prefix: URI prefix for entity references.
        profile_ids: Optional list of profile QIDs to export.

    Returns:
        Export result summary.
    """
    builder = EntityProfileJsonBuilder(
        cache_entities_dir=cache_entities_dir,
        entity_prefix=entity_prefix,
    )
    build_result = builder.build_all_with_report()
    documents = build_result["documents"]

    requested_ids = set(profile_ids or [])
    if requested_ids:
        filtered_documents = []
        for document in documents:
            entity_id = str(document.get("entity", "")).rstrip("/").split("/")[-1]
            if entity_id in requested_ids:
                filtered_documents.append(document)
        documents = filtered_documents

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written_ids: list[str] = []
    for document in documents:
        entity_id = str(document.get("entity", "")).rstrip("/").split("/")[-1]
        if not entity_id:
            continue
        destination = out_dir / f"{entity_id}.json"
        destination.write_text(json.dumps(document, indent=2), encoding="utf-8")
        written_ids.append(entity_id)

    return EntityProfileJsonExportResult(
        output_dir=str(out_dir.resolve()),
        written_ids=sorted(written_ids),
        skipped_ids=sorted(
            [
                str(item.get("profile_id"))
                for item in build_result["skipped_profiles"]
                if item.get("profile_id")
            ]
        ),
        failures=build_result["skipped_profiles"],
        language_filtering=build_result["language_filtering"],
    )


# ============================================================================
# Phase 3: Artifact Manifest, JSON Profile Loading, and Curation Packets
# ============================================================================


SPIRITSAFE_ENTITY_URI_PREFIX = "https://datadistillery.wikibase.cloud/entity/"


def _manifest_source_url() -> str:
    return f"https://github.com/{DEFAULT_SPIRIT_SAFE_GITHUB_REPO}"


def _resolve_spiritsafe_meta_wikibase_config(
    spiritsafe_root: Union[str, Path],
) -> tuple[Optional[Path], MetaWikibaseConfigValues]:
    root = Path(spiritsafe_root).expanduser().resolve()

    for subdir in DEFAULT_META_WB_CONFIG_SEARCH_DIRS:
        if subdir and subdir != "config":
            continue
        for filename in DEFAULT_META_WB_CONFIG_FILENAMES:
            candidate = root / subdir / filename if subdir else root / filename
            if candidate.is_file():
                return candidate, load_meta_wikibase_config(candidate)

    return None, default_meta_wikibase_config_values()


def _entity_id_from_reference(reference: Any) -> Optional[str]:
    """Normalize a QID/property ID or entity URI to its trailing identifier."""

    if not isinstance(reference, str):
        return None

    candidate = reference.rstrip("/").split("/")[-1]
    if not candidate:
        return None
    if candidate[0] in {"Q", "P"} and candidate[1:].isdigit():
        return candidate
    return None


def _entity_uri_from_reference(reference: Any) -> Optional[str]:
    """Normalize a QID or entity URI to a full Data Distillery entity URI."""

    if not isinstance(reference, str):
        return None
    if reference.startswith("http://") or reference.startswith("https://"):
        return reference.rstrip("/")

    entity_id = _entity_id_from_reference(reference)
    if not entity_id:
        return None
    return f"{SPIRITSAFE_ENTITY_URI_PREFIX}{entity_id}"


def _load_json_from_resolved_path(resolved: Union[Path, str]) -> dict[str, Any]:
    """Load JSON content from a resolved local path or GitHub raw URL."""

    try:
        return json.loads(_read_text_from_resolved_path(resolved))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at {resolved}: {exc}") from exc


def _profile_label_from_map(values: Any) -> str:
    if not isinstance(values, dict):
        return ""
    for language in ("mul", "en"):
        value = values.get(language)
        if isinstance(value, str) and value:
            return value
    for value in values.values():
        if isinstance(value, str) and value:
            return value
    return ""


def _label_from_cache_entity(document: dict[str, Any]) -> str:
    labels = document.get("entity", {}).get("labels", {})
    for language in ("mul", "en"):
        payload = labels.get(language, {})
        if isinstance(payload, dict) and payload.get("value"):
            return str(payload["value"])
    for payload in labels.values():
        if isinstance(payload, dict) and payload.get("value"):
            return str(payload["value"])
    return ""


def _claim_entity_id_value(claim: dict[str, Any]) -> Optional[str]:
    value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
    return value.get("id") if isinstance(value, dict) else None


def _claim_string_value(claim: dict[str, Any]) -> Optional[str]:
    value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
    return value if isinstance(value, str) and value else None


def _claim_quantity_int_value(claim: dict[str, Any]) -> Optional[int]:
    value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
    if not isinstance(value, dict):
        return None
    amount = value.get("amount")
    if not isinstance(amount, str) or not amount:
        return None
    try:
        return int(float(amount))
    except ValueError:
        return None


def _qualifier_entity_ids(
    qualifiers: Any,
    prop_id: str,
) -> list[str]:
    if not isinstance(qualifiers, dict):
        return []

    values: list[str] = []
    for snak in qualifiers.get(prop_id, []):
        value = snak.get("datavalue", {}).get("value", {})
        entity_id = value.get("id") if isinstance(value, dict) else None
        if isinstance(entity_id, str) and entity_id:
            values.append(entity_id)
    return values


def _claim_monolingual_by_language(claims: list[dict[str, Any]]) -> dict[str, str]:
    by_language: dict[str, str] = {}
    for claim in claims:
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
        if not isinstance(value, dict):
            continue
        language = value.get("language")
        text = value.get("text")
        if (
            isinstance(language, str)
            and language
            and isinstance(text, str)
            and text
            and language not in by_language
        ):
            by_language[language] = text
    return by_language


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def _build_link_entries(
    claims: list[dict[str, Any]],
    *,
    applies_to_profile_prop: str,
    applies_to_statement_prop: str,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for claim in claims:
        target_id = _claim_entity_id_value(claim)
        if not target_id:
            continue

        entry: dict[str, Any] = {"target": target_id}
        scope_profiles = _sorted_unique(
            _qualifier_entity_ids(claim.get("qualifiers", {}), applies_to_profile_prop)
        )
        scope_statements = _sorted_unique(
            _qualifier_entity_ids(
                claim.get("qualifiers", {}),
                applies_to_statement_prop,
            )
        )
        if scope_profiles or scope_statements:
            entry["scope"] = {
                "profiles": scope_profiles,
                "statements": scope_statements,
            }
        entries.append(entry)

    return sorted(entries, key=lambda entry: (entry["target"], json.dumps(entry)))


def _build_entity_index_entry(entity_doc: dict[str, Any]) -> dict[str, Any]:
    entity_id = str(entity_doc.get("entity_id") or "")
    claims = entity_doc.get("entity", {}).get("claims", {})
    classes = _sorted_unique(
        [
            entity_id_value
            for entity_id_value in (
                _claim_entity_id_value(claim) for claim in claims.get("P1", [])
            )
            if entity_id_value
        ]
    )

    value_type = next(
        (
            value
            for value in (
                _claim_entity_id_value(claim) for claim in claims.get("P194", [])
            )
            if value
        ),
        None,
    )
    max_count = next(
        (
            value
            for value in (
                _claim_quantity_int_value(claim) for claim in claims.get("P182", [])
            )
            if value is not None
        ),
        None,
    )
    name_identifier = next(
        (
            value
            for value in (
                _claim_string_value(claim) for claim in claims.get("P214", [])
            )
            if value
        ),
        None,
    )

    messages: dict[str, dict[str, str]] = {}
    for prop_id, field_name in {
        "P171": "prompt",
        "P169": "guidance",
        "P170": "consequences_message",
        "P168": "error_message",
    }.items():
        for language, text in _claim_monolingual_by_language(
            claims.get(prop_id, [])
        ).items():
            messages.setdefault(language, {})[field_name] = text

    return {
        "id": entity_id,
        "entity": f"{SPIRITSAFE_ENTITY_URI_PREFIX}{entity_id}",
        "label": _label_from_cache_entity(entity_doc),
        "name_identifier": name_identifier,
        "classes": classes,
        "value_type": value_type,
        "io_map": _sorted_unique(
            [
                value
                for value in (
                    _claim_string_value(claim) for claim in claims.get("P5", [])
                )
                if value
            ]
        ),
        "max_count": max_count,
        "messages": messages,
        "links": {
            "statements": _build_link_entries(
                claims.get("P157", []),
                applies_to_profile_prop="P205",
                applies_to_statement_prop="P163",
            ),
            "qualifiers": _build_link_entries(
                claims.get("P158", []),
                applies_to_profile_prop="P205",
                applies_to_statement_prop="P163",
            ),
            "references": _build_link_entries(
                claims.get("P211", []),
                applies_to_profile_prop="P205",
                applies_to_statement_prop="P163",
            ),
            "values": _build_link_entries(
                claims.get("P161", []),
                applies_to_profile_prop="P205",
                applies_to_statement_prop="P163",
            ),
            "derives_default_value_from": _build_link_entries(
                claims.get("P213", []),
                applies_to_profile_prop="P205",
                applies_to_statement_prop="P163",
            ),
        },
    }


def build_spiritsafe_entity_index_document(
    spiritsafe_root: Union[str, Path],
) -> dict[str, Any]:
    """Build a normalized entity index from cached SpiritSafe entity JSON docs."""

    root = Path(spiritsafe_root).expanduser().resolve()
    cache_entities_dir = root / "cache" / "entities"

    entities: dict[str, dict[str, Any]] = {}
    by_class: dict[str, list[str]] = {}

    for entity_path in sorted(cache_entities_dir.glob("*.json")):
        entity_doc = json.loads(entity_path.read_text(encoding="utf-8"))
        entry = _build_entity_index_entry(entity_doc)
        entity_id = str(entry.get("id") or entity_path.stem)
        entities[entity_id] = entry

        for class_id in entry.get("classes", []):
            by_class.setdefault(class_id, []).append(entity_id)

    for class_id, members in by_class.items():
        by_class[class_id] = sorted(set(members))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": _manifest_source_url(),
        "entity_count": len(entities),
        "class_count": len(by_class),
        "entities": entities,
        "class_index": by_class,
    }


def export_spiritsafe_entity_index(
    spiritsafe_root: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    """Build and write the SpiritSafe normalized entity index document."""

    root = Path(spiritsafe_root).expanduser().resolve()
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else (root / "cache" / "entity_index.json")
    )

    index_document = build_spiritsafe_entity_index_document(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(index_document, indent=2), encoding="utf-8")
    return index_document


def _build_semantic_anchor_entry(
    entity_doc: dict[str, Any],
    *,
    name_identifier_property_id: str,
    internal_prefix: str,
) -> Optional[dict[str, Any]]:
    entity = entity_doc.get("entity", {})
    entity_id = str(entity_doc.get("entity_id") or entity.get("id") or "")
    claims = entity_doc.get("entity", {}).get("claims", {})
    name_identifier = next(
        (
            value
            for value in (
                _claim_string_value(claim)
                for claim in claims.get(name_identifier_property_id, [])
            )
            if value
        ),
        None,
    )
    if not name_identifier:
        return None

    if not (internal_prefix and name_identifier.startswith(internal_prefix)):
        return None

    entry = {
        "id": entity_id,
        "entity": f"{SPIRITSAFE_ENTITY_URI_PREFIX}{entity_id}",
    }

    if entity.get("type") == "property" and isinstance(entity.get("datatype"), str):
        entry["datatype"] = entity["datatype"]

    return entry


def build_spiritsafe_semantic_anchor_document(
    spiritsafe_root: Union[str, Path],
) -> dict[str, Any]:
    """Build a thin semantic anchor artifact from cached SpiritSafe entities."""

    root = Path(spiritsafe_root).expanduser().resolve()
    cache_entities_dir = root / "cache" / "entities"
    _config_path, config_values = _resolve_spiritsafe_meta_wikibase_config(root)

    name_identifier_property_id = (
        config_values.get("name_identifier_property_id") or "P214"
    )
    internal_prefix = config_values.get("internal_name_identifier_prefix") or "_"

    anchors: dict[str, dict[str, Any]] = {}

    for entity_path in sorted(cache_entities_dir.glob("*.json")):
        entity_doc = json.loads(entity_path.read_text(encoding="utf-8"))
        claims = entity_doc.get("entity", {}).get("claims", {})
        name_identifier = next(
            (
                value
                for value in (
                    _claim_string_value(claim)
                    for claim in claims.get(name_identifier_property_id, [])
                )
                if value
            ),
            None,
        )
        entry = _build_semantic_anchor_entry(
            entity_doc,
            name_identifier_property_id=name_identifier_property_id,
            internal_prefix=internal_prefix,
        )
        if not entry or not name_identifier:
            continue

        anchors[name_identifier] = entry

    property_count = sum(
        1
        for entry in anchors.values()
        if isinstance(entry.get("id"), str) and entry["id"].startswith("P")
    )
    item_count = sum(
        1
        for entry in anchors.values()
        if isinstance(entry.get("id"), str) and entry["id"].startswith("Q")
    )

    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "property_count": property_count,
            "item_count": item_count,
        },
        "entities": anchors,
    }


def export_spiritsafe_semantic_anchors(
    spiritsafe_root: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    """Build and write the SpiritSafe semantic anchor artifact."""

    root = Path(spiritsafe_root).expanduser().resolve()
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else (root / "cache" / "config" / "semantic_anchors.json")
    )

    semantic_anchor_document = build_spiritsafe_semantic_anchor_document(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(semantic_anchor_document, indent=2), encoding="utf-8"
    )
    return semantic_anchor_document


def _statement_id_from_definition(statement: dict[str, Any]) -> Optional[str]:
    entity_id = _entity_id_from_reference(statement.get("id"))
    if entity_id:
        return entity_id

    entity_id = _entity_id_from_reference(statement.get("entity"))
    if entity_id:
        return entity_id

    io_map = statement.get("io_map", [])
    if isinstance(io_map, list):
        for route in io_map:
            if not isinstance(route, dict):
                continue
            target = route.get("to") or route.get("from")
            target_id = _entity_id_from_reference(target)
            if target_id:
                return target_id

    label = statement.get("label")
    if isinstance(label, str) and label:
        return label
    return None


def _normalized_packet_statement(statement: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(statement)
    statement_id = _statement_id_from_definition(normalized)
    if statement_id and "id" not in normalized:
        normalized["id"] = f"{SPIRITSAFE_ENTITY_URI_PREFIX}{statement_id}"
    return normalized


def build_spiritsafe_manifest_document(
    spiritsafe_root: Union[str, Path],
) -> dict[str, Any]:
    """Build a manifest document from already-generated SpiritSafe artifacts.

    The manifest indexes artifacts present under a local SpiritSafe checkout. It
    does not re-query Wikibase or regenerate profile/value-list artifacts.
    """

    root = Path(spiritsafe_root).expanduser().resolve()
    profiles_dir = root / "profiles"
    cache_entities_dir = root / "cache" / "entities"
    queries_dir = root / "queries"
    cache_queries_dir = root / "cache" / "queries"

    entity_label_index: dict[str, str] = {}
    entity_qids: list[str] = []
    for entity_path in sorted(cache_entities_dir.glob("*.json")):
        entity_doc = json.loads(entity_path.read_text(encoding="utf-8"))
        entity_id = str(entity_doc.get("entity_id") or entity_path.stem)
        entity_qids.append(entity_id)
        entity_label_index[entity_id] = _label_from_cache_entity(entity_doc)

    profiles: list[dict[str, Any]] = []
    for profile_path in sorted(profiles_dir.glob("*.json")):
        profile_doc = json.loads(profile_path.read_text(encoding="utf-8"))
        metadata = profile_doc.get("metadata", {})
        entity_uri = _entity_uri_from_reference(profile_doc.get("entity"))
        qid = _entity_id_from_reference(entity_uri) or profile_path.stem
        profiles.append(
            {
                "entity": entity_uri,
                "qid": qid,
                "labels": metadata.get("labels", {}),
                "descriptions": metadata.get("descriptions", {}),
                "statement_count": metadata.get(
                    "statement_count", len(profile_doc.get("statements", []))
                ),
                "profile_graph": metadata.get("profile_graph", []),
                "value_list_graph": metadata.get("value_list_graph", []),
            }
        )

    queries = [
        {"qid": query_path.stem, "path": f"queries/{query_path.name}"}
        for query_path in sorted(queries_dir.glob("*.sparql"))
    ]

    value_lists: list[dict[str, Any]] = []
    for cache_path in sorted(cache_queries_dir.glob("*.json")):
        cache_doc = json.loads(cache_path.read_text(encoding="utf-8"))
        metadata = cache_doc.get("metadata", {})
        qid = cache_path.stem
        entity_uri = _entity_uri_from_reference(metadata.get("entity")) or (
            f"{SPIRITSAFE_ENTITY_URI_PREFIX}{qid}"
        )
        value_lists.append(
            {
                "entity": entity_uri,
                "qid": qid,
                "label": (
                    metadata.get("label")
                    or entity_label_index.get(qid)
                    or _profile_label_from_map(metadata.get("labels", {}))
                ),
                "path": f"cache/queries/{cache_path.name}",
                "item_count": metadata.get("count", len(cache_doc.get("items", []))),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": _manifest_source_url(),
        "profiles": profiles,
        "entities": {
            "count": len(entity_qids),
            "qids": sorted(entity_qids),
        },
        "queries": queries,
        "value_lists": value_lists,
    }


def export_spiritsafe_manifest(
    spiritsafe_root: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    """Build and write the SpiritSafe artifact manifest.

    Returns the manifest document that was written to disk.
    """

    root = Path(spiritsafe_root).expanduser().resolve()
    destination = (
        Path(output_path).expanduser().resolve()
        if output_path is not None
        else (root / "cache" / "manifest.json")
    )
    manifest_document = build_spiritsafe_manifest_document(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest_document, indent=2), encoding="utf-8")
    return manifest_document


@dataclass(frozen=True)
class Manifest:
    """Container for a loaded URI-keyed SpiritSafe artifact manifest."""

    generated_at: str
    source: str
    profiles: list[dict[str, Any]]
    entities: dict[str, Any]
    queries: list[dict[str, Any]]
    value_lists: list[dict[str, Any]]
    raw_manifest: dict[str, Any]

    @property
    def profile_qids(self) -> list[str]:
        """List the QIDs indexed in the manifest profile section."""

        qids: list[str] = []
        for profile in self.profiles:
            qid = _entity_id_from_reference(profile.get("qid") or profile.get("entity"))
            if qid:
                qids.append(qid)
        return qids

    def get_profile_entry(self, qid_or_uri: str) -> Optional[dict[str, Any]]:
        """Retrieve a manifest profile entry by QID or full entity URI."""

        requested_qid = _entity_id_from_reference(qid_or_uri)
        requested_uri = _entity_uri_from_reference(qid_or_uri)
        for profile in self.profiles:
            profile_qid = _entity_id_from_reference(
                profile.get("qid") or profile.get("entity")
            )
            profile_uri = _entity_uri_from_reference(profile.get("entity"))
            if requested_qid and profile_qid == requested_qid:
                return profile
            if requested_uri and profile_uri == requested_uri:
                return profile
        return None


_MANIFEST_CACHE: Optional[tuple[str, Manifest]] = None


def load_manifest(
    source_mode: Optional[SpiritSafeSourceMode] = None,
    github_repo: Optional[str] = None,
    github_ref: Optional[str] = None,
    local_root: Optional[Union[str, Path]] = None,
    use_cache: bool = True,
) -> Manifest:
    """Load the SpiritSafe artifact manifest with optional caching."""

    global _MANIFEST_CACHE

    if source_mode is not None or github_repo is not None or local_root is not None:
        source = SpiritSafeSourceConfig(
            mode=source_mode or get_spirit_safe_source().mode,
            github_repo=github_repo or get_spirit_safe_source().github_repo,
            github_ref=github_ref or get_spirit_safe_source().github_ref,
            local_root=(
                Path(local_root).expanduser().resolve()
                if local_root
                else get_spirit_safe_source().local_root
            ),
        )
    else:
        source = get_spirit_safe_source()

    cache_key = (
        f"{source.mode}:{source.github_repo}:{source.github_ref}:{source.local_root}"
    )
    if use_cache and _MANIFEST_CACHE is not None:
        cached_key, cached_manifest = _MANIFEST_CACHE
        if cached_key == cache_key:
            return cached_manifest

    manifest_path = source.resolve_relative("cache/manifest.json")

    try:
        manifest_data = _load_json_from_resolved_path(manifest_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Manifest not found at {manifest_path}. Ensure SpiritSafe artifacts are built."
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to load manifest: {exc}") from exc

    manifest = Manifest(
        generated_at=str(manifest_data.get("generated_at", "")),
        source=str(manifest_data.get("source", "")),
        profiles=manifest_data.get("profiles", []),
        entities=manifest_data.get("entities", {}),
        queries=manifest_data.get("queries", []),
        value_lists=manifest_data.get("value_lists", []),
        raw_manifest=manifest_data,
    )

    if use_cache:
        _MANIFEST_CACHE = (cache_key, manifest)

    return manifest


def load_profile(
    profile_id: str, manifest: Optional[Manifest] = None
) -> dict[str, Any]:
    """Load a single JSON entity profile by QID or entity URI."""

    del manifest

    entity_id = _entity_id_from_reference(profile_id)
    if not entity_id:
        raise FileNotFoundError(f"Invalid profile reference: {profile_id}")

    source = get_spirit_safe_source()
    resolved_path = source.resolve_relative(f"profiles/{entity_id}.json")

    try:
        return _load_json_from_resolved_path(resolved_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Profile JSON not found: profiles/{entity_id}.json"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to load profile '{entity_id}': {exc}") from exc


def _load_profile_documents_for_depth(
    profile_id: str,
    depth: int,
    loaded_profiles: dict[str, dict[str, Any]],
    visited: set[str],
) -> None:
    if profile_id in visited:
        return

    visited.add(profile_id)
    profile_document = load_profile(profile_id)
    loaded_profiles[profile_id] = profile_document

    if depth <= 0:
        return

    profile_graph = profile_document.get("metadata", {}).get("profile_graph", [])
    if not isinstance(profile_graph, list):
        return

    for edge in profile_graph:
        target_id = _entity_id_from_reference(edge.get("entity"))
        if not target_id or target_id in visited:
            continue
        try:
            _load_profile_documents_for_depth(
                target_id,
                depth - 1,
                loaded_profiles=loaded_profiles,
                visited=visited,
            )
        except FileNotFoundError:
            continue


def load_profile_package(
    profile_id: str, depth: int = 1, manifest: Optional[Manifest] = None
) -> dict[str, Any]:
    """Load a JSON profile plus related JSON profiles from embedded graph metadata."""

    del manifest

    normalized_profile_id = _entity_id_from_reference(profile_id)
    if not normalized_profile_id:
        raise FileNotFoundError(f"Invalid profile reference: {profile_id}")

    profiles_to_load: dict[str, dict[str, Any]] = {}
    _load_profile_documents_for_depth(
        normalized_profile_id,
        depth,
        loaded_profiles=profiles_to_load,
        visited=set(),
    )

    primary_profile = profiles_to_load.get(normalized_profile_id)
    if primary_profile is None:
        raise FileNotFoundError(
            f"Profile '{normalized_profile_id}' could not be loaded"
        )

    return {
        "primary_profile": normalized_profile_id,
        "primary_profile_entity": primary_profile.get("id")
        or primary_profile.get("entity"),
        "profiles": profiles_to_load,
        "depth": depth,
    }


def resolve_profile_link(
    source_profile_id: str,
    statement_id: str,
    manifest: Optional[Manifest] = None,
) -> Optional[dict[str, Any]]:
    """Resolve a profile-graph edge by source profile and linking statement URI/QID."""

    del manifest

    profile_document = load_profile(source_profile_id)
    requested_statement_id = _entity_id_from_reference(statement_id)
    requested_statement_uri = _entity_uri_from_reference(statement_id)

    for edge in profile_document.get("metadata", {}).get("profile_graph", []):
        edge_statement_id = _entity_id_from_reference(edge.get("via_statement"))
        edge_statement_uri = _entity_uri_from_reference(edge.get("via_statement"))
        if requested_statement_id and edge_statement_id == requested_statement_id:
            return {
                "target_profile": _entity_id_from_reference(edge.get("entity")),
                "target_entity": _entity_uri_from_reference(edge.get("entity")),
                "via_statement": edge_statement_uri,
                "relationship_type": edge.get("linkage_type"),
                "label": edge.get("label"),
            }
        if requested_statement_uri and edge_statement_uri == requested_statement_uri:
            return {
                "target_profile": _entity_id_from_reference(edge.get("entity")),
                "target_entity": _entity_uri_from_reference(edge.get("entity")),
                "via_statement": edge_statement_uri,
                "relationship_type": edge.get("linkage_type"),
                "label": edge.get("label"),
            }

    return None


def validate_packet_structure(packet: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate packet structure and basic linkage consistency."""

    errors = []
    if "metadata" in packet and "data" in packet:
        required_fields = ["packet_id", "operation_mode", "metadata", "data"]
    else:
        required_fields = [
            "packet_id",
            "operation_mode",
            "entities",
            "cross_references",
        ]

    for required_field in required_fields:
        if required_field not in packet:
            errors.append(f"Missing required field: {required_field}")

    if "metadata" in packet and "data" in packet:
        data_entities = packet.get("data", {}).get("entities", [])
        if not isinstance(data_entities, list):
            errors.append("data.entities must be a list")
            data_entities = []

        for entity in data_entities:
            if not isinstance(entity, dict):
                errors.append("Each data.entities item must be an object")
                continue
            if not entity.get("profile"):
                errors.append("Each data.entities item must include profile")
            entity_id = entity.get("id")
            if not isinstance(entity_id, str) or not entity_id.startswith("http"):
                errors.append("Each data.entities item id must be an HTTP URI")

        metadata = packet.get("metadata", {})
        if not isinstance(metadata.get("profiles", []), list):
            errors.append("metadata.profiles must be a list")

        integrity = metadata.get("integrity", {})
        if not isinstance(integrity, dict):
            errors.append("metadata.integrity must be an object")
        else:
            if not integrity.get("metadata_digest"):
                errors.append("metadata.integrity.metadata_digest is required")

        return (len(errors) == 0, errors)

    entity_ids = {
        str(entity.get("id"))
        for entity in packet.get("entities", [])
        if isinstance(entity, dict) and entity.get("id")
    }

    for cross_ref in packet.get("cross_references", []):
        if cross_ref.get("from") not in entity_ids:
            errors.append(
                f"Cross-reference from {cross_ref.get('from')} points to unknown entity"
            )
        if cross_ref.get("to") not in entity_ids:
            errors.append(
                f"Cross-reference to {cross_ref.get('to')} points to unknown entity"
            )

    for constraint in packet.get("cardinality_constraints", []):
        minimum = constraint.get("min")
        maximum = constraint.get("max")
        if isinstance(minimum, int) and minimum < 0:
            errors.append(f"Cardinality min must be >= 0: {constraint}")
        if (
            isinstance(minimum, int)
            and isinstance(maximum, int)
            and maximum != -1
            and maximum < minimum
        ):
            errors.append(f"Cardinality max must be >= min or -1: {constraint}")

    return (len(errors) == 0, errors)
