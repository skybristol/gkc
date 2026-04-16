"""Wikibase-specific runtime helpers and package-owned registries."""

from __future__ import annotations

import hashlib
import json
import re
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
class MetaWikibaseCompiledEntity:
    """Compiled symbolic Wikibase payload for one init-fixture entity."""

    key: str
    kind: str
    internal_name_identifier: str
    entity_type: str
    datatype: str | None
    claims: dict[str, list[dict[str, Any]]]
    payload: dict[str, Any]


@dataclass(frozen=True)
class MetaWikibaseSeedCompilation:
    """Compiled symbolic Wikibase payload set derived from the init fixture."""

    metadata: MetaWikibaseInitMetadata
    entities: dict[str, MetaWikibaseCompiledEntity]
    by_internal_name_identifier: dict[str, MetaWikibaseCompiledEntity]


@dataclass(frozen=True)
class MetaWikibaseSeedPlanEntry:
    """One dry-run baseline action derived from the compiled init fixture."""

    action: str
    key: str
    internal_name_identifier: str
    entity_type: str
    datatype: str | None
    payload: dict[str, Any]
    current_entity_id: str | None = None
    changed_fields: list[str] | None = None
    details: str | None = None


@dataclass(frozen=True)
class MetaWikibaseSeedPlan:
    """Dry-run baseline plan for the package-owned Meta-Wikibase seed."""

    metadata: MetaWikibaseInitMetadata
    operations: list[MetaWikibaseSeedPlanEntry]


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
            entity_value_kind=(
                entity_value_kind.strip()
                if isinstance(entity_value_kind, str)
                else None
            ),
        )

    return registry


@lru_cache(maxsize=1)
def _load_meta_wikibase_init_yaml_text() -> str:
    return (
        files("gkc.registry").joinpath("meta_wb_init.yaml").read_text(encoding="utf-8")
    )


def load_wikibase_init_document() -> dict[str, Any]:
    """Load the package-owned Meta-Wikibase init document and normalize it."""

    raw_document = yaml.safe_load(_load_meta_wikibase_init_yaml_text())
    return normalize_wikibase_init_document(raw_document)


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


def normalize_wikibase_init_document(document: dict[str, Any]) -> dict[str, Any]:
    """Normalize a Meta-Wikibase init document to canonical runtime datatypes."""

    if not isinstance(document, dict):
        raise RuntimeError("meta_wb_init document must be a mapping")

    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("meta_wb_init document is missing metadata")

    entities = document.get("entities")
    if not isinstance(entities, dict):
        raise RuntimeError("meta_wb_init document is missing entities")

    metadata_languages = _normalize_meta_wikibase_languages(metadata)

    normalized_entities: dict[str, dict[str, Any]] = {}
    normalized_properties: dict[str, dict[str, Any]] = {}

    for key, payload in entities.items():
        if not isinstance(payload, dict):
            raise RuntimeError(f"meta_wb_init entity '{key}' must be a mapping")
        normalized_payload = dict(payload)
        kind = normalized_payload.get("kind")
        if kind not in {"property", "item"}:
            raise RuntimeError(
                f"meta_wb_init entity '{key}' must define kind 'property' or 'item'"
            )

        normalized_payload["label"] = _normalize_meta_wikibase_authored_text(
            normalized_payload,
            field_name="label",
            languages=metadata_languages,
            entity_key=key,
        )
        normalized_payload["description"] = _normalize_meta_wikibase_authored_text(
            normalized_payload,
            field_name="description",
            languages=metadata_languages,
            entity_key=key,
        )

        if kind == "property":
            datatype = normalized_payload.get("datatype")
            if not isinstance(datatype, str) or not datatype.strip():
                raise RuntimeError(f"meta_wb_init property '{key}' is missing datatype")
            normalized_payload["datatype"] = canonicalize_wikibase_datatype(
                datatype,
                strict=True,
            )
            normalized_properties[key] = normalized_payload

        normalized_entities[key] = normalized_payload

    property_datatypes = {
        property_key: str(property_payload["datatype"])
        for property_key, property_payload in normalized_properties.items()
    }

    for key, payload in normalized_entities.items():
        normalized_entities[key] = _normalize_meta_wikibase_entity_attributes(
            payload,
            property_datatypes=property_datatypes,
            metadata_languages=metadata_languages,
        )

    _validate_meta_wikibase_value_list_contract(normalized_entities)

    normalized_metadata = dict(metadata)
    normalized_metadata["languages"] = metadata_languages

    return {
        "metadata": normalized_metadata,
        "entities": normalized_entities,
    }


