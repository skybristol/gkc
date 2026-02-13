"""
GKC - Global Knowledge Commons

A Python package for working with the Global Knowledge Commons including
Wikidata, Wikipedia, Wikimedia Commons, and OpenStreetMap.

The package is organized around stages of the distillation metaphor: taking
messy input ingredients and distilling them to produce more usable, linked,
and validated content.
"""

__version__ = "0.1.0"

# Authentication (core infrastructure)
from gkc.auth import AuthenticationError, OpenStreetMapAuth, WikiverseAuth

# Cooperage (schema and reference management)
from gkc.cooperage import (
    CooperageError,
    fetch_entity_rdf,
    fetch_schema_specification,
    get_entity_uri,
    validate_entity_reference,
)

# Backwards compat: old names from wd.py
fetch_entity_schema = fetch_schema_specification  # noqa: F401
validate_entity_id = validate_entity_reference  # noqa: F401
WikidataFetchError = CooperageError  # noqa: F401

# Recipe (transformation blueprint design)
from gkc.recipe import (
    PropertyCatalog,
    PropertyProfile,
    RecipeBuilder,
    SpecificationExtractor,
)

# Spirit Safe (validation and quality gates)
from gkc.spirit_safe import SpiritSafeValidationError, SpiritSafeValidator

# Bottler (final output transformation)
from gkc.bottler import (
    ClaimBuilder,
    DataTypeTransformer,
    Distillate,
    SnakBuilder,
)

# Sitelinks (cross-reference validation)
from gkc.sitelinks import (
    SitelinkValidator,
    check_wikipedia_page,
    validate_sitelink_dict,
)

# SPARQL (query utility, cross-cutting)
from gkc.sparql import (
    SPARQLError,
    SPARQLQuery,
    execute_sparql,
    execute_sparql_to_dataframe,
)

# Backwards compatibility aliases (deprecated)
from gkc.recipe import RecipeBuilder as ClaimsMapBuilder
from gkc.recipe import PropertyProfile as PropertyInfo
from gkc.recipe import SpecificationExtractor as ShExPropertyExtractor
from gkc.recipe import PropertyCatalog as WikidataPropertyFetcher
from gkc.spirit_safe import SpiritSafeValidator as ShExValidator
from gkc.spirit_safe import SpiritSafeValidationError as ShExValidationError
from gkc.cooperage import CooperageError as WikidataFetchError
from gkc.bottler import Distillate as PropertyMapper

__all__ = [
    # Authentication
    "WikiverseAuth",
    "OpenStreetMapAuth",
    "AuthenticationError",
    # Cooperage (new names)
    "CooperageError",
    "fetch_entity_rdf",
    "fetch_schema_specification",
    "get_entity_uri",
    "validate_entity_reference",
    # Recipe (new names)
    "RecipeBuilder",
    "PropertyProfile",
    "SpecificationExtractor",
    "PropertyCatalog",
    # Spirit Safe (new names)
    "SpiritSafeValidator",
    "SpiritSafeValidationError",
    # Bottler (new names)
    "Distillate",
    "ClaimBuilder",
    "SnakBuilder",
    "DataTypeTransformer",
    # Sitelinks
    "SitelinkValidator",
    "check_wikipedia_page",
    "validate_sitelink_dict",
    # SPARQL
    "SPARQLError",
    "SPARQLQuery",
    "execute_sparql",
    "execute_sparql_to_dataframe",
    # Backwards compatibility (deprecated, old names)
    "fetch_entity_schema",
    "validate_entity_id",
    "WikidataFetchError",
    "ClaimsMapBuilder",
    "PropertyInfo",
    "ShExPropertyExtractor",
    "WikidataPropertyFetcher",
    "ShExValidator",
    "ShExValidationError",
    "PropertyMapper",
]
