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

Data flows: Source → Still → Unified Still Schema → Target Schema → Target

## Key Components

- **Mash** - Loads data and schema artifacts from source systems
- **Wikibase** - Coordinates profile-driven write planning and Wikibase flows
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

# Entity Profiles (GKC Entity Profile definitions)
from gkc.entity_profile import GKCEntityProfile

# Fermenter (validation and coercion layer)
from gkc.fermenter import (
    ConformanceNotice,
    enforce_fixed_value,
    validate_by_datatype,
    validate_commons_media,
    validate_entity_packet_data,
    validate_globe_coordinate,
    validate_inline_value,
    validate_monolingualtext,
    validate_quantity,
    validate_string,
    validate_time,
    validate_url,
    validate_value_from_list,
    validate_wikibase_item,
    validate_with_pattern,
)

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

# Runtime configuration
from gkc.runtime_config import DEFAULT_USER_AGENT

# Wikibase-specific helpers
from gkc.wikibase import (
    WikibaseDatatypeSpec,
    canonicalize_wikibase_datatype,
    get_wikibase_datatype_spec,
    is_known_wikibase_datatype,
    is_wikibase_item_datatype,
    list_wikibase_datatypes,
    load_wikibase_datatype_registry,
    load_wikibase_datatype_registry_json,
)

# ShEx validation utilities
from gkc.shex import ShexValidationError, ShexValidator

# Sitelinks (cross-reference validation)
from gkc.sitelinks import (
    DEFAULT_WIKIMEDIA_SITEMATRIX_URL,
    SitelinkValidator,
    build_wikimedia_sites_artifact_from_sitematrix,
    check_wikipedia_page,
    export_wikimedia_sites_artifact,
    fetch_wikimedia_sitematrix,
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
    Manifest,
    SpiritSafeSourceConfig,
    ValueListHydrationResult,
    build_entity_profile_json_documents,
    build_spiritsafe_manifest_document,
    build_spiritsafe_semantic_anchor_document,
    discover_value_list_ids,
    export_entity_profile_json_documents,
    export_spiritsafe_manifest,
    export_spiritsafe_semantic_anchors,
    export_value_list_sparql_queries,
    get_spirit_safe_source,
    hydrate_value_list_query_caches,
    hydrate_value_lists_from_cache,
    list_profiles,
    load_manifest,
    load_profile,
    load_profile_package,
    profile_exists,
    resolve_profile_link,
    resolve_profile_path,
    resolve_query_ref,
    set_spirit_safe_source,
    validate_packet_structure,
)
from gkc.still_charger import (
    ChargeIssue,
    ChargeReport,
    build_curation_packet_from_json_profile,
    charge_curation_packet,
    charge_packet_from_wikidata_items,
    create_and_charge_curation_packet,
    create_curation_packet,
    packet_entities,
    packet_entity_by_ref,
    packet_outgoing_links,
    packet_primary_profile_id,
)

# Utilities (common helpers)
from gkc.utilities import (
    get_entity_uri,
    resolve_name_to_identifier,
    search_exact_label,
    validate_entity_reference,
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
    # Runtime Configuration
    "DEFAULT_USER_AGENT",
    # Wikibase-specific helpers
    "WikibaseDatatypeSpec",
    "canonicalize_wikibase_datatype",
    "get_wikibase_datatype_spec",
    "is_known_wikibase_datatype",
    "is_wikibase_item_datatype",
    "list_wikibase_datatypes",
    "load_wikibase_datatype_registry",
    "load_wikibase_datatype_registry_json",
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
    # Utilities
    "get_entity_uri",
    "search_exact_label",
    "resolve_name_to_identifier",
    "validate_entity_reference",
    # Still Charger
    "ChargeIssue",
    "ChargeReport",
    "charge_curation_packet",
    "build_curation_packet_from_json_profile",
    "charge_packet_from_wikidata_items",
    "create_and_charge_curation_packet",
    "packet_entities",
    "packet_entity_by_ref",
    "packet_outgoing_links",
    "packet_primary_profile_id",
    # Fermenter validation
    "ConformanceNotice",
    "validate_inline_value",
    "validate_entity_packet_data",
    "validate_by_datatype",
    "validate_wikibase_item",
    "validate_string",
    "validate_with_pattern",
    "validate_monolingualtext",
    "validate_url",
    "validate_time",
    "validate_quantity",
    "validate_globe_coordinate",
    "validate_commons_media",
    "validate_value_from_list",
    "enforce_fixed_value",
    # Mash schema functions
    "extract_first_sparql_block",
    "extract_sparql_blocks",
    "fetch_entity_rdf",
    "fetch_mediawiki_page_wikitext",
    "fetch_schema_specification",
    # Entity Profiles
    "GKCEntityProfile",
    # Sitelinks
    "DEFAULT_WIKIMEDIA_SITEMATRIX_URL",
    "SitelinkValidator",
    "build_wikimedia_sites_artifact_from_sitematrix",
    "check_wikipedia_page",
    "export_wikimedia_sites_artifact",
    "fetch_wikimedia_sitematrix",
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
    "Manifest",
    "ValueListHydrationResult",
    "SpiritSafeSourceConfig",
    "get_spirit_safe_source",
    "set_spirit_safe_source",
    "LookupCache",
    "LookupFetcher",
    "build_entity_profile_json_documents",
    "build_spiritsafe_manifest_document",
    "build_spiritsafe_semantic_anchor_document",
    "create_curation_packet",
    "discover_value_list_ids",
    "export_entity_profile_json_documents",
    "export_spiritsafe_manifest",
    "export_spiritsafe_semantic_anchors",
    "export_value_list_sparql_queries",
    "hydrate_value_list_query_caches",
    "hydrate_value_lists_from_cache",
    "load_manifest",
    "load_profile",
    "load_profile_package",
    "list_profiles",
    "profile_exists",
    "resolve_profile_link",
    "resolve_profile_path",
    "resolve_query_ref",
    "validate_packet_structure",
]
