"""
Mash: Load data from various sources as templates for processing.

The Mash stage loads data from diverse sources (Wikidata items, CSV files,
JSON APIs, dataframes, etc.) as templates, allowing users to view, filter,
and export them in various formats for further processing.

Current implementations:
- Wikidata items: Load existing items as templates for bulk modification

Future implementations:
- CSV files: Parse CSV data into template format
- JSON APIs: Fetch and transform API responses
- Dataframes: Process in-memory data structures

Plain meaning: Load source data and prepare it for distillery processing.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Optional, Protocol, Union
from urllib.parse import urlparse

import requests

from gkc.mash.protocols import MashSourceAdapter
from gkc.runtime_config import DEFAULT_USER_AGENT
from gkc.sparql import fetch_entity_labels


class WikibaseApiClient:
    """Generic MediaWiki/Wikibase API helper.

    Plain meaning: Reusable client for wbsearchentities and wbgetentities across
    Wikidata, Data Distillery, or any compatible Wikibase API endpoint.
    """

    def __init__(
        self,
        api_url: str = "https://www.wikidata.org/w/api.php",
        *,
        session: Optional[requests.Session] = None,
        user_agent: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_url = api_url
        self.timeout = timeout
        self.session = session or requests.Session()
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        session_headers = getattr(self.session, "headers", None)
        if session_headers is None:
            try:
                setattr(self.session, "headers", {})
                session_headers = self.session.headers
            except Exception:
                session_headers = None

        if hasattr(session_headers, "update"):
            session_headers.update({"User-Agent": self.user_agent})

    def search_entities(
        self,
        *,
        label: str,
        entity_type: str,
        language: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        payload = self.request(
            {
                "action": "wbsearchentities",
                "format": "json",
                "search": label,
                "language": language,
                "type": entity_type,
                "limit": limit,
            }
        )
        return payload.get("search", [])

    def get_entities(self, entity_ids: list[str]) -> dict[str, dict[str, Any]]:
        if not entity_ids:
            return {}

        payload = self.request(
            {
                "action": "wbgetentities",
                "format": "json",
                "ids": "|".join(entity_ids),
            }
        )
        entities = payload.get("entities", {})
        if not isinstance(entities, dict):
            return {}

        return {
            eid: entity_data
            for eid, entity_data in entities.items()
            if isinstance(entity_data, dict) and "missing" not in entity_data
        }

    def get_entity(self, entity_id: str) -> dict[str, Any]:
        entities = self.get_entities([entity_id])
        if entity_id not in entities:
            raise RuntimeError(f"Entity '{entity_id}' not found")
        return entities[entity_id]

    def request(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self.session.get(
                self.api_url,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Wikibase API request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("Wikibase API returned non-JSON response") from exc

        if "error" in payload:
            raise RuntimeError(f"Wikibase API returned error: {payload['error']}")

        return payload


@dataclass(frozen=True)
class WikibaseRecentChangesResult:
    """Recentchanges polling result for Wikibase entity updates."""

    since: str
    next_since: str
    changed_ids: list[str] = field(default_factory=list)
    ignored_ids: list[str] = field(default_factory=list)
    recentchanges: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class WikibaseCacheRefreshResult:
    """Result of refreshing per-entity cache files from recentchanges."""

    cache_dir: str
    since: str
    next_since: str
    changed_ids: list[str] = field(default_factory=list)
    ignored_ids: list[str] = field(default_factory=list)
    refreshed_ids: list[str] = field(default_factory=list)
    deleted_ids: list[str] = field(default_factory=list)
    missing_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WikibaseFullSyncResult:
    """Result of a full-sync baseline entity cache operation.

    Plain meaning: What happened when we re-cached every live entity in a
    Wikibase instance from scratch.
    """

    cache_dir: str
    api_url: str
    api_url_source: str
    run_mode: str
    started_at: str
    completed_at: str
    duration_seconds: float
    discovered_ids: list[str] = field(default_factory=list)
    hydrated_ids: list[str] = field(default_factory=list)
    tombstone_ids: list[str] = field(default_factory=list)
    redirect_ids: list[str] = field(default_factory=list)
    failed_ids: list[str] = field(default_factory=list)
    batch_size_requested: int = 500
    batch_size_effective: int = 500
    batch_fallback_count: int = 0
    batch_fallback_first_error: Optional[str] = None


@dataclass(frozen=True)
class URLFetchResult:
    """Result envelope for generic URL retrieval checks."""

    url: str
    ok: bool
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    content_type: Optional[str] = None
    response_size: Optional[int] = None
    error: Optional[str] = None


def _resolve_wikibase_entity_namespace_specs(
    api_client: WikibaseApiClient,
) -> dict[str, tuple[int, str]]:
    """Resolve Wikibase item/property namespaces from MediaWiki siteinfo.

    Returns a mapping like ``{"item": (120, "Item:"), "property": (122, "Property:")}``
    when the instance uses dedicated content namespaces, or ``{"item": (0, "")}``
    for Wikibase installations that store items in the main namespace.
    """

    payload = api_client.request(
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "meta": "siteinfo",
            "siprop": "namespaces|namespacealiases",
        }
    )
    query = payload.get("query", {})
    raw_namespaces = query.get("namespaces", [])
    if not isinstance(raw_namespaces, list):
        raise RuntimeError("Wikibase siteinfo response did not include namespaces")

    specs: dict[str, tuple[int, str]] = {}
    for namespace in raw_namespaces:
        if not isinstance(namespace, dict):
            continue
        namespace_id = namespace.get("id")
        if not isinstance(namespace_id, int):
            continue

        content_model = namespace.get("defaultcontentmodel")
        if content_model == "wikibase-item":
            namespace_name = namespace.get("name")
            prefix = f"{namespace_name}:" if namespace_name else ""
            specs["item"] = (namespace_id, prefix)
        elif content_model == "wikibase-property":
            namespace_name = namespace.get("name")
            prefix = f"{namespace_name}:" if namespace_name else ""
            specs["property"] = (namespace_id, prefix)

    missing = [
        entity_type for entity_type in ("item", "property") if entity_type not in specs
    ]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise RuntimeError(
            f"Wikibase siteinfo did not expose namespaces for: {missing_text}"
        )

    return specs


@dataclass(frozen=True)
class CommonsFileInfoResult:
    """Result envelope for Wikimedia Commons file existence and metadata checks.

    Parallels URLFetchResult for consistent result handling in validation workflows.

    Attributes:
        filename: Canonical Commons filename with ``File:`` prefix.
        ok: Whether the API request completed without error.
        exists: Whether the file exists on Wikimedia Commons.
        page_url: URL of the file description page on Commons.
        resource_url: Direct URL of the media resource itself.
        mime_type: MIME type reported by Commons (e.g., ``image/jpeg``).
        size: File size in bytes.
        width: Image width in pixels (images only).
        height: Image height in pixels (images only).
        sha1: SHA-1 hash of the file content.
        error: Error message if the fetch failed or the file was not found.
    """

    filename: str
    ok: bool
    exists: bool = False
    page_url: Optional[str] = None
    resource_url: Optional[str] = None
    mime_type: Optional[str] = None
    size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    sha1: Optional[str] = None
    error: Optional[str] = None


def fetch_commons_file_info(
    api_client: WikibaseApiClient,
    filename: str,
    *,
    mode: str = "heartbeat",
) -> CommonsFileInfoResult:
    """Fetch file existence and metadata from the Wikimedia Commons MediaWiki API.

    Accepts a Commons filename with or without the ``File:`` prefix.  The canonical
    form (with prefix) is always stored in the result.

    Args:
        api_client: Configured client pointing at the Commons API endpoint.
            Typically ``WikibaseApiClient(api_url="https://commons.wikimedia.org/w/api.php")``.
        filename: Commons filename, e.g. ``File:Example.jpg`` or ``Example.jpg``.
        mode: ``"heartbeat"`` checks file existence only; ``"actionable"`` retrieves
            full imageinfo (URL, MIME type, size, SHA-1).

    Returns:
        CommonsFileInfoResult with existence flag and, for ACTIONABLE mode, full
        file metadata.
    """
    canonical = filename if filename.startswith("File:") else f"File:{filename}"

    iiprop = "url|mime|size|sha1" if mode == "actionable" else "url"
    params: dict[str, Any] = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        "prop": "imageinfo",
        "iiprop": iiprop,
        "titles": canonical,
    }

    try:
        payload = api_client.request(params)
    except RuntimeError as exc:
        return CommonsFileInfoResult(filename=canonical, ok=False, error=str(exc))

    pages = payload.get("query", {}).get("pages", [])
    if not isinstance(pages, list) or not pages:
        return CommonsFileInfoResult(
            filename=canonical,
            ok=True,
            exists=False,
            error=f"File not found on Commons: {canonical}",
        )

    page = pages[0]
    if not isinstance(page, dict) or page.get("missing"):
        return CommonsFileInfoResult(
            filename=canonical,
            ok=True,
            exists=False,
            error=f"File not found on Commons: {canonical}",
        )

    imageinfo_list = page.get("imageinfo", [])
    if not isinstance(imageinfo_list, list) or not imageinfo_list:
        return CommonsFileInfoResult(filename=canonical, ok=True, exists=True)

    info = imageinfo_list[0] if isinstance(imageinfo_list[0], dict) else {}
    return CommonsFileInfoResult(
        filename=canonical,
        ok=True,
        exists=True,
        page_url=f"https://commons.wikimedia.org/wiki/{canonical.replace(' ', '_')}",
        resource_url=info.get("url"),
        mime_type=info.get("mime") if mode == "actionable" else None,
        size=info.get("size") if mode == "actionable" else None,
        width=info.get("width") if mode == "actionable" else None,
        height=info.get("height") if mode == "actionable" else None,
        sha1=info.get("sha1") if mode == "actionable" else None,
    )


def fetch_url_resource(
    url: str,
    *,
    mode: str = "head",
    timeout: int = 10,
    allow_redirects: bool = True,
    accept: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> URLFetchResult:
    """Fetch URL metadata or content for policy-driven online validation workflows.

    Args:
        url: Absolute URL to retrieve.
        mode: ``head`` for HEARTBEAT checks or ``get`` for ACTIONABLE checks.
        timeout: Request timeout in seconds.
        allow_redirects: Whether redirects should be followed.
        accept: Optional Accept header for content negotiation.
        session: Optional requests session. New session is created when omitted.

    Returns:
        URLFetchResult with status, content type, and retrieval metadata.
    """
    request_mode = mode.lower().strip()
    if request_mode not in {"head", "get"}:
        return URLFetchResult(
            url=url,
            ok=False,
            error=f"Unsupported fetch mode: {mode}",
        )

    client = session or requests.Session()
    headers: dict[str, str] = {}
    if accept:
        headers["Accept"] = accept

    try:
        response = client.request(
            request_mode,
            url,
            timeout=timeout,
            allow_redirects=allow_redirects,
            headers=headers or None,
        )
    except requests.RequestException as exc:
        return URLFetchResult(
            url=url,
            ok=False,
            error=str(exc),
        )

    content_type = response.headers.get("Content-Type")
    body_size: Optional[int] = None
    if request_mode == "get":
        try:
            body_size = len(response.content)
        except Exception:
            body_size = None

    return URLFetchResult(
        url=url,
        ok=response.ok,
        status_code=response.status_code,
        final_url=str(response.url) if response.url else None,
        content_type=content_type,
        response_size=body_size,
        error=None if response.ok else f"HTTP {response.status_code}",
    )


_ENTITY_ID_PATTERN = re.compile(r"\b([QP]\d+)\b")
_SPARQL_BLOCK_PATTERN = re.compile(
    r"<\s*sparql(?:\s+[^>]*)?>(.*?)</\s*sparql\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)


def fetch_mediawiki_page_wikitext(api_client: WikibaseApiClient, title: str) -> str:
    """Fetch page wikitext from a MediaWiki API endpoint.

    Args:
        api_client: Configured Wikibase/MediaWiki API client.
        title: Full page title (for example, ``Item_talk:Q4``).

    Returns:
        Page wikitext as a string.

    Raises:
        RuntimeError: If page content is missing or cannot be parsed.
    """
    payload = api_client.request(
        {
            "action": "query",
            "format": "json",
            "formatversion": 2,
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": title,
        }
    )

    pages = payload.get("query", {}).get("pages", [])
    if not isinstance(pages, list) or not pages:
        raise RuntimeError(f"MediaWiki page '{title}' not found")

    page = pages[0]
    if not isinstance(page, dict) or page.get("missing"):
        raise RuntimeError(f"MediaWiki page '{title}' not found")

    revisions = page.get("revisions", [])
    if not isinstance(revisions, list) or not revisions:
        raise RuntimeError(f"No revision content found for page '{title}'")

    revision = revisions[0]
    if not isinstance(revision, dict):
        raise RuntimeError(f"Invalid revision payload for page '{title}'")

    slots = revision.get("slots", {})
    main_slot = slots.get("main") if isinstance(slots, dict) else None
    if isinstance(main_slot, dict):
        content = main_slot.get("content")
        if isinstance(content, str):
            return content

    # Backward compatibility for installations using legacy '*' content key.
    content = revision.get("*")
    if isinstance(content, str):
        return content

    raise RuntimeError(f"No wikitext content found for page '{title}'")


def extract_sparql_blocks(wikitext: str) -> list[str]:
    """Extract SPARQL blocks from wikitext in source order."""
    blocks: list[str] = []
    for match in _SPARQL_BLOCK_PATTERN.findall(wikitext):
        snippet = match.strip()
        if snippet:
            blocks.append(snippet)
    return blocks


def extract_first_sparql_block(wikitext: str) -> str:
    """Return the first SPARQL block from wikitext.

    Raises:
        RuntimeError: If no ``<sparql>...</sparql>`` block exists.
    """
    blocks = extract_sparql_blocks(wikitext)
    if not blocks:
        raise RuntimeError("No <sparql> block found in page content")
    return blocks[0]


def get_latest_cache_timestamp(cache_dir: str | Path) -> Optional[str]:
    """Return the latest timestamp represented in current cache artifacts.

    Prefers entity.modified when present, falling back to cache-export metadata.
    """
    cache_path = Path(cache_dir)
    latest: Optional[datetime] = None

    if not cache_path.exists():
        return None

    for json_file in cache_path.glob("*.json"):
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            continue

        entity = payload.get("entity", payload)
        metadata = payload.get("metadata", {})
        candidates = [
            entity.get("modified") if isinstance(entity, dict) else None,
            metadata.get("cache_exported_at") if isinstance(metadata, dict) else None,
            metadata.get("graph_fetched_at") if isinstance(metadata, dict) else None,
        ]
        for candidate in candidates:
            parsed = _parse_iso8601(candidate)
            if parsed and (latest is None or parsed > latest):
                latest = parsed

    if latest is None:
        return None
    return latest.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_recent_entity_changes(
    api_client: WikibaseApiClient,
    *,
    since: str,
    overlap_seconds: int = 60,
    ignore_ids: Optional[set[str]] = None,
    limit: int = 500,
) -> WikibaseRecentChangesResult:
    """Poll MediaWiki recentchanges and return changed Wikibase entity IDs."""
    ignore_set = set(ignore_ids or set())
    effective_since = _apply_overlap_window(since, overlap_seconds)
    params: dict[str, Any] = {
        "action": "query",
        "format": "json",
        "list": "recentchanges",
        "rcdir": "newer",
        "rcstart": effective_since,
        "rclimit": min(limit, 500),
        "rcprop": "title|timestamp|ids|loginfo",
    }

    recentchanges: list[dict[str, Any]] = []
    changed_ids: set[str] = set()
    ignored_hits: set[str] = set()

    while True:
        payload = api_client.request(params)
        batch = payload.get("query", {}).get("recentchanges", [])
        if not isinstance(batch, list):
            batch = []

        for change in batch:
            if not isinstance(change, dict):
                continue
            recentchanges.append(change)
            entity_id = _extract_entity_id_from_recentchange(change)
            if not entity_id:
                continue
            if entity_id in ignore_set:
                ignored_hits.add(entity_id)
                continue
            changed_ids.add(entity_id)

        continuation = payload.get("continue", {})
        rccontinue = (
            continuation.get("rccontinue") if isinstance(continuation, dict) else None
        )
        if not rccontinue:
            break
        params["rccontinue"] = rccontinue

    next_since = since
    for change in recentchanges:
        if not isinstance(change, dict):
            continue
        timestamp = change.get("timestamp")
        parsed = _parse_iso8601(timestamp)
        current = _parse_iso8601(next_since)
        if parsed and current and parsed > current:
            next_since = (
                parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            )

    return WikibaseRecentChangesResult(
        since=effective_since,
        next_since=next_since,
        changed_ids=sorted(changed_ids),
        ignored_ids=sorted(ignored_hits),
        recentchanges=recentchanges,
    )


def refresh_entity_cache_from_recentchanges(
    api_client: WikibaseApiClient,
    cache_dir: str | Path,
    *,
    since: Optional[str] = None,
    overlap_seconds: int = 60,
    ignore_ids: Optional[set[str]] = None,
    source_endpoint: Optional[str] = None,
    workflow_mode: str = "recentchanges",
    batch_size: int = 50,
) -> WikibaseCacheRefreshResult:
    """Refresh per-entity cache files from MediaWiki recentchanges."""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    resolved_since = since or get_latest_cache_timestamp(cache_path)
    if not resolved_since:
        raise RuntimeError(
            "No cache watermark available; provide --since or seed the cache first"
        )

    recent_result = fetch_recent_entity_changes(
        api_client,
        since=resolved_since,
        overlap_seconds=overlap_seconds,
        ignore_ids=ignore_ids,
    )

    source_repo_path = Path(__file__).resolve().parents[2]
    source_branch, source_commit = _get_git_context(source_repo_path)
    extractor_version = _get_installed_gkc_version()
    refreshed_ids: list[str] = []
    deleted_ids: list[str] = []
    missing_ids: list[str] = []
    refreshed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    for entity_chunk in _chunked(recent_result.changed_ids, batch_size):
        payload = api_client.request(
            {
                "action": "wbgetentities",
                "format": "json",
                "ids": "|".join(entity_chunk),
            }
        )
        entities = payload.get("entities", {})
        if not isinstance(entities, dict):
            entities = {}

        for entity_id in entity_chunk:
            entity_data = entities.get(entity_id)
            out_file = cache_path / f"{entity_id}.json"

            if not isinstance(entity_data, dict) or "missing" in entity_data:
                missing_ids.append(entity_id)
                if out_file.exists():
                    out_file.unlink()
                    deleted_ids.append(entity_id)
                continue

            payload_doc = _build_entity_cache_payload(
                entity_id=entity_id,
                entity_data=entity_data,
                source_endpoint=source_endpoint or api_client.api_url,
                workflow_mode=workflow_mode,
                profile_entry_ids=[],
                graph_fetched_at=entity_data.get("modified") or refreshed_at,
                cache_exported_at=refreshed_at,
                extractor="gkc.mash.refresh_entity_cache_from_recentchanges",
                extractor_version=extractor_version,
                source_branch=source_branch,
                source_commit=source_commit,
            )
            out_file.write_text(json.dumps(payload_doc, indent=2), encoding="utf-8")
            refreshed_ids.append(entity_id)

    return WikibaseCacheRefreshResult(
        cache_dir=str(cache_path.resolve()),
        since=recent_result.since,
        next_since=recent_result.next_since,
        changed_ids=recent_result.changed_ids,
        ignored_ids=recent_result.ignored_ids,
        refreshed_ids=refreshed_ids,
        deleted_ids=deleted_ids,
        missing_ids=missing_ids,
    )


def discover_wikibase_entity_ids(
    api_client: WikibaseApiClient,
    *,
    include_items: bool = True,
    include_properties: bool = True,
) -> list[str]:
    """Discover all entity IDs from a Wikibase instance using the allpages API.

    Uses MediaWiki ``list=allpages`` with namespace filtering to enumerate all
    non-redirect entity pages. Namespace ids and title prefixes are resolved
    from MediaWiki ``siteinfo`` so discovery works on Wikibase instances with
    custom item/property namespaces.

    Redirect pages are excluded via ``apfilteredir=nonredirects``.

    Args:
        api_client: Configured Wikibase API client.
        include_items: Include Q-entity items (namespace 0).
        include_properties: Include P-entity properties (namespace 120).

    Returns:
        Sorted list of discovered entity IDs (e.g. ``["P1", "Q1", "Q42", ...]``).

    Plain meaning: Enumerate every live entity ID so full-sync knows exactly
    what to fetch.
    """
    entity_ids: set[str] = set()
    namespace_specs = _resolve_wikibase_entity_namespace_specs(api_client)
    patterns: dict[str, re.Pattern[str]] = {
        "item": re.compile(r"^Q[1-9]\d*$"),
        "property": re.compile(r"^P[1-9]\d*$"),
    }

    namespaces: list[tuple[str, int, str]] = []
    if include_items:
        item_namespace, item_prefix = namespace_specs["item"]
        namespaces.append(("item", item_namespace, item_prefix))
    if include_properties:
        property_namespace, property_prefix = namespace_specs["property"]
        namespaces.append(("property", property_namespace, property_prefix))

    for entity_type, namespace_id, prefix in namespaces:
        params: dict[str, Any] = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "list": "allpages",
            "apnamespace": str(namespace_id),
            "apfilteredir": "nonredirects",
            "aplimit": "500",
        }
        while True:
            payload = api_client.request(params)
            pages = payload.get("query", {}).get("allpages", [])
            if not isinstance(pages, list):
                break
            for page in pages:
                if not isinstance(page, dict):
                    continue
                title = page.get("title", "")
                if not isinstance(title, str):
                    continue
                entity_id = title[len(prefix) :].strip() if prefix else title.strip()
                pattern = patterns[entity_type]
                if entity_id and pattern and pattern.fullmatch(entity_id):
                    entity_ids.add(entity_id)
            continuation = payload.get("continue")
            if not isinstance(continuation, dict):
                break
            apcontinue = continuation.get("apcontinue")
            if not apcontinue:
                break
            params["apcontinue"] = apcontinue

    return sorted(entity_ids)


def full_sync_wikibase_entity_cache(
    api_client: WikibaseApiClient,
    cache_dir: str | Path,
    *,
    auth: Optional[Any] = None,
    include_items: bool = True,
    include_properties: bool = True,
    ignore_ids: Optional[set[str]] = None,
    batch_size: Optional[int] = None,
    source_endpoint: Optional[str] = None,
    api_url_source: str = "default",
) -> WikibaseFullSyncResult:
    """Perform a full-sync baseline of all entity cache files from a Wikibase instance.

    Discovers every live entity via the allpages API, then fetches and re-writes
    cache artifacts for each one.  Redirects and tombstoned IDs are silently
    ignored per Data Distillery design policy.

    Batch size is auto-selected based on ``auth.has_api_high_limits()`` (500
    when available, 50 otherwise).  If a 500-item batch fails, the request is
    automatically retried in 50-item sub-batches and the fallback is recorded
    in the result diagnostics.

    Args:
        api_client: Configured Wikibase API client pointed at the target instance.
        cache_dir: Directory to write per-entity cache JSON files.
        auth: Optional authenticated session (``WikiverseAuth``) used for
            capability detection.  When omitted, batch size defaults to 50.
        include_items: Sync Q-entity items.
        include_properties: Sync P-entity properties.
        ignore_ids: Entity IDs to exclude from cache writes (e.g. housekeeping
            placeholder items).
        batch_size: Override auto-detected batch size.  Ignored when ``auth``
            provides a valid capability signal.
        source_endpoint: Source endpoint label stored in cache metadata.
            Defaults to ``api_client.api_url``.
        api_url_source: Human-readable label for how the API URL was resolved
            (``"explicit"``, ``"env"``, or ``"default"``).  Stored in metadata.

    Returns:
        :class:`WikibaseFullSyncResult` with full run diagnostics.

    Plain meaning: Re-cache every live entity from scratch — the authoritative
    bootstrap/rebuild operation for the SpiritSafe entity cache.
    """
    started_dt = datetime.now(timezone.utc)
    started_at = started_dt.isoformat().replace("+00:00", "Z")
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    ignore_set = set(ignore_ids or set())

    # Resolve effective batch size
    if batch_size is not None:
        effective_batch_size = max(1, batch_size)
    elif auth is not None and callable(getattr(auth, "has_api_high_limits", None)):
        try:
            effective_batch_size = 500 if auth.has_api_high_limits() else 50
        except Exception:
            effective_batch_size = 50
    else:
        effective_batch_size = 50

    batch_size_requested = effective_batch_size

    # Collect provenance metadata
    source_repo_path = Path(__file__).resolve().parents[2]
    source_branch, source_commit = _get_git_context(source_repo_path)
    extractor_version = _get_installed_gkc_version()
    synced_at = started_at

    # Discover all entity IDs
    discovered_ids = discover_wikibase_entity_ids(
        api_client,
        include_items=include_items,
        include_properties=include_properties,
    )

    # Filter ignored IDs from candidates
    candidate_ids = [eid for eid in discovered_ids if eid not in ignore_set]

    hydrated_ids: list[str] = []
    tombstone_ids: list[str] = []
    redirect_ids: list[str] = []
    failed_ids: list[str] = []
    batch_fallback_count = 0
    batch_fallback_first_error: Optional[str] = None

    for chunk in _chunked(candidate_ids, effective_batch_size):
        entities_raw: dict[str, Any] = {}
        chunk_failed: set[str] = set()

        try:
            payload = api_client.request(
                {
                    "action": "wbgetentities",
                    "format": "json",
                    "ids": "|".join(chunk),
                }
            )
            raw = payload.get("entities", {})
            entities_raw = raw if isinstance(raw, dict) else {}
        except RuntimeError as exc:
            if effective_batch_size <= 50:
                # Already at fallback size; mark whole chunk as failed
                failed_ids.extend(chunk)
                continue

            # Fallback: retry this chunk in 50-item sub-batches
            batch_fallback_count += 1
            if batch_fallback_first_error is None:
                batch_fallback_first_error = str(exc)

            for sub_chunk in _chunked(chunk, 50):
                try:
                    sub_payload = api_client.request(
                        {
                            "action": "wbgetentities",
                            "format": "json",
                            "ids": "|".join(sub_chunk),
                        }
                    )
                    sub_raw = sub_payload.get("entities", {})
                    if isinstance(sub_raw, dict):
                        entities_raw.update(sub_raw)
                except RuntimeError:
                    for eid in sub_chunk:
                        chunk_failed.add(eid)

        for entity_id in chunk:
            if entity_id in chunk_failed:
                failed_ids.append(entity_id)
                continue

            entity_data = entities_raw.get(entity_id)

            if not isinstance(entity_data, dict) or "missing" in entity_data:
                tombstone_ids.append(entity_id)
                continue

            if "redirects" in entity_data:
                redirect_ids.append(entity_id)
                continue

            payload_doc = _build_entity_cache_payload(
                entity_id=entity_id,
                entity_data=entity_data,
                source_endpoint=source_endpoint or api_client.api_url,
                workflow_mode="full_sync_baseline",
                profile_entry_ids=[],
                graph_fetched_at=entity_data.get("modified") or synced_at,
                cache_exported_at=synced_at,
                extractor="gkc.mash.full_sync_wikibase_entity_cache",
                extractor_version=extractor_version,
                source_branch=source_branch,
                source_commit=source_commit,
            )
            out_file = cache_path / f"{entity_id}.json"
            out_file.write_text(json.dumps(payload_doc, indent=2), encoding="utf-8")
            hydrated_ids.append(entity_id)

    completed_dt = datetime.now(timezone.utc)
    completed_at = completed_dt.isoformat().replace("+00:00", "Z")
    duration_seconds = (completed_dt - started_dt).total_seconds()

    return WikibaseFullSyncResult(
        cache_dir=str(cache_path.resolve()),
        api_url=api_client.api_url,
        api_url_source=api_url_source,
        run_mode="full_sync_baseline",
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration_seconds,
        discovered_ids=discovered_ids,
        hydrated_ids=sorted(hydrated_ids),
        tombstone_ids=sorted(tombstone_ids),
        redirect_ids=sorted(redirect_ids),
        failed_ids=sorted(failed_ids),
        batch_size_requested=batch_size_requested,
        batch_size_effective=effective_batch_size,
        batch_fallback_count=batch_fallback_count,
        batch_fallback_first_error=batch_fallback_first_error,
    )


def _build_entity_cache_payload(
    *,
    entity_id: str,
    entity_data: dict[str, Any],
    source_endpoint: str,
    workflow_mode: str,
    profile_entry_ids: list[str],
    graph_fetched_at: str,
    cache_exported_at: str,
    extractor: str,
    extractor_version: str,
    source_branch: Optional[str],
    source_commit: Optional[str],
) -> dict[str, Any]:
    """Build a normalized entity cache payload document."""
    return {
        "entity_id": entity_id,
        "entity": entity_data,
        "metadata": {
            "source_endpoint": source_endpoint,
            "workflow_mode": workflow_mode,
            "profile_entry_ids": list(profile_entry_ids),
            "graph_fetched_at": graph_fetched_at,
            "cache_exported_at": cache_exported_at,
            "extractor": extractor,
            "extractor_version": extractor_version,
            "source_branch": source_branch,
            "source_commit": source_commit,
        },
    }


def _extract_entity_id_from_recentchange(change: dict[str, Any]) -> Optional[str]:
    """Extract a Q/P entity ID from recentchanges row data when present."""
    title = change.get("title")
    if isinstance(title, str):
        match = _ENTITY_ID_PATTERN.search(title)
        if match:
            return match.group(1)

    logparams = change.get("logparams")
    if isinstance(logparams, dict):
        for value in logparams.values():
            if isinstance(value, str):
                match = _ENTITY_ID_PATTERN.search(value)
                if match:
                    return match.group(1)

    return None


def _apply_overlap_window(timestamp: str, overlap_seconds: int) -> str:
    """Shift a timestamp backward by overlap window for safe polling."""
    parsed = _parse_iso8601(timestamp)
    if parsed is None:
        raise RuntimeError(f"Invalid timestamp: {timestamp}")
    adjusted = parsed - timedelta(seconds=max(overlap_seconds, 0))
    return adjusted.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso8601(timestamp: object) -> Optional[datetime]:
    """Parse ISO 8601 timestamps used by Wikibase and cache metadata."""
    if not isinstance(timestamp, str) or not timestamp:
        return None
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def _chunked(values: list[str], size: int) -> list[list[str]]:
    """Split a list into fixed-size chunks."""
    if size <= 0:
        raise RuntimeError("batch size must be positive")
    return [values[index : index + size] for index in range(0, len(values), size)]


def _get_git_context(repo_path: Path) -> tuple[Optional[str], Optional[str]]:
    """Return git branch and commit for a repository path when available."""
    try:
        branch_result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        commit_result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return branch_result.stdout.strip(), commit_result.stdout.strip()
    except Exception:
        return None, None


def _get_installed_gkc_version() -> str:
    """Return installed package version when available."""
    try:
        return importlib_metadata.version("gkc")
    except Exception:
        return "unknown"


class DataTemplate(Protocol):
    """Abstract interface for all data templates in the mash module.

    All template types (Wikidata, CSV, JSON, etc.) should implement this
    protocol to ensure consistent behavior across different data sources.

    This protocol defines the minimum interface that templates must provide:
    - summary(): Return a dict with basic metadata about the template
    - to_dict(): Serialize the template to a dictionary

    Future template implementations should follow this pattern to ensure
    compatibility with formatters and other downstream components.

    Plain meaning: The blueprint that all data templates must follow.
    """

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Plain meaning: Get a quick overview without full details.
        """
        ...

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Plain meaning: Return the original entity JSON for round-trip safety.
        """
        ...


def fetch_property_labels(
    property_ids: list[str], language: Optional[str] = None
) -> dict[str, str]:
    """Fetch human-readable labels for Wikidata properties using SPARQL.

    Args:
        property_ids: List of property IDs (e.g., ['P31', 'P21']).
        language: Language code for labels (defaults to package configuration).

    Returns:
        Dict mapping property IDs to their labels (e.g., {'P31': 'instance of'}).

    Plain meaning: Look up property names efficiently to make QS output more readable.
    """
    if not property_ids:
        return {}
    if language is None:
        import gkc

        languages = gkc.get_languages()
        if languages == "all":
            language = "en"
        elif isinstance(languages, str):
            language = languages
        else:
            language = languages[0] if languages else "en"
    return fetch_entity_labels(property_ids, languages=[language])


def strip_entity_identifiers(entity_data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of entity data with identifiers stripped for new-item use.

    Removes fields that prevent using the JSON as a new item template:
    - Item-level: id, pageid, lastrevid, modified, ns, title
    - Statement-level: id (statement GUID)
    - Snak-level: hash (in mainsnak, qualifiers, and references)

    Plain meaning: Remove IDs that prevent using the JSON as a new item template.
    """

    cleaned = copy.deepcopy(entity_data)

    # Remove item-level identifiers and metadata
    cleaned.pop("id", None)
    cleaned.pop("pageid", None)
    cleaned.pop("lastrevid", None)
    cleaned.pop("modified", None)
    cleaned.pop("ns", None)
    cleaned.pop("title", None)

    # Remove statement-level identifiers and hashes
    claims = cleaned.get("claims")
    if isinstance(claims, dict):
        for statements in claims.values():
            if not isinstance(statements, list):
                continue
            for statement in statements:
                if isinstance(statement, dict):
                    statement.pop("id", None)

                    # Remove hash from mainsnak
                    mainsnak = statement.get("mainsnak")
                    if isinstance(mainsnak, dict):
                        mainsnak.pop("hash", None)

                    # Remove hash from qualifiers
                    qualifiers = statement.get("qualifiers")
                    if isinstance(qualifiers, dict):
                        for qualifier_snaks in qualifiers.values():
                            if isinstance(qualifier_snaks, list):
                                for snak in qualifier_snaks:
                                    if isinstance(snak, dict):
                                        snak.pop("hash", None)

                    # Remove hash from references
                    references = statement.get("references")
                    if isinstance(references, list):
                        for reference in references:
                            if isinstance(reference, dict):
                                reference.pop("hash", None)
                                ref_snaks = reference.get("snaks")
                                if isinstance(ref_snaks, dict):
                                    for ref_snak_list in ref_snaks.values():
                                        if isinstance(ref_snak_list, list):
                                            for snak in ref_snak_list:
                                                if isinstance(snak, dict):
                                                    snak.pop("hash", None)

    return cleaned


