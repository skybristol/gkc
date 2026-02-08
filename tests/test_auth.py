"""Tests for authentication module."""

from gkc.auth import OpenStreetMapAuth, WikiverseAuth


class TestWikiverseAuth:
    """Tests for WikiverseAuth class."""

    def test_init_with_credentials(self):
        """Test initialization with explicit credentials."""
        auth = WikiverseAuth(username="testuser@testbot", password="testpass")
        assert auth.username == "testuser@testbot"
        assert auth.password == "testpass"
        assert auth.is_authenticated()

    def test_init_from_environment(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv("WIKIVERSE_USERNAME", "envuser@envbot")
        monkeypatch.setenv("WIKIVERSE_PASSWORD", "envpass")
        auth = WikiverseAuth()
        assert auth.username == "envuser@envbot"
        assert auth.password == "envpass"
        assert auth.is_authenticated()

    def test_init_partial_credentials(self):
        """Test initialization with partial credentials."""
        auth = WikiverseAuth(username="testuser@testbot")
        assert auth.username == "testuser@testbot"
        assert auth.password is None
        assert not auth.is_authenticated()

    def test_init_no_credentials(self):
        """Test initialization without credentials."""
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

    def test_get_bot_name_no_username(self):
        """Test get_bot_name with no username."""
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

    def test_get_account_name_no_username(self):
        """Test get_account_name with no username."""
        auth = WikiverseAuth()
        assert auth.get_account_name() is None


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

    def test_init_partial_credentials(self):
        """Test initialization with partial credentials."""
        auth = OpenStreetMapAuth(username="testuser")
        assert auth.username == "testuser"
        assert auth.password is None
        assert not auth.is_authenticated()

    def test_init_no_credentials(self):
        """Test initialization without credentials."""
        auth = OpenStreetMapAuth()
        assert not auth.is_authenticated()

    def test_repr(self):
        """Test string representation."""
        auth = OpenStreetMapAuth(username="testuser", password="testpass")
        repr_str = repr(auth)
        assert "OpenStreetMapAuth" in repr_str
        assert "testuser" in repr_str
        assert "authenticated" in repr_str
