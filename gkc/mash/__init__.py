"""Mash package public API.

This package provides source-loading templates and loaders used by GKC.
"""

from gkc.mash.core import (
    ClaimSummary,
    DataTemplate,
    WikibaseApiClient,
    WikibaseCacheRefreshResult,
    WikibaseEntitySchemaTemplate,
    WikibaseItemTemplate,
    WikibaseLoader,
    WikibaseMashSourceAdapter,
    WikibasePropertyTemplate,
    WikibaseRecentChangesResult,
    WikipediaLoader,
    WikipediaMashSourceAdapter,
    WikipediaTemplate,
    apply_item_property_filters,
    apply_template_language_filter,
    fetch_entity_rdf,
    fetch_entity_schema_json,
    fetch_entity_schema_specification,
    fetch_property_labels,
    fetch_recent_entity_changes,
    get_latest_cache_timestamp,
    refresh_entity_cache_from_recentchanges,
    strip_entity_identifiers,
)
from gkc.mash.protocols import MashSourceAdapter

__all__ = [
    "ClaimSummary",
    "DataTemplate",
    "WikibaseCacheRefreshResult",
    "MashSourceAdapter",
    "WikibaseMashSourceAdapter",
    "WikipediaMashSourceAdapter",
    "apply_item_property_filters",
    "apply_template_language_filter",
    "WikibaseApiClient",
    "WikibaseRecentChangesResult",
    "WikibaseLoader",
    "WikibaseItemTemplate",
    "WikibasePropertyTemplate",
    "WikibaseEntitySchemaTemplate",
    "WikipediaLoader",
    "WikipediaTemplate",
    "fetch_entity_rdf",
    "fetch_entity_schema_json",
    "fetch_entity_schema_specification",
    "fetch_property_labels",
    "fetch_recent_entity_changes",
    "get_latest_cache_timestamp",
    "refresh_entity_cache_from_recentchanges",
    "strip_entity_identifiers",
]
