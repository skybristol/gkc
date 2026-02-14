"""
Cooperage: Barrel Schema management, property metadata, and reference data.

The Cooperage manages **Barrel Schemas** - the structured schemas, property
definitions, and constraints from target knowledge systems (Wikidata, OSM,
Commons, Wikipedia). It provides the specifications needed to build Barrel
Recipes and validate data against target system requirements.

Think of it as the toolkit for barrel-making: fetching schema specifications,
caching property metadata, managing validation rules, and providing reference
lookups.

Plain meaning: Central repository for target system schemas and metadata.
"""

from typing import Optional

import requests

DEFAULT_USER_AGENT = "GKC-Python-Client/0.1 (https://github.com/skybristol/gkc)"


class CooperageError(Exception):
    """Raised when Cooperage operations (Barrel Schema/reference management) fail."""

    pass


def fetch_entity_rdf(
    qid: str, format: str = "ttl", user_agent: Optional[str] = None
) -> str:
    """
    Fetch RDF data for a Wikidata entity.

    Args:
        qid: Wikidata entity ID (e.g., 'Q42', 'P31')
        format: RDF format - 'ttl' (Turtle), 'rdf' (RDF/XML), 'nt' (N-Triples)
        user_agent: Custom user agent string

    Returns:
        RDF data as string

    Raises:
        CooperageError: If fetch fails

    Example:
        >>> rdf = fetch_entity_rdf('Q42')  # Get Douglas Adams RDF
        >>> rdf = fetch_entity_rdf('P31', format='nt')  # Get property in N-Triples
    """
    if not qid:
        raise ValueError("Entity ID (qid) is required")

    # Validate format
    valid_formats = {"ttl", "rdf", "nt"}
    if format not in valid_formats:
        raise ValueError(f"Invalid format '{format}'. Must be one of: {valid_formats}")

    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.{format}"
    headers = {"User-Agent": user_agent or DEFAULT_USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise CooperageError(
            f"Failed to fetch RDF for {qid} from {url}: {str(e)}"
        ) from e


def fetch_schema_specification(eid: str, user_agent: Optional[str] = None) -> str:
    """
    Fetch Wikidata Barrel Schema (EntitySchema in ShExC format).

    Retrieves a Wikidata EntitySchema specification from Wikidata. EntitySchemas
    define the shape and structure constraints that form part of Wikidata's
    Barrel Schema (along with property constraints).

    Plain meaning: Get the shape/structure specification for Wikidata entities.

    Args:
        eid: EntitySchema ID (e.g., 'E502')
        user_agent: Custom user agent string

    Returns:
        ShExC schema text as string

    Raises:
        CooperageError: If fetch fails

    Example:
        >>> schema = fetch_schema_specification('E502')  # Barrel Schema for tribes
    """
    if not eid:
        raise ValueError("EntitySchema ID (eid) is required")

    url = f"https://www.wikidata.org/wiki/Special:EntitySchemaText/{eid}"
    headers = {"User-Agent": user_agent or DEFAULT_USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        raise CooperageError(
            f"Failed to fetch EntitySchema {eid} from {url}: {str(e)}"
        ) from e


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
