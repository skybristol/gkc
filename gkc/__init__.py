"""
GKC - Global Knowledge Commons

A Python package for working with the Global Knowledge Commons including
Wikidata, Wikipedia, Wikimedia Commons, and OpenStreetMap.
"""

__version__ = "0.1.0"

from gkc.auth import AuthenticationError, OpenStreetMapAuth, WikiverseAuth
from gkc.mapping_builder import (
    ClaimsMapBuilder,
    PropertyInfo,
    ShExPropertyExtractor,
    WikidataPropertyFetcher,
)
from gkc.shex import ShExValidationError, ShExValidator
from gkc.sitelinks import (
    SitelinkValidator,
    check_wikipedia_page,
    validate_sitelink_dict,
)
from gkc.sparql import (
    SPARQLError,
    SPARQLQuery,
    execute_sparql,
    execute_sparql_to_dataframe,
)
from gkc.wd import WikidataFetchError, fetch_entity_rdf, fetch_entity_schema

__all__ = [
    "WikiverseAuth",
    "OpenStreetMapAuth",
    "AuthenticationError",
    "ShExValidator",
    "ShExValidationError",
    "WikidataFetchError",
    "fetch_entity_rdf",
    "fetch_entity_schema",
    "ClaimsMapBuilder",
    "PropertyInfo",
    "ShExPropertyExtractor",
    "WikidataPropertyFetcher",
    "SitelinkValidator",
    "check_wikipedia_page",
    "validate_sitelink_dict",
    "SPARQLError",
    "SPARQLQuery",
    "execute_sparql",
    "execute_sparql_to_dataframe",
]
