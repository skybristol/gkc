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

import getpass
import os
from typing import Optional

import requests

# Default MediaWiki API endpoints for common Wikimedia projects
DEFAULT_WIKIMEDIA_APIS = {
    "wikidata": "https://www.wikidata.org/w/api.php",
    "wikipedia": "https://en.wikipedia.org/w/api.php",
    "commons": "https://commons.wikimedia.org/w/api.php",
}


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


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

    Supports both default Wikimedia instances and custom MediaWiki installations.

    Credentials can be provided in three ways (in order of precedence):
    1. Direct parameters
    2. Environment variables (WIKIVERSE_USERNAME, WIKIVERSE_PASSWORD, WIKIVERSE_API_URL)
    3. Interactive prompt

    Example:
        >>> # Authenticate to Wikidata (default)
        >>> auth = WikiverseAuth()
        >>> auth.login()

        >>> # Direct parameters (bot password format)
        >>> auth = WikiverseAuth(
        ...     username="MyUsername@MyBot",
        ...     password="abc123def456ghi789",
        ...     api_url="https://www.wikidata.org/w/api.php"
        ... )
        >>> auth.login()

        >>> # Custom MediaWiki instance
        >>> auth = WikiverseAuth(
        ...     username="MyUsername@MyBot",
        ...     password="abc123def456ghi789",
        ...     api_url="https://my-wiki.example.com/w/api.php"
        ... )
        >>> auth.login()

        >>> # Use authenticated session for API requests
        >>> response = auth.session.get(auth.api_url, params={
        ...     "action": "query",
        ...     "format": "json"
        ... })
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_url: Optional[str] = None,
        interactive: bool = False,
    ):
        """
        Initialize Wikiverse authentication for bot accounts.

        Args:
            username: Bot password username in format "Username@BotName".
                If not provided, reads from WIKIVERSE_USERNAME
                environment variable.
            password: Bot password. If not provided, reads from
                WIKIVERSE_PASSWORD environment variable.
            api_url: MediaWiki API endpoint URL. If not provided, reads from
                    WIKIVERSE_API_URL environment variable, or defaults to Wikidata.
                    Can also use shortcuts: "wikidata", "wikipedia", "commons"
            interactive: If True and credentials are not found, prompt user for input.
        """
        # Try provided parameters first
        username = username or os.environ.get("WIKIVERSE_USERNAME")
        password = password or os.environ.get("WIKIVERSE_PASSWORD")
        api_url = api_url or os.environ.get("WIKIVERSE_API_URL")

        # If credentials still not available and interactive mode is requested
        if interactive and not (username and password):
            print("Bot password credentials not found in environment.")
            username = input(
                "Enter Wikiverse username (format: Username@BotName): "
            ).strip()
            password = getpass.getpass("Enter Wikiverse password: ").strip()
            if not api_url:
                api_url_input = input(
                    "Enter API URL (or 'wikidata', 'wikipedia', 'commons') "
                    "[default: wikidata]: "
                ).strip()
                api_url = api_url_input if api_url_input else "wikidata"

        super().__init__(username, password)

        # Resolve API URL shortcuts to full URLs
        if api_url and api_url.lower() in DEFAULT_WIKIMEDIA_APIS:
            self.api_url = DEFAULT_WIKIMEDIA_APIS[api_url.lower()]
        elif api_url:
            self.api_url = api_url
        else:
            # Default to Wikidata
            self.api_url = DEFAULT_WIKIMEDIA_APIS["wikidata"]

        # Initialize session for authenticated requests
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "GKC-Python-Client/0.1 (https://github.com/skybristol/gkc)"}
        )
        self._logged_in = False

    def login(self) -> bool:
        """
        Perform login to MediaWiki API using bot password credentials.

        Returns:
            True if login successful, False otherwise.

        Raises:
            AuthenticationError: If login fails with detailed error message.

        Example:
            >>> auth = WikiverseAuth(username="User@Bot", password="secret")
            >>> if auth.login():
            ...     print("Successfully logged in!")
        """
        if not self.is_authenticated():
            raise AuthenticationError(
                "Cannot login: credentials not provided. "
                "Please provide username and password."
            )

        try:
            # Step 1: Get login token
            token_params = {
                "action": "query",
                "meta": "tokens",
                "type": "login",
                "format": "json",
            }
            token_response = self.session.get(self.api_url, params=token_params)
            token_response.raise_for_status()
            token_data = token_response.json()

            if "query" not in token_data or "tokens" not in token_data["query"]:
                raise AuthenticationError(
                    f"Failed to get login token from {self.api_url}. "
                    f"Response: {token_data}"
                )

            login_token = token_data["query"]["tokens"]["logintoken"]

            # Step 2: Perform login with credentials and token
            login_params = {
                "action": "login",
                "lgname": self.username,
                "lgpassword": self.password,
                "lgtoken": login_token,
                "format": "json",
            }
            login_response = self.session.post(self.api_url, data=login_params)
            login_response.raise_for_status()
            login_data = login_response.json()

            # Check login result
            if "login" not in login_data:
                raise AuthenticationError(
                    f"Unexpected login response from {self.api_url}. "
                    f"Response: {login_data}"
                )

            result = login_data["login"]["result"]

            if result == "Success":
                self._logged_in = True
                return True
            else:
                # Provide detailed error message
                reason = login_data["login"].get("reason", "Unknown reason")
                raise AuthenticationError(
                    f"Login failed with result '{result}'. Reason: {reason}. "
                    f"Check your bot password credentials and permissions."
                )

        except requests.RequestException as e:
            raise AuthenticationError(
                f"Network error during login to {self.api_url}: {str(e)}"
            )

    def is_logged_in(self) -> bool:
        """
        Check if currently logged in to MediaWiki API.

        Returns:
            True if logged in, False otherwise.
        """
        return self._logged_in

    def logout(self) -> None:
        """
        Logout from MediaWiki API and clear session.

        Example:
            >>> auth = WikiverseAuth(username="User@Bot", password="secret")
            >>> auth.login()
            >>> # ... do some work ...
            >>> auth.logout()
        """
        if self._logged_in:
            try:
                # Get CSRF token for logout
                token_params = {
                    "action": "query",
                    "meta": "tokens",
                    "type": "csrf",
                    "format": "json",
                }
                token_response = self.session.get(self.api_url, params=token_params)
                token_data = token_response.json()
                csrf_token = token_data["query"]["tokens"]["csrftoken"]

                # Perform logout
                logout_params = {
                    "action": "logout",
                    "token": csrf_token,
                    "format": "json",
                }
                self.session.post(self.api_url, data=logout_params)
            except Exception:
                # Ignore logout errors, just clear session
                pass
            finally:
                self._logged_in = False
                self.session.cookies.clear()

    def get_csrf_token(self) -> str:
        """
        Get a CSRF token for making edits.

        Returns:
            CSRF token string.

        Raises:
            AuthenticationError: If not logged in or token retrieval fails.

        Example:
            >>> auth = WikiverseAuth(username="User@Bot", password="secret")
            >>> auth.login()
            >>> token = auth.get_csrf_token()
            >>> # Use token for edits
        """
        if not self.is_logged_in():
            raise AuthenticationError(
                "Not logged in. Call login() first before getting CSRF token."
            )

        try:
            token_params = {
                "action": "query",
                "meta": "tokens",
                "type": "csrf",
                "format": "json",
            }
            response = self.session.get(self.api_url, params=token_params)
            response.raise_for_status()
            data = response.json()

            if "query" in data and "tokens" in data["query"]:
                csrf_token: str = data["query"]["tokens"]["csrftoken"]
                return csrf_token
            else:
                raise AuthenticationError(f"Failed to get CSRF token. Response: {data}")

        except requests.RequestException as e:
            raise AuthenticationError(f"Network error getting CSRF token: {str(e)}")

    def __repr__(self) -> str:
        status = (
            "logged in"
            if self._logged_in
            else ("authenticated" if self.is_authenticated() else "not authenticated")
        )
        return (
            f"WikiverseAuth(username={self.username!r}, "
            f"api_url={self.api_url!r}, {status})"
        )

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
