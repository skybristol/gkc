"""
Cooperage: DEPRECATED - Compatibility facade for refactored modules.

This module has been superseded as part of architectural consolidation.
All functionality has been migrated to:
- gkc.mash: Entity schema and RDF retrieval (Wikibase read operations)
- gkc.utilities: Helper functions (get_entity_uri, validate_entity_reference)

This module remains for backward compatibility only. New code should import
directly from gkc.mash or gkc.utilities.

Deprecation Timeline:
- v0.2.x: Functions available via re-exports (current)
- v0.3.0: Re-exports removed; import directly from mash/utilities
- v0.4.0: This module removed entirely

Migration Guide:
    OLD: from gkc.cooperage import fetch_entity_rdf
    NEW: from gkc.mash import fetch_entity_rdf

    OLD: from gkc.cooperage import get_entity_uri
    NEW: from gkc.utilities import get_entity_uri
"""

# Re-export functions from their new homes for backward compatibility
from gkc.mash import (
    fetch_entity_rdf,
    fetch_entity_schema_json,
)
from gkc.mash import (
    fetch_entity_schema_specification as fetch_schema_specification,
)
from gkc.utilities import get_entity_uri, validate_entity_reference


# CooperageError is deprecated; mash functions raise RuntimeError instead
class CooperageError(Exception):
    """
    DEPRECATED: Use RuntimeError instead.

    Raised when entity/schema fetch operations fail. This exception is provided
    for backward compatibility but new code should catch RuntimeError instead.

    See: gkc.mash for fetch functions that raise RuntimeError.
    """

    pass


# Deprecated function (never used externally; kept for completeness)
def fetch_entity_schema_metadata(
    eid: str, language: str = "en", user_agent=None
) -> dict:
    """
    DEPRECATED: Fetch metadata for a Wikidata EntitySchema.

    This function is no longer actively maintained. For basic entity schema
    retrieval, use fetch_entity_schema_json() instead.

    To be removed in v0.3.0.
    """
    # This function is rarely/never used. If needed, implement via fetch_entity_schema_json
    raise NotImplementedError(
        "fetch_entity_schema_metadata has been removed. "
        "Use fetch_entity_schema_json() and extract metadata directly."
    )


__all__ = [
    # Re-exported from mash
    "fetch_entity_rdf",
    "fetch_entity_schema_json",
    "fetch_schema_specification",
    # Re-exported from utilities
    "get_entity_uri",
    "validate_entity_reference",
    # Deprecated exception (for backward compat)
    "CooperageError",
]
