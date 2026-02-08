"""Tests for Wikidata utilities module."""

from unittest.mock import Mock, patch

import pytest

from gkc.wd import (
    WikidataFetchError,
    fetch_entity_rdf,
    fetch_entity_schema,
    get_entity_uri,
    validate_entity_id,
)


class TestFetchEntityRdf:
    """Tests for fetch_entity_rdf function."""

    @patch("gkc.wd.requests.get")
    def test_fetch_entity_rdf_success(self, mock_get):
        """Test successful RDF fetch."""
        mock_response = Mock()
        mock_response.text = "@prefix wd: <http://www.wikidata.org/entity/> ."
        mock_get.return_value = mock_response

        result = fetch_entity_rdf("Q42")

        assert result == "@prefix wd: <http://www.wikidata.org/entity/> ."
        mock_get.assert_called_once()
        assert "Q42.ttl" in mock_get.call_args[0][0]

    @patch("gkc.wd.requests.get")
    def test_fetch_entity_rdf_different_formats(self, mock_get):
        """Test fetching RDF in different formats."""
        mock_response = Mock()
        mock_response.text = "RDF data"
        mock_get.return_value = mock_response

        # Test Turtle
        fetch_entity_rdf("Q42", format="ttl")
        assert "Q42.ttl" in mock_get.call_args[0][0]

        # Test RDF/XML
        fetch_entity_rdf("Q42", format="rdf")
        assert "Q42.rdf" in mock_get.call_args[0][0]

        # Test N-Triples
        fetch_entity_rdf("Q42", format="nt")
        assert "Q42.nt" in mock_get.call_args[0][0]

    def test_fetch_entity_rdf_invalid_format(self):
        """Test error with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            fetch_entity_rdf("Q42", format="invalid")
        assert "Invalid format" in str(exc_info.value)

    def test_fetch_entity_rdf_no_qid(self):
        """Test error when no QID provided."""
        with pytest.raises(ValueError) as exc_info:
            fetch_entity_rdf("")
        assert "required" in str(exc_info.value)

    @patch("gkc.wd.requests.get")
    def test_fetch_entity_rdf_network_error(self, mock_get):
        """Test handling of network errors."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(WikidataFetchError) as exc_info:
            fetch_entity_rdf("Q42")
        assert "Failed to fetch RDF" in str(exc_info.value)

    @patch("gkc.wd.requests.get")
    def test_fetch_entity_rdf_custom_user_agent(self, mock_get):
        """Test custom user agent."""
        mock_response = Mock()
        mock_response.text = "RDF data"
        mock_get.return_value = mock_response

        fetch_entity_rdf("Q42", user_agent="TestAgent/1.0")

        headers = mock_get.call_args[1]["headers"]
        assert headers["User-Agent"] == "TestAgent/1.0"


class TestFetchEntitySchema:
    """Tests for fetch_entity_schema function."""

    @patch("gkc.wd.requests.get")
    def test_fetch_entity_schema_success(self, mock_get):
        """Test successful EntitySchema fetch."""
        mock_response = Mock()
        mock_response.text = "PREFIX wd: <http://www.wikidata.org/entity/>"
        mock_get.return_value = mock_response

        result = fetch_entity_schema("E502")

        assert result == "PREFIX wd: <http://www.wikidata.org/entity/>"
        mock_get.assert_called_once()
        assert "E502" in mock_get.call_args[0][0]

    def test_fetch_entity_schema_no_eid(self):
        """Test error when no EID provided."""
        with pytest.raises(ValueError) as exc_info:
            fetch_entity_schema("")
        assert "required" in str(exc_info.value)

    @patch("gkc.wd.requests.get")
    def test_fetch_entity_schema_network_error(self, mock_get):
        """Test handling of network errors."""
        import requests

        mock_get.side_effect = requests.RequestException("Network error")

        with pytest.raises(WikidataFetchError) as exc_info:
            fetch_entity_schema("E502")
        assert "Failed to fetch EntitySchema" in str(exc_info.value)

    @patch("gkc.wd.requests.get")
    def test_fetch_entity_schema_custom_user_agent(self, mock_get):
        """Test custom user agent."""
        mock_response = Mock()
        mock_response.text = "Schema data"
        mock_get.return_value = mock_response

        fetch_entity_schema("E502", user_agent="TestAgent/1.0")

        headers = mock_get.call_args[1]["headers"]
        assert headers["User-Agent"] == "TestAgent/1.0"


class TestGetEntityUri:
    """Tests for get_entity_uri function."""

    def test_get_entity_uri_item(self):
        """Test getting URI for item."""
        uri = get_entity_uri("Q42")
        assert uri == "http://www.wikidata.org/entity/Q42"

    def test_get_entity_uri_property(self):
        """Test getting URI for property."""
        uri = get_entity_uri("P31")
        assert uri == "http://www.wikidata.org/entity/P31"

    def test_get_entity_uri_lexeme(self):
        """Test getting URI for lexeme."""
        uri = get_entity_uri("L1")
        assert uri == "http://www.wikidata.org/entity/L1"

    def test_get_entity_uri_entityschema(self):
        """Test getting URI for EntitySchema."""
        uri = get_entity_uri("E502")
        assert uri == "http://www.wikidata.org/entity/E502"

    def test_get_entity_uri_empty(self):
        """Test error with empty string."""
        with pytest.raises(ValueError):
            get_entity_uri("")


class TestValidateEntityId:
    """Tests for validate_entity_id function."""

    def test_validate_entity_id_valid_item(self):
        """Test validation of valid item IDs."""
        assert validate_entity_id("Q42") is True
        assert validate_entity_id("Q1") is True
        assert validate_entity_id("Q123456789") is True

    def test_validate_entity_id_valid_property(self):
        """Test validation of valid property IDs."""
        assert validate_entity_id("P31") is True
        assert validate_entity_id("P1") is True

    def test_validate_entity_id_valid_lexeme(self):
        """Test validation of valid lexeme IDs."""
        assert validate_entity_id("L1") is True
        assert validate_entity_id("L12345") is True

    def test_validate_entity_id_valid_entityschema(self):
        """Test validation of valid EntitySchema IDs."""
        assert validate_entity_id("E502") is True
        assert validate_entity_id("E1") is True

    def test_validate_entity_id_invalid_prefix(self):
        """Test validation of invalid prefixes."""
        assert validate_entity_id("X42") is False
        assert validate_entity_id("Z1") is False

    def test_validate_entity_id_invalid_format(self):
        """Test validation of invalid formats."""
        assert validate_entity_id("Q") is False
        assert validate_entity_id("Q-1") is False
        assert validate_entity_id("Qabc") is False
        assert validate_entity_id("42") is False
        assert validate_entity_id("") is False
        assert validate_entity_id("invalid") is False

    def test_validate_entity_id_none_or_non_string(self):
        """Test validation with None or non-string input."""
        assert validate_entity_id(None) is False
        assert validate_entity_id(42) is False
        assert validate_entity_id([]) is False
