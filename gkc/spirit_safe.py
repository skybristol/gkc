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
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Optional, Union

import requests
import yaml

from gkc.sparql import SPARQLQuery, paginate_query

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


def _read_text_from_resolved_path(resolved_path: Union[Path, str]) -> str:
    """Read text from a resolved local path or URL.

    Args:
        resolved_path: Local filesystem path or HTTP URL.

    Returns:
        UTF-8 text content.

    Raises:
        FileNotFoundError: If local path does not exist.
        requests.HTTPError: If URL fetch fails.
    """
    if isinstance(resolved_path, Path):
        return resolved_path.read_text(encoding="utf-8")

    response = requests.get(resolved_path, timeout=30)
    response.raise_for_status()
    return response.text


def resolve_profile_path(profile_ref: Union[str, Path]) -> Union[str, Path]:
    """Resolve a profile reference to a path within SpiritSafe structure.

    Handles profile name resolution (with or without .yaml extension) to the
    profiles/ subdirectory, and preserves full paths as-is.

    Args:
        profile_ref: Profile name (e.g., "TribalGovernmentUS",
                    "TribalGovernmentUS.yaml") or full path
                    (e.g., "profiles/TribalGovernmentUS.yaml").

    Returns:
        Resolved path suitable for _resolve_profile_text().
    """
    ref_str = str(profile_ref)

    # If it's already a path with directory separators, use as-is
    if "/" in ref_str or "\\" in ref_str:
        return profile_ref

    # If it looks like an absolute path, use as-is
    path_obj = Path(profile_ref)
    if path_obj.is_absolute():
        return profile_ref

    # Simple profile name: resolve to profiles/ subdirectory
    # Add .yaml extension if not present
    profile_name = ref_str if ref_str.endswith(".yaml") else f"{ref_str}.yaml"
    return f"profiles/{profile_name}"


def _resolve_profile_text(profile_path: Union[str, Path]) -> str:
    """Resolve and read profile YAML text from local path or configured source.

    Args:
        profile_path: Absolute path, relative path, or SpiritSafe-relative path.

    Returns:
        YAML text.
    """
    path_obj = Path(profile_path)
    if path_obj.is_absolute() and path_obj.exists():
        return path_obj.read_text(encoding="utf-8")

    if path_obj.exists():
        return path_obj.read_text(encoding="utf-8")

    resolved = get_spirit_safe_source().resolve_relative(str(profile_path))
    return _read_text_from_resolved_path(resolved)


def _extract_sparql_specs(node: Any, location: str = "") -> list[dict[str, Any]]:
    """Extract SPARQL lookup specs from nested profile data.

    Args:
        node: Nested YAML data node.
        location: Dot/bracket path for diagnostics.

    Returns:
        List of extracted lookup spec dictionaries.
    """
    specs: list[dict[str, Any]] = []

    if isinstance(node, dict):
        if node.get("source") == "sparql" and ("query" in node or "query_ref" in node):
            specs.append(
                {
                    "location": location or "<root>",
                    "query": node.get("query"),
                    "query_ref": node.get("query_ref"),
                    "query_params": node.get("query_params") or {},
                    "refresh": node.get("refresh", "manual"),
                }
            )

        for key, value in node.items():
            child_location = f"{location}.{key}" if location else key
            specs.extend(_extract_sparql_specs(value, child_location))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            child_location = f"{location}[{index}]" if location else f"[{index}]"
            specs.extend(_extract_sparql_specs(item, child_location))

    return specs