def build_wikibase_init_index(
    document: dict[str, Any] | None = None,
) -> MetaWikibaseInitIndex:
    """Build a typed index over the package-owned Meta-Wikibase init fixture."""

    normalized_document = (
        load_wikibase_init_document()
        if document is None
        else normalize_wikibase_init_document(document)
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

    entities_block = normalized_document["entities"]
    entities: dict[str, MetaWikibaseInitEntity] = {}
    properties: dict[str, MetaWikibaseInitEntity] = {}
    items: dict[str, MetaWikibaseInitEntity] = {}
    by_internal_name_identifier: dict[str, MetaWikibaseInitEntity] = {}

    for key, payload in entities_block.items():
        kind = str(payload.get("kind", "")).strip()
        internal_name_identifier = f"{metadata.internal_name_identifier_prefix}{key}"
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
        elif kind == "item":
            items[key] = entity

    return MetaWikibaseInitIndex(
        metadata=metadata,
        entities=entities,
        properties=properties,
        items=items,
        by_internal_name_identifier=by_internal_name_identifier,
    )


def get_wikibase_init_entity(entity_key: str) -> MetaWikibaseInitEntity:
    """Return one normalized entity entry from the package-owned init fixture."""

    index = build_wikibase_init_index()
    try:
        return index.entities[entity_key]
    except KeyError as exc:
        raise KeyError(f"Unknown Meta-Wikibase init entity: {entity_key}") from exc


def build_wikibase_semantic_anchor_contract(
    document: dict[str, Any] | None = None,
    *,
    internal_name_identifier_prefix: str | None = None,
) -> MetaWikibaseSemanticAnchorContract:
    """Compile the package-owned init fixture into a required anchor contract."""

    index = build_wikibase_init_index(document)
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


def get_wikibase_init_contract_digest(
    document: dict[str, Any] | None = None,
) -> str:
    """Return a stable digest for the normalized Meta-Wikibase init contract."""

    normalized_document = (
        load_wikibase_init_document()
        if document is None
        else normalize_wikibase_init_document(document)
    )
    serialized = json.dumps(
        normalized_document,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compile_wikibase_seed(
    document: dict[str, Any] | None = None,
    *,
    label_language: str | None = None,
) -> MetaWikibaseSeedCompilation:
    """Compile the init fixture into symbolic Wikibase JSON payloads.

    The compiled payloads use internal name identifiers such as ``_instance_of``
    as unresolved placeholders for entity references. This keeps the output in a
    deterministic dry-run form that can be inspected before any live baseline
    orchestration resolves or writes entities.
    """

    from gkc.bottler import (
        ClaimBuilder,
        DataTypeTransformer,
        EntityShellBuilder,
        SnakBuilder,
    )

    index = build_wikibase_init_index(document)
    entity_shell_builder = EntityShellBuilder()
    claim_builder = ClaimBuilder(SnakBuilder(DataTypeTransformer()))
    resolved_label_language = _resolve_meta_wikibase_label_language(label_language)

    compiled_entities: dict[str, MetaWikibaseCompiledEntity] = {}
    compiled_by_internal_name_identifier: dict[str, MetaWikibaseCompiledEntity] = {}

    for entity in index.entities.values():
        symbolic_claims = _compile_meta_wikibase_entity_claims(
            entity,
            index=index,
            claim_builder=claim_builder,
        )

        shell = entity_shell_builder.build_entity_shell(
            {
                "labels": {resolved_label_language: entity.label},
                "descriptions": {resolved_label_language: entity.description},
                "statement_pids": sorted(symbolic_claims.keys()),
            }
        )
        payload = dict(shell)
        payload["type"] = entity.kind
        if entity.kind == "property" and entity.datatype is not None:
            payload["datatype"] = entity.datatype

        if symbolic_claims:
            payload_claims = payload.setdefault("claims", {})
            for property_id in sorted(symbolic_claims.keys()):
                payload_claims[property_id] = list(symbolic_claims[property_id])

        compiled_entity = MetaWikibaseCompiledEntity(
            key=entity.key,
            kind=entity.kind,
            internal_name_identifier=entity.internal_name_identifier,
            entity_type=entity.kind,
            datatype=entity.datatype,
            claims=symbolic_claims,
            payload=payload,
        )
        compiled_entities[entity.key] = compiled_entity
        compiled_by_internal_name_identifier[entity.internal_name_identifier] = (
            compiled_entity
        )

    return MetaWikibaseSeedCompilation(
        metadata=index.metadata,
        entities=compiled_entities,
        by_internal_name_identifier=compiled_by_internal_name_identifier,
    )


def plan_wikibase_seed_baseline(
    document: dict[str, Any] | None = None,
    *,
    current_entities_by_internal_name_identifier: (
        dict[str, dict[str, Any]] | None
    ) = None,
    entity_id_to_internal_name_identifier: dict[str, str] | None = None,
    label_language: str | None = None,
    required_value_language: str = "mul",
) -> MetaWikibaseSeedPlan:
    """Return a dry-run baseline plan for the package-owned init fixture."""

    compilation = compile_wikibase_seed(
        document,
        label_language=label_language,
    )
    operations: list[MetaWikibaseSeedPlanEntry] = []
    resolved_label_language = _resolve_meta_wikibase_label_language(label_language)
    required_monolingualtext_properties = {
        entity.internal_name_identifier
        for entity in build_wikibase_init_index(document).properties.values()
        if entity.datatype == "monolingualtext"
    }

    for entity in compilation.entities.values():
        current_entity = None
        if current_entities_by_internal_name_identifier is not None:
            current_entity = current_entities_by_internal_name_identifier.get(
                entity.internal_name_identifier
            )

        if current_entity is None:
            operations.append(
                MetaWikibaseSeedPlanEntry(
                    action="create",
                    key=entity.key,
                    internal_name_identifier=entity.internal_name_identifier,
                    entity_type=entity.entity_type,
                    datatype=entity.datatype,
                    current_entity_id=None,
                    changed_fields=None,
                    details="missing from current state",
                    payload=entity.payload,
                )
            )
            continue

        comparison = _compare_meta_wikibase_compiled_to_current(
            entity.payload,
            current_entity=current_entity,
            entity_id_to_internal_name_identifier=(
                entity_id_to_internal_name_identifier or {}
            ),
            label_language=resolved_label_language,
            required_value_language=required_value_language,
            required_monolingualtext_properties=required_monolingualtext_properties,
        )
        operations.append(
            MetaWikibaseSeedPlanEntry(
                action="skip" if comparison["matches"] else "update",
                key=entity.key,
                internal_name_identifier=entity.internal_name_identifier,
                entity_type=entity.entity_type,
                datatype=entity.datatype,
                current_entity_id=str(current_entity.get("id") or "").strip() or None,
                changed_fields=comparison["changed_fields"] or None,
                details=comparison["details"],
                payload=entity.payload,
            )
        )

    operations.sort(key=lambda operation: operation.internal_name_identifier)
    return MetaWikibaseSeedPlan(
        metadata=compilation.metadata,
        operations=operations,
    )


def normalize_wikibase_required_entity_view(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Return the canonical comparable view for one compiled seed payload."""

    return _normalize_meta_wikibase_compiled_payload(payload)


def normalize_wikibase_current_entity_view(
    entity: dict[str, Any],
    *,
    entity_id_to_internal_name_identifier: dict[str, str],
    label_language: str,
    required_value_language: str,
    required_monolingualtext_properties: set[str],
    expected_property_ids: set[str],
) -> tuple[dict[str, Any], list[str]]:
    """Return the canonical comparable view for one current Wikibase entity."""

    return _normalize_meta_wikibase_live_entity(
        entity,
        entity_id_to_internal_name_identifier=entity_id_to_internal_name_identifier,
        label_language=label_language,
        required_value_language=required_value_language,
        required_monolingualtext_properties=required_monolingualtext_properties,
        expected_property_ids=expected_property_ids,
    )


def compare_wikibase_entity_views(
    required_view: dict[str, Any],
    current_view: dict[str, Any],
    *,
    issues: list[str] | None = None,
) -> list[str]:
    """Compare canonical required and current views and return changed-field codes."""

    changed_fields: list[str] = []
    for field_name in _declared_meta_wikibase_fields(required_view):
        if field_name == "claims":
            changed_fields.extend(
                _compare_meta_wikibase_claim_field_changes(
                    required_view.get("claims"),
                    current_view.get("claims"),
                )
            )
            continue
        if required_view.get(field_name) != current_view.get(field_name):
            changed_fields.append(field_name)

    for issue in issues or []:
        if issue not in changed_fields:
            changed_fields.append(issue)

    return changed_fields


def _declared_meta_wikibase_fields(required_view: dict[str, Any]) -> tuple[str, ...]:
    """Return the managed fields explicitly declared by the authored contract."""

    return tuple(
        field_name
        for field_name in (
            "type",
            "datatype",
            "labels",
            "descriptions",
            "aliases",
            "claims",
        )
        if field_name in required_view
    )


def _compare_meta_wikibase_claim_field_changes(
    expected_claims: Any,
    current_claims: Any,
) -> list[str]:
    """Return property-level claim difference codes for comparable claim blocks."""

    expected = expected_claims if isinstance(expected_claims, dict) else {}
    current = current_claims if isinstance(current_claims, dict) else {}

    changed_fields: list[str] = []
    for property_id in sorted(set(expected.keys()) | set(current.keys())):
        if expected.get(property_id) != current.get(property_id):
            changed_fields.append(f"claims.{property_id}")
    return changed_fields


def _restrict_expected_meta_wikibase_claims_to_resolved_properties(
    expected: dict[str, Any],
    *,
    current_entity: dict[str, Any],
    entity_id_to_internal_name_identifier: dict[str, str],
) -> dict[str, Any]:
    """Limit claim comparison to properties that can be resolved from current evidence."""

    expected_claims = expected.get("claims")
    current_claims = current_entity.get("claims")
    if not isinstance(expected_claims, dict) or not expected_claims:
        return expected
    if not isinstance(current_claims, dict) or not current_claims:
        normalized = dict(expected)
        normalized.pop("claims", None)
        return normalized

    comparable_property_ids: set[str] = set()
    for property_id in current_claims.keys():
        if not isinstance(property_id, str) or not property_id:
            continue
        comparable_property_ids.add(
            entity_id_to_internal_name_identifier.get(property_id, property_id)
        )

    comparable_property_ids.update(
        internal_name
        for internal_name in entity_id_to_internal_name_identifier.values()
        if isinstance(internal_name, str) and internal_name
    )

    restricted_claims = {
        property_id: payload
        for property_id, payload in expected_claims.items()
        if property_id in comparable_property_ids
    }

    normalized = dict(expected)
    if restricted_claims:
        normalized["claims"] = restricted_claims
    else:
        normalized.pop("claims", None)
    return normalized


def _compare_meta_wikibase_compiled_to_current(
    compiled_payload: dict[str, Any],
    *,
    current_entity: dict[str, Any],
    entity_id_to_internal_name_identifier: dict[str, str],
    label_language: str,
    required_value_language: str,
    required_monolingualtext_properties: set[str],
) -> dict[str, Any]:
    """Compare one compiled symbolic payload against one live Wikibase entity."""

    expected = _normalize_meta_wikibase_compiled_payload(compiled_payload)
    expected = _restrict_expected_meta_wikibase_claims_to_resolved_properties(
        expected,
        current_entity=current_entity,
        entity_id_to_internal_name_identifier=entity_id_to_internal_name_identifier,
    )
    current, issues = _normalize_meta_wikibase_live_entity(
        current_entity,
        entity_id_to_internal_name_identifier=entity_id_to_internal_name_identifier,
        label_language=label_language,
        required_value_language=required_value_language,
        required_monolingualtext_properties=required_monolingualtext_properties,
        expected_property_ids=set(expected.get("claims", {}).keys()),
    )

    changed_fields: list[str] = []
    for field_name in _declared_meta_wikibase_fields(expected):
        if field_name == "claims":
            changed_fields.extend(
                _compare_meta_wikibase_claim_field_changes(
                    expected.get("claims"),
                    current.get("claims"),
                )
            )
            continue
        if expected.get(field_name) != current.get(field_name):
            changed_fields.append(field_name)

    if issues:
        changed_fields.extend(issue for issue in issues if issue not in changed_fields)

    details = "matches current state"
    if changed_fields:
        details = "fields changed: " + ", ".join(changed_fields)

    return {
        "matches": not changed_fields,
        "changed_fields": changed_fields,
        "details": details,
    }


def _normalize_meta_wikibase_compiled_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Normalize a compiled symbolic payload to a comparable canonical form."""

    normalized: dict[str, Any] = {
        "type": payload.get("type"),
    }
    if "datatype" in payload:
        normalized["datatype"] = payload.get("datatype")

    labels = payload.get("labels")
    descriptions = payload.get("descriptions")
    aliases = payload.get("aliases")
    claims = payload.get("claims")

    if isinstance(labels, dict) and labels:
        normalized["labels"] = _normalize_meta_wikibase_language_block(labels)
    if isinstance(descriptions, dict) and descriptions:
        normalized["descriptions"] = _normalize_meta_wikibase_language_block(
            descriptions
        )
    if isinstance(aliases, dict) and aliases:
        normalized["aliases"] = _normalize_meta_wikibase_alias_block(aliases)
    if isinstance(claims, dict) and claims:
        normalized["claims"] = _normalize_meta_wikibase_claims(claims)

    return normalized


def _normalize_meta_wikibase_live_entity(
    entity: dict[str, Any],
    *,
    entity_id_to_internal_name_identifier: dict[str, str],
    label_language: str,
    required_value_language: str,
    required_monolingualtext_properties: set[str],
    expected_property_ids: set[str],
) -> tuple[dict[str, Any], list[str]]:
    """Normalize one fetched Wikibase entity into comparable symbolic form."""

    normalized: dict[str, Any] = {
        "type": entity.get("type"),
    }
    datatype = entity.get("datatype")
    if isinstance(datatype, str) and datatype:
        normalized["datatype"] = canonicalize_wikibase_datatype(datatype)

    labels = _normalize_meta_wikibase_language_block(
        entity.get("labels"),
        allowed_languages={label_language},
    )
    descriptions = _normalize_meta_wikibase_language_block(
        entity.get("descriptions"),
        allowed_languages={label_language},
    )
    aliases = _normalize_meta_wikibase_alias_block(
        entity.get("aliases"),
        allowed_languages={label_language},
    )
    claims, issues = _normalize_meta_wikibase_claims(
        entity.get("claims"),
        entity_id_to_internal_name_identifier=entity_id_to_internal_name_identifier,
        expected_property_ids=expected_property_ids,
        required_monolingualtext_properties=required_monolingualtext_properties,
        required_value_language=required_value_language,
    )

    if labels:
        normalized["labels"] = labels
    if descriptions:
        normalized["descriptions"] = descriptions
    if aliases:
        normalized["aliases"] = aliases
    if claims:
        normalized["claims"] = claims

    return normalized, issues


def _normalize_meta_wikibase_language_block(
    block: Any,
    *,
    allowed_languages: set[str] | None = None,
) -> dict[str, dict[str, str]]:
    """Normalize a labels/descriptions block to comparable minimal form."""

    if not isinstance(block, dict):
        return {}

    normalized: dict[str, dict[str, str]] = {}
    for language in sorted(block.keys()):
        if allowed_languages is not None and language not in allowed_languages:
            continue
        payload = block.get(language)
        if not isinstance(payload, dict):
            continue
        value = payload.get("value")
        if isinstance(language, str) and language and isinstance(value, str) and value:
            normalized[language] = {"language": language, "value": value}
    return normalized


def _normalize_meta_wikibase_alias_block(
    block: Any,
    *,
    allowed_languages: set[str] | None = None,
) -> dict[str, list[dict[str, str]]]:
    """Normalize an aliases block to comparable minimal form."""

    if not isinstance(block, dict):
        return {}

    normalized: dict[str, list[dict[str, str]]] = {}
    for language in sorted(block.keys()):
        if allowed_languages is not None and language not in allowed_languages:
            continue
        payloads = block.get(language)
        if not isinstance(payloads, list):
            continue
        values: list[dict[str, str]] = []
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            value = payload.get("value")
            if isinstance(value, str) and value:
                values.append({"language": language, "value": value})
        if values:
            values.sort(key=lambda payload: payload["value"])
            normalized[language] = values
    return normalized


def _normalize_meta_wikibase_claims(
    claims: Any,
    *,
    entity_id_to_internal_name_identifier: dict[str, str] | None = None,
    expected_property_ids: set[str] | None = None,
    required_monolingualtext_properties: set[str] | None = None,
    required_value_language: str = "mul",
) -> Any:
    """Normalize claims to a comparable deterministic symbolic form."""

    if not isinstance(claims, dict):
        return ({}, []) if entity_id_to_internal_name_identifier is not None else {}

    issues: list[str] = []
    normalized: dict[str, list[dict[str, Any]]] = {}

    for property_id in sorted(claims.keys()):
        symbolic_property_id = (
            entity_id_to_internal_name_identifier.get(property_id, property_id)
            if entity_id_to_internal_name_identifier is not None
            else property_id
        )
        if (
            expected_property_ids is not None
            and symbolic_property_id not in expected_property_ids
        ):
            continue

        raw_claims = claims.get(property_id)
        if not isinstance(raw_claims, list):
            continue

        normalized_claims: list[dict[str, Any]] = []
        for claim in raw_claims:
            normalized_claim = _normalize_meta_wikibase_claim(
                claim,
                symbolic_property_id=symbolic_property_id,
                entity_id_to_internal_name_identifier=(
                    entity_id_to_internal_name_identifier or {}
                ),
                required_value_language=required_value_language,
                require_mul=symbolic_property_id
                in (required_monolingualtext_properties or set()),
            )
            if normalized_claim is None:
                continue
            if "issue" in normalized_claim:
                issues.append(str(normalized_claim.pop("issue")))
            normalized_claims.append(normalized_claim)

        if normalized_claims:
            normalized_claims.sort(key=lambda claim: json.dumps(claim, sort_keys=True))
            normalized[symbolic_property_id] = normalized_claims

    if entity_id_to_internal_name_identifier is not None:
        return normalized, issues
    return normalized


def _normalize_meta_wikibase_claim(
    claim: Any,
    *,
    symbolic_property_id: str,
    entity_id_to_internal_name_identifier: dict[str, str],
    required_value_language: str,
    require_mul: bool,
) -> dict[str, Any] | None:
    """Normalize one claim to comparable canonical form."""

    if not isinstance(claim, dict):
        return None
    mainsnak = claim.get("mainsnak")
    if not isinstance(mainsnak, dict):
        return None

    snaktype = mainsnak.get("snaktype")
    if snaktype == "novalue":
        normalized_claim = {
            "mainsnak": {
                "snaktype": "novalue",
                "property": symbolic_property_id,
            },
            "type": claim.get("type", "statement"),
            "rank": claim.get("rank", "normal"),
        }
        datatype = mainsnak.get("datatype")
        if isinstance(datatype, str) and datatype:
            normalized_claim["mainsnak"]["datatype"] = canonicalize_wikibase_datatype(
                datatype
            )
        return normalized_claim

    if snaktype != "value":
        return None

    datavalue = mainsnak.get("datavalue")
    if not isinstance(datavalue, dict):
        return None

    normalized_datavalue, issue = _normalize_meta_wikibase_datavalue(
        datavalue,
        entity_id_to_internal_name_identifier=entity_id_to_internal_name_identifier,
        required_value_language=required_value_language,
        require_mul=require_mul,
        property_id=symbolic_property_id,
    )
    normalized_claim = {
        "mainsnak": {
            "snaktype": "value",
            "property": symbolic_property_id,
            "datavalue": normalized_datavalue,
        },
        "type": claim.get("type", "statement"),
        "rank": claim.get("rank", "normal"),
    }
    if issue is not None:
        normalized_claim["issue"] = issue
    return normalized_claim


def _normalize_meta_wikibase_datavalue(
    datavalue: dict[str, Any],
    *,
    entity_id_to_internal_name_identifier: dict[str, str],
    required_value_language: str,
    require_mul: bool,
    property_id: str,
) -> tuple[dict[str, Any], str | None]:
    """Normalize one datavalue block to symbolic comparable form."""

    datavalue_type = datavalue.get("type")
    value = datavalue.get("value")

    if datavalue_type == "wikibase-entityid" and isinstance(value, dict):
        entity_id = value.get("id")
        if isinstance(entity_id, str) and entity_id:
            entity_id = entity_id_to_internal_name_identifier.get(entity_id, entity_id)
        return (
            {
                "type": "wikibase-entityid",
                "value": {
                    "entity-type": value.get("entity-type"),
                    "id": entity_id,
                },
            },
            None,
        )

    if datavalue_type == "monolingualtext":
        normalized_value = _normalize_meta_wikibase_monolingualtext(value)
        if normalized_value is None:
            return datavalue, f"{property_id}.invalid_monolingualtext"
        issue = None
        if require_mul and normalized_value["language"] != required_value_language:
            issue = f"{property_id}.language"
        return (
            {"type": "monolingualtext", "value": normalized_value},
            issue,
        )

    return ({"type": datavalue_type, "value": value}, None)


def _resolve_meta_wikibase_label_language(
    configured_language: str | None = None,
) -> str:
    """Resolve the display language for labels, descriptions, and aliases."""

    if isinstance(configured_language, str) and configured_language.strip():
        return configured_language.strip()

    try:
        from gkc import get_languages

        languages = get_languages()
    except Exception:
        return "en"

    if isinstance(languages, str):
        candidate = languages.strip()
        return candidate if candidate and candidate != "all" else "en"

    if isinstance(languages, list):
        for candidate in languages:
            if isinstance(candidate, str):
                candidate = candidate.strip()
                if candidate and candidate != "all":
                    return candidate

    return "en"


def _compile_meta_wikibase_entity_claims(
    entity: MetaWikibaseInitEntity,
    *,
    index: MetaWikibaseInitIndex,
    claim_builder: Any,
) -> dict[str, list[dict[str, Any]]]:
    """Compile the symbolic claim set for one init-fixture entity."""

    claims: dict[str, list[dict[str, Any]]] = {}

    _append_meta_wikibase_claim(
        claims,
        index.properties["name_identifier"].internal_name_identifier,
        claim_builder.create_claim(
            index.properties["name_identifier"].internal_name_identifier,
            entity.internal_name_identifier,
            "string",
        ),
    )

    if (
        isinstance(entity.instance_of, str)
        and entity.instance_of
        and entity.instance_of != "novalue"
    ):
        _append_meta_wikibase_claim(
            claims,
            index.properties["instance_of"].internal_name_identifier,
            _build_symbolic_entity_reference_claim(
                claim_builder,
                property_id=index.properties["instance_of"].internal_name_identifier,
                value_internal_name_identifier=(
                    index.entities[entity.instance_of].internal_name_identifier
                ),
                entity_type="item",
            ),
        )

    if (
        isinstance(entity.subclass_of, str)
        and entity.subclass_of
        and entity.subclass_of != "novalue"
    ):
        _append_meta_wikibase_claim(
            claims,
            index.properties["subclass_of"].internal_name_identifier,
            _build_symbolic_entity_reference_claim(
                claim_builder,
                property_id=index.properties["subclass_of"].internal_name_identifier,
                value_internal_name_identifier=(
                    index.entities[entity.subclass_of].internal_name_identifier
                ),
                entity_type="item",
            ),
        )

    for attribute_key, attribute_value in sorted((entity.attributes or {}).items()):
        property_entity = index.properties.get(attribute_key)
        if property_entity is None:
            continue
        claim = _build_meta_wikibase_attribute_claim(
            claim_builder,
            property_entity=property_entity,
            attribute_value=attribute_value,
            index=index,
        )
        if claim is None:
            continue
        _append_meta_wikibase_claim(
            claims,
            property_entity.internal_name_identifier,
            claim,
        )

    return {property_id: claims[property_id] for property_id in sorted(claims.keys())}


def _build_meta_wikibase_attribute_claim(
    claim_builder: Any,
    *,
    property_entity: MetaWikibaseInitEntity,
    attribute_value: Any,
    index: MetaWikibaseInitIndex,
) -> dict[str, Any] | None:
    """Compile one authored attribute into a symbolic claim when supported."""

    if attribute_value == "novalue":
        return _build_meta_wikibase_novalue_claim(
            property_id=property_entity.internal_name_identifier,
            datatype=property_entity.datatype,
        )

    if property_entity.datatype == "wikibase-item":
        if (
            not isinstance(attribute_value, str)
            or attribute_value not in index.entities
        ):
            return None
        return _build_symbolic_entity_reference_claim(
            claim_builder,
            property_id=property_entity.internal_name_identifier,
            value_internal_name_identifier=(
                index.entities[attribute_value].internal_name_identifier
            ),
            entity_type="item",
        )

    if property_entity.datatype == "monolingualtext":
        normalized_value = _normalize_meta_wikibase_monolingualtext(attribute_value)
        if normalized_value is None:
            return None
        return claim_builder.create_claim(
            property_entity.internal_name_identifier,
            normalized_value["text"],
            "monolingualtext",
            {"language": normalized_value["language"]},
        )

    if property_entity.datatype in {"string", "url", "quantity", "time"}:
        return claim_builder.create_claim(
            property_entity.internal_name_identifier,
            attribute_value,
            property_entity.datatype,
        )

    return None


def _build_meta_wikibase_novalue_claim(
    *,
    property_id: str,
    datatype: str | None,
) -> dict[str, Any]:
    """Build a claim payload for authored novalue requirements."""

    mainsnak: dict[str, Any] = {
        "snaktype": "novalue",
        "property": property_id,
    }
    if isinstance(datatype, str) and datatype:
        mainsnak["datatype"] = datatype

    return {
        "mainsnak": mainsnak,
        "type": "statement",
        "rank": "normal",
    }


def _build_symbolic_entity_reference_claim(
    claim_builder: Any,
    *,
    property_id: str,
    value_internal_name_identifier: str,
    entity_type: str,
) -> dict[str, Any]:
    """Build a symbolic entity-reference claim using bottler primitives."""

    from gkc.bottler import DataTypeTransformer

    datavalue = DataTypeTransformer.to_wikibase_entity_reference(
        value_internal_name_identifier,
        entity_type=entity_type,
    )
    return claim_builder.create_claim_from_datavalue(
        property_id,
        datavalue,
    )


def _append_meta_wikibase_claim(
    claims: dict[str, list[dict[str, Any]]],
    property_id: str,
    claim: dict[str, Any],
) -> None:
    """Append one compiled claim to the per-property claim bucket."""

    claims.setdefault(property_id, []).append(claim)


def _normalize_meta_wikibase_languages(metadata: dict[str, Any]) -> list[str]:
    raw_languages = metadata.get("languages")
    if not isinstance(raw_languages, list) or not raw_languages:
        return ["en"]

    normalized_languages: list[str] = []
    for language in raw_languages:
        if not isinstance(language, str) or not language.strip():
            continue
        normalized_languages.append(language.strip())

    return normalized_languages or ["en"]


def _normalize_meta_wikibase_authored_text(
    payload: dict[str, Any],
    *,
    field_name: str,
    languages: list[str],
    entity_key: str,
) -> str:
    direct_value = payload.get(field_name)
    if isinstance(direct_value, str) and direct_value.strip():
        return direct_value.strip()

    for language in languages:
        localized_key = f"{field_name}_{language}"
        localized_value = payload.get(localized_key)
        if isinstance(localized_value, str) and localized_value.strip():
            return localized_value.strip()

    raise RuntimeError(
        f"meta_wb_init entity '{entity_key}' is missing {field_name} text"
    )


def _normalize_meta_wikibase_entity_attributes(
    payload: dict[str, Any],
    *,
    property_datatypes: dict[str, str],
    metadata_languages: list[str],
) -> dict[str, Any]:
    skipped_keys = {
        "kind",
        "label",
        "description",
        "datatype",
        "instance_of",
        "subclass_of",
    }
    skipped_keys.update(f"label_{language}" for language in metadata_languages)
    skipped_keys.update(f"description_{language}" for language in metadata_languages)

    grouped_localized: dict[str, dict[str, Any]] = {}
    passthrough: dict[str, Any] = {}

    for key, value in payload.items():
        if key in skipped_keys:
            continue

        match = re.match(r"^(?P<base>.+)_(?P<lang>[a-z]{2,3}(?:-[a-z0-9]+)*)$", key)
        if match:
            base_key = str(match.group("base"))
            language = str(match.group("lang"))
            if language in metadata_languages and base_key in property_datatypes:
                grouped_localized.setdefault(base_key, {})[language] = value
                continue

        passthrough[key] = value

    normalized_payload: dict[str, Any] = {}
    for key in (
        "kind",
        "label",
        "description",
        "datatype",
        "instance_of",
        "subclass_of",
    ):
        if key in payload:
            normalized_payload[key] = payload[key]

    for key, value in passthrough.items():
        normalized_payload[key] = value

    for base_key, localized_values in grouped_localized.items():
        _ = property_datatypes.get(base_key)
        for language in metadata_languages:
            if language in localized_values:
                localized_value = localized_values[language]
                if isinstance(localized_value, str):
                    normalized_payload[base_key] = localized_value.strip()
                else:
                    normalized_payload[base_key] = localized_value
                break

    return normalized_payload


def _validate_meta_wikibase_value_list_contract(
    entities: dict[str, dict[str, Any]],
) -> None:
    for entity_key, payload in entities.items():
        if not isinstance(payload, dict):
            continue

        instance_of = payload.get("instance_of")
        if instance_of == "sparql_value_list":
            sparql_endpoint = payload.get("sparql_endpoint")
            query = payload.get("query")
            if not isinstance(sparql_endpoint, str) or not sparql_endpoint.strip():
                raise RuntimeError(
                    f"meta_wb_init entity '{entity_key}' requires 'sparql_endpoint' and 'query'"
                )
            if not isinstance(query, str) or not query.strip():
                raise RuntimeError(
                    f"meta_wb_init entity '{entity_key}' requires 'sparql_endpoint' and 'query'"
                )

        if instance_of == "embedded_value_list":
            value_list = payload.get("value_list")
            if not isinstance(value_list, list) or not value_list:
                raise RuntimeError(
                    f"meta_wb_init entity '{entity_key}' requires 'value_list'"
                )
            for row in value_list:
                if not isinstance(row, dict):
                    raise RuntimeError(
                        f"meta_wb_init entity '{entity_key}' requires 'value_list' rows with 'item' and 'itemLabel'"
                    )
                if "item" not in row or "itemLabel" not in row:
                    raise RuntimeError(
                        f"meta_wb_init entity '{entity_key}' requires 'value_list' rows with 'item' and 'itemLabel'"
                    )


def _normalize_meta_wikibase_monolingualtext(
    value: Any,
) -> dict[str, str] | None:
    """Normalize authored monolingualtext fixture values to text/language pairs."""

    from gkc.fermenter import validate_monolingualtext

    validation = validate_monolingualtext(value)
    if not validation.valid or not isinstance(validation.value, dict):
        return None

    language = validation.value.get("language")
    text = validation.value.get("text")
    if not isinstance(language, str) or not language:
        return None
    if not isinstance(text, str) or not text:
        return None

    return {"text": text, "language": language}


__all__ = [
    "MetaWikibaseInitEntity",
    "MetaWikibaseInitIndex",
    "MetaWikibaseInitMetadata",
    "MetaWikibaseCompiledEntity",
    "MetaWikibaseSemanticAnchorContract",
    "MetaWikibaseSemanticAnchorRequirement",
    "MetaWikibaseSeedCompilation",
    "MetaWikibaseSeedPlan",
    "MetaWikibaseSeedPlanEntry",
    "WikibaseDatatypeSpec",
    "build_wikibase_init_index",
    "build_wikibase_semantic_anchor_contract",
    "canonicalize_wikibase_datatype",
    "compare_wikibase_entity_views",
    "compile_wikibase_seed",
    "get_wikibase_init_entity",
    "get_wikibase_init_contract_digest",
    "get_wikibase_datatype_spec",
    "is_known_wikibase_datatype",
    "is_wikibase_item_datatype",
    "list_wikibase_datatypes",
    "load_wikibase_init_document",
    "load_wikibase_datatype_registry",
    "load_wikibase_datatype_registry_json",
    "normalize_wikibase_current_entity_view",
    "normalize_wikibase_init_document",
    "normalize_wikibase_required_entity_view",
    "plan_wikibase_seed_baseline",
]
