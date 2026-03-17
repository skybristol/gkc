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
from gkc.cooperage import (
    BarrelIssue,
    BarrelPlanReport,
    barrel_curation_packet_to_wikibase_plan,
)

# Entity Profiles (GKC Entity Profile definitions)
from gkc.entity_profile import GKCEntityProfile

# Mash (inbound data retrieval)
from gkc.mash import (
    extract_first_sparql_block,
    extract_sparql_blocks,
    fetch_entity_rdf,
    fetch_mediawiki_page_wikitext,
)
from gkc.mash import (
    fetch_entity_schema_specification as fetch_schema_specification,
)

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

# Runtime configuration
from gkc.runtime_config import DEFAULT_USER_AGENT

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
    execute_sparql_file,
    execute_sparql_to_dataframe,
    paginate_query_file,
    read_sparql_query_file,
)

# SpiritSafe source configuration + lookup utilities
from gkc.spirit_safe import (
    DEFAULT_SPIRIT_SAFE_GITHUB_REPO,
    EntityProfileJsonBuilder,
    EntityProfileJsonExportResult,
    LookupCache,
    LookupFetcher,
    ProfileMetadata,
    SpiritSafeSourceConfig,
    ValueListHydrationResult,
    build_entity_profile_json_documents,
    discover_value_list_ids,
    export_entity_profile_json_documents,
    export_value_list_sparql_queries,
    get_profile_metadata,
    get_spirit_safe_source,
    hydrate_profile_lookups,
    hydrate_value_list_query_caches,
    hydrate_value_lists_from_cache,
    list_profiles,
    profile_exists,
    resolve_profile_path,
    resolve_query_ref,
    set_spirit_safe_source,
)
from gkc.still_charger import ChargeIssue, ChargeReport, charge_curation_packet

# Utilities (common helpers)
from gkc.utilities import (
    get_entity_uri,
    resolve_name_to_identifier,
    search_exact_label,
    validate_entity_reference,
)
from gkc.wikibase import WikibaseWritePlanResult, build_wikibase_write_plan

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
    # Runtime Configuration
    "DEFAULT_USER_AGENT",
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
    # Cooperage (barreling transforms)
    "BarrelIssue",
    "BarrelPlanReport",
    "barrel_curation_packet_to_wikibase_plan",
    # Utilities
    "get_entity_uri",
    "search_exact_label",
    "resolve_name_to_identifier",
    "validate_entity_reference",
    # Wikibase orchestration
    "WikibaseWritePlanResult",
    "build_wikibase_write_plan",
    # Still Charger
    "ChargeIssue",
    "ChargeReport",
    "charge_curation_packet",
    # Mash schema functions
    "extract_first_sparql_block",
    "extract_sparql_blocks",
    "fetch_entity_rdf",
    "fetch_mediawiki_page_wikitext",
    "fetch_schema_specification",
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
    "execute_sparql_file",
    "execute_sparql_to_dataframe",
    "paginate_query_file",
    "read_sparql_query_file",
    # ShEx validation
    "ShexValidationError",
    "ShexValidator",
    # SpiritSafe source configuration + lookup utilities
    "DEFAULT_SPIRIT_SAFE_GITHUB_REPO",
    "EntityProfileJsonBuilder",
    "EntityProfileJsonExportResult",
    "ValueListHydrationResult",
    "SpiritSafeSourceConfig",
    "get_spirit_safe_source",
    "set_spirit_safe_source",
    "LookupCache",
    "LookupFetcher",
    "build_entity_profile_json_documents",
    "discover_value_list_ids",
    "export_entity_profile_json_documents",
    "export_value_list_sparql_queries",
    "hydrate_profile_lookups",
    "hydrate_value_list_query_caches",
    "hydrate_value_lists_from_cache",
    "ProfileMetadata",
    "get_profile_metadata",
    "list_profiles",
    "profile_exists",
    "resolve_profile_path",
    "resolve_query_ref",
]
