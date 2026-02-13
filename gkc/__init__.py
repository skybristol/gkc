"""
GKC - Global Knowledge Commons

A Python package for working with the Global Knowledge Commons including
Wikidata, Wikipedia, Wikimedia Commons, and OpenStreetMap.

The package is organized around stages of the distillation metaphor: taking
messy input ingredients and distilling them to produce more usable, linked,
and validated content.
"""

__version__ = "0.1.0"

# Core imports organized by module

# Authentication (core infrastructure)
from gkc.auth import AuthenticationError, OpenStreetMapAuth, WikiverseAuth

# Bottler (final output transformation)
from gkc.bottler import (
    ClaimBuilder,
    DataTypeTransformer,
    Distillate,
    SnakBuilder,
)

# Cooperage (schema and reference management)
from gkc.cooperage import (
    CooperageError,
    fetch_entity_rdf,
    fetch_schema_specification,
    get_entity_uri,
    validate_entity_reference,
)

# Recipe (transformation blueprint design)
from gkc.recipe import (
    PropertyCatalog,
    PropertyProfile,
    RecipeBuilder,
    SpecificationExtractor,
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

# Spirit Safe (validation and quality gates)
from gkc.spirit_safe import SpiritSafeValidationError, SpiritSafeValidator

# Backwards compatibility aliases (deprecated - old names for legacy code)
fetch_entity_schema = fetch_schema_specification  # noqa: F401
validate_entity_id = validate_entity_reference  # noqa: F401
WikidataFetchError = CooperageError  # noqa: F401

ClaimsMapBuilder = RecipeBuilder  # noqa: F401
PropertyInfo = PropertyProfile  # noqa: F401
ShExPropertyExtractor = SpecificationExtractor  # noqa: F401
WikidataPropertyFetcher = PropertyCatalog  # noqa: F401
ShExValidator = SpiritSafeValidator  # noqa: F401
ShExValidationError = SpiritSafeValidationError  # noqa: F401
PropertyMapper = Distillate  # noqa: F401

__all__ = [
    # Authentication
    "AuthenticationError",
    "OpenStreetMapAuth",
    "WikiverseAuth",
    # Bottler (new names)
    "ClaimBuilder",
    "DataTypeTransformer",
    "Distillate",
    "SnakBuilder",
    # Cooperage (new names)
    "CooperageError",
    "fetch_entity_rdf",
    "fetch_schema_specification",
    "get_entity_uri",
    "validate_entity_reference",
    # Recipe (new names)
    "PropertyCatalog",
    "PropertyProfile",
    "RecipeBuilder",
    "SpecificationExtractor",
    # Sitelinks
    "SitelinkValidator",
    "check_wikipedia_page",
    "validate_sitelink_dict",
    # SPARQL
    "SPARQLError",
    "SPARQLQuery",
    "execute_sparql",
    "execute_sparql_to_dataframe",
    # Spirit Safe (new names)
    "SpiritSafeValidationError",
    "SpiritSafeValidator",
    # Backwards compatibility (deprecated, old names)
    "ClaimsMapBuilder",
    "PropertyInfo",
    "PropertyMapper",
    "ShExPropertyExtractor",
    "ShExValidationError",
    "ShExValidator",
    "WikidataFetchError",
    "WikidataPropertyFetcher",
    "fetch_entity_schema",
    "validate_entity_id",
]
