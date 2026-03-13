"""
GKC Utilities: Common helper functions and lightweight utilities.

This module contains small, widely-reusable utilities that don't fit neatly
into other modules. Use this for any common utilities needed across the
codebase.

Plain meaning: A home for universal helper functions.
"""

from typing import Any, Optional


def get_entity_uri(entity_id: str) -> str:
    """
    Get the full URI for a Wikidata entity.

    Args:
        entity_id: Entity ID (e.g., 'Q42', 'P31', 'L1', 'E502')

    Returns:
        Full URI string

    Example:
        >>> get_entity_uri('Q42')
        'http://www.wikidata.org/entity/Q42'
        >>> get_entity_uri('P31')
        'http://www.wikidata.org/entity/P31'
    """
    if not entity_id:
        raise ValueError("Entity ID is required")

    return f"http://www.wikidata.org/entity/{entity_id}"


def validate_entity_reference(entity_id: str) -> bool:
    """
    Validate that a string looks like a Wikidata entity ID.

    Plain meaning: Check if an ID is in valid Wikidata format.

    Args:
        entity_id: String to validate

    Returns:
        True if valid format, False otherwise

    Example:
        >>> validate_entity_reference('Q42')
        True
        >>> validate_entity_reference('P31')
        True
        >>> validate_entity_reference('E502')
        True
        >>> validate_entity_reference('invalid')
        False
    """
    if not entity_id or not isinstance(entity_id, str):
        return False

    # Must start with Q, P, L, or E followed by digits
    if len(entity_id) < 2:
        return False

    prefix = entity_id[0].upper()
    rest = entity_id[1:]

    return prefix in ("Q", "P", "L", "E") and rest.isdigit()


def search_exact_label(
    api_client: Any,
    *,
    label: str,
    entity_type: str,
    language: str = "en",
) -> list[dict[str, Any]]:
    """Search for entities and return only exact label matches.

    Args:
        api_client: Client with ``search_entities`` method.
        label: Label text to resolve.
        entity_type: Wikibase entity type ("item" or "property").
        language: Search language.

    Returns:
        List of exact label matches.
    """
    candidates = api_client.search_entities(
        label=label,
        entity_type=entity_type,
        language=language,
    )
    return [
        candidate
        for candidate in candidates
        if (candidate.get("label") or "").casefold() == label.casefold()
    ]


def resolve_name_to_identifier(
    ref: str,
    *,
    api_client: Any,
    language: str = "en",
    entity_type: Optional[str] = None,
    label_to_id_map: Optional[dict[str, str]] = None,
) -> Optional[str]:
    """Resolve a human-readable label to a unique Wikibase identifier.

    Resolution order:
    1. If ``ref`` is already a Wikibase-like identifier, return it uppercased.
    2. If a map is provided and contains ``ref`` (case-insensitive), return mapped ID.
    3. Search Wikibase by exact label and return a unique match.

    Args:
        ref: Label or ID to resolve.
        api_client: Client with ``search_entities`` method.
        language: Search language.
        entity_type: Optional target type ("item" or "property").
            When omitted, tries item first then property.
        label_to_id_map: Optional case-insensitive map of label to ID.

    Returns:
        Resolved identifier, or ``None`` when ambiguous/not found.
    """
    if validate_entity_reference(ref):
        return ref.upper()

    if label_to_id_map:
        mapped = label_to_id_map.get(ref.casefold())
        if mapped:
            return mapped

    if entity_type:
        candidates = search_exact_label(
            api_client,
            label=ref,
            entity_type=entity_type,
            language=language,
        )
        if len(candidates) == 1:
            return (candidates[0].get("id") or "").upper() or None
        return None

    item_candidates = search_exact_label(
        api_client,
        label=ref,
        entity_type="item",
        language=language,
    )
    if len(item_candidates) == 1:
        return (item_candidates[0].get("id") or "").upper() or None

    property_candidates = search_exact_label(
        api_client,
        label=ref,
        entity_type="property",
        language=language,
    )
    if len(property_candidates) == 1:
        return (property_candidates[0].get("id") or "").upper() or None

    return None
