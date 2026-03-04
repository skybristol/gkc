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
import uuid
from dataclasses import dataclass, field
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


# ============================================================================
# Profile Registry Abstraction
# ============================================================================


@dataclass(frozen=True)
class ProfileMetadata:
    """Metadata for a SpiritSafe profile registrant.

    This dataclass represents the structured metadata from a profile's
    metadata.yaml file, supporting discovery, versioning, and governance.

    Attributes:
        profile_id: Profile identifier (directory name)
        name: Human-readable profile name
        description: Profile description
        version: Semantic version string
        status: Profile status (e.g., "stable", "draft", "deprecated")
        published_date: Publication date (ISO 8601 string)
        authors: List of author dicts with 'name' and optional 'email'
        maintainers: List of maintainer dicts with 'name' and optional 'email'
        source_references: List of reference dicts with 'name' and 'url'
        related_profiles: List of related profile IDs
        community_feedback: Dict with issue tracker and other feedback URLs
        datatypes_used: List of Wikibase datatypes used in profile
        statements_count: Number of statements defined in profile
        references_required: Whether references are required
        qualifiers_used: List of qualifier property IDs used
        sparql_sources: List of SPARQL query filenames
        raw_metadata: Complete raw metadata dict for access to additional fields

    Plain meaning: Structured information about a profile package.
    """

    profile_id: str
    name: str
    description: str
    version: str
    status: str
    published_date: Optional[str] = None
    authors: list[dict[str, str]] = field(default_factory=list)
    maintainers: list[dict[str, str]] = field(default_factory=list)
    source_references: list[dict[str, str]] = field(default_factory=list)
    related_profiles: list[str] = field(default_factory=list)
    community_feedback: dict[str, str] = field(default_factory=dict)
    datatypes_used: list[str] = field(default_factory=list)
    statements_count: Optional[int] = None
    references_required: Optional[bool] = None
    qualifiers_used: list[str] = field(default_factory=list)
    sparql_sources: list[str] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


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


def get_profile_metadata(profile_id: str) -> ProfileMetadata:
    """Load metadata for a profile from its metadata.yaml file.

    Args:
        profile_id: Profile identifier (directory name)

    Returns:
        Structured profile metadata

    Raises:
        FileNotFoundError: If profile or metadata.yaml doesn't exist
        ValueError: If metadata.yaml is invalid

    Example:
        >>> metadata = get_profile_metadata("TribalGovernmentUS")
        >>> print(metadata.name)
        'Federally Recognized Tribe'
        >>> print(metadata.version)
        '1.0.0'

    Plain meaning: Get information about a profile without loading its full definition.
    """
    source = get_spirit_safe_source()
    metadata_path = f"profiles/{profile_id}/metadata.yaml"
    resolved = source.resolve_relative(metadata_path)

    try:
        metadata_text = _read_text_from_resolved_path(resolved)
        raw = yaml.safe_load(metadata_text) or {}
    except Exception as exc:
        raise FileNotFoundError(
            f"Could not load metadata for profile '{profile_id}'"
        ) from exc

    # Validate required fields
    if "name" not in raw:
        raise ValueError(
            f"Profile '{profile_id}' metadata missing required field 'name'"
        )
    if "version" not in raw:
        raise ValueError(
            f"Profile '{profile_id}' metadata missing required field 'version'"
        )
    if "status" not in raw:
        raise ValueError(
            f"Profile '{profile_id}' metadata missing required field 'status'"
        )

    # Normalize published_date to string if it was parsed as date object
    published_date = raw.get("published_date")
    if published_date is not None and not isinstance(published_date, str):
        # YAML may parse ISO dates as date objects
        published_date = str(published_date)

    return ProfileMetadata(
        profile_id=profile_id,
        name=raw["name"],
        description=raw.get("description", ""),
        version=raw["version"],
        status=raw["status"],
        published_date=published_date,
        authors=raw.get("authors", []),
        maintainers=raw.get("maintainers", []),
        source_references=raw.get("source_references", []),
        related_profiles=raw.get("related_profiles", []),
        community_feedback=raw.get("community_feedback", {}),
        datatypes_used=raw.get("datatypes_used", []),
        statements_count=raw.get("statements_count"),
        references_required=raw.get("references_required"),
        qualifiers_used=raw.get("qualifiers_used", []),
        sparql_sources=raw.get("sparql_sources", []),
        raw_metadata=raw,
    )


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

    # Simple profile name: resolve to registrant package path
    # Allow both "ProfileName" and "ProfileName.yaml" inputs
    profile_name = ref_str.removesuffix(".yaml")
    return f"profiles/{profile_name}/profile.yaml"


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

    source = get_spirit_safe_source()
    profile_path_str = str(profile_path)

    # Transition compatibility:
    # Prefer caller path first, then try alternate registrant/legacy forms.
    candidates: list[str] = [profile_path_str]

    # registrant path -> legacy flat YAML fallback
    # profiles/Foo/profile.yaml -> profiles/Foo.yaml
    if profile_path_str.startswith("profiles/") and profile_path_str.endswith(
        "/profile.yaml"
    ):
        profile_id = profile_path_str[len("profiles/") : -len("/profile.yaml")]
        if profile_id:
            candidates.append(f"profiles/{profile_id}.yaml")

    # legacy flat YAML -> registrant path fallback
    # profiles/Foo.yaml -> profiles/Foo/profile.yaml
    if profile_path_str.startswith("profiles/") and profile_path_str.endswith(".yaml"):
        profile_file = profile_path_str[len("profiles/") :]
        if "/" not in profile_file:
            profile_id = Path(profile_file).stem
            candidates.append(f"profiles/{profile_id}/profile.yaml")

    last_error: Optional[Exception] = None
    for candidate in dict.fromkeys(candidates):
        try:
            resolved = source.resolve_relative(candidate)
            return _read_text_from_resolved_path(resolved)
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise last_error

    raise FileNotFoundError(f"Unable to resolve profile path: {profile_path_str}")


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
                resolved_query_ref = resolve_query_ref(
                    str(query_ref), spec.get("profile", "")
                )
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