@dataclass
class ClaimSummary:
    """Simplified representation of a Wikidata claim for display and export.

    Plain meaning: A simple view of a claim without requiring RDF knowledge.
    """

    property_id: str
    value: str
    qualifiers: list[dict] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)
    rank: str = "normal"
    value_metadata: Optional[dict[str, Any]] = None


@dataclass
class WikibaseItemTemplate:
    """An extracted Wikidata item ready for filtering and export.

    This is the Wikidata-specific implementation of the DataTemplate protocol.

    Plain meaning: A loaded Wikidata item template ready for modification.
    """

    qid: str
    labels: dict[str, str]
    descriptions: dict[str, str]
    aliases: dict[str, list[str]]
    claims: list[ClaimSummary]
    entity_data: dict[str, Any]

    def filter_qualifiers(self) -> None:
        """Remove all qualifiers from claims in-place.

        Plain meaning: Strip qualifier detail from claims.
        """

        for claim in self.claims:
            claim.qualifiers = []

        claims = self.entity_data.get("claims")
        if isinstance(claims, dict):
            for statements in claims.values():
                if not isinstance(statements, list):
                    continue
                for statement in statements:
                    if isinstance(statement, dict):
                        statement.pop("qualifiers", None)
                        statement.pop("qualifiers-order", None)

    def filter_references(self) -> None:
        """Remove all references from claims in-place.

        Plain meaning: Strip reference detail from claims.
        """

        for claim in self.claims:
            claim.references = []

        claims = self.entity_data.get("claims")
        if isinstance(claims, dict):
            for statements in claims.values():
                if not isinstance(statements, list):
                    continue
                for statement in statements:
                    if isinstance(statement, dict):
                        statement.pop("references", None)

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Plain meaning: Get a quick overview without full details.
        """

        return {
            "qid": self.qid,
            "labels": self.labels,
            "descriptions": self.descriptions,
            "total_statements": len(self.claims),
            "aliases": self.aliases,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Plain meaning: Convert to a form suitable for JSON export.
        """

        return copy.deepcopy(self.entity_data)

    def to_simple_dict(self) -> dict[str, Any]:
        """Serialize to a simplified dictionary.

        Plain meaning: Convert to a compact summary structure.
        """

        return {
            "qid": self.qid,
            "labels": self.labels,
            "descriptions": self.descriptions,
            "aliases": self.aliases,
            "claims": [
                {
                    "property_id": c.property_id,
                    "value": c.value,
                    "qualifiers": c.qualifiers,
                    "references": c.references,
                    "rank": c.rank,
                }
                for c in self.claims
            ],
        }

    def to_shell(self) -> dict[str, Any]:
        """Strip identifiers and metadata to create a shell for new item creation.

        Returns entity data with all system IDs, metadata, and hashes removed,
        suitable for use as a template for creating new items.

        Returns:
            Dict with identifiers stripped, ready for new item creation.

        Plain meaning: Prepare this template as a clean shell for a new item.
        """
        return strip_entity_identifiers(self.entity_data)

    def to_qsv1(
        self, for_new_item: bool = False, entity_labels: Optional[dict[str, str]] = None
    ) -> str:
        """Convert to QuickStatements V1 format.

        Args:
            for_new_item: If True, use CREATE/LAST syntax for new items.
                         If False, use the item's QID for updates.
            entity_labels: Optional dict mapping entity IDs to labels for comments.

        Returns:
            QuickStatements V1 formatted string.

        Plain meaning: Export as QuickStatements commands for bulk operations.
        """
        from gkc.mash_formatters import QSV1Formatter

        formatter = QSV1Formatter(entity_labels=entity_labels or {})
        return formatter.format(self, for_new_item=for_new_item)

    def to_gkc_entity_profile(self) -> dict[str, Any]:
        """Convert to GKC Entity Profile format.

        Returns:
            Dict representing the GKC Entity Profile.

        Raises:
            NotImplementedError: This transformation is not yet implemented for items.

        Plain meaning: Transform into a GKC Entity Profile (not yet implemented).
        """
        raise NotImplementedError(
            "Item to GKC Entity Profile transformation is not yet implemented. "
            "This will be added in a future version."
        )


