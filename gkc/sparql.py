"""
SPARQL query execution utilities for querying Wikidata and other SPARQL endpoints.

This module provides utilities for executing SPARQL queries against Wikidata
or custom SPARQL endpoints, with support for both Wikidata Query Service URL format
and raw query strings.
"""

from typing import Any, Optional
from urllib.parse import unquote, urlparse

import requests

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


DEFAULT_WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
DEFAULT_USER_AGENT = "GKC-SPARQL/1.0 (https://github.com/skybristol/gkc)"


class SPARQLError(Exception):
    """Raised when a SPARQL query fails."""

    pass


class SPARQLQuery:
    """Execute SPARQL queries against a SPARQL endpoint."""

    def __init__(
        self,
        endpoint: str = DEFAULT_WIKIDATA_ENDPOINT,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = 30,
    ):
        """
        Initialize SPARQL query executor.

        Args:
            endpoint: SPARQL endpoint URL (default: Wikidata)
            user_agent: User agent string for HTTP requests
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    @staticmethod
    def parse_wikidata_query_url(url: str) -> str:
        """
        Extract and decode SPARQL query from Wikidata Query Service URL.

        The Wikidata Query Service URL format is:
        https://query.wikidata.org/#<URL_ENCODED_QUERY>

        Args:
            url: Wikidata Query Service URL

        Returns:
            Decoded SPARQL query string

        Raises:
            SPARQLError: If URL is not a valid Wikidata Query Service URL

        Example:
            >>> url = "https://query.wikidata.org/#SELECT%20%3Fitem..."
            >>> query = SPARQLQuery.parse_wikidata_query_url(url)
        """
        try:
            # Parse the URL
            parsed = urlparse(url)

            # Check if it's a Wikidata Query Service URL
            if "query.wikidata.org" not in parsed.netloc:
                raise SPARQLError(f"Not a Wikidata Query Service URL: {parsed.netloc}")

            # Extract the fragment (everything after #)
            fragment = parsed.fragment
            if not fragment:
                raise SPARQLError("No query found in URL fragment (after #)")

            # URL decode the fragment
            decoded_query = unquote(fragment)

            return decoded_query
        except Exception as e:
            if isinstance(e, SPARQLError):
                raise
            raise SPARQLError(f"Failed to parse Wikidata URL: {str(e)}")

    @staticmethod
    def normalize_query(query: str) -> str:
        """
        Normalize a SPARQL query string.

        If the query appears to be a Wikidata Query Service URL,
        extract and decode it. Otherwise, return as-is.

        Args:
            query: SPARQL query string or Wikidata Query Service URL

        Returns:
            Normalized SPARQL query string
        """
        query = query.strip()

        # Check if it's a URL
        if query.startswith("http://") or query.startswith("https://"):
            return SPARQLQuery.parse_wikidata_query_url(query)

        return query

    def query(
        self,
        query: str,
        format: str = "json",
        raw: bool = False,
    ) -> Any:
        """
        Execute a SPARQL query.

        Args:
            query: SPARQL query string or Wikidata Query Service URL
            format: Response format ('json', 'xml', 'csv', 'tsv')
            raw: If False, parse JSON to Python dict; if True, return raw string

        Returns:
            Query results (dict if JSON and raw=False, else string)

        Raises:
            SPARQLError: If query fails

        Example:
            >>> executor = SPARQLQuery()
            >>> results = executor.query(
            ...     '''SELECT ?item ?itemLabel WHERE {
            ...         ?item wdt:P31 wd:Q7840353 .
            ...         SERVICE wikibase:label {
            ...             bd:serviceParam wikibase:language "en" .
            ...         }
            ...     }'''
            ... )
        """
        # Normalize query
        normalized_query = self.normalize_query(query)

        # Prepare request parameters
        params = {
            "query": normalized_query,
            "format": format,
        }

        try:
            response = self.session.get(
                self.endpoint,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()

            # Parse response
            if format == "json" and not raw:
                return response.json()
            else:
                return response.text

        except requests.Timeout:
            raise SPARQLError(f"Query timeout after {self.timeout} seconds")
        except requests.RequestException as e:
            raise SPARQLError(f"Query failed: {str(e)}")
        except ValueError as e:
            raise SPARQLError(f"Failed to parse response: {str(e)}")

    def to_dataframe(self, query: str) -> "pd.DataFrame":
        """
        Execute a SPARQL query and return results as a pandas DataFrame.

        Args:
            query: SPARQL query string or Wikidata Query Service URL

        Returns:
            pandas DataFrame with query results

        Raises:
            SPARQLError: If pandas is not installed or query fails

        Example:
            >>> executor = SPARQLQuery()
            >>> df = executor.to_dataframe(
            ...     'SELECT ?item ?itemLabel WHERE { ... }'
            ... )
            >>> print(df.head())
        """
        if not HAS_PANDAS:
            raise SPARQLError(
                "pandas is required for to_dataframe(). "
                "Install with: pip install pandas"
            )

        # Execute query
        results = self.query(query, format="json", raw=False)

        # Extract bindings
        bindings = results.get("results", {}).get("bindings", [])

        # Convert to DataFrame
        data = []
        for binding in bindings:
            row = {}
            for var, value_obj in binding.items():
                # Value objects have structure: {"value": "...", "type": "..."}
                row[var] = value_obj.get("value")
            data.append(row)

        return pd.DataFrame(data)

    def to_dict_list(self, query: str) -> list[dict[str, str]]:
        """
        Execute a SPARQL query and return results as a list of dicts.

        Each dict represents one result row, with variable names as keys
        and result values as values.

        Args:
            query: SPARQL query string or Wikidata Query Service URL

        Returns:
            List of dictionaries

        Example:
            >>> executor = SPARQLQuery()
            >>> results = executor.to_dict_list(
            ...     'SELECT ?item ?itemLabel WHERE { ... }'
            ... )
            >>> for row in results:
            ...     print(row)
        """
        results = self.query(query, format="json", raw=False)
        bindings = results.get("results", {}).get("bindings", [])

        data = []
        for binding in bindings:
            row = {}
            for var, value_obj in binding.items():
                row[var] = value_obj.get("value")
            data.append(row)

        return data

    def to_csv(self, query: str, filepath: Optional[str] = None) -> str:
        """
        Execute a SPARQL query and return results as CSV.

        Args:
            query: SPARQL query string or Wikidata Query Service URL
            filepath: Optional file path to save CSV results

        Returns:
            CSV string

        Example:
            >>> executor = SPARQLQuery()
            >>> csv_data = executor.to_csv(
            ...     'SELECT ?item ?itemLabel WHERE { ... }',
            ...     filepath="results.csv"
            ... )
        """
        csv_data = self.query(query, format="csv", raw=True)

        if filepath:
            with open(filepath, "w") as f:
                f.write(csv_data)

        return csv_data


def execute_sparql(
    query: str,
    endpoint: str = DEFAULT_WIKIDATA_ENDPOINT,
    format: str = "json",
) -> Any:
    """
    Convenience function to execute a single SPARQL query.

    Args:
        query: SPARQL query string or Wikidata Query Service URL
        endpoint: SPARQL endpoint (default: Wikidata)
        format: Response format ('json', 'xml', 'csv', 'tsv')

    Returns:
        Query results

    Example:
        >>> results = execute_sparql(
        ...     'SELECT ?item ?itemLabel WHERE { ... }'
        ... )
    """
    executor = SPARQLQuery(endpoint=endpoint)
    return executor.query(query, format=format)


def execute_sparql_to_dataframe(
    query: str,
    endpoint: str = DEFAULT_WIKIDATA_ENDPOINT,
) -> "pd.DataFrame":
    """
    Convenience function to execute a SPARQL query and return DataFrame.

    Args:
        query: SPARQL query string or Wikidata Query Service URL
        endpoint: SPARQL endpoint (default: Wikidata)

    Returns:
        pandas DataFrame with query results

    Example:
        >>> df = execute_sparql_to_dataframe(
        ...     'SELECT ?item ?itemLabel WHERE { ... }'
        ... )
    """
    executor = SPARQLQuery(endpoint=endpoint)
    return executor.to_dataframe(query)
