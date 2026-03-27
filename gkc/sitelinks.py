"""
Sitelinks validation and utilities for Wikidata.

This module provides utilities for validating Wikipedia and other Wikimedia
project sitelinks before attempting to create them on Wikidata items.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from gkc.runtime_config import DEFAULT_USER_AGENT

DEFAULT_WIKIMEDIA_SITEMATRIX_URL = (
    "https://meta.wikimedia.org/w/api.php?action=sitematrix&format=json&smstate=all"
)
WIKIMEDIA_SITES_SCHEMA_VERSION = "1.0"


class SitelinkValidator:
    """Validates Wikipedia and Wikimedia project sitelinks."""

    # Map site codes to API endpoints
    SITE_API_ENDPOINTS = {
        # Wikipedia sites
        "enwiki": "https://en.wikipedia.org/w/api.php",
        "frwiki": "https://fr.wikipedia.org/w/api.php",
        "dewiki": "https://de.wikipedia.org/w/api.php",
        "eswiki": "https://es.wikipedia.org/w/api.php",
        "jawiki": "https://ja.wikipedia.org/w/api.php",
        "itwiki": "https://it.wikipedia.org/w/api.php",
        "nlwiki": "https://nl.wikipedia.org/w/api.php",
        "plwiki": "https://pl.wikipedia.org/w/api.php",
        "ptwiki": "https://pt.wikipedia.org/w/api.php",
        "ruwiki": "https://ru.wikipedia.org/w/api.php",
        "zhwiki": "https://zh.wikipedia.org/w/api.php",
        # Wikimedia Commons
        "commonswiki": "https://commons.wikimedia.org/w/api.php",
        # Wikispecies
        "specieswiki": "https://species.wikimedia.org/w/api.php",
        # Add more as needed - pattern: {lang}wiki, {lang}wikisource, etc.
    }

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: int = 10):
        """
        Initialize the sitelink validator.

        Args:
            user_agent: User agent string for API requests
            timeout: Timeout in seconds for API requests
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _get_api_endpoint(self, site_code: str) -> Optional[str]:
        """
        Get the MediaWiki API endpoint for a site code.

        Args:
            site_code: Site code like 'enwiki', 'frwiki', 'commonswiki'

        Returns:
            API endpoint URL or None if not found
        """
        # Check known sites
        if site_code in self.SITE_API_ENDPOINTS:
            return self.SITE_API_ENDPOINTS[site_code]

        # Try to construct URL for Wikipedia sites
        if site_code.endswith("wiki") and len(site_code) > 4:
            lang_code = site_code[:-4]
            return f"https://{lang_code}.wikipedia.org/w/api.php"

        # Try for other Wikimedia projects
        if site_code.endswith("wikisource"):
            lang_code = site_code[:-10]
            return f"https://{lang_code}.wikisource.org/w/api.php"
        elif site_code.endswith("wikivoyage"):
            lang_code = site_code[:-10]
            return f"https://{lang_code}.wikivoyage.org/w/api.php"
        elif site_code.endswith("wiktionary"):
            lang_code = site_code[:-10]
            return f"https://{lang_code}.wiktionary.org/w/api.php"

        return None

    def check_page_exists(
        self, title: str, site_code: str, allow_redirects: bool = False
    ) -> tuple[bool, str]:
        """
        Check if a Wikipedia/Wikimedia page exists and optionally check for redirects.

        Args:
            title: Page title to check
            site_code: Site code (e.g., 'enwiki', 'commonswiki')
            allow_redirects: If False, return False for redirect pages

        Returns:
            Tuple of (exists: bool, message: str)
            - (True, ""): Page exists and is valid
            - (False, reason): Page doesn't exist or is invalid, with reason
        """
        if not title or not title.strip():
            return (False, "Empty title")

        # Get API endpoint
        api_url = self._get_api_endpoint(site_code)
        if not api_url:
            return (False, f"Unknown site code: {site_code}")

        # Query the MediaWiki API
        params = {
            "action": "query",
            "titles": title.strip(),
            "format": "json",
            "redirects": "" if not allow_redirects else None,
        }

        try:
            response = self.session.get(api_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Check for redirects
            if not allow_redirects and "redirects" in data.get("query", {}):
                redirect_to = data["query"]["redirects"][0].get("to", "")
                return (False, f"Page is a redirect to: {redirect_to}")

            # Check if page exists
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if int(page_id) > 0:
                    # Page exists (positive page ID)
                    return (True, "")
                else:
                    # Page doesn't exist (negative page ID)
                    return (False, "Page does not exist")

            return (False, "No pages returned from API")

        except requests.Timeout:
            return (False, f"Timeout checking {site_code}")
        except requests.RequestException as e:
            return (False, f"Request error: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            return (False, f"Error parsing response: {str(e)}")

    def validate_sitelinks(
        self, sitelinks: dict[str, dict], delay_between_checks: float = 0.1
    ) -> dict[str, tuple[bool, str]]:
        """
        Validate multiple sitelinks at once.

        Args:
            sitelinks: Dictionary of sitelinks from transform_to_wikidata()
                Format: {"enwiki": {"site": "enwiki", "title": "...",
                         "badges": []}}
            delay_between_checks: Delay in seconds between API requests
                (rate limiting)

        Returns:
            Dictionary mapping site codes to (valid: bool, message: str)

        Example:
            >>> validator = SitelinkValidator()
            >>> sitelinks = {
            ...     "enwiki": {"site": "enwiki", "title": "Example", "badges": []},
            ...     "frwiki": {"site": "frwiki", "title": "Exemple", "badges": []}
            ... }
            >>> results = validator.validate_sitelinks(sitelinks)
            >>> results
            {
                "enwiki": (True, ""),
                "frwiki": (False, "Page does not exist")
            }
        """
        results = {}

        for site_code, sitelink_data in sitelinks.items():
            title = sitelink_data.get("title")
            if not title:
                results[site_code] = (False, "No title provided")
                continue

            # Check if page exists
            exists, message = self.check_page_exists(title, site_code)
            results[site_code] = (exists, message)

            # Rate limiting
            if delay_between_checks > 0:
                sleep(delay_between_checks)

        return results

    def filter_valid_sitelinks(
        self, sitelinks: dict[str, dict], verbose: bool = False
    ) -> dict[str, dict]:
        """
        Filter out invalid sitelinks, returning only valid ones.

        Args:
            sitelinks: Dictionary of sitelinks to validate
            verbose: If True, print validation results

        Returns:
            Filtered dictionary containing only valid sitelinks
        """
        validation_results = self.validate_sitelinks(sitelinks)
        valid_sitelinks = {}

        for site_code, sitelink_data in sitelinks.items():
            is_valid, message = validation_results.get(
                site_code, (False, "Not checked")
            )

            if verbose:
                status = "✓" if is_valid else "✗"
                title = sitelink_data.get("title", "")
                print(
                    f"{status} {site_code}: {title} - {message if message else 'valid'}"
                )

            if is_valid:
                valid_sitelinks[site_code] = sitelink_data

        return valid_sitelinks


def check_wikipedia_page(
    title: str, site_code: str = "enwiki", allow_redirects: bool = False
) -> Optional[str]:
    """
    Convenience function to check if a Wikipedia page exists.

    Args:
        title: Page title to check
        site_code: Wikipedia site code (default: "enwiki" for English Wikipedia)
        allow_redirects: If False, reject redirect pages

    Returns:
        The title if page exists and is valid, None otherwise

    Example:
        >>> check_wikipedia_page("Python (programming language)")
        'Python (programming language)'
        >>> check_wikipedia_page("NonexistentPage123")
        None
    """
    if not title:
        return None

    validator = SitelinkValidator()
    exists, message = validator.check_page_exists(title, site_code, allow_redirects)

    return title if exists else None


def validate_sitelink_dict(sitelinks: dict[str, dict]) -> dict[str, dict]:
    """
    Convenience function to validate and filter sitelinks.

    Args:
        sitelinks: Dictionary of sitelinks from transform_to_wikidata()

    Returns:
        Filtered dictionary containing only valid sitelinks

    Example:
        >>> sitelinks = {
        ...     "enwiki": {"site": "enwiki", "title": "Example", "badges": []},
        ...     "frwiki": {"site": "frwiki", "title": "BadPage", "badges": []}
        ... }
        >>> valid = validate_sitelink_dict(sitelinks)
        >>> # Returns only valid sitelinks
    """
    validator = SitelinkValidator()
    return validator.filter_valid_sitelinks(sitelinks, verbose=False)


def _normalize_domain_from_url(site_url: str) -> str:
    """Derive lowercase host/domain from a Wikimedia site URL."""
    parsed = urlparse(site_url)
    host = parsed.netloc.lower().strip()
    if host.startswith("www."):
        host = host[4:]
    return host


def _coerce_closed_flag(site: dict[str, Any]) -> bool:
    """Normalize MediaWiki closed marker to a boolean value."""
    if "closed" not in site:
        return False

    closed_value = site.get("closed")
    if isinstance(closed_value, bool):
        return closed_value
    if isinstance(closed_value, str):
        stripped = closed_value.strip().lower()
        if stripped in {"0", "false", "no", "open"}:
            return False
        # In sitematrix, closed is often emitted as an empty marker value.
        return True

    # Presence of marker keys in sitematrix is enough to treat as closed.
    return True


def _project_from_dbname(dbname: str) -> str:
    """Infer Wikimedia project family from site dbname suffix."""
    known_suffixes = [
        "wiktionary",
        "wikisource",
        "wikiversity",
        "wikivoyage",
        "wikinews",
        "wikiquote",
        "wikibooks",
        "wikidata",
        "wikimedia",
        "wiki",
    ]
    for suffix in known_suffixes:
        if dbname.endswith(suffix):
            return suffix
    return ""


def build_wikimedia_sites_artifact_from_sitematrix(
    sitematrix_payload: dict[str, Any],
    *,
    source_url: str = DEFAULT_WIKIMEDIA_SITEMATRIX_URL,
    fetched_at: Optional[str] = None,
) -> dict[str, Any]:
    """Build a deterministic Wikimedia sites artifact from sitematrix payload."""
    sitematrix = sitematrix_payload.get("sitematrix")
    if not isinstance(sitematrix, dict):
        raise ValueError("Invalid sitematrix payload: missing 'sitematrix' object")

    sites: list[dict[str, Any]] = []

    def _append_sites(
        site_list: Any, *, lang_code: Optional[str], lang_name: Optional[str]
    ) -> None:
        if not isinstance(site_list, list):
            return
        for site in site_list:
            if not isinstance(site, dict):
                continue
            dbname = site.get("dbname")
            site_url = site.get("url")
            if not isinstance(dbname, str) or not dbname:
                continue
            if not isinstance(site_url, str) or not site_url:
                continue

            normalized_site = {
                "dbname": dbname,
                "url": site_url,
                "domain": _normalize_domain_from_url(site_url),
                "code": site.get("code") if isinstance(site.get("code"), str) else "",
                "lang": lang_name or "",
                "sitename": (
                    site.get("sitename")
                    if isinstance(site.get("sitename"), str)
                    else ""
                ),
                "project": _project_from_dbname(dbname),
                "closed": _coerce_closed_flag(site),
            }
            # Keep both explicit language code and site code for runtime filters.
            normalized_site["language_code"] = lang_code or ""
            sites.append(normalized_site)

    for key, value in sitematrix.items():
        if isinstance(value, dict) and isinstance(value.get("site"), list):
            lang_code = (
                value.get("code") if isinstance(value.get("code"), str) else None
            )
            lang_name = (
                value.get("name") if isinstance(value.get("name"), str) else None
            )
            _append_sites(value.get("site"), lang_code=lang_code, lang_name=lang_name)
            continue

        if key == "specials" and isinstance(value, list):
            _append_sites(value, lang_code=None, lang_name=None)

    deduped_by_dbname: dict[str, dict[str, Any]] = {}
    for site in sites:
        dbname = str(site["dbname"])
        existing = deduped_by_dbname.get(dbname)
        if existing is None:
            deduped_by_dbname[dbname] = site
            continue
        if existing != site:
            raise ValueError(f"Conflicting sitematrix entries for dbname: {dbname}")

    sorted_sites = sorted(
        deduped_by_dbname.values(),
        key=lambda site: (str(site.get("dbname", "")), str(site.get("domain", ""))),
    )

    by_dbname = {site["dbname"]: site for site in sorted_sites}
    domains: dict[str, set[str]] = {}
    for site in sorted_sites:
        domain = str(site.get("domain", ""))
        dbname = str(site.get("dbname", ""))
        if not domain or not dbname:
            continue
        domains.setdefault(domain, set()).add(dbname)

    by_domain = {
        domain: sorted(dbnames)
        for domain, dbnames in sorted(domains.items(), key=lambda item: item[0])
    }

    fetched_at_value = fetched_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    closed_count = sum(1 for site in sorted_sites if bool(site.get("closed")))

    return {
        "metadata": {
            "source_url": source_url,
            "fetched_at": fetched_at_value,
            "schema_version": WIKIMEDIA_SITES_SCHEMA_VERSION,
            "total_sites": len(sorted_sites),
            "active_sites": len(sorted_sites) - closed_count,
            "closed_sites": closed_count,
        },
        "sites": sorted_sites,
        "index": {
            "by_dbname": by_dbname,
            "by_domain": by_domain,
        },
    }


def fetch_wikimedia_sitematrix(
    *,
    source_url: str = DEFAULT_WIKIMEDIA_SITEMATRIX_URL,
    timeout: int = 30,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    """Fetch raw Wikimedia sitematrix JSON payload."""
    response = requests.get(
        source_url,
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Invalid sitematrix response: expected JSON object")
    return payload


def export_wikimedia_sites_artifact(
    output_path: str,
    *,
    source_url: str = DEFAULT_WIKIMEDIA_SITEMATRIX_URL,
    timeout: int = 30,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Any]:
    """Fetch, normalize, and write Wikimedia sites artifact JSON to disk."""
    payload = fetch_wikimedia_sitematrix(
        source_url=source_url,
        timeout=timeout,
        user_agent=user_agent,
    )
    artifact = build_wikimedia_sites_artifact_from_sitematrix(
        payload,
        source_url=source_url,
    )

    target_path = Path(output_path).expanduser().resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return artifact