@dataclass
class WikibasePropertyTemplate:
    """An extracted Wikidata property ready for filtering and export.

    This is the property-specific implementation of the DataTemplate protocol.

    Plain meaning: A loaded Wikidata property template ready for modification.
    """

    pid: str
    labels: dict[str, str]
    descriptions: dict[str, str]
    aliases: dict[str, list[str]]
    datatype: Optional[str]
    formatter_url: Optional[str]
    entity_data: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Plain meaning: Get a quick overview without full details.
        """
        return {
            "pid": self.pid,
            "labels": self.labels,
            "descriptions": self.descriptions,
            "datatype": self.datatype,
            "formatter_url": self.formatter_url,
            "aliases": self.aliases,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Plain meaning: Convert to a form suitable for JSON export.
        """
        return copy.deepcopy(self.entity_data)

    def to_shell(self) -> dict[str, Any]:
        """Strip identifiers and metadata to create a shell for new property creation.

        Returns entity data with all system IDs, metadata, and hashes removed,
        suitable for use as a template for creating new properties.

        Returns:
            Dict with identifiers stripped, ready for new property creation.

        Plain meaning: Prepare this template as a clean shell for a new property.
        """
        return strip_entity_identifiers(self.entity_data)

    def to_gkc_entity_profile(self) -> dict[str, Any]:
        """Convert to GKC Entity Profile format.

        Returns:
            Dict representing the GKC Entity Profile.

        Raises:
            NotImplementedError: This transformation is not yet implemented
                for properties.

        Plain meaning: Transform into a GKC Entity Profile
            (not yet implemented).
        """
        raise NotImplementedError(
            "Property to GKC Entity Profile transformation is not yet implemented. "
            "This will be added in a future version."
        )