# ============================================================================
# Phase 3: Manifest Loading, Profile Registration, and Curation Packets
# ============================================================================


@dataclass(frozen=True)
class Manifest:
    """Container for loaded SpiritSafe manifest with registry-wide metadata.

    This represents the authoritative registry of available profiles, their
    relationships, and caching/versioning information. The manifest is generated
    by the SpiritSafe build process and used by gkc for discovering profiles,
    validating cross-profile relationships, and managing curation workflows.

    Attributes:
        generated_at: ISO 8601 timestamp of manifest generation
        commit_sha: Git commit SHA that generated this manifest
        commit_timestamp: Git commit timestamp (ISO 8601)
        profiles: List of profile metadata dictionaries from manifest
        raw_manifest: Complete raw manifest dict for access to other fields

    Plain meaning: The authoritative registry of available entity profiles.
    """

    generated_at: str
    commit_sha: str
    commit_timestamp: str
    profiles: list[dict[str, Any]]
    raw_manifest: dict[str, Any]

    @property
    def profile_ids(self) -> list[str]:
        """List of all profile IDs in the manifest.

        Returns:
            List of profile identifiers.
        """
        return [p["id"] for p in self.profiles]

    def get_profile_entry(self, profile_id: str) -> Optional[dict[str, Any]]:
        """Retrieve manifest entry for a specific profile.

        Args:
            profile_id: Profile identifier

        Returns:
            Profile manifest entry dict or None if not found
        """
        for profile in self.profiles:
            if profile["id"] == profile_id:
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
    """Load the SpiritSafe manifest with optional caching.

    The manifest is a machine-readable registry of all available profiles,
    their metadata, relationships, and file locations. It's generated by the
    SpiritSafe build process and committed to the repository.

    Args:
        source_mode: Source mode ("github" or "local"), overrides global config if provided
        github_repo: GitHub repository slug, overrides global config if provided
        github_ref: Git ref for resolution, overrides global config if provided
        local_root: Local SpiritSafe root, overrides global config if provided
        use_cache: Use in-memory cache if available

    Returns:
        Loaded Manifest instance

    Raises:
        FileNotFoundError: If manifest.json cannot be found
        ValueError: If manifest.json is invalid JSON
        RuntimeError: If manifest loading fails (network, permissions, etc.)

    Example:
        >>> manifest = load_manifest()
        >>> print(manifest.profile_ids)
        ['TribalGovernmentUS', 'OfficeHeldByHeadOfState']

    Plain meaning: Load the registry of available profiles.
    """
    global _MANIFEST_CACHE

    # Build source config from params or use global
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

    # Check cache
    cache_key = (
        f"{source.mode}:{source.github_repo}:{source.github_ref}:{source.local_root}"
    )
    if use_cache and _MANIFEST_CACHE is not None:
        cached_key, cached_manifest = _MANIFEST_CACHE
        if cached_key == cache_key:
            return cached_manifest

    # Resolve manifest path
    manifest_path = source.resolve_relative("cache/manifest.json")

    # Load manifest JSON
    try:
        manifest_text = _read_text_from_resolved_path(manifest_path)
        manifest_data = json.loads(manifest_text)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Manifest not found at {manifest_path}. Ensure SpiritSafe cache is built."
        ) from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Manifest JSON is invalid: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to load manifest: {exc}") from exc

    # Parse manifest
    manifest = Manifest(
        generated_at=manifest_data.get("generated_at", ""),
        commit_sha=manifest_data.get("commit_sha", ""),
        commit_timestamp=manifest_data.get("commit_timestamp", ""),
        profiles=manifest_data.get("profiles", []),
        raw_manifest=manifest_data,
    )

    # Cache manifest
    if use_cache:
        _MANIFEST_CACHE = (cache_key, manifest)

    return manifest


