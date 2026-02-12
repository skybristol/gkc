"""Tests for SPARQL query utilities."""

import json
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest

from gkc.sparql import (
    DEFAULT_WIKIDATA_ENDPOINT,
    SPARQLError,
    SPARQLQuery,
    execute_sparql,
    execute_sparql_to_dataframe,
)


class TestSPARQLQueryParseWikidataURL:
    """Test Wikidata URL parsing."""

    def test_parse_simple_wikidata_url(self):
        """Parse a simple Wikidata Query Service URL."""
        query_text = "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }"
        encoded = quote(query_text)
        url = f"https://query.wikidata.org/#{encoded}"

        result = SPARQLQuery.parse_wikidata_query_url(url)
        assert result == query_text

    def test_parse_wikidata_url_with_newlines(self):
        """Parse Wikidata URL with multi-line query."""
        query_text = """SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q7840353 .
  SERVICE wikibase:label {
    bd:serviceParam wikibase:language "en" .
  }
}"""
        encoded = quote(query_text)
        url = f"https://query.wikidata.org/#{encoded}"

        result = SPARQLQuery.parse_wikidata_query_url(url)
        assert result == query_text

    def test_parse_wikidata_url_empty_fragment(self):
        """Raise error for URL with no query."""
        url = "https://query.wikidata.org/#"

        with pytest.raises(SPARQLError, match="No query found"):
            SPARQLQuery.parse_wikidata_query_url(url)

    def test_parse_non_wikidata_url(self):
        """Raise error for non-Wikidata URL."""
        url = "https://example.com/#SELECT%20*"

        with pytest.raises(SPARQLError, match="Not a Wikidata Query Service URL"):
            SPARQLQuery.parse_wikidata_query_url(url)

    def test_parse_invalid_url(self):
        """Raise error for invalid URL."""
        with pytest.raises(SPARQLError):
            SPARQLQuery.parse_wikidata_query_url("not a url")


class TestSPARQLQueryNormalize:
    """Test query normalization."""

    def test_normalize_plain_query(self):
        """Normalize a plain SPARQL query."""
        query = "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }"
        assert SPARQLQuery.normalize_query(query) == query

    def test_normalize_wikidata_url(self):
        """Normalize a Wikidata URL to a query."""
        query_text = "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }"
        encoded = quote(query_text)
        url = f"https://query.wikidata.org/#{encoded}"

        result = SPARQLQuery.normalize_query(url)
        assert result == query_text

    def test_normalize_query_with_whitespace(self):
        """Normalize query with extra whitespace."""
        query = "  SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }  "
        result = SPARQLQuery.normalize_query(query)
        assert result == "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }"


class TestSPARQLQueryExecution:
    """Test SPARQL query execution."""

    @patch("gkc.sparql.requests.Session.get")
    def test_query_json_response(self, mock_get):
        """Execute query with JSON response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_get.return_value = mock_response

        executor = SPARQLQuery()
        result = executor.query("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }")

        assert result == {"results": {"bindings": []}}
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["format"] == "json"

    @patch("gkc.sparql.requests.Session.get")
    def test_query_csv_response(self, mock_get):
        """Execute query with CSV response."""
        mock_response = MagicMock()
        mock_response.text = "item,itemLabel\nQ1,One"
        mock_get.return_value = mock_response

        executor = SPARQLQuery()
        result = executor.query(
            "SELECT ?item ?itemLabel WHERE { ...}", format="csv", raw=True
        )

        assert result == "item,itemLabel\nQ1,One"
        call_args = mock_get.call_args
        assert call_args[1]["params"]["format"] == "csv"

    @patch("gkc.sparql.requests.Session.get")
    def test_query_with_url(self, mock_get):
        """Execute query provided as Wikidata URL."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_get.return_value = mock_response

        query_text = "SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }"
        encoded = quote(query_text)
        url = f"https://query.wikidata.org/#{encoded}"

        executor = SPARQLQuery()
        executor.query(url)

        call_args = mock_get.call_args
        assert call_args[1]["params"]["query"] == query_text

    @patch("gkc.sparql.requests.Session.get")
    def test_query_timeout(self, mock_get):
        """Handle query timeout."""
        import requests

        mock_get.side_effect = requests.Timeout()

        executor = SPARQLQuery()
        with pytest.raises(SPARQLError, match="timeout"):
            executor.query("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }")

    @patch("gkc.sparql.requests.Session.get")
    def test_query_connection_error(self, mock_get):
        """Handle connection error."""
        import requests

        mock_get.side_effect = requests.ConnectionError()

        executor = SPARQLQuery()
        with pytest.raises(SPARQLError, match="Query failed"):
            executor.query("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }")

    @patch("gkc.sparql.requests.Session.get")
    def test_query_http_error(self, mock_get):
        """Handle HTTP error."""
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.RequestException(
            "404 Not Found"
        )
        mock_get.return_value = mock_response

        executor = SPARQLQuery()
        with pytest.raises(SPARQLError):
            executor.query("SELECT ?item WHERE { ?item wdt:P31 wd:Q5 }")