@dataclass
class WikibaseEntitySchemaTemplate:
    """An extracted Wikidata EntitySchema ready for filtering and export.

    This is the EntitySchema-specific implementation of the DataTemplate protocol.

    Plain meaning: A loaded Wikidata EntitySchema template ready for modification.
    """

    eid: str
    labels: dict[str, str]
    descriptions: dict[str, str]
    schema_text: str
    entity_data: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Plain meaning: Get a quick overview without full details.
        """
        return {
            "eid": self.eid,
            "labels": self.labels,
            "descriptions": self.descriptions,
            "schema_text_length": len(self.schema_text),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Plain meaning: Convert to a form suitable for JSON export.
        """
        return copy.deepcopy(self.entity_data)

    def to_shell(self) -> dict[str, Any]:
        """Strip identifiers and metadata for new EntitySchema creation.

        Returns entity data with all system IDs and metadata removed,
        suitable for use as a template for creating new EntitySchemas.

        Returns:
            Dict with identifiers stripped, ready for new EntitySchema creation.

        Plain meaning: Prepare this template as a clean shell for a new EntitySchema.
        """
        return strip_entity_identifiers(self.entity_data)

    def to_gkc_entity_profile(self) -> dict[str, Any]:
        """Convert to GKC Entity Profile format.

        Returns:
            Dict representing the GKC Entity Profile.

        Raises:
            NotImplementedError: EntitySchema to Entity Profile transformation
                is not yet supported. This functionality will be restored
                when the new Entity Profile architecture is finalized.

        Plain meaning: Transform into a GKC Entity Profile (not yet supported).
        """
        raise NotImplementedError(
            "EntitySchema to GKC Entity Profile transformation is not yet supported. "
            "This functionality will be restored when the new Entity Profile "
            "architecture is finalized."
        )