def load_profile(
    profile_id: str, manifest: Optional[Manifest] = None
) -> dict[str, Any]:
    """Load a single profile YAML definition.

    Args:
        profile_id: Profile identifier
        manifest: Optional pre-loaded manifest (loaded if not provided)

    Returns:
        Parsed profile YAML as dictionary

    Raises:
        FileNotFoundError: If profile or manifest not found
        ValueError: If profile YAML is invalid
        RuntimeError: If loading fails

    Example:
        >>> profile = load_profile("TribalGovernmentUS")
        >>> print(profile.get("name"))

    Plain meaning: Load the YAML definition of a single entity profile.
    """
    if manifest is None:
        manifest = load_manifest()

    profile_entry = manifest.get_profile_entry(profile_id)
    if profile_entry is None:
        raise FileNotFoundError(
            f"Profile '{profile_id}' not found in manifest. "
            f"Available profiles: {manifest.profile_ids}"
        )

    # Resolve profile YAML path
    profile_yaml_path = profile_entry.get("files", {}).get("profile_yaml")
    if not profile_yaml_path:
        raise ValueError(f"Profile entry missing profile_yaml path: {profile_id}")

    source = get_spirit_safe_source()
    resolved_path = source.resolve_relative(profile_yaml_path)

    # Load and parse YAML
    try:
        yaml_text = _read_text_from_resolved_path(resolved_path)
        profile_data = yaml.safe_load(yaml_text) or {}
        return profile_data
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Profile YAML not found: {profile_yaml_path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Profile YAML is invalid: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Failed to load profile: {exc}") from exc


def load_profile_package(
    profile_id: str, depth: int = 1, manifest: Optional[Manifest] = None
) -> dict[str, Any]:
    """Load a profile package with primary profile and related profiles.

    This function loads the primary profile plus all related profiles at the
    specified depth, returning a package suitable for multi-entity curation
    workflows. The package includes graph information for cross-profile linkages.

    Args:
        profile_id: Primary profile identifier
        depth: How many levels of related profiles to include (default: 1)
        manifest: Optional pre-loaded manifest (loaded if not provided)

    Returns:
        Package dictionary with structure:
        {
            "primary_profile": "TribalGovernmentUS",
            "profiles": {...profiles loaded...},
            "graph": {...profile graph...},
            "depth": 1
        }

    Raises:
        FileNotFoundError: If profile not found
        ValueError: If configuration invalid
        RuntimeError: If loading fails

    Example:
        >>> package = load_profile_package("TribalGovernmentUS", depth=1)
        >>> print(list(package["profiles"].keys()))
        ['TribalGovernmentUS', 'OfficeHeldByHeadOfState']

    Plain meaning: Load a profile plus related profiles for multi-entity curation.
    """
    if manifest is None:
        manifest = load_manifest()

    # Validate profile exists
    if manifest.get_profile_entry(profile_id) is None:
        raise FileNotFoundError(
            f"Profile '{profile_id}' not found in manifest. "
            f"Available profiles: {manifest.profile_ids}"
        )

    # Load primary profile
    primary_profile = load_profile(profile_id, manifest)

    profiles_to_load = {profile_id: primary_profile}

    # Traverse to load related profiles at specified depth
    if depth > 0:
        related_ids = _get_related_profile_ids(
            profile_id, manifest, visited=set(), depth=depth
        )
        for related_id in related_ids:
            if related_id not in profiles_to_load:
                try:
                    profiles_to_load[related_id] = load_profile(related_id, manifest)
                except Exception:
                    # Skip profiles that fail to load
                    pass

    # Build graph from manifest
    from gkc.profiles.graph import ProfileGraph

    graph = ProfileGraph.from_manifest_data(manifest.profiles)

    return {
        "primary_profile": profile_id,
        "profiles": profiles_to_load,
        "graph": graph,
        "depth": depth,
        "manifest_commit_sha": manifest.commit_sha,
    }


def _get_related_profile_ids(
    profile_id: str,
    manifest: Manifest,
    visited: Optional[set[str]] = None,
    depth: int = 1,
) -> set[str]:
    """Recursively find related profile IDs up to specified depth.

    Args:
        profile_id: Starting profile ID
        manifest: Loaded manifest
        visited: Set of already-visited profile IDs (for cycle prevention)
        depth: Remaining depth to traverse

    Returns:
        Set of related profile IDs
    """
    if visited is None:
        visited = set()

    if depth <= 0 or profile_id in visited:
        return set()

    visited.add(profile_id)
    related = set()

    profile_entry = manifest.get_profile_entry(profile_id)
    if profile_entry is None:
        return related

    # Get direct related profiles
    related_profiles = profile_entry.get("related_profiles", [])
    for rel_id in related_profiles:
        if rel_id not in visited:
            related.add(rel_id)
            # Recurse if depth > 1
            if depth > 1:
                related.update(
                    _get_related_profile_ids(rel_id, manifest, visited, depth - 1)
                )

    return related


def get_profile_graph(manifest: Optional[Manifest] = None) -> Any:
    """Get the complete ProfileGraph from manifest.

    Args:
        manifest: Optional pre-loaded manifest (loaded if not provided)

    Returns:
        ProfileGraph instance representing all profiles and relationships

    Example:
        >>> graph = get_profile_graph()
        >>> neighbors = graph.get_neighbors("TribalGovernmentUS")

    Plain meaning: Get the graph of all profile relationships.
    """
    if manifest is None:
        manifest = load_manifest()

    from gkc.profiles.graph import ProfileGraph

    return ProfileGraph.from_manifest_data(manifest.profiles)


def resolve_profile_link(
    source_profile_id: str,
    statement_id: str,
    manifest: Optional[Manifest] = None,
) -> Optional[dict[str, Any]]:
    """Resolve cross-profile linkage for a statement.

    Given a source profile and statement ID, find the target profile and
    linkage metadata from manifest data.

    Args:
        source_profile_id: Profile ID containing the linking statement
        statement_id: Statement ID that creates the linkage
        manifest: Optional pre-loaded manifest (loaded if not provided)

    Returns:
        Linkage metadata dict or None if not found. Includes:
        {
            "target_profile": "...",
            "via_statement": "...",
            "relationship_type": "...",
            "cardinality": {...},
            "workflow_policy": {...},
            ...
        }

    Example:
        >>> linkage = resolve_profile_link(
        ...     "TribalGovernmentUS",
        ...     "office_held_by_head_of_state"
        ... )
        >>> if linkage:
        ...     print(linkage["target_profile"])

    Plain meaning: Find target profile and linkage rules for a cross-profile statement.
    """
    if manifest is None:
        manifest = load_manifest()

    profile_entry = manifest.get_profile_entry(source_profile_id)
    if profile_entry is None:
        return None

    # Look in statement_linkages array
    linkages = profile_entry.get("statement_linkages", [])
    for linkage in linkages:
        if linkage.get("statement_id") == statement_id:
            return linkage.get("linkage")

    return None


def create_curation_packet(
    profile_id: str,
    operation_mode: str = "single",
    load_wikidata_qids: bool = False,
    depth: int = 1,
    manifest: Optional[Manifest] = None,
) -> dict[str, Any]:
    """Create a curation packet for multi-entity workflows.

    A curation packet is a self-contained work unit containing entity scaffolds,
    cross-reference information, linkage metadata, and cardinality constraints.
    It serves as the primary interface between gkc and the Wizard for guiding
    curator workflows.

    Args:
        profile_id: Primary profile to create packet for
        operation_mode: "single" (primary only) or "bulk" (with related profiles)
        load_wikidata_qids: Whether to pre-populate from Wikidata (future enhancement)
        depth: Related profile depth to include (for bulk mode)
        manifest: Optional pre-loaded manifest (loaded if not provided)

    Returns:
        Curation packet dictionary with structure:
        {
            "packet_id": "pkt-...",
            "operation_mode": "single" or "bulk",
            "created_at": "ISO 8601",
            "manifest_commit_sha": "...",
            "entities": [...entity scaffolds...],
            "cross_references": [...linkage info...],
            "cardinality_constraints": [...constraints...],
            "profile_package": {...profile data...}
        }

    Raises:
        FileNotFoundError: If profile not found
        ValueError: If configuration invalid

    Example:
        >>> packet = create_curation_packet("TribalGovernmentUS", "single")
        >>> print(f"Packet {packet['packet_id']} for {len(packet['entities'])} entities")

    Plain meaning: Create a work unit for multi-entity curation.
    """
    if manifest is None:
        manifest = load_manifest()

    # Determine packet depth and what to load
    actual_depth = depth if operation_mode == "bulk" else 0

    # Load profile package
    package = load_profile_package(profile_id, depth=actual_depth, manifest=manifest)

    # Build entity scaffolds
    entities = []
    entity_id_map = {}  # Map profile_id -> packet entity_id

    for idx, (prof_id, profile_data) in enumerate(package["profiles"].items()):
        entity_id = f"ent-{idx + 1:03d}"
        entity_id_map[prof_id] = entity_id

        # Create scaffold for this entity with profile structure
        entity = {
            "id": entity_id,
            "profile": prof_id,
            "data": {},  # Curator fills this in the wizard
            "profile_structure": {
                # This will be used by the Wizard for form generation
                "statements": profile_data.get("statements", {}),
            },
        }
        entities.append(entity)

    # Build cross-references
    cross_references = []

    for source_profile_id in package["profiles"].keys():
        profile_entry = manifest.get_profile_entry(source_profile_id)
        if not profile_entry:
            continue

        linkages = profile_entry.get("statement_linkages", [])
        for linkage in linkages:
            target_profile = linkage.get("linkage", {}).get("target_profile")
            statement_id = linkage.get("statement_id")

            if (
                target_profile in package["profiles"]
                and target_profile in entity_id_map
            ):
                source_entity_id = entity_id_map[source_profile_id]
                target_entity_id = entity_id_map[target_profile]

                cross_reference = {
                    "from": source_entity_id,
                    "from_profile": source_profile_id,
                    "to": target_entity_id,
                    "to_profile": target_profile,
                    "via_statement": statement_id,
                    "cardinality": linkage.get("linkage", {}).get("cardinality", {}),
                    "workflow_policy": linkage.get("linkage", {}).get(
                        "workflow_policy", {}
                    ),
                }
                cross_references.append(cross_reference)

    # Build cardinality constraints (for validation)
    cardinality_constraints = []
    for cross_ref in cross_references:
        constraint = {
            "from": cross_ref["from"],
            "to": cross_ref["to"],
            "min": cross_ref.get("cardinality", {}).get("min", 0),
            "max": cross_ref.get("cardinality", {}).get("max", -1),  # -1 = unlimited
        }
        cardinality_constraints.append(constraint)

    # Generate packet ID
    packet_id = f"pkt-{uuid.uuid4().hex[:12]}"

    # Build packet
    packet = {
        "packet_id": packet_id,
        "operation_mode": operation_mode,
        "created_at": datetime.now().isoformat(),
        "manifest_commit_sha": manifest.commit_sha,
        "primary_profile": profile_id,
        "entities": entities,
        "cross_references": cross_references,
        "cardinality_constraints": cardinality_constraints,
        "profile_package": package,
    }

    return packet


def validate_packet_structure(packet: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate packet structure and cardinality constraints.

    Checks that:
    - Required fields are present
    - Entity IDs are consistent
    - Cross-references point to valid entities
    - Cardinality constraints are satisfiable

    Args:
        packet: Curation packet to validate

    Returns:
        Tuple of (is_valid, errors) where is_valid is bool and errors is list of strings

    Example:
        >>> is_valid, errors = validate_packet_structure(packet)
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(f"  - {error}")

    Plain meaning: Check that a curation packet is well-formed.
    """
    errors = []

    # Check required fields
    required_fields = ["packet_id", "operation_mode", "entities", "cross_references"]
    for required_field in required_fields:
        if required_field not in packet:
            errors.append(f"Missing required field: {required_field}")

    # Check entities
    if "entities" in packet:
        entity_ids = {e["id"] for e in packet["entities"]}

        # Validate cross-references
        for cross_ref in packet.get("cross_references", []):
            if cross_ref["from"] not in entity_ids:
                errors.append(
                    f"Cross-reference from {cross_ref['from']} points to unknown entity"
                )
            if cross_ref["to"] not in entity_ids:
                errors.append(
                    f"Cross-reference to {cross_ref['to']} points to unknown entity"
                )

    # Check cardinality is feasible
    for constraint in packet.get("cardinality_constraints", []):
        if constraint["min"] < 0:
            errors.append(f"Cardinality min must be >= 0: {constraint}")
        if constraint["max"] != -1 and constraint["max"] < constraint["min"]:
            errors.append(f"Cardinality max must be >= min or -1: {constraint}")

    return (len(errors) == 0, errors)
