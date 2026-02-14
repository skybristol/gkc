"""Tests for authentication module."""

from unittest.mock import Mock, patch

import pytest

from gkc.auth import AuthenticationError, OpenStreetMapAuth, WikiverseAuth


class TestWikiverseAuth:
    """Tests for WikiverseAuth class."""

    def test_init_with_credentials(self):
        """Test initialization with explicit credentials."""
        auth = WikiverseAuth(username="testuser@testbot", password="testpass")
        assert auth.username == "testuser@testbot"
        assert auth.password == "testpass"
        assert auth.is_authenticated()
        assert not auth.is_logged_in()

    def test_init_from_environment(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv("WIKIVERSE_USERNAME", "envuser@envbot")
        monkeypatch.setenv("WIKIVERSE_PASSWORD", "envpass")
        auth = WikiverseAuth()
        assert auth.username == "envuser@envbot"
        assert auth.password == "envpass"
        assert auth.is_authenticated()

    def test_init_with_custom_api_url(self):
        """Test initialization with custom API URL."""
        auth = WikiverseAuth(
            username="testuser@testbot",
            password="testpass",
            api_url="https://custom.wiki.org/w/api.php",
        )
        assert auth.api_url == "https://custom.wiki.org/w/api.php"

    def test_init_with_api_url_shortcut_wikidata(self):
        """Test initialization with API URL shortcut for Wikidata."""
        auth = WikiverseAuth(
            username="testuser@testbot", password="testpass", api_url="wikidata"
        )
        assert auth.api_url == "https://www.wikidata.org/w/api.php"

    def test_init_with_api_url_shortcut_wikipedia(self):
        """Test initialization with API URL shortcut for Wikipedia."""
        auth = WikiverseAuth(
            username="testuser@testbot", password="testpass", api_url="wikipedia"
        )
        assert auth.api_url == "https://en.wikipedia.org/w/api.php"

    def test_init_with_api_url_shortcut_commons(self):
        """Test initialization with API URL shortcut for Commons."""
        auth = WikiverseAuth(
            username="testuser@testbot", password="testpass", api_url="commons"
        )
        assert auth.api_url == "https://commons.wikimedia.org/w/api.php"

    def test_default_api_url_is_wikidata(self):
        """Test that default API URL is Wikidata."""
        auth = WikiverseAuth(username="testuser@testbot", password="testpass")
        assert auth.api_url == "https://www.wikidata.org/w/api.php"

    def test_api_url_from_environment(self, monkeypatch):
        """Test API URL from environment variable."""
        monkeypatch.setenv("WIKIVERSE_USERNAME", "envuser@envbot")
        monkeypatch.setenv("WIKIVERSE_PASSWORD", "envpass")
        monkeypatch.setenv("WIKIVERSE_API_URL", "https://custom.example.com/w/api.php")
        auth = WikiverseAuth()
        assert auth.api_url == "https://custom.example.com/w/api.php"

    def test_init_partial_credentials(self, monkeypatch):
        """Test initialization with partial credentials."""
        monkeypatch.delenv("WIKIVERSE_PASSWORD", raising=False)
        auth = WikiverseAuth(username="testuser@testbot")
        assert auth.username == "testuser@testbot"
        assert auth.password is None
        assert not auth.is_authenticated()

    def test_init_no_credentials(self, monkeypatch):
        """Test initialization without credentials."""
        monkeypatch.delenv("WIKIVERSE_USERNAME", raising=False)
        monkeypatch.delenv("WIKIVERSE_PASSWORD", raising=False)
        auth = WikiverseAuth()
        assert not auth.is_authenticated()

    def test_repr(self):
        """Test string representation."""
        auth = WikiverseAuth(username="testuser@testbot", password="testpass")
        repr_str = repr(auth)
        assert "WikiverseAuth" in repr_str
        assert "testuser@testbot" in repr_str
        assert "authenticated" in repr_str

    def test_get_bot_name(self):
        """Test extracting bot name from username."""
        auth = WikiverseAuth(username="alice@mybot", password="pass")
        assert auth.get_bot_name() == "mybot"

    def test_get_bot_name_no_bot(self):
        """Test get_bot_name with no bot format."""
        auth = WikiverseAuth(username="alice", password="pass")
        assert auth.get_bot_name() is None

    def test_get_bot_name_no_username(self, monkeypatch):
        """Test get_bot_name with no username."""
        monkeypatch.delenv("WIKIVERSE_USERNAME", raising=False)
        monkeypatch.delenv("WIKIVERSE_PASSWORD", raising=False)
        auth = WikiverseAuth()
        assert auth.get_bot_name() is None

    def test_get_account_name(self):
        """Test extracting account name from username."""
        auth = WikiverseAuth(username="alice@mybot", password="pass")
        assert auth.get_account_name() == "alice"

    def test_get_account_name_no_bot(self):
        """Test get_account_name with no bot format."""
        auth = WikiverseAuth(username="alice", password="pass")
        assert auth.get_account_name() is None

    def test_get_account_name_no_username(self, monkeypatch):
        """Test get_account_name with no username."""
        monkeypatch.delenv("WIKIVERSE_USERNAME", raising=False)
        monkeypatch.delenv("WIKIVERSE_PASSWORD", raising=False)
        auth = WikiverseAuth()
        assert auth.get_account_name() is None

    @patch("gkc.auth.requests.Session")
    def test_login_success(self, mock_session_class):
        """Test successful login."""
        # Setup mock session
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            "query": {"tokens": {"logintoken": "test_token"}}
        }

        # Mock login request
        login_response = Mock()
        login_response.json.return_value = {"login": {"result": "Success"}}

        mock_session.get.return_value = token_response
        mock_session.post.return_value = login_response

        auth = WikiverseAuth(username="testuser@testbot", password="testpass")
        result = auth.login()

        assert result is True
        assert auth.is_logged_in()

    @patch("gkc.auth.requests.Session")
    def test_login_failure(self, mock_session_class):
        """Test failed login."""
        # Setup mock session
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock token request
        token_response = Mock()
        token_response.json.return_value = {
            "query": {"tokens": {"logintoken": "test_token"}}
        }

        # Mock login request with failure
        login_response = Mock()
        login_response.json.return_value = {
            "login": {"result": "Failed", "reason": "Invalid credentials"}
        }

        mock_session.get.return_value = token_response
        mock_session.post.return_value = login_response

        auth = WikiverseAuth(username="testuser@testbot", password="testpass")

        with pytest.raises(AuthenticationError) as exc_info:
            auth.login()

        assert "Failed" in str(exc_info.value)
        assert not auth.is_logged_in()

    def test_login_without_credentials(self, monkeypatch):
        """Test login without credentials."""
        monkeypatch.delenv("WIKIVERSE_USERNAME", raising=False)
        monkeypatch.delenv("WIKIVERSE_PASSWORD", raising=False)
        auth = WikiverseAuth()

        with pytest.raises(AuthenticationError) as exc_info:
            auth.login()

        assert "credentials not provided" in str(exc_info.value)

    @patch("gkc.auth.requests.Session")
    def test_get_csrf_token(self, mock_session_class):
        """Test getting CSRF token."""
        # Setup mock session
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock token response
        token_response = Mock()
        token_response.json.return_value = {
            "query": {"tokens": {"csrftoken": "csrf_test_token"}}
        }
        mock_session.get.return_value = token_response

        auth = WikiverseAuth(username="testuser@testbot", password="testpass")
        auth._logged_in = True  # Simulate logged in state

        token = auth.get_csrf_token()
        assert token == "csrf_test_token"

    def test_get_csrf_token_not_logged_in(self):
        """Test getting CSRF token when not logged in."""
        auth = WikiverseAuth(username="testuser@testbot", password="testpass")

        with pytest.raises(AuthenticationError) as exc_info:
            auth.get_csrf_token()

        assert "Not logged in" in str(exc_info.value)

    @patch("gkc.auth.requests.Session")
    def test_logout(self, mock_session_class):
        """Test logout."""
        # Setup mock session
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock responses
        token_response = Mock()
        token_response.json.return_value = {
            "query": {"tokens": {"csrftoken": "csrf_token"}}
        }
        mock_session.get.return_value = token_response

        auth = WikiverseAuth(username="testuser@testbot", password="testpass")
        auth._logged_in = True

        auth.logout()
        assert not auth.is_logged_in()
        mock_session.cookies.clear.assert_called_once()


