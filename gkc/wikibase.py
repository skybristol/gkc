"""Wikibase-specific runtime helpers and package-owned registries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

import yaml

_DATATYPE_ALIASES = {
    "item": "wikibase-item",
    "globecoordinate": "globe-coordinate",
}


@dataclass(frozen=True)
class MetaWikibaseInitMetadata:
    """Package-owned metadata for the Meta-Wikibase init fixture."""

    name: str
    description: str
    source: str
    reference: str
    internal_name_identifier_prefix: str


@dataclass(frozen=True)
class MetaWikibaseInitEntity:
    """Normalized entity entry from the package-owned Meta-Wikibase init fixture."""

    key: str
    kind: str
    label: str
    description: str
    internal_name_identifier: str
    datatype: str | None = None
    instance_of: str | None = None
    subclass_of: str | None = None
    attributes: dict[str, Any] | None = None


@dataclass(frozen=True)
class MetaWikibaseInitIndex:
    """Indexed access surface for the package-owned Meta-Wikibase init fixture."""

    metadata: MetaWikibaseInitMetadata
    entities: dict[str, MetaWikibaseInitEntity]
    properties: dict[str, MetaWikibaseInitEntity]
    items: dict[str, MetaWikibaseInitEntity]
    by_internal_name_identifier: dict[str, MetaWikibaseInitEntity]


@dataclass(frozen=True)
class MetaWikibaseSemanticAnchorRequirement:
    """Required internal semantic anchor compiled from the init fixture."""

    key: str
    internal_name_identifier: str
    kind: str
    datatype: str | None = None


@dataclass(frozen=True)
class MetaWikibaseSemanticAnchorContract:
    """Compiled required semantic-anchor contract derived from the init fixture."""

    internal_name_identifier_prefix: str
    requirements: dict[str, MetaWikibaseSemanticAnchorRequirement]


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


@lru_cache(maxsize=1)
def _load_meta_wikibase_init_yaml_text() -> str:
    return files("gkc.registry").joinpath("meta_wb_init.yaml").read_text(
        encoding="utf-8"
    )


def load_meta_wikibase_init_document() -> dict[str, Any]:
    """Load the package-owned Meta-Wikibase init document and normalize it."""

    raw_document = yaml.safe_load(_load_meta_wikibase_init_yaml_text())
    return normalize_meta_wikibase_init_document(raw_document)


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


@lru_cache(maxsize=1)
def _build_wikibase_datatype_aliases() -> dict[str, str]:
    aliases = dict(_DATATYPE_ALIASES)
    for canonical_name, spec in load_wikibase_datatype_registry().items():
        aliases[canonical_name] = canonical_name
        aliases[spec.ontology_uri] = canonical_name
        ontology_name = spec.ontology_uri.rsplit("#", 1)[-1]
        aliases[ontology_name] = canonical_name
    return aliases


def canonicalize_wikibase_datatype(
    datatype: str,
    *,
    strict: bool = False,
) -> str:
    """Normalize a Wikibase datatype token to its canonical runtime spelling."""

    normalized = datatype.strip()
    canonical = _build_wikibase_datatype_aliases().get(normalized, normalized)
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


def normalize_meta_wikibase_init_document(document: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Meta-Wikibase init document to canonical runtime datatypes."""

    if not isinstance(document, dict):
        raise RuntimeError("meta_wb_init document must be a mapping")

    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("meta_wb_init document is missing metadata")

    entities = document.get("entities")
    if not isinstance(entities, dict):
        raise RuntimeError("meta_wb_init document is missing entities")

    wikibase_entities = entities.get("wikibase_entities")
    if not isinstance(wikibase_entities, dict):
        raise RuntimeError(
            "meta_wb_init document is missing entities.wikibase_entities"
        )

    normalized_properties: dict[str, dict[str, Any]] = {}
    raw_properties = wikibase_entities.get("properties", {})
    if not isinstance(raw_properties, dict):
        raise RuntimeError("meta_wb_init properties must be a mapping")
    for key, payload in raw_properties.items():
        if not isinstance(payload, dict):
            raise RuntimeError(f"meta_wb_init property '{key}' must be a mapping")
        normalized_payload = dict(payload)
        normalized_payload["kind"] = "property"
        datatype = normalized_payload.get("datatype")
        if not isinstance(datatype, str) or not datatype.strip():
            raise RuntimeError(
                f"meta_wb_init property '{key}' is missing datatype"
            )
        normalized_payload["datatype"] = canonicalize_wikibase_datatype(
            datatype,
            strict=True,
        )
        normalized_properties[key] = normalized_payload

    normalized_items: dict[str, dict[str, Any]] = {}
    raw_items = wikibase_entities.get("items", {})
    if not isinstance(raw_items, dict):
        raise RuntimeError("meta_wb_init items must be a mapping")
    for key, payload in raw_items.items():
        if not isinstance(payload, dict):
            raise RuntimeError(f"meta_wb_init item '{key}' must be a mapping")
        normalized_payload = dict(payload)
        normalized_payload["kind"] = "item"
        normalized_items[key] = normalized_payload

    return {
        "metadata": dict(metadata),
        "entities": {
            "wikibase_entities": {
                "properties": normalized_properties,
                "items": normalized_items,
            }
        },
    }