class TestSPARQLToDataFrame:
    """Test DataFrame conversion."""

    @pytest.mark.skipif(
        not __import__("importlib.util").util.find_spec("pandas"),
        reason="pandas not installed",
    )
    @patch("gkc.sparql.requests.Session.get")
    def test_to_dataframe_with_pandas(self, mock_get):
        """Convert query results to DataFrame."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "head": {"vars": ["item", "itemLabel"]},
            "results": {
                "bindings": [
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q1"},
                        "itemLabel": {"value": "One"},
                    },
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q2"},
                        "itemLabel": {"value": "Two"},
                    },
                ]
            },
        }
        mock_get.return_value = mock_response

        executor = SPARQLQuery()
        df = executor.to_dataframe("SELECT ?item ?itemLabel WHERE { ... }")

        assert len(df) == 2
        assert list(df.columns) == ["item", "itemLabel"]
        assert df.iloc[0]["item"] == "http://www.wikidata.org/entity/Q1"
        assert df.iloc[0]["itemLabel"] == "One"

    def test_to_dataframe_without_pandas(self):
        """Raise error if pandas is not available."""
        with patch("gkc.sparql.HAS_PANDAS", False):
            executor = SPARQLQuery()
            with pytest.raises(SPARQLError, match="pandas is required"):
                executor.to_dataframe("SELECT ?item WHERE { ... }")


class TestSPARQLToDictList:
    """Test dictionary list conversion."""

    @patch("gkc.sparql.requests.Session.get")
    def test_to_dict_list(self, mock_get):
        """Convert query results to list of dicts."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "head": {"vars": ["item", "itemLabel"]},
            "results": {
                "bindings": [
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q1"},
                        "itemLabel": {"value": "One"},
                    },
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q2"},
                        "itemLabel": {"value": "Two"},
                    },
                ]
            },
        }
        mock_get.return_value = mock_response

        executor = SPARQLQuery()
        results = executor.to_dict_list("SELECT ?item ?itemLabel WHERE { ... }")

        assert len(results) == 2
        assert results[0] == {
            "item": "http://www.wikidata.org/entity/Q1",
            "itemLabel": "One",
        }
        assert results[1] == {
            "item": "http://www.wikidata.org/entity/Q2",
            "itemLabel": "Two",
        }


class TestSPARQLToCSV:
    """Test CSV conversion."""

    @patch("gkc.sparql.requests.Session.get")
    def test_to_csv(self, mock_get):
        """Convert query results to CSV."""
        csv_data = "item,itemLabel\nQ1,One\nQ2,Two"
        mock_response = MagicMock()
        mock_response.text = csv_data
        mock_get.return_value = mock_response

        executor = SPARQLQuery()
        result = executor.to_csv("SELECT ?item ?itemLabel WHERE { ... }")

        assert result == csv_data
        call_args = mock_get.call_args
        assert call_args[1]["params"]["format"] == "csv"

    @patch("gkc.sparql.requests.Session.get")
    def test_to_csv_with_file(self, mock_get, tmp_path):
        """Save CSV results to file."""
        csv_data = "item,itemLabel\nQ1,One\nQ2,Two"
        mock_response = MagicMock()
        mock_response.text = csv_data
        mock_get.return_value = mock_response

        filepath = tmp_path / "results.csv"

        executor = SPARQLQuery()
        result = executor.to_csv("SELECT ?item ?itemLabel WHERE { ... }", filepath=str(filepath))

        assert result == csv_data
        assert filepath.read_text() == csv_data


class TestSPARQLConvenienceFunctions:
    """Test convenience functions."""

    @patch("gkc.sparql.SPARQLQuery.query")
    def test_execute_sparql(self, mock_query):
        """Test execute_sparql convenience function."""
        mock_query.return_value = {"results": {"bindings": []}}

        result = execute_sparql("SELECT ?item WHERE { ... }")

        assert result == {"results": {"bindings": []}}
        mock_query.assert_called_once()

    @patch("gkc.sparql.SPARQLQuery.to_dataframe")
    def test_execute_sparql_to_dataframe(self, mock_to_df):
        """Test execute_sparql_to_dataframe convenience function."""
        try:
            import pandas as pd

            mock_df = pd.DataFrame({"item": ["Q1"], "itemLabel": ["One"]})
            mock_to_df.return_value = mock_df

            result = execute_sparql_to_dataframe(
                "SELECT ?item ?itemLabel WHERE { ... }"
            )

            assert isinstance(result, pd.DataFrame)
            mock_to_df.assert_called_once()
        except ImportError:
            pytest.skip("pandas not installed")


class TestSPARQLEndpointCustomization:
    """Test custom endpoint configuration."""

    @patch("gkc.sparql.requests.Session.get")
    def test_custom_endpoint(self, mock_get):
        """Use custom SPARQL endpoint."""
        custom_endpoint = "https://custom.sparql.endpoint/query"
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_get.return_value = mock_response

        executor = SPARQLQuery(endpoint=custom_endpoint)
        executor.query("SELECT ?item WHERE { ... }")

        call_args = mock_get.call_args
        assert call_args[0][0] == custom_endpoint

    @patch("gkc.sparql.requests.Session.get")
    def test_custom_user_agent(self, mock_get):
        """Use custom user agent."""
        custom_agent = "Custom-Agent/1.0"
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_get.return_value = mock_response

        executor = SPARQLQuery(user_agent=custom_agent)
        executor.query("SELECT ?item WHERE { ... }")

        # Check that session headers were set
        assert executor.session.headers.get("User-Agent") == custom_agent

    @patch("gkc.sparql.requests.Session.get")
    def test_custom_timeout(self, mock_get):
        """Use custom timeout."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_get.return_value = mock_response

        executor = SPARQLQuery(timeout=60)
        executor.query("SELECT ?item WHERE { ... }")

        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 60