class TestOpenStreetMapAuth:
    """Tests for OpenStreetMapAuth class."""

    def test_init_with_credentials(self):
        """Test initialization with explicit credentials."""
        auth = OpenStreetMapAuth(username="testuser", password="testpass")
        assert auth.username == "testuser"
        assert auth.password == "testpass"
        assert auth.is_authenticated()

    def test_init_from_environment(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv("OPENSTREETMAP_USERNAME", "envuser")
        monkeypatch.setenv("OPENSTREETMAP_PASSWORD", "envpass")
        auth = OpenStreetMapAuth()
        assert auth.username == "envuser"
        assert auth.password == "envpass"
        assert auth.is_authenticated()

    def test_init_partial_credentials(self, monkeypatch):
        """Test initialization with partial credentials."""
        monkeypatch.delenv("OPENSTREETMAP_PASSWORD", raising=False)
        auth = OpenStreetMapAuth(username="testuser")
        assert auth.username == "testuser"
        assert auth.password is None
        assert not auth.is_authenticated()

    def test_init_no_credentials(self, monkeypatch):
        """Test initialization without credentials."""
        monkeypatch.delenv("OPENSTREETMAP_USERNAME", raising=False)
        monkeypatch.delenv("OPENSTREETMAP_PASSWORD", raising=False)
        auth = OpenStreetMapAuth()
        assert not auth.is_authenticated()

    def test_repr(self):
        """Test string representation."""
        auth = OpenStreetMapAuth(username="testuser", password="testpass")
        repr_str = repr(auth)
        assert "OpenStreetMapAuth" in repr_str
        assert "testuser" in repr_str
        assert "authenticated" in repr_str
