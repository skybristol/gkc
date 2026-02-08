"""Tests for authentication module."""

from gkc.auth import OpenStreetMapAuth, WikidataAuth, WikipediaAuth


class TestWikidataAuth:
    """Tests for WikidataAuth class."""

    def test_init_with_credentials(self):
        """Test initialization with explicit credentials."""
        auth = WikidataAuth(username="testuser", password="testpass")
        assert auth.username == "testuser"
        assert auth.password == "testpass"
        assert auth.is_authenticated()

    def test_init_from_environment(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv("WIKIDATA_USERNAME", "envuser")
        monkeypatch.setenv("WIKIDATA_PASSWORD", "envpass")
        auth = WikidataAuth()
        assert auth.username == "envuser"
        assert auth.password == "envpass"
        assert auth.is_authenticated()

    def test_init_partial_credentials(self):
        """Test initialization with partial credentials."""
        auth = WikidataAuth(username="testuser")
        assert auth.username == "testuser"
        assert auth.password is None
        assert not auth.is_authenticated()

    def test_init_no_credentials(self):
        """Test initialization without credentials."""
        # Clear any existing environment variables
        auth = WikidataAuth()
        assert not auth.is_authenticated()

    def test_repr(self):
        """Test string representation."""
        auth = WikidataAuth(username="testuser", password="testpass")
        repr_str = repr(auth)
        assert "WikidataAuth" in repr_str
        assert "testuser" in repr_str
        assert "authenticated" in repr_str


class TestWikipediaAuth:
    """Tests for WikipediaAuth class."""

    def test_init_with_credentials(self):
        """Test initialization with explicit credentials."""
        auth = WikipediaAuth(username="testuser", password="testpass")
        assert auth.username == "testuser"
        assert auth.password == "testpass"
        assert auth.is_authenticated()

    def test_init_from_environment(self, monkeypatch):
        """Test initialization from environment variables."""
        monkeypatch.setenv("WIKIPEDIA_USERNAME", "envuser")
        monkeypatch.setenv("WIKIPEDIA_PASSWORD", "envpass")
        auth = WikipediaAuth()
        assert auth.username == "envuser"
        assert auth.password == "envpass"
        assert auth.is_authenticated()

    def test_init_partial_credentials(self):
        """Test initialization with partial credentials."""
        auth = WikipediaAuth(username="testuser")
        assert auth.username == "testuser"
        assert auth.password is None
        assert not auth.is_authenticated()

    def test_init_no_credentials(self):
        """Test initialization without credentials."""
        auth = WikipediaAuth()
        assert not auth.is_authenticated()

    def test_repr(self):
        """Test string representation."""
        auth = WikipediaAuth(username="testuser", password="testpass")
        repr_str = repr(auth)
        assert "WikipediaAuth" in repr_str
        assert "testuser" in repr_str
        assert "authenticated" in repr_str


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