def _resolve_languages(
    languages: Optional[Union[str, list[str]]] = None,
) -> Optional[set[str]]:
    """Resolve language input to a normalized set or ``None`` for all languages."""
    import gkc

    resolved_languages = languages
    if resolved_languages is None:
        resolved_languages = gkc.get_languages()

    if resolved_languages == "all":
        return None

    if isinstance(resolved_languages, str):
        return {resolved_languages}

    return set(resolved_languages)


def apply_template_language_filter(
    template: Union[
        WikibaseItemTemplate,
        WikibasePropertyTemplate,
        WikibaseEntitySchemaTemplate,
    ],
    languages: Optional[Union[str, list[str]]] = None,
) -> None:
    """Apply language filtering to a mash template in-place.

    Plain meaning: Keep only the selected languages for labels/descriptions/aliases.
    """

    language_filter = _resolve_languages(languages)
    if language_filter is None:
        return

    template.labels = {
        key: value for key, value in template.labels.items() if key in language_filter
    }
    template.descriptions = {
        key: value
        for key, value in template.descriptions.items()
        if key in language_filter
    }

    if isinstance(template, (WikibaseItemTemplate, WikibasePropertyTemplate)):
        template.aliases = {
            key: value
            for key, value in template.aliases.items()
            if key in language_filter
        }

    labels = template.entity_data.get("labels")
    if isinstance(labels, dict):
        template.entity_data["labels"] = {
            key: value for key, value in labels.items() if key in language_filter
        }

    descriptions = template.entity_data.get("descriptions")
    if isinstance(descriptions, dict):
        template.entity_data["descriptions"] = {
            key: value for key, value in descriptions.items() if key in language_filter
        }

    if isinstance(template, (WikibaseItemTemplate, WikibasePropertyTemplate)):
        aliases = template.entity_data.get("aliases")
        if isinstance(aliases, dict):
            template.entity_data["aliases"] = {
                key: value for key, value in aliases.items() if key in language_filter
            }


def apply_item_property_filters(
    template: WikibaseItemTemplate,
    include_properties: Optional[list[str]] = None,
    exclude_properties: Optional[list[str]] = None,
) -> None:
    """Apply item property include/exclude filtering in-place.

    Plain meaning: Keep selected properties first, then remove excluded properties.
    """

    if include_properties:
        include_set = set(include_properties)
        template.claims = [
            claim for claim in template.claims if claim.property_id in include_set
        ]
        claims = template.entity_data.get("claims")
        if isinstance(claims, dict):
            template.entity_data["claims"] = {
                prop_id: statements
                for prop_id, statements in claims.items()
                if prop_id in include_set
            }

    if exclude_properties:
        exclude_set = set(exclude_properties)
        template.claims = [
            claim for claim in template.claims if claim.property_id not in exclude_set
        ]
        claims = template.entity_data.get("claims")
        if isinstance(claims, dict):
            template.entity_data["claims"] = {
                prop_id: statements
                for prop_id, statements in claims.items()
                if prop_id not in exclude_set
            }


