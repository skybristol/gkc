"""Runtime configuration helpers for GKC integrations.

Plain meaning: Read environment-based defaults in one place.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

DEFAULT_WIKIBASE_API_URL = "https://datadistillery.wikibase.cloud/w/api.php"
DEFAULT_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
DEFAULT_USER_AGENT = "GKC/1.0 (https://github.com/skybristol/gkc; data integration)"


@dataclass(frozen=True)
class WikibaseRuntimeConfig:
    """Wikibase-related runtime settings resolved from environment."""

    api_url: str
    sparql_endpoint: Optional[str]
    username: Optional[str]
    password: Optional[str]


def get_wikibase_runtime_config() -> WikibaseRuntimeConfig:
    """Return resolved Wikibase runtime settings.

    Resolution order:
      - API URL: DD_WB_API_URL or default Data Distillery URL
      - SPARQL endpoint: DD_WB_SPARQL_ENDPOINT or default Wikidata QS endpoint
            - Username/password: DD_WB_USERNAME/DD_WB_PASSWORD (optional)
    """

    api_url = os.environ.get("DD_WB_API_URL") or DEFAULT_WIKIBASE_API_URL
    sparql_endpoint = os.environ.get("DD_WB_SPARQL_ENDPOINT") or DEFAULT_SPARQL_ENDPOINT

    username = os.environ.get("DD_WB_USERNAME")
    password = os.environ.get("DD_WB_PASSWORD")

    return WikibaseRuntimeConfig(
        api_url=api_url,
        sparql_endpoint=sparql_endpoint,
        username=username,
        password=password,
    )
