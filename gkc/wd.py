"""
Deprecated: This module has been renamed to 'cooperage'.

This file provides backwards compatibility during the terminology refactoring.
Please update imports to use gkc.cooperage instead.

Example:
    Old: from gkc.wd import fetch_entity_rdf
    New: from gkc.cooperage import fetch_entity_rdf
"""

import warnings

import requests

# Re-export everything from cooperage
from gkc.cooperage import (
    CooperageError,
    DEFAULT_USER_AGENT,
    fetch_entity_rdf,
    fetch_schema_specification,
    get_entity_uri,
    validate_entity_reference,
)

# Deprecated aliases
WikidataFetchError = CooperageError


def fetch_entity_schema(eid: str, user_agent=None):
    """Deprecated: Use fetch_schema_specification instead."""
    warnings.warn(
        "fetch_entity_schema is deprecated. Use fetch_schema_specification instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return fetch_schema_specification(eid, user_agent)


def validate_entity_id(entity_id: str):
    """Deprecated: Use validate_entity_reference instead."""
    warnings.warn(
        "validate_entity_id is deprecated. Use validate_entity_reference instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return validate_entity_reference(entity_id)


__all__ = [
    "WikidataFetchError",
    "DEFAULT_USER_AGENT",
    "fetch_entity_rdf",
    "fetch_entity_schema",
    "get_entity_uri",
    "validate_entity_id",
    "CooperageError",
    "fetch_schema_specification",
    "validate_entity_reference",
]