def fetch_entity_schema_json(
    eid: str, user_agent: Optional[str] = None
) -> dict[str, Any]:
    """
    Fetch the JSON content for a Wikidata EntitySchema.

    Uses the MediaWiki raw action endpoint to retrieve the full EntitySchema
    JSON, which includes labels, descriptions, aliases, and schemaText.

    Args:
        eid: EntitySchema ID (e.g., 'E502')
        user_agent: Custom user agent string

    Returns:
        Parsed JSON dictionary for the EntitySchema

    Raises:
        RuntimeError: If fetch or parsing fails

    Plain meaning: Retrieve an EntitySchema JSON document from Wikibase.
    """
    if not eid:
        raise ValueError("EntitySchema ID (eid) is required")

    url = f"https://www.wikidata.org/wiki/EntitySchema:{eid}?action=raw"
    headers = {"User-Agent": user_agent or DEFAULT_USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected EntitySchema JSON content for {eid}")
        return data
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to fetch EntitySchema JSON for {eid} from {url}: {str(exc)}"
        ) from exc
    except ValueError as exc:
        raise RuntimeError(
            f"Failed to parse EntitySchema JSON for {eid}: {str(exc)}"
        ) from exc


def fetch_entity_schema_specification(
    eid: str, user_agent: Optional[str] = None
) -> str:
    """
    Fetch Wikidata EntitySchema specification text (ShExC format).

    Retrieves a Wikidata EntitySchema's schemaText from the raw action endpoint.
    EntitySchemas define the shape and structure constraints that form part of
    Wikibase's validation schema (along with property constraints).

    Args:
        eid: EntitySchema ID (e.g., 'E502')
        user_agent: Custom user agent string

    Returns:
        ShExC schema text as string

    Raises:
        RuntimeError: If fetch fails

    Plain meaning: Get the shape/structure specification for a Wikibase entity type.

    Example:
        >>> schema = fetch_entity_schema_specification('E502')  # Schema for tribes
    """
    if not eid:
        raise ValueError("EntitySchema ID (eid) is required")

    # Prefer the EntitySchema JSON content (action=raw), which includes schemaText
    try:
        schema_json = fetch_entity_schema_json(eid, user_agent=user_agent)
        schema_text = schema_json.get("schemaText")
        if isinstance(schema_text, str) and schema_text.strip():
            return schema_text
    except RuntimeError:
        # Fall back to the Special:EntitySchemaText endpoint
        pass

    url = f"https://www.wikidata.org/wiki/Special:EntitySchemaText/{eid}"
    headers = {"User-Agent": user_agent or DEFAULT_USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to fetch EntitySchema {eid} from {url}: {str(exc)}"
        ) from exc


def fetch_entity_rdf(
    qid: str, format: str = "ttl", user_agent: Optional[str] = None
) -> str:
    """
    Fetch RDF data for a Wikidata entity.

    Retrieves entity data in RDF format using Wikibase's Special:EntityData endpoint,
    which supports multiple RDF serialization formats (Turtle, RDF/XML, N-Triples).

    Args:
        qid: Wikidata entity ID (e.g., 'Q42', 'P31')
        format: RDF format - 'ttl' (Turtle), 'rdf' (RDF/XML), 'nt' (N-Triples)
        user_agent: Custom user agent string

    Returns:
        RDF data as string

    Raises:
        RuntimeError: If fetch fails

    Plain meaning: Download entity data in RDF format.

    Example:
        >>> rdf = fetch_entity_rdf('Q42')  # Get Douglas Adams RDF
        >>> rdf = fetch_entity_rdf('P31', format='nt')  # Get property in N-Triples
    """
    if not qid:
        raise ValueError("Entity ID (qid) is required")

    # Validate format
    valid_formats = {"ttl", "rdf", "nt"}
    if format not in valid_formats:
        raise ValueError(f"Invalid format '{format}'. Must be one of: {valid_formats}")

    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.{format}"
    headers = {"User-Agent": user_agent or DEFAULT_USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to fetch RDF for {qid} from {url}: {str(exc)}"
        ) from exc


