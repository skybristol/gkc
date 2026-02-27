"""
GKC - Global Knowledge Commons

A Python package for distributing data across the Global Knowledge Commons including
Wikidata, Wikipedia, Wikimedia Commons, and OpenStreetMap.

## Two-Schema Architecture

GKC uses a two-schema design to enable multi-system data distribution:

1. **Unified Still Schema** (meta schema) - Canonical, system-agnostic
   data model
2. **Barrel Schemas** - Target system schemas (Wikidata EntitySchemas,
   OSM tagging, etc.)

Data flows: Source → Still → Unified Still Schema → Barrel Schema → Target

## Key Components

- **Cooperage** - Manages Barrel Schemas from target systems
  (EntitySchemas, tagging schemes, etc.)
- **Spirit Safe** - Validates data against profiles before processing
- **Bottler** - Transforms and exports data using specifications

See documentation at: https://datadistillery.org/
"""

from typing import Union

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

# Cooperage (Barrel Schema and reference management)
from gkc.cooperage import (
    CooperageError,
    fetch_entity_rdf,
    fetch_schema_specification,
    get_entity_uri,
    validate_entity_reference,
)

# Entity Profiles (GKC Entity Profile definitions)
from gkc.entity_profile import GKCEntityProfile

# YAML-first profiles (SpiritSafe)
from gkc.profiles import (
    FormSchemaGenerator,
    ProfileDefinition,
    ProfileLoader,
    ProfilePydanticGenerator,
    ProfileValidator,
    ValidationIssue,
    ValidationResult,
)

# ShEx validation utilities
from gkc.shex import ShexValidationError, ShexValidator

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

# SpiritSafe source configuration + lookup utilities
from gkc.spirit_safe import (
    DEFAULT_SPIRIT_SAFE_GITHUB_REPO,
    LookupCache,
    LookupFetcher,
    SpiritSafeSourceConfig,
    get_spirit_safe_source,
    hydrate_profile_lookups,
    resolve_profile_path,
    set_spirit_safe_source,
)

# Language Configuration
# Package-level language settings for multilingual data handling
_DEFAULT_LANGUAGES: Union[str, list[str]] = "en"


def set_languages(languages: Union[str, list[str]]) -> None:
    """Set the package-wide language configuration.

    Args:
        languages: Either:
            - A single language code string (e.g., "en")
            - A list of language codes (e.g., ["en", "es", "fr"])
            - The string "all" for all available languages

    Example:
        >>> import gkc
        >>> gkc.set_languages("en")  # Single language
        >>> gkc.set_languages(["en", "fr"])  # Multiple languages
        >>> gkc.set_languages("all")  # All languages

    Plain meaning: Choose which languages to work with in the package.
    """
    global _DEFAULT_LANGUAGES
    _DEFAULT_LANGUAGES = languages


def get_languages() -> Union[str, list[str]]:
    """Get the current language configuration.

    Returns:
        The current language setting (string or list of strings).

    Plain meaning: Find out which languages are set for processing.
    """
    return _DEFAULT_LANGUAGES


__all__ = [
    # Language Configuration
    "get_languages",
    "set_languages",
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
    # Entity Profiles
    "GKCEntityProfile",
    # YAML-first profiles
    "FormSchemaGenerator",
    "ProfileDefinition",
    "ProfileLoader",
    "ProfilePydanticGenerator",
    "ProfileValidator",
    "ValidationIssue",
    "ValidationResult",
    # Sitelinks
    "SitelinkValidator",
    "check_wikipedia_page",
    "validate_sitelink_dict",
    # SPARQL
    "SPARQLError",
    "SPARQLQuery",
    "execute_sparql",
    "execute_sparql_to_dataframe",
    # ShEx validation
    "ShexValidationError",
    "ShexValidator",
    # SpiritSafe source configuration + lookup utilities
    "DEFAULT_SPIRIT_SAFE_GITHUB_REPO",
    "SpiritSafeSourceConfig",
    "get_spirit_safe_source",
    "set_spirit_safe_source",
    "LookupCache",
    "LookupFetcher",
    "hydrate_profile_lookups",
    "resolve_profile_path",
]
