"""
Authentication module for Global Knowledge Commons services.

This module provides authentication classes for:
- Wikidata
- Wikipedia
- OpenStreetMap
"""

import os
from typing import Optional


class AuthBase:
    """Base class for authentication."""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize authentication.

        Args:
            username: Username for authentication. If not provided, will try to
                     read from environment variable.
            password: Password for authentication. If not provided, will try to
                     read from environment variable.
        """
        self.username = username
        self.password = password

    def is_authenticated(self) -> bool:
        """Check if credentials are available."""
        return bool(self.username and self.password)


class WikidataAuth(AuthBase):
    """
    Authentication for Wikidata.

    Credentials can be provided directly or via environment variables:
    - WIKIDATA_USERNAME
    - WIKIDATA_PASSWORD
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Wikidata authentication.

        Args:
            username: Wikidata username. If not provided, reads from
                     WIKIDATA_USERNAME environment variable.
            password: Wikidata password. If not provided, reads from
                     WIKIDATA_PASSWORD environment variable.
        """
        username = username or os.environ.get("WIKIDATA_USERNAME")
        password = password or os.environ.get("WIKIDATA_PASSWORD")
        super().__init__(username, password)

    def __repr__(self) -> str:
        status = "authenticated" if self.is_authenticated() else "not authenticated"
        return f"WikidataAuth(username={self.username!r}, {status})"


class WikipediaAuth(AuthBase):
    """
    Authentication for Wikipedia.

    Credentials can be provided directly or via environment variables:
    - WIKIPEDIA_USERNAME
    - WIKIPEDIA_PASSWORD
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Wikipedia authentication.

        Args:
            username: Wikipedia username. If not provided, reads from
                     WIKIPEDIA_USERNAME environment variable.
            password: Wikipedia password. If not provided, reads from
                     WIKIPEDIA_PASSWORD environment variable.
        """
        username = username or os.environ.get("WIKIPEDIA_USERNAME")
        password = password or os.environ.get("WIKIPEDIA_PASSWORD")
        super().__init__(username, password)

    def __repr__(self) -> str:
        status = "authenticated" if self.is_authenticated() else "not authenticated"
        return f"WikipediaAuth(username={self.username!r}, {status})"


class OpenStreetMapAuth(AuthBase):
    """
    Authentication for OpenStreetMap.

    Credentials can be provided directly or via environment variables:
    - OPENSTREETMAP_USERNAME
    - OPENSTREETMAP_PASSWORD
    """

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize OpenStreetMap authentication.

        Args:
            username: OpenStreetMap username. If not provided, reads from
                     OPENSTREETMAP_USERNAME environment variable.
            password: OpenStreetMap password. If not provided, reads from
                     OPENSTREETMAP_PASSWORD environment variable.
        """
        username = username or os.environ.get("OPENSTREETMAP_USERNAME")
        password = password or os.environ.get("OPENSTREETMAP_PASSWORD")
        super().__init__(username, password)

    def __repr__(self) -> str:
        status = "authenticated" if self.is_authenticated() else "not authenticated"
        return f"OpenStreetMapAuth(username={self.username!r}, {status})"
