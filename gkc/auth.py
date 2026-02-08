"""
Authentication module for Global Knowledge Commons services.

This module provides authentication classes for:
- Wikiverse (Wikidata, Wikipedia, Wikimedia Commons)
- OpenStreetMap

Bot Password Authentication:
---------------------------
For Wikimedia projects, use bot passwords created at:
https://www.wikidata.org/wiki/Special:BotPasswords

Bot passwords provide:
- Granular permission control
- Cross-wiki authentication (works on all Wikimedia projects)
- Security without exposing main account password
- Format: Username@BotName (e.g., "Alice@MyBot")
"""

import os
import getpass
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


class WikiverseAuth(AuthBase):
    """
    Authentication for Wikimedia projects (Wikidata, Wikipedia, Wikimedia Commons).

    Designed for bot accounts using bot passwords. The same credentials work
    across all Wikimedia projects due to Single User Login (SUL).

    Credentials can be provided in three ways (in order of precedence):
    1. Direct parameters
    2. Environment variables (WIKIVERSE_USERNAME, WIKIVERSE_PASSWORD)
    3. Interactive prompt

    Example:
        >>> # Using environment variables
        >>> auth = WikiverseAuth()
        
        >>> # Direct parameters (bot password format)
        >>> auth = WikiverseAuth(
        ...     username="MyUsername@MyBot",
        ...     password="abc123def456ghi789"
        ... )
        
        >>> # Interactive prompt
        >>> auth = WikiverseAuth(interactive=True)
        Enter Wikiverse username (format: Username@BotName): MyUsername@MyBot
        Enter Wikiverse password: ****
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        interactive: bool = False,
    ):
        """
        Initialize Wikiverse authentication for bot accounts.

        Args:
            username: Bot password username in format "Username@BotName".
                     If not provided, reads from WIKIVERSE_USERNAME environment variable.
            password: Bot password. If not provided, reads from WIKIVERSE_PASSWORD
                     environment variable.
            interactive: If True and credentials are not found, prompt user for input.
        """
        # Try provided parameters first
        username = username or os.environ.get("WIKIVERSE_USERNAME")
        password = password or os.environ.get("WIKIVERSE_PASSWORD")

        # If credentials still not available and interactive mode is requested
        if interactive and not (username and password):
            print("Bot password credentials not found in environment.")
            username = input("Enter Wikiverse username (format: Username@BotName): ").strip()
            password = getpass.getpass("Enter Wikiverse password: ").strip()

        super().__init__(username, password)

    def __repr__(self) -> str:
        status = "authenticated" if self.is_authenticated() else "not authenticated"
        return f"WikiverseAuth(username={self.username!r}, {status})"

    def get_bot_name(self) -> Optional[str]:
        """
        Extract bot name from username.

        Returns:
            Bot name if username is in bot password format, None otherwise.

        Example:
            >>> auth = WikiverseAuth(username="Alice@MyBot")
            >>> auth.get_bot_name()
            'MyBot'
        """
        if self.username and "@" in self.username:
            return self.username.split("@", 1)[1]
        return None

    def get_account_name(self) -> Optional[str]:
        """
        Extract account name from username.

        Returns:
            Account name if username is in bot password format, None otherwise.

        Example:
            >>> auth = WikiverseAuth(username="Alice@MyBot")
            >>> auth.get_account_name()
            'Alice'
        """
        if self.username and "@" in self.username:
            return self.username.split("@", 1)[0]
        return None


class OpenStreetMapAuth(AuthBase):
    """
    Authentication for OpenStreetMap.

    Credentials can be provided in three ways (in order of precedence):
    1. Direct parameters
    2. Environment variables (OPENSTREETMAP_USERNAME, OPENSTREETMAP_PASSWORD)
    3. Interactive prompt

    Example:
        >>> # Using environment variables
        >>> auth = OpenStreetMapAuth()
        
        >>> # Direct parameters
        >>> auth = OpenStreetMapAuth(username="myuser", password="mypass")
        
        >>> # Interactive prompt
        >>> auth = OpenStreetMapAuth(interactive=True)
        Enter OpenStreetMap username: myuser
        Enter OpenStreetMap password: ****
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        interactive: bool = False,
    ):
        """
        Initialize OpenStreetMap authentication.

        Args:
            username: OpenStreetMap username. If not provided, reads from
                     OPENSTREETMAP_USERNAME environment variable.
            password: OpenStreetMap password. If not provided, reads from
                     OPENSTREETMAP_PASSWORD environment variable.
            interactive: If True and credentials are not found, prompt user for input.
        """
        # Try provided parameters first
        username = username or os.environ.get("OPENSTREETMAP_USERNAME")
        password = password or os.environ.get("OPENSTREETMAP_PASSWORD")

        # If credentials still not available and interactive mode is requested
        if interactive and not (username and password):
            print("OpenStreetMap credentials not found in environment.")
            username = input("Enter OpenStreetMap username: ").strip()
            password = getpass.getpass("Enter OpenStreetMap password: ").strip()

        super().__init__(username, password)

    def __repr__(self) -> str:
        status = "authenticated" if self.is_authenticated() else "not authenticated"
        return f"OpenStreetMapAuth(username={self.username!r}, {status})"
