"""
Sitelinks validation and utilities for Wikidata.

This module provides utilities for validating Wikipedia and other Wikimedia
project sitelinks before attempting to create them on Wikidata items.
"""

from time import sleep
from typing import Optional

import requests

from gkc.wd import DEFAULT_USER_AGENT


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
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a Wikipedia/Wikimedia page exists and optionally check for redirects.

        Args:
            title: Page title to check
            site_code: Site code (e.g., 'enwiki', 'commonswiki')
            allow_redirects: If False, return False for redirect pages

        Returns:
            Tuple of (exists: bool, message: Optional[str])
            - (True, None): Page exists and is valid
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
                    return (True, None)
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
    ) -> dict[str, tuple[bool, Optional[str]]]:
        """
        Validate multiple sitelinks at once.

        Args:
            sitelinks: Dictionary of sitelinks from transform_to_wikidata()
                Format: {"enwiki": {"site": "enwiki", "title": "...",
                         "badges": []}}
            delay_between_checks: Delay in seconds between API requests
                (rate limiting)

        Returns:
            Dictionary mapping site codes to (valid: bool, message: Optional[str])

        Example:
            >>> validator = SitelinkValidator()
            >>> sitelinks = {
            ...     "enwiki": {"site": "enwiki", "title": "Example", "badges": []},
            ...     "frwiki": {"site": "frwiki", "title": "Exemple", "badges": []}
            ... }
            >>> results = validator.validate_sitelinks(sitelinks)
            >>> results
            {
                "enwiki": (True, None),
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
