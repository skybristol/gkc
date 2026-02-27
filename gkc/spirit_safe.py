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

from dataclasses import dataclass
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Optional, Union

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
