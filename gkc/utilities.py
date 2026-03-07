"""
GKC Utilities: Common helper functions and lightweight utilities.

This module contains small, widely-reusable utilities that don't fit neatly
into other modules. Use this for any common utilities needed across the
codebase.

Plain meaning: A home for universal helper functions.
"""


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

    prefix = entity_id[0]
    rest = entity_id[1:]

    return prefix in ("Q", "P", "L", "E") and rest.isdigit()
