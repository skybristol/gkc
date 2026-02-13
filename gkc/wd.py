"""
Deprecated: This module has been renamed to 'cooperage'.

Please update imports to use gkc.cooperage instead.
"""

# Re-export from cooperage for backwards compatibility during migration
from gkc.cooperage import (
    DEFAULT_USER_AGENT,
    CooperageError,
    fetch_entity_rdf,
    fetch_schema_specification,
    get_entity_uri,
    validate_entity_reference,
)

__all__ = [
    "CooperageError",
    "DEFAULT_USER_AGENT",
    "fetch_entity_rdf",
    "fetch_schema_specification",
    "get_entity_uri",
    "validate_entity_reference",
]