def build_meta_wikibase_init_index(
    document: dict[str, Any] | None = None,
) -> MetaWikibaseInitIndex:
    """Build a typed index over the package-owned Meta-Wikibase init fixture."""

    normalized_document = (
        load_meta_wikibase_init_document()
        if document is None
        else normalize_meta_wikibase_init_document(document)
    )
    metadata_payload = normalized_document["metadata"]
    metadata = MetaWikibaseInitMetadata(
        name=str(metadata_payload.get("name", "")).strip(),
        description=str(metadata_payload.get("description", "")).strip(),
        source=str(metadata_payload.get("source", "")).strip(),
        reference=str(metadata_payload.get("reference", "")).strip(),
        internal_name_identifier_prefix=str(
            metadata_payload.get("internal_name_identifier_prefix", "_")
        ),
    )

    entities_block = normalized_document["entities"]["wikibase_entities"]
    entities: dict[str, MetaWikibaseInitEntity] = {}
    properties: dict[str, MetaWikibaseInitEntity] = {}
    items: dict[str, MetaWikibaseInitEntity] = {}
    by_internal_name_identifier: dict[str, MetaWikibaseInitEntity] = {}

    for kind, bucket in (("property", entities_block["properties"]), ("item", entities_block["items"])):
        for key, payload in bucket.items():
            internal_name_identifier = (
                f"{metadata.internal_name_identifier_prefix}{key}"
            )
            attributes = {
                attr_key: attr_value
                for attr_key, attr_value in payload.items()
                if attr_key
                not in {
                    "kind",
                    "label",
                    "description",
                    "datatype",
                    "instance_of",
                    "subclass_of",
                }
            }
            entity = MetaWikibaseInitEntity(
                key=key,
                kind=kind,
                label=str(payload.get("label", "")).strip(),
                description=str(payload.get("description", "")).strip(),
                internal_name_identifier=internal_name_identifier,
                datatype=payload.get("datatype"),
                instance_of=payload.get("instance_of"),
                subclass_of=payload.get("subclass_of"),
                attributes=attributes or None,
            )
            entities[key] = entity
            by_internal_name_identifier[internal_name_identifier] = entity
            if kind == "property":
                properties[key] = entity
            else:
                items[key] = entity

    return MetaWikibaseInitIndex(
        metadata=metadata,
        entities=entities,
        properties=properties,
        items=items,
        by_internal_name_identifier=by_internal_name_identifier,
    )


def get_meta_wikibase_init_entity(entity_key: str) -> MetaWikibaseInitEntity:
    """Return one normalized entity entry from the package-owned init fixture."""

    index = build_meta_wikibase_init_index()
    try:
        return index.entities[entity_key]
    except KeyError as exc:
        raise KeyError(f"Unknown Meta-Wikibase init entity: {entity_key}") from exc


def build_meta_wikibase_semantic_anchor_contract(
    document: dict[str, Any] | None = None,
    *,
    internal_name_identifier_prefix: str | None = None,
) -> MetaWikibaseSemanticAnchorContract:
    """Compile the package-owned init fixture into a required anchor contract."""

    index = build_meta_wikibase_init_index(document)
    prefix = (
        internal_name_identifier_prefix
        if isinstance(internal_name_identifier_prefix, str)
        and internal_name_identifier_prefix
        else index.metadata.internal_name_identifier_prefix
    )

    requirements: dict[str, MetaWikibaseSemanticAnchorRequirement] = {}
    for entity in index.entities.values():
        requirement = MetaWikibaseSemanticAnchorRequirement(
            key=entity.key,
            internal_name_identifier=f"{prefix}{entity.key}",
            kind=entity.kind,
            datatype=entity.datatype if entity.kind == "property" else None,
        )
        requirements[requirement.internal_name_identifier] = requirement

    return MetaWikibaseSemanticAnchorContract(
        internal_name_identifier_prefix=prefix,
        requirements=requirements,
    )


__all__ = [
    "MetaWikibaseInitEntity",
    "MetaWikibaseInitIndex",
    "MetaWikibaseInitMetadata",
    "MetaWikibaseSemanticAnchorContract",
    "MetaWikibaseSemanticAnchorRequirement",
    "WikibaseDatatypeSpec",
    "build_meta_wikibase_init_index",
    "build_meta_wikibase_semantic_anchor_contract",
    "canonicalize_wikibase_datatype",
    "get_meta_wikibase_init_entity",
    "get_wikibase_datatype_spec",
    "is_known_wikibase_datatype",
    "is_wikibase_item_datatype",
    "list_wikibase_datatypes",
    "load_meta_wikibase_init_document",
    "load_wikibase_datatype_registry",
    "load_wikibase_datatype_registry_json",
    "normalize_meta_wikibase_init_document",
]