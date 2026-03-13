"""Wikibase integration utilities for GKC.

Scope: Wikibase-first ProfilesV2 support, including live ontology snapshots
for semantic resolution, write plan orchestration, and legacy foundation workflows.
"""

from gkc.wikibase.ontology import (
    DDOntologyIndex,
    DDProfileCacheExportResult,
    DDProfileGraph,
    build_discovery_sparql_query,
    build_profile_ids_sparql_query,
    export_profile_graph_to_entity_cache,
    fetch_ontology_index,
    fetch_profile_graph,
    fetch_profile_ids,
    get_label_for_language,
    get_monolingualtext_for_language,
    resolve_profile_statement_guidance,
    resolve_statement_guidance,
)
from gkc.wikibase.orchestration import (
    WikibaseWriteExecutionResult,
    WikibaseWritePlanResult,
    build_wikibase_write_plan,
    execute_wikibase_write_plan,
)

__all__ = [
    "DDOntologyIndex",
    "DDProfileCacheExportResult",
    "DDProfileGraph",
    "build_discovery_sparql_query",
    "build_profile_ids_sparql_query",
    "export_profile_graph_to_entity_cache",
    "fetch_ontology_index",
    "fetch_profile_graph",
    "fetch_profile_ids",
    "get_label_for_language",
    "get_monolingualtext_for_language",
    "resolve_profile_statement_guidance",
    "resolve_statement_guidance",
    "WikibaseWriteExecutionResult",
    "WikibaseWritePlanResult",
    "build_wikibase_write_plan",
    "execute_wikibase_write_plan",
]