def _render_query_template(template: str, params: dict[str, Any]) -> str:
    """Render a template query using simple token replacement.

    Tokens are expected as `{{token_name}}`.

    Args:
        template: Query template text.
        params: Token replacement values.

    Returns:
        Rendered query string.
    """
    rendered = template
    for key, value in params.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def hydrate_profile_lookups(
    profile_paths: list[Union[str, Path]],
    *,
    refresh_policy: Optional[RefreshPolicy] = None,
    force_refresh: bool = False,
    page_size: int = 1000,
    max_results: Optional[int] = None,
    endpoint: str = "https://query.wikidata.org/sparql",
    dry_run: bool = False,
    fail_on_query_error: bool = False,
) -> dict[str, Any]:
    """Hydrate SPARQL lookup caches for one or more profile files.

    This performs an explicit lookup hydration workflow by scanning profile YAML,
    extracting SPARQL lookup specs, resolving query references/templates, deduplicating
    identical rendered queries, and optionally executing them through `LookupFetcher`.

    Args:
        profile_paths: Paths to profile YAML files.
        refresh_policy: Optional global refresh policy override.
        force_refresh: Force refresh even if cache is fresh.
        page_size: Page size for paginated query execution.
        max_results: Optional maximum total results per query.
        endpoint: SPARQL endpoint URL.
        dry_run: If True, do not execute queries; return discovery summary only.
        fail_on_query_error: If True, raise on first query execution failure.

    Returns:
        Summary dictionary with discovery/execution stats.
    """
    source = get_spirit_safe_source()
    discovered_specs: list[dict[str, Any]] = []

    for profile_path in profile_paths:
        yaml_text = _resolve_profile_text(profile_path)
        profile_data = yaml.safe_load(yaml_text) or {}
        profile_specs = _extract_sparql_specs(profile_data)
        for spec in profile_specs:
            spec["profile"] = str(profile_path)
            discovered_specs.append(spec)

    unique_queries: dict[tuple[str, str], dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    for spec in discovered_specs:
        try:
            if spec.get("query"):
                rendered_query = str(spec["query"])
            else:
                query_ref = spec.get("query_ref")
                if not query_ref:
                    raise ValueError("Missing both 'query' and 'query_ref'")
                resolved_query_ref = source.resolve_relative(str(query_ref))
                query_template = _read_text_from_resolved_path(resolved_query_ref)
                rendered_query = _render_query_template(
                    query_template, spec.get("query_params", {})
                )

            key = (endpoint, rendered_query.strip())
            if key not in unique_queries:
                unique_queries[key] = {
                    "endpoint": endpoint,
                    "query": rendered_query,
                    "refresh": refresh_policy or spec.get("refresh", "manual"),
                    "sources": [],
                }
            unique_queries[key]["sources"].append(
                {
                    "profile": spec.get("profile"),
                    "location": spec.get("location"),
                    "query_ref": spec.get("query_ref"),
                }
            )
        except Exception as exc:
            failure = {
                "profile": spec.get("profile"),
                "location": spec.get("location"),
                "query_ref": spec.get("query_ref"),
                "error": str(exc),
            }
            failures.append(failure)
            if fail_on_query_error:
                profile_loc = f"{failure['profile']}:{failure['location']}"
                raise RuntimeError(
                    f"Failed to prepare query for {profile_loc}"
                ) from exc

    hydrated: list[dict[str, Any]] = []
    if not dry_run:
        fetcher = LookupFetcher(endpoint=endpoint)
        for entry in unique_queries.values():
            try:
                results = fetcher.fetch(
                    entry["query"],
                    refresh_policy=entry["refresh"],
                    force_refresh=force_refresh,
                    page_size=page_size,
                    max_results=max_results,
                )
                hydrated.append(
                    {
                        "endpoint": endpoint,
                        "refresh": entry["refresh"],
                        "source_count": len(entry["sources"]),
                        "result_count": len(results),
                        "sources": entry["sources"],
                    }
                )
            except Exception as exc:
                failure = {
                    "endpoint": endpoint,
                    "sources": entry["sources"],
                    "error": str(exc),
                }
                failures.append(failure)
                if fail_on_query_error:
                    raise RuntimeError(
                        "Failed to execute hydrated lookup query"
                    ) from exc

    cache_dir = source.resolve_cache_dir()
    cache_file_count = len(list(cache_dir.glob("*.json"))) if cache_dir.exists() else 0

    return {
        "source_mode": source.mode,
        "profiles_scanned": len(profile_paths),
        "lookup_specs_found": len(discovered_specs),
        "unique_queries": len(unique_queries),
        "unique_queries_executed": 0 if dry_run else len(hydrated),
        "dry_run": dry_run,
        "cache_dir": str(cache_dir),
        "cache_file_count": cache_file_count,
        "hydrated": hydrated,
        "failures": failures,
    }
