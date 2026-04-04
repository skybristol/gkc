"""Wikibase-specific runtime helpers and package-owned registries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files


_DATATYPE_ALIASES = {
    "item": "wikibase-item",
    "globecoordinate": "globe-coordinate",
}


@dataclass(frozen=True)
class WikibaseDatatypeSpec:
    """Canonical runtime specification for one Wikibase datatype."""

    ontology_uri: str
    datavalue_type: str
    entity_value_kind: str | None = None


@lru_cache(maxsize=1)
def load_wikibase_datatype_registry() -> dict[str, WikibaseDatatypeSpec]:
    """Load the package-owned Wikibase datatype registry.

    Returns:
        Mapping from canonical Wikibase datatype token to typed registry entry.
    """

    registry_path = files("gkc.registry").joinpath("wikibase_datatypes.json")
    raw_registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(raw_registry, dict):
        raise RuntimeError("wikibase datatype registry must be a JSON object")

    registry: dict[str, WikibaseDatatypeSpec] = {}
    for canonical_name, payload in raw_registry.items():
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            raise RuntimeError(
                "wikibase datatype registry keys must be non-empty strings"
            )
        if not isinstance(payload, dict):
            raise RuntimeError(
                "wikibase datatype registry entries must be JSON objects"
            )

        ontology_uri = payload.get("ontology_uri")
        datavalue_type = payload.get("datavalue_type")
        entity_value_kind = payload.get("entity_value_kind")

        if not isinstance(ontology_uri, str) or not ontology_uri.strip():
            raise RuntimeError(
                f"wikibase datatype '{canonical_name}' is missing ontology_uri"
            )
        if not isinstance(datavalue_type, str) or not datavalue_type.strip():
            raise RuntimeError(
                f"wikibase datatype '{canonical_name}' is missing datavalue_type"
            )
        if entity_value_kind is not None and (
            not isinstance(entity_value_kind, str) or not entity_value_kind.strip()
        ):
            raise RuntimeError(
                f"wikibase datatype '{canonical_name}' has invalid entity_value_kind"
            )

        registry[canonical_name] = WikibaseDatatypeSpec(
            ontology_uri=ontology_uri.strip(),
            datavalue_type=datavalue_type.strip(),
            entity_value_kind=entity_value_kind.strip()
            if isinstance(entity_value_kind, str)
            else None,
        )

    return registry


def get_wikibase_datatype_spec(canonical_name: str) -> WikibaseDatatypeSpec:
    """Return the registry entry for one canonical datatype token."""

    registry = load_wikibase_datatype_registry()
    canonical_name = canonicalize_wikibase_datatype(canonical_name)
    try:
        return registry[canonical_name]
    except KeyError as exc:
        raise KeyError(f"Unknown Wikibase datatype: {canonical_name}") from exc


def list_wikibase_datatypes() -> list[str]:
    """Return the canonical runtime datatype tokens in stable order."""

    return sorted(load_wikibase_datatype_registry().keys())


def canonicalize_wikibase_datatype(
    datatype: str,
    *,
    strict: bool = False,
) -> str:
    """Normalize a Wikibase datatype token to its canonical runtime spelling."""

    normalized = datatype.strip()
    canonical = _DATATYPE_ALIASES.get(normalized, normalized)
    if strict and canonical not in load_wikibase_datatype_registry():
        raise KeyError(f"Unknown Wikibase datatype: {canonical}")
    return canonical


def is_known_wikibase_datatype(datatype: str) -> bool:
    """Return whether a datatype token resolves to a known registry entry."""

    if not isinstance(datatype, str):
        return False
    canonical = canonicalize_wikibase_datatype(datatype)
    return canonical in load_wikibase_datatype_registry()


def is_wikibase_item_datatype(datatype: str) -> bool:
    """Return whether a datatype token resolves to the Wikibase item datatype."""

    if not isinstance(datatype, str):
        return False
    return canonicalize_wikibase_datatype(datatype) == "wikibase-item"


def load_wikibase_datatype_registry_json() -> dict[str, dict[str, str]]:
    """Return the raw JSON-compatible registry mapping."""

    registry = load_wikibase_datatype_registry()
    return {
        canonical_name: {
            "ontology_uri": spec.ontology_uri,
            "datavalue_type": spec.datavalue_type,
            **(
                {"entity_value_kind": spec.entity_value_kind}
                if spec.entity_value_kind is not None
                else {}
            ),
        }
        for canonical_name, spec in registry.items()
    }


__all__ = [
    "WikibaseDatatypeSpec",
    "canonicalize_wikibase_datatype",
    "get_wikibase_datatype_spec",
    "is_known_wikibase_datatype",
    "is_wikibase_item_datatype",
    "list_wikibase_datatypes",
    "load_wikibase_datatype_registry",
    "load_wikibase_datatype_registry_json",
]