class WikibaseLoader:
    """Load a Wikidata item as a template for bulk modification.

    This is the Wikidata-specific implementation of a data loader.
    Future loaders for CSV, JSON APIs, etc. should follow a similar pattern.

    Plain meaning: Fetch and parse a Wikidata item into a usable template.
    """

    def __init__(
        self,
        user_agent: Optional[str] = None,
        api_url: str = "https://www.wikidata.org/w/api.php",
        api_client: Optional[WikibaseApiClient] = None,
        auth: Optional[Any] = None,
    ):
        """Initialize the loader.

        Args:
            user_agent: Custom user agent for Wikidata requests.
                       If not provided, a default GKC user agent is used.
            api_client: Optional pre-configured WikibaseApiClient.
            auth: Optional WikiverseAuth instance. When provided and the
                authenticated user has the ``apihighlimits`` right, batch
                requests are made in chunks of 500 instead of 50.
        """

        if user_agent is None:
            user_agent = DEFAULT_USER_AGENT

        self.user_agent = user_agent
        self.api_url = api_url
        self.api_client = api_client or WikibaseApiClient(
            api_url=api_url,
            user_agent=user_agent,
        )
        has_high_limits = (
            auth is not None
            and callable(getattr(auth, "has_api_high_limits", None))
            and auth.has_api_high_limits()
        )
        self.entity_batch_size: int = 500 if has_high_limits else 50

    def load_item(self, qid: str) -> WikibaseItemTemplate:
        """Load a Wikidata item and return it as a template.

        Args:
            qid: The Wikidata item ID (e.g., 'Q42').

        Returns:
            WikibaseItemTemplate with the item's structure.

        Raises:
            RuntimeError: If the item cannot be fetched or parsed.

        Plain meaning: Retrieve the item and return it ready for use.

        Example:
            >>> loader = WikibaseLoader()
            >>> template = loader.load_item("Q42")
            >>> print(template.summary())
        """

        entity_data = self.load_entity_data(qid)

        # Convert to MashTemplate
        template = self._build_template(qid, entity_data)

        return template

    def load(self, qid: str) -> WikibaseItemTemplate:
        """Load a Wikidata item and return it as a template.

        .. deprecated:: 1.0
            Use :meth:`load_item` instead. This method is maintained for
            backwards compatibility and will be removed in a future version.

        Args:
            qid: The Wikidata item ID (e.g., 'Q42').

        Returns:
            WikibaseItemTemplate with the item's structure.

        Plain meaning: Retrieve the item and return it ready for use.
        """
        return self.load_item(qid)

    def load_entities_raw(self, entity_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Load raw entity JSON in wbgetentities-sized batches.

        Uses ``self.entity_batch_size`` so authenticated sessions with
        ``apihighlimits`` can fetch 500 entities per request.
        """
        if not entity_ids:
            return {}

        result: dict[str, dict[str, Any]] = {}

        for i in range(0, len(entity_ids), self.entity_batch_size):
            batch = entity_ids[i : i + self.entity_batch_size]
            batch_results = self._fetch_entities_batch(batch)
            result.update(batch_results)

        return result

    def load_items(self, qids: list[str]) -> dict[str, WikibaseItemTemplate]:
        """Load multiple Wikidata items in batch and return them as templates.

        Uses the wbgetentities API to efficiently fetch multiple items in
        ``self.entity_batch_size`` chunks. Handles partial failures gracefully.

        Args:
            qids: List of Wikidata item IDs (e.g., ['Q42', 'Q5']).

        Returns:
            Dict mapping QIDs to WikidataTemplates. Only successfully loaded
            items are included in the result.

        Raises:
            RuntimeError: If the API request fails completely.

        Plain meaning: Load multiple items efficiently in batch.

        Example:
            >>> loader = WikibaseLoader()
            >>> templates = loader.load_items(["Q42", "Q5", "Q30"])
            >>> print(len(templates))
            3
        """
        if not qids:
            return {}

        result: dict[str, WikibaseItemTemplate] = {}
        batch_results = self.load_entities_raw(qids)

        # Build templates for each successfully fetched entity
        for qid, entity_data in batch_results.items():
            try:
                template = self._build_template(qid, entity_data)
                result[qid] = template
            except Exception:
                # Skip items that fail to parse
                continue

        return result

    def load_property(self, pid: str) -> WikibasePropertyTemplate:
        """Load a Wikidata property and return it as a template.

        Args:
            pid: The Wikidata property ID (e.g., 'P31').

        Returns:
            WikibasePropertyTemplate with the property's metadata.

        Raises:
            RuntimeError: If the property cannot be fetched or parsed.

        Plain meaning: Retrieve a property definition and return it ready for use.

        Example:
            >>> loader = WikibaseLoader()
            >>> prop = loader.load_property("P31")
            >>> print(prop.summary())
        """
        entity_data = self.load_entity_data(pid)
        return self._build_property_template(pid, entity_data)

    def load_entity_schema(self, eid: str) -> WikibaseEntitySchemaTemplate:
        """Load a Wikidata EntitySchema and return it as a template.

        Args:
            eid: The Wikidata EntitySchema ID (e.g., 'E502').

        Returns:
            WikibaseEntitySchemaTemplate with the schema content.

        Raises:
            RuntimeError: If the EntitySchema cannot be fetched or parsed.

        Plain meaning: Retrieve an EntitySchema and return it ready for use.

        Example:
            >>> loader = WikibaseLoader()
            >>> schema = loader.load_entity_schema("E502")
            >>> print(schema.summary())
        """
        entity_data = fetch_entity_schema_json(eid, user_agent=self.user_agent)
        return self._build_entity_schema_template(eid, entity_data)

    def _fetch_entities_batch(self, entity_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch multiple entities using wbgetentities API.

        Args:
            entity_ids: List of entity IDs (max 50).

        Returns:
            Dict mapping entity IDs to their entity data.

        Raises:
            RuntimeError: If the API request fails.

        Plain meaning: Fetch a batch of entities from Wikidata.
        """
        try:
            return self.api_client.get_entities(entity_ids)
        except RuntimeError as exc:
            raise RuntimeError(f"Failed to fetch entities batch: {exc}") from exc

    def load_entity_data(self, qid: str) -> dict[str, Any]:
        """Load raw Wikidata entity data.

        Plain meaning: Return the entity JSON as provided by Wikidata.
        """

        # Fetch the item via Special:EntityData endpoint which returns JSON
        # This is equivalent to wbgetentities but simpler for single-item fetches
        json_text = self._fetch_entity_json(qid)

        # Parse the JSON response from Wikidata
        return self._parse_wikidata_json(json_text, qid)

    def _fetch_entity_json(self, qid: str) -> str:
        """Fetch a single Wikidata entity as JSON.

        Args:
            qid: The Wikidata item ID (e.g., 'Q42').

        Returns:
            JSON string with entity data.

        Raises:
            RuntimeError: If the fetch fails or entity doesn't exist.

        Plain meaning: Download the item from Wikidata as JSON.
        """

        parsed = urlparse(self.api_url)
        if not parsed.scheme or not parsed.netloc:
            raise RuntimeError(f"Invalid API URL configured: {self.api_url}")

        url = f"{parsed.scheme}://{parsed.netloc}/wiki/Special:EntityData/{qid}.json"

        headers = {}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent

        try:
            response = requests.get(url, headers=headers, timeout=30)

            # Handle 404 or 400 errors which indicate item doesn't exist
            if response.status_code == 404:
                raise RuntimeError(f"no-such-entity: {qid} not found on Wikidata")
            if response.status_code == 400:
                raise RuntimeError(f"no-such-entity: {qid} is invalid")

            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to load item {qid}: {exc}") from exc

    def _parse_wikidata_json(self, json_text: str, qid: str) -> dict[str, Any]:
        """Parse Wikidata JSON response from Special:EntityData endpoint.

        Args:
            json_text: Raw JSON response text.
            qid: The QID being parsed (used for error messages).

        Returns:
            Dictionary with entity data.

        Raises:
            ValueError: If JSON parsing fails or format is unexpected.

        Plain meaning: Extract entity data from the API response.
        """

        try:
            response = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse JSON response for {qid}: {exc}") from exc

        if not isinstance(response, dict):
            raise ValueError(f"Expected JSON object for {qid}, got {type(response)}")

        # Special:EntityData wraps data in an "entities" key
        entities = response.get("entities", {})
        entity_data: dict[str, Any] = entities.get(qid, {})

        # Check for API error
        if "error" in entity_data:
            error_code = entity_data["error"].get("code", "unknown")
            error_info = entity_data["error"].get("info", "No error details")
            raise ValueError(
                f"Wikidata API error for {qid} ({error_code}): {error_info}"
            )

        if not entity_data:
            raise ValueError(f"Entity {qid} not found in response")

        return entity_data

    def _build_template(
        self, qid: str, entity_data: dict[str, Any]
    ) -> WikibaseItemTemplate:
        """Convert entity data to a WikibaseItemTemplate.

        Plain meaning: Transform API data into our simplified format.
        """

        # Extract labels, descriptions, aliases
        labels = entity_data.get("labels", {})
        descriptions = entity_data.get("descriptions", {})
        aliases = entity_data.get("aliases", {})

        # Simplify to language -> value mappings
        labels_dict = {
            lang: item.get("value", "")
            for lang, item in labels.items()
            if isinstance(item, dict)
        }
        descriptions_dict = {
            lang: item.get("value", "")
            for lang, item in descriptions.items()
            if isinstance(item, dict)
        }
        aliases_dict = {
            lang: [alias.get("value", "") for alias in alias_list]
            for lang, alias_list in aliases.items()
            if isinstance(alias_list, list)
        }

        # Extract claims
        claims = self._extract_claims(entity_data.get("claims", {}))

        return WikibaseItemTemplate(
            qid=qid,
            labels=labels_dict,
            descriptions=descriptions_dict,
            aliases=aliases_dict,
            claims=claims,
            entity_data=copy.deepcopy(entity_data),
        )

    @staticmethod
    def _extract_claims(claims_data: dict[str, Any]) -> list[ClaimSummary]:
        """Extract claims from entity data.

        Plain meaning: Parse statement data into simplified claim objects.
        """

        claims: list[ClaimSummary] = []

        for prop_id, statements in claims_data.items():
            if not isinstance(statements, list):
                continue

            for statement in statements:
                claim = WikibaseLoader._statement_to_claim(prop_id, statement)
                if claim:
                    claims.append(claim)

        return claims

    def _build_property_template(
        self, pid: str, entity_data: dict[str, Any]
    ) -> WikibasePropertyTemplate:
        """Convert entity data to a WikibasePropertyTemplate.

        Plain meaning: Transform API data into our simplified property format.
        """
        # Extract labels, descriptions, aliases
        labels = entity_data.get("labels", {})
        descriptions = entity_data.get("descriptions", {})
        aliases = entity_data.get("aliases", {})

        # Simplify to language -> value mappings
        labels_dict = {
            lang: item.get("value", "")
            for lang, item in labels.items()
            if isinstance(item, dict)
        }
        descriptions_dict = {
            lang: item.get("value", "")
            for lang, item in descriptions.items()
            if isinstance(item, dict)
        }
        aliases_dict = {
            lang: [alias.get("value", "") for alias in alias_list]
            for lang, alias_list in aliases.items()
            if isinstance(alias_list, list)
        }

        # Extract property-specific metadata
        datatype = entity_data.get("datatype")

        # Formatter URL is in claims P1630
        formatter_url = None
        claims = entity_data.get("claims", {})
        p1630_statements = claims.get("P1630", [])
        if p1630_statements and isinstance(p1630_statements, list):
            first_statement = p1630_statements[0]
            mainsnak = first_statement.get("mainsnak", {})
            datavalue = mainsnak.get("datavalue", {})
            if datavalue.get("type") == "string":
                formatter_url = datavalue.get("value")

        return WikibasePropertyTemplate(
            pid=pid,
            labels=labels_dict,
            descriptions=descriptions_dict,
            aliases=aliases_dict,
            datatype=datatype,
            formatter_url=formatter_url,
            entity_data=copy.deepcopy(entity_data),
        )

    def _build_entity_schema_template(
        self, eid: str, entity_data: dict[str, Any]
    ) -> WikibaseEntitySchemaTemplate:
        """Convert entity data to a WikibaseEntitySchemaTemplate.

        Plain meaning: Transform API data into our simplified EntitySchema format.
        """
        # Extract labels and descriptions
        labels = entity_data.get("labels", {})
        descriptions = entity_data.get("descriptions", {})

        # Simplify to language -> value mappings
        labels_dict = {
            lang: item.get("value", "")
            for lang, item in labels.items()
            if isinstance(item, dict)
        }
        descriptions_dict = {
            lang: item.get("value", "")
            for lang, item in descriptions.items()
            if isinstance(item, dict)
        }

        # Extract schema text
        schema_text = entity_data.get("schemaText", "")

        return WikibaseEntitySchemaTemplate(
            eid=eid,
            labels=labels_dict,
            descriptions=descriptions_dict,
            schema_text=schema_text,
            entity_data=copy.deepcopy(entity_data),
        )

    @staticmethod
    def _statement_to_claim(
        prop_id: str, statement: dict[str, Any]
    ) -> Optional[ClaimSummary]:
        """Convert a single statement to a ClaimSummary.

        Plain meaning: Simplify a statement object for display.
        """

        # Extract main value
        mainsnak = statement.get("mainsnak", {})
        value, value_metadata = WikibaseLoader._snak_to_value(mainsnak)
        if value is None:
            return None

        # Extract qualifiers with their values
        qualifiers = statement.get("qualifiers", {})
        qualifiers_list = []
        for prop, snaks in qualifiers.items():
            if snaks:
                # Extract value from the first snak of each qualifier property
                snak = snaks[0]
                qual_value, qual_metadata = WikibaseLoader._snak_to_value(snak)
                if qual_value:
                    qualifier_dict = {"property": prop, "value": qual_value}
                    if qual_metadata:
                        qualifier_dict["metadata"] = qual_metadata
                    qualifiers_list.append(qualifier_dict)

        # Extract references
        references = statement.get("references", [])
        references_list = [{"count": len(ref.get("snaks", {}))} for ref in references]

        rank = statement.get("rank", "normal")

        return ClaimSummary(
            property_id=prop_id,
            value=value,
            qualifiers=qualifiers_list,
            references=references_list,
            rank=rank,
            value_metadata=value_metadata,
        )

    @staticmethod
    def _snak_to_value(
        snak: dict[str, Any],
    ) -> tuple[Optional[str], Optional[dict[str, Any]]]:
        """Extract a human-readable value from a snak with metadata.

        Returns:
            Tuple of (value_string, metadata_dict) where metadata contains
            things like precision for dates, units for quantities, etc.

        Plain meaning: Get a simple string representation of the value plus metadata.
        """

        snaktype = snak.get("snaktype", "value")

        if snaktype == "novalue":
            return "[no value]", None
        if snaktype == "somevalue":
            return "[unknown value]", None

        datavalue = snak.get("datavalue")
        if not datavalue:
            return None, None

        dv_type = datavalue.get("type", "")
        dv_value = datavalue.get("value")

        if dv_type == "wikibase-entityid":
            if isinstance(dv_value, dict):
                return dv_value.get("id", "[entity]"), None
            return str(dv_value), None

        if dv_type == "quantity":
            if isinstance(dv_value, dict):
                amount = dv_value.get("amount", "[quantity]")
                unit = dv_value.get("unit")
                metadata = {"unit": unit} if unit else None
                return amount, metadata
            return str(dv_value), None

        if dv_type == "time":
            if isinstance(dv_value, dict):
                time_str = dv_value.get("time", "[time]")
                precision = dv_value.get("precision")
                metadata = {"precision": precision} if precision is not None else None
                return time_str, metadata
            return str(dv_value), None

        if dv_type == "monolingualtext":
            if isinstance(dv_value, dict):
                return dv_value.get("text", "[text]"), None
            return str(dv_value), None

        if dv_type == "string":
            return str(dv_value), None

        if dv_type == "globecoordinate":
            if isinstance(dv_value, dict):
                lat = dv_value.get("latitude", "?")
                lon = dv_value.get("longitude", "?")
                precision_val = dv_value.get("precision")
                metadata = (
                    {"precision": precision_val} if precision_val is not None else None
                )
                return f"({lat}, {lon})", metadata
            return str(dv_value), None

        return (str(dv_value), None) if dv_value else (None, None)


@dataclass
class WikipediaTemplate:
    """A Wikipedia template loaded from Wikimedia API for use in Wikipedia editing.

    This is the Wikipedia-specific implementation of the DataTemplate protocol.

    Plain meaning: A loaded Wikipedia template ready for display and use
    in editing workflows.
    """

    title: str
    description: str
    params: dict[str, Any]
    param_order: list[str]
    raw_data: dict[str, Any]

    def summary(self) -> dict[str, Any]:
        """Return a summary of the template for display.

        Returns:
            Dict with title, description, and number of parameters.

        Plain meaning: Get a quick overview without full details.
        """
        return {
            "title": self.title,
            "description": self.description,
            "param_count": len(self.params),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Returns:
            Dict containing title, description, params, and paramOrder.

        Plain meaning: Convert to a form suitable for JSON export.
        """
        return {
            "title": self.title,
            "description": self.description,
            "params": self.params,
            "paramOrder": self.param_order,
        }


class WikipediaLoader:
    """Load Wikipedia templates from Wikimedia API as templates for editing workflows.

    This is the Wikipedia-specific implementation of a data loader.

    Plain meaning: Fetch and parse a Wikipedia template into a usable format.
    """

    def __init__(self, user_agent: Optional[str] = None):
        """Initialize the loader.

        Args:
            user_agent: Custom user agent for Wikimedia API requests.
                       If not provided, a default GKC user agent is used.

        Plain meaning: Set up the loader with optional custom user agent.
        """
        if user_agent is None:
            user_agent = DEFAULT_USER_AGENT

        self.user_agent = user_agent
        self.base_url = "https://en.wikipedia.org/w/api.php"

    def load_template(self, template_name: str) -> WikipediaTemplate:
        """Load a Wikipedia template and return it as a template.

        Args:
            template_name: The Wikipedia template name (e.g., 'Infobox settlement').

        Returns:
            WikipediaTemplate with the template's structure.

        Raises:
            RuntimeError: If the template cannot be fetched or parsed.

        Plain meaning: Retrieve the template and return it ready for use.

        Example:
            >>> loader = WikipediaLoader()
            >>> template = loader.load_template("Infobox settlement")
            >>> print(template.summary())
        """
        # Fetch template data from Wikimedia API
        params: dict[str, Any] = {
            "action": "templatedata",
            "format": "json",
            "titles": f"Template:{template_name}",
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Failed to fetch template '{template_name}' from Wikimedia API: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                f"Failed to parse JSON response for template '{template_name}': {exc}"
            ) from exc

        # Extract pages from response. The templatedata API returns pages directly,
        # not nested under a "query" key like other Mediawiki APIs.
        pages = data.get("pages", {})
        if not pages:
            raise RuntimeError(
                f"Template '{template_name}' not found in Wikimedia API response"
            )

        # Get the first (and only) page
        page_data = next(iter(pages.values()))

        # Check if this page has template data
        if "notabledescriptions" in page_data or "missing" in page_data:
            raise RuntimeError(
                f"Template '{template_name}' not found or has no template data"
            )

        # Extract required fields
        title = page_data.get("title", template_name)

        # Get description in English, or empty string if not available
        descriptions = page_data.get("description", {})
        if isinstance(descriptions, dict):
            description = descriptions.get("en", "")
        else:
            description = str(descriptions) if descriptions else ""

        params_data = page_data.get("params", {})
        param_order = page_data.get("paramOrder", [])

        # Build and return the template
        return WikipediaTemplate(
            title=title,
            description=description,
            params=params_data,
            param_order=param_order,
            raw_data=page_data,
        )


class WikibaseMashSourceAdapter(MashSourceAdapter):
    """Mash source adapter for Wikibase entity references.

    Supports item/property/schema IDs and delegates loading to ``WikibaseLoader``.
    """

    source_name = "wikibase"

    def __init__(self, loader: Optional[WikibaseLoader] = None):
        self.loader = loader or WikibaseLoader()

    @staticmethod
    def _is_wikibase_entity_ref(source_ref: str) -> bool:
        if not source_ref or len(source_ref) < 2:
            return False

        prefix = source_ref[0]
        suffix = source_ref[1:]
        return prefix in {"Q", "P", "E"} and suffix.isdigit()

    def can_load(self, source_ref: str) -> bool:
        """Return True for Wikibase entity IDs (Q/P/E)."""
        return self._is_wikibase_entity_ref(source_ref)

    def load(self, source_ref: str) -> DataTemplate:
        """Load a Wikibase entity ID into the appropriate template type."""
        if not self.can_load(source_ref):
            raise ValueError(
                f"WikibaseMashSourceAdapter cannot load source reference: {source_ref}"
            )

        prefix = source_ref[0]
        if prefix == "Q":
            return self.loader.load_item(source_ref)
        if prefix == "P":
            return self.loader.load_property(source_ref)
        if prefix == "E":
            return self.loader.load_entity_schema(source_ref)

        raise ValueError(f"Unsupported Wikibase entity reference: {source_ref}")

    def load_many(self, source_refs: list[str]) -> dict[str, DataTemplate]:
        """Load multiple Wikibase references into templates keyed by source ref."""
        if not source_refs:
            return {}

        invalid_refs = [
            source_ref for source_ref in source_refs if not self.can_load(source_ref)
        ]
        if invalid_refs:
            raise ValueError(
                f"Invalid Wikibase source references: {', '.join(invalid_refs)}"
            )

        loaded: dict[str, DataTemplate] = {}

        qids = [source_ref for source_ref in source_refs if source_ref.startswith("Q")]
        if qids:
            loaded.update(self.loader.load_items(qids))

        for source_ref in source_refs:
            if source_ref in loaded:
                continue
            loaded[source_ref] = self.load(source_ref)

        return loaded


class WikipediaMashSourceAdapter(MashSourceAdapter):
    """Mash source adapter for Wikipedia template references."""

    source_name = "wikipedia-template"

    def __init__(self, loader: Optional[WikipediaLoader] = None):
        self.loader = loader or WikipediaLoader()

    @staticmethod
    def _normalize_template_name(source_ref: str) -> str:
        name = source_ref.strip()
        if name.startswith("Template:"):
            return name.removeprefix("Template:")
        return name

    def can_load(self, source_ref: str) -> bool:
        """Return True for non-empty template references."""
        return bool(source_ref and source_ref.strip())

    def load(self, source_ref: str) -> WikipediaTemplate:
        """Load a Wikipedia template by name."""
        if not self.can_load(source_ref):
            raise ValueError(
                "WikipediaMashSourceAdapter requires a non-empty template reference"
            )

        template_name = self._normalize_template_name(source_ref)
        return self.loader.load_template(template_name)

    def load_many(self, source_refs: list[str]) -> dict[str, WikipediaTemplate]:
        """Load multiple Wikipedia templates keyed by the original source ref."""
        loaded: dict[str, WikipediaTemplate] = {}
        for source_ref in source_refs:
            loaded[source_ref] = self.load(source_ref)
        return loaded
