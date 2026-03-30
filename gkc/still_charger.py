"""Still Charger: Fill curation packets with concrete entity data.

This module provides the "charge the still" stage of the workflow:
profile-generated curation packets are populated with real input values before
barreling/transformation for shipping.
"""

import hashlib
import json
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import gkc
from gkc.fermenter import ConformanceNotice


@dataclass
class ChargeIssue:
    """Represents a non-fatal charging issue."""

    severity: str
    entity_id: str
    field: str
    message: str


@dataclass
class ChargeReport:
    """Summary of a charge operation."""

    entities_charged: int = 0
    entities_skipped: int = 0
    issues: list[ChargeIssue] = field(default_factory=list)


def _normalize_entity_uri(entity_uri: str) -> tuple[str, str]:
    """Normalize an entity URI to full URI and QID.

    Args:
        entity_uri: Full URI like "https://datadistillery.wikibase.cloud/entity/Q4"
                    or QID like "Q4"

    Returns:
        Tuple of (full_uri, qid)
    """
    if entity_uri.startswith("http://") or entity_uri.startswith("https://"):
        qid = entity_uri.split("/")[-1]
        return entity_uri, qid
    else:
        # Assume it's a QID; construct a default URI (can be customized if needed)
        return f"https://datadistillery.wikibase.cloud/entity/{entity_uri}", entity_uri


def _statement_is_fixed(statement: dict[str, Any]) -> bool:
    """Return True when a statement should be treated as fixed-value."""
    value_block = statement.get("value")
    if not isinstance(value_block, dict):
        return False
    value_list = value_block.get("value_list")
    return isinstance(value_list, list) and len(value_list) > 0


def _normalize_statement_scaffold(statement: dict[str, Any]) -> dict[str, Any]:
    """Normalize statement scaffold fields for packet assembly."""
    normalized = deepcopy(statement)
    normalized.setdefault("fixed", _statement_is_fixed(normalized))
    return normalized


def _target_profile_uri_from_edge(edge: dict[str, Any]) -> Optional[str]:
    """Extract target profile URI from a profile graph edge."""
    target_ref = edge.get("id") or edge.get("entity") or edge.get("target")
    if not isinstance(target_ref, str) or not target_ref:
        return None
    target_uri, _ = _normalize_entity_uri(target_ref)
    return target_uri


def _extract_wikidata_property_id(target: Any) -> Optional[str]:
    """Extract a Wikidata property id from an io_map route target."""
    if not isinstance(target, str) or not target:
        return None

    candidate = target.rstrip("/").split("/")[-1]
    if candidate.startswith("P") and candidate[1:].isdigit():
        return candidate
    return None


def _profile_statement_routes(profile_meta: dict[str, Any]) -> list[dict[str, Any]]:
    """Return statement/property/profile routes for one profile.

    Prefer generated linkage_index metadata and fall back to statement io_map/value.profile.
    """
    metadata = profile_meta.get("metadata", {})
    linkage_index = (
        metadata.get("linkage_index") if isinstance(metadata, dict) else None
    )
    outbound = (
        linkage_index.get("outbound_by_statement")
        if isinstance(linkage_index, dict)
        else None
    )
    if isinstance(outbound, dict) and outbound:
        routes: list[dict[str, Any]] = []
        for statement_uri in sorted(outbound.keys()):
            route = outbound.get(statement_uri, {})
            if not isinstance(route, dict):
                continue
            property_ids = route.get("wikidata_properties", [])
            target_profiles = route.get("target_profiles", [])
            routes.append(
                {
                    "statement_uri": statement_uri,
                    "property_ids": [
                        prop_id
                        for prop_id in property_ids
                        if isinstance(prop_id, str) and prop_id
                    ],
                    "target_profiles": [
                        target_profile
                        for target_profile in target_profiles
                        if isinstance(target_profile, str) and target_profile
                    ],
                }
            )
        if routes:
            return routes

    routes = []
    statements = profile_meta.get("statements", [])
    if not isinstance(statements, list):
        return routes

    targets_by_statement: dict[str, set[str]] = {}
    profile_graph = (
        metadata.get("profile_graph", []) if isinstance(metadata, dict) else []
    )
    if isinstance(profile_graph, list):
        for edge in profile_graph:
            if not isinstance(edge, dict):
                continue
            via_statement = edge.get("via_statement")
            target_profile = _target_profile_uri_from_edge(edge)
            if (
                not isinstance(via_statement, str)
                or not via_statement
                or not target_profile
            ):
                continue
            targets_by_statement.setdefault(via_statement, set()).add(target_profile)

    for stmt in statements:
        if not isinstance(stmt, dict):
            continue
        statement_uri = stmt.get("entity")
        if not isinstance(statement_uri, str) or not statement_uri:
            continue
        io_map = stmt.get("io_map", [])
        property_ids: list[str] = []
        if isinstance(io_map, list):
            for mapping in io_map:
                if not isinstance(mapping, dict):
                    continue
                property_id = _extract_wikidata_property_id(mapping.get("to"))
                if property_id and property_id not in property_ids:
                    property_ids.append(property_id)

        target_profiles: list[str] = []
        value_payload = stmt.get("value")
        if isinstance(value_payload, dict):
            profile_payload = value_payload.get("profile")
            if isinstance(profile_payload, dict):
                target_profile = profile_payload.get("entity")
                if isinstance(target_profile, str) and target_profile:
                    target_profiles.append(target_profile)

        graph_targets = sorted(targets_by_statement.get(statement_uri, set()))
        for target_profile in graph_targets:
            if target_profile not in target_profiles:
                target_profiles.append(target_profile)

        routes.append(
            {
                "statement_uri": statement_uri,
                "property_ids": property_ids,
                "target_profiles": target_profiles,
            }
        )

    return routes


def _profile_statement_map(
    profile_meta: dict[str, Any],
) -> tuple[dict[str, str], set[str]]:
    """Return property->statement_uri map and allowed property set for a profile."""
    statement_by_property: dict[str, str] = {}
    allowed_properties: set[str] = set()

    for route in _profile_statement_routes(profile_meta):
        statement_uri = route.get("statement_uri")
        if not isinstance(statement_uri, str) or not statement_uri:
            continue
        for property_id in route.get("property_ids", []):
            if not isinstance(property_id, str) or not property_id:
                continue
            allowed_properties.add(property_id)
            statement_by_property.setdefault(property_id, statement_uri)

    return statement_by_property, allowed_properties


def packet_entities(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Return packet data entities in deterministic list form.

    Wizard-facing packet operations should consume only the canonical
    ``data.entities`` surface.
    """
    data = packet.get("data")
    if not isinstance(data, dict):
        return []
    entities = data.get("entities")
    if not isinstance(entities, list):
        return []
    return [entity for entity in entities if isinstance(entity, dict)]


def packet_primary_profile_id(packet: dict[str, Any]) -> Optional[str]:
    """Return primary profile URI from packet metadata when available."""
    metadata = packet.get("metadata")
    if not isinstance(metadata, dict):
        return None
    primary = metadata.get("primary_profile")
    if not isinstance(primary, dict):
        return None
    primary_id = primary.get("id")
    if isinstance(primary_id, str) and primary_id:
        return primary_id
    return None


def packet_entity_by_ref(
    packet: dict[str, Any], entity_ref: str
) -> Optional[dict[str, Any]]:
    """Resolve one packet entity by profile name_identifier or profile URI."""
    if not isinstance(entity_ref, str) or not entity_ref:
        return None

    for entity in packet_entities(packet):
        profile_name = entity.get("profile")
        profile_id = entity.get("id")
        if entity_ref == profile_name or entity_ref == profile_id:
            return entity
    return None


def packet_outgoing_links(
    packet: dict[str, Any], entity_ref: str
) -> list[dict[str, Any]]:
    """Return outgoing linked-entity edges for one packet entity.

    Results are sorted and each edge includes the resolved target entity slot
    under ``target_entity`` when present in ``data.entities``.
    """
    source_entity = packet_entity_by_ref(packet, entity_ref)
    if not isinstance(source_entity, dict):
        return []

    source_profile = source_entity.get("profile")
    if not isinstance(source_profile, str) or not source_profile:
        return []

    target_by_profile = {
        entity.get("profile"): entity
        for entity in packet_entities(packet)
        if isinstance(entity.get("profile"), str)
    }

    metadata = packet.get("metadata")
    graph = metadata.get("graph") if isinstance(metadata, dict) else None
    edges = graph.get("edges") if isinstance(graph, dict) else None
    if not isinstance(edges, list):
        return []

    resolved: list[dict[str, Any]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("from") != source_profile:
            continue

        target_profile = edge.get("to")
        target_entity = (
            target_by_profile.get(target_profile)
            if isinstance(target_profile, str)
            else None
        )

        resolved.append(
            {
                "from": source_profile,
                "to": target_profile,
                "from_id": edge.get("from_id"),
                "to_id": edge.get("to_id"),
                "via_statement": edge.get("via_statement"),
                "relationship_type": edge.get("relationship_type"),
                "label": edge.get("label"),
                "target_entity": target_entity,
            }
        )

    resolved.sort(
        key=lambda edge: (
            str(edge.get("to", "")),
            str(edge.get("via_statement", "")),
            str(edge.get("relationship_type", "")),
        )
    )
    return resolved


def _profile_uri_from_doc(profile_doc: dict[str, Any], fallback_uri: str) -> str:
    candidate = profile_doc.get("id") or profile_doc.get("entity")
    if isinstance(candidate, str) and candidate:
        normalized, _ = _normalize_entity_uri(candidate)
        return normalized
    return fallback_uri


def _profile_name_identifier(profile_doc: dict[str, Any], profile_uri: str) -> str:
    name_identifier = profile_doc.get("name_identifier")
    if isinstance(name_identifier, str) and name_identifier.strip():
        return name_identifier.strip()
    return profile_uri.rstrip("/").split("/")[-1]


def _statement_identifier(statement: dict[str, Any]) -> Optional[str]:
    candidate = statement.get("id") or statement.get("entity")
    if not isinstance(candidate, str) or not candidate:
        return None
    normalized, _ = _normalize_entity_uri(candidate)
    return normalized


def _statement_name_identifier(statement: dict[str, Any]) -> str:
    explicit = statement.get("name_identifier")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    statement_id = _statement_identifier(statement)
    if statement_id:
        return statement_id.rstrip("/").split("/")[-1]

    label = statement.get("label")
    if isinstance(label, str) and label.strip():
        normalized = re.sub(r"[^A-Za-z0-9_]+", "_", label.strip()).strip("_")
        if normalized:
            return normalized

    return "statement"


def _statement_data_slot(
    statement: dict[str, Any],
    value_list_routes: Optional[dict[str, dict[str, Any]]] = None,
    *,
    include_children: bool = False,
) -> dict[str, Any]:
    value_block = statement.get("value")
    data_type = value_block.get("type") if isinstance(value_block, dict) else None
    data_value: Any = None

    if isinstance(value_block, dict):
        value_list = value_block.get("value_list")
        if isinstance(value_list, list) and len(value_list) == 1:
            data_value = value_list[0]

    statement_id = _statement_identifier(statement)
    value_list_path: Any = None
    if isinstance(value_block, dict):
        route_ref = value_block.get("value_list_reference")
        if isinstance(route_ref, str) and route_ref:
            value_list_path = route_ref

    if value_list_path is None and statement_id and isinstance(value_list_routes, dict):
        route_entry = value_list_routes.get(statement_id, {})
        if isinstance(route_entry, dict):
            route_path = route_entry.get("cache_path")
            if isinstance(route_path, str) and route_path:
                value_list_path = route_path

    slot: dict[str, Any] = {
        "id": statement_id,
        "data-type": data_type,
        "data-value": data_value,
    }
    if value_list_path is not None:
        slot["value-list"] = value_list_path

    if include_children:
        qualifiers = statement.get("qualifiers")
        if isinstance(qualifiers, list) and qualifiers:
            qualifier_slots: dict[str, list[dict[str, Any]]] = {}
            for qualifier in qualifiers:
                if not isinstance(qualifier, dict):
                    continue
                qualifier_key = _statement_name_identifier(qualifier)
                qualifier_entity_classes = qualifier.get("entity_classes", [])
                qualifier_is_modifier = "Q58" in qualifier_entity_classes
                qualifier_slots.setdefault(qualifier_key, []).append(
                    _statement_data_slot(
                        qualifier,
                        value_list_routes,
                        include_children=qualifier_is_modifier,
                    )
                )
            if qualifier_slots:
                slot["qualifiers"] = qualifier_slots

        references = statement.get("references")
        if isinstance(references, list) and references:
            reference_slots: dict[str, list[dict[str, Any]]] = {}
            for reference in references:
                if not isinstance(reference, dict):
                    continue
                reference_key = _statement_name_identifier(reference)
                reference_entity_classes = reference.get("entity_classes", [])
                reference_is_modifier = "Q58" in reference_entity_classes
                reference_slots.setdefault(reference_key, []).append(
                    _statement_data_slot(
                        reference,
                        value_list_routes,
                        include_children=reference_is_modifier,
                    )
                )
            if reference_slots:
                slot["references"] = reference_slots

    return slot


def _identification_language_slots(
    identification: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    def _slots_for(field_name: str) -> dict[str, Any]:
        field_def = identification.get(field_name)
        if isinstance(field_def, dict):
            languages = sorted(
                language
                for language, value in field_def.items()
                if isinstance(language, str) and language and isinstance(value, dict)
            )
            if languages:
                return {language: {"data-value": ""} for language in languages}
        return {"mul": {"data-value": ""}}

    return (
        _slots_for("labels"),
        _slots_for("descriptions"),
        _slots_for("aliases"),
    )


def _canonical_json_digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _reseal_packet_metadata(packet: dict[str, Any]) -> None:
    """Recompute metadata digest after packet metadata changes."""
    metadata = packet.get("metadata")
    if not isinstance(metadata, dict):
        return

    canonical_metadata = deepcopy(metadata)
    canonical_metadata.pop("integrity", None)
    metadata_digest = _canonical_json_digest(canonical_metadata)
    metadata["integrity"] = {
        "metadata_canonicalization": "json-sort-keys-v1",
        "metadata_digest_algorithm": "sha256",
        "metadata_digest": metadata_digest,
    }


def _copy_language_values(
    slot: dict[str, Any],
    source: Any,
    *,
    aliases: bool = False,
) -> None:
    """Copy Wikibase language-keyed values into packet slot shape."""
    if not isinstance(source, dict):
        return

    for language, payload in source.items():
        if not isinstance(language, str) or not language:
            continue

        if aliases:
            values: list[str] = []
            if isinstance(payload, list):
                for alias_entry in payload:
                    if isinstance(alias_entry, dict):
                        alias_value = alias_entry.get("value")
                        if isinstance(alias_value, str):
                            values.append(alias_value)
            elif isinstance(payload, dict):
                alias_value = payload.get("value")
                if isinstance(alias_value, str):
                    values.append(alias_value)

            if values:
                slot[language] = {"data-value": values}
            continue

        if isinstance(payload, dict):
            value = payload.get("value")
            if isinstance(value, str):
                slot[language] = {"data-value": value}


def _claims_to_values(raw_claims: list[dict[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for claim in raw_claims:
        if not isinstance(claim, dict):
            continue
        mainsnak = claim.get("mainsnak")
        if not isinstance(mainsnak, dict):
            continue
        datavalue = mainsnak.get("datavalue")
        if not isinstance(datavalue, dict):
            continue
        if "value" in datavalue:
            values.append(datavalue.get("value"))
    return values


def _notice_payloads(notices: list[ConformanceNotice]) -> list[dict[str, Any]]:
    return [
        {
            "severity": notice.severity,
            "code": notice.code,
            "message": notice.message,
            "statement_ref": notice.statement_ref,
            "normalized_value": notice.normalized_value,
        }
        for notice in notices
    ]


def _build_unified_graph(
    profile_docs: dict[str, dict[str, Any]],
    name_by_uri: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    for profile_uri, profile_doc in profile_docs.items():
        profile_name = name_by_uri[profile_uri]
        nodes[profile_name] = {
            "kind": "profile",
            "name_identifier": profile_name,
            "id": profile_uri,
            "label": profile_doc.get("metadata", {}).get("labels", {}).get("mul")
            or profile_doc.get("metadata", {}).get("labels", {}).get("en"),
        }

        for edge in profile_doc.get("metadata", {}).get("profile_graph", []):
            if not isinstance(edge, dict):
                continue
            target_uri = _target_profile_uri_from_edge(edge)
            if not target_uri:
                continue
            target_name = name_by_uri.get(
                target_uri, target_uri.rstrip("/").split("/")[-1]
            )
            edges.append(
                {
                    "from": profile_name,
                    "to": target_name,
                    "from_id": profile_uri,
                    "to_id": target_uri,
                    "via_statement": edge.get("via_statement"),
                    "relationship_type": edge.get("linkage_type") or "profile_link",
                }
            )

    edges.sort(
        key=lambda edge: (
            str(edge.get("from", "")),
            str(edge.get("to", "")),
            str(edge.get("via_statement", "")),
        )
    )
    ordered_nodes = [nodes[key] for key in sorted(nodes.keys())]
    return {"nodes": ordered_nodes, "edges": edges}


def _load_related_profile_documents(
    root_profile_uri: str,
    root_profile_doc: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Load root and directly linked profile documents from profile_graph edges."""
    from gkc.spirit_safe import load_profile

    profile_docs: dict[str, dict[str, Any]] = {root_profile_uri: root_profile_doc}
    profile_graph = root_profile_doc.get("metadata", {}).get("profile_graph", [])
    if not isinstance(profile_graph, list):
        return profile_docs

    for edge in profile_graph:
        if not isinstance(edge, dict):
            continue
        target_uri = _target_profile_uri_from_edge(edge)
        if not target_uri or target_uri in profile_docs:
            continue

        target_qid = target_uri.split("/")[-1]
        try:
            loaded = load_profile(target_qid)
        except Exception:
            continue

        loaded_uri = (
            loaded.get("id")
            if isinstance(loaded.get("id"), str)
            else (
                loaded.get("entity")
                if isinstance(loaded.get("entity"), str)
                else target_uri
            )
        )
        profile_docs[loaded_uri] = loaded

    return profile_docs


def _build_cross_references(
    profile_docs: dict[str, dict[str, Any]],
    entity_id_by_uri: dict[str, str],
) -> list[dict[str, Any]]:
    """Build deterministic cross-reference edges for packet entities."""
    uri_by_qid = {uri.split("/")[-1]: uri for uri in profile_docs}
    cross_refs: list[dict[str, Any]] = []

    for source_uri in sorted(profile_docs.keys()):
        source_doc = profile_docs[source_uri]
        source_entity_id = entity_id_by_uri.get(source_uri)
        if not source_entity_id:
            continue

        source_qid = source_uri.split("/")[-1]
        profile_graph = source_doc.get("metadata", {}).get("profile_graph", [])
        if not isinstance(profile_graph, list):
            continue

        for edge in profile_graph:
            if not isinstance(edge, dict):
                continue

            raw_target_uri = _target_profile_uri_from_edge(edge)
            if not raw_target_uri:
                continue
            target_qid = raw_target_uri.split("/")[-1]
            target_uri = uri_by_qid.get(target_qid, raw_target_uri)
            target_entity_id = entity_id_by_uri.get(target_uri)
            if not target_entity_id:
                continue

            cross_refs.append(
                {
                    "from": source_entity_id,
                    "from_profile": source_qid,
                    "from_entity": source_uri,
                    "to": target_entity_id,
                    "to_profile": target_qid,
                    "to_entity": target_uri,
                    "via_statement": edge.get("via_statement"),
                    "relationship_type": edge.get("linkage_type"),
                    "label": edge.get("label"),
                }
            )

    cross_refs.sort(
        key=lambda ref: (
            str(ref.get("from", "")),
            str(ref.get("to", "")),
            str(ref.get("via_statement", "")),
        )
    )
    return cross_refs


def _build_value_list_routes(
    profile_docs: dict[str, dict[str, Any]],
    source_root: Optional[Path],
) -> dict[str, dict[str, Any]]:
    """Build URI-keyed value list routes from profile metadata."""
    routes: dict[str, dict[str, Any]] = {}

    for profile_doc in profile_docs.values():
        value_list_graph = profile_doc.get("metadata", {}).get("value_list_graph", [])
        if not isinstance(value_list_graph, list):
            continue

        for route in value_list_graph:
            if not isinstance(route, dict):
                continue

            statement_uri = route.get("via_statement")
            if not isinstance(statement_uri, str) or not statement_uri:
                continue

            cache_path = route.get("cache_path")
            if not cache_path and isinstance(route.get("query_id"), str):
                cache_path = f"cache/queries/{route['query_id']}.json"

            entry = {
                "entity": route.get("entity"),
                "label": route.get("label"),
            }
            if isinstance(cache_path, str) and cache_path:
                entry["cache_path"] = cache_path

                if source_root is not None:
                    resolved_cache = source_root / cache_path
                    if resolved_cache.exists():
                        try:
                            cache_data = json.loads(
                                resolved_cache.read_text(encoding="utf-8")
                            )
                            metadata = cache_data.get("metadata", {})
                            if isinstance(metadata.get("count"), int):
                                entry["item_count"] = metadata["count"]
                            elif isinstance(cache_data.get("items"), list):
                                entry["item_count"] = len(cache_data["items"])
                            else:
                                entry["item_count"] = len(
                                    cache_data.get("results", {}).get("bindings", [])
                                )
                        except Exception:
                            pass

            existing = routes.get(statement_uri)
            if existing is None:
                routes[statement_uri] = entry
            elif "item_count" not in existing and "item_count" in entry:
                routes[statement_uri] = entry

    return {
        statement_uri: routes[statement_uri] for statement_uri in sorted(routes.keys())
    }


def build_curation_packet_from_json_profile(
    profile_entity: str,
    json_profile_doc: dict,
    *,
    source_root: Optional[Path] = None,
) -> dict:
    """Build a curation packet from a JSON Entity Profile document.

    This is the first stage of the still_charger pipeline: assembling a blank
    curation packet scaffold from a pre-loaded JSON profile, ready to be charged
    with concrete values.

    Args:
        profile_entity: Full entity URI (e.g., "https://datadistillery.wikibase.cloud/entity/Q4")
                       or QID (e.g., "Q4")
        json_profile_doc: The loaded JSON Entity Profile document
        source_root: Optional path root for resolving value list cache files;
                    if provided, item_count will be hydrated from cache JSON

    Returns:
        A dictionary representing the curation packet matching the frozen contract:
        {
            "packet_id": "pkt-<uuid>",
            "operation_mode": "new",
            "profile_entity": "<full_uri>",
            "entities": [...],
            "cross_references": {...},
            "value_list_routes": {...}
        }
    """
    # Step 1: Normalize profile_entity to full URI
    full_profile_uri, _ = _normalize_entity_uri(profile_entity)

    # Step 2: Load primary + linked profile documents from metadata.profile_graph
    profile_docs = _load_related_profile_documents(full_profile_uri, json_profile_doc)

    # Step 3: Build ordered profiles (primary first, then deterministic linked order)
    ordered_profile_uris = [full_profile_uri] + sorted(
        uri for uri in profile_docs.keys() if uri != full_profile_uri
    )

    data_entities: list[dict[str, Any]] = []
    metadata_profiles: list[dict[str, Any]] = []
    profile_name_by_uri: dict[str, str] = {}
    value_list_routes = _build_value_list_routes(profile_docs, source_root)

    for profile_uri in ordered_profile_uris:
        profile_doc = profile_docs[profile_uri]
        profile_uri = _profile_uri_from_doc(profile_doc, profile_uri)
        profile_name = _profile_name_identifier(profile_doc, profile_uri)
        profile_name_by_uri[profile_uri] = profile_name

        statements = profile_doc.get("statements", [])
        if not isinstance(statements, list):
            statements = []

        normalized_statements = [
            _normalize_statement_scaffold(statement)
            for statement in statements
            if isinstance(statement, dict)
        ]

        statement_slots: dict[str, dict[str, Any]] = {}
        for statement in normalized_statements:
            key_base = _statement_name_identifier(statement)
            key = key_base
            suffix = 2
            while key in statement_slots:
                key = f"{key_base}_{suffix}"
                suffix += 1
            statement_slots[key] = _statement_data_slot(
                statement,
                value_list_routes,
                include_children=True,
            )

        identification = deepcopy(profile_doc.get("identification", {}))
        if not isinstance(identification, dict):
            identification = {}

        labels_slot, descriptions_slot, aliases_slot = _identification_language_slots(
            identification
        )

        metadata_profiles.append(
            {
                "id": profile_uri,
                "name_identifier": profile_name,
                "identification": identification,
                "statements": normalized_statements,
                "metadata": deepcopy(profile_doc.get("metadata", {})),
            }
        )

        data_entities.append(
            {
                "profile": profile_name,
                "id": profile_uri,
                "labels": labels_slot,
                "descriptions": descriptions_slot,
                "aliases": aliases_slot,
                "statements": statement_slots,
            }
        )

    primary_profile_name = profile_name_by_uri.get(
        full_profile_uri, full_profile_uri.rstrip("/").split("/")[-1]
    )

    # Step 4: Build packet metadata graph and mint metadata
    unified_graph = _build_unified_graph(profile_docs, profile_name_by_uri)
    minted_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Step 5: Generate packet_id
    packet_id = f"pkt-{uuid.uuid4()}"

    metadata = {
        "primary_profile": {
            "name_identifier": primary_profile_name,
            "id": full_profile_uri,
        },
        "profiles": metadata_profiles,
        "graph": unified_graph,
        "mint": {
            "minted_at": minted_at,
            "generator": "gkc.still_charger.build_curation_packet_from_json_profile",
            "gkc_version": gkc.__version__,
        },
    }

    metadata_digest = _canonical_json_digest(metadata)
    metadata["integrity"] = {
        "metadata_canonicalization": "json-sort-keys-v1",
        "metadata_digest_algorithm": "sha256",
        "metadata_digest": metadata_digest,
    }

    packet = {
        "packet_id": packet_id,
        "operation_mode": "new",
        "metadata": metadata,
        "data": {
            "entities": data_entities,
        },
    }

    return packet


def create_curation_packet(
    profile_id: str,
    operation_mode: str = "single",
    load_wikidata_qids: bool = False,
    depth: int = 1,
    manifest: Optional[Any] = None,
) -> dict[str, Any]:
    """Create a curation packet scaffold from SpiritSafe JSON profiles.

    This is the canonical packet-assembly entrypoint. It loads the primary
    profile from SpiritSafe, applies operation-mode expansion policy, and
    delegates scaffold construction to ``build_curation_packet_from_json_profile``.
    """

    del load_wikidata_qids
    del depth
    del manifest

    if operation_mode not in {"single", "bulk"}:
        raise ValueError(
            f"Unsupported operation_mode '{operation_mode}'. Expected 'single' or 'bulk'."
        )

    from gkc.spirit_safe import get_spirit_safe_source, load_profile

    profile_doc = load_profile(profile_id)
    profile_uri, _ = _normalize_entity_uri(str(profile_doc.get("id") or profile_id))

    if operation_mode == "single":
        profile_doc = deepcopy(profile_doc)
        profile_doc.setdefault("metadata", {})["profile_graph"] = []

    source = get_spirit_safe_source()
    packet = build_curation_packet_from_json_profile(
        profile_entity=profile_uri,
        json_profile_doc=profile_doc,
        source_root=source.local_root if source.mode == "local" else None,
    )
    packet["operation_mode"] = operation_mode
    return packet


def create_and_charge_curation_packet(
    profile_id: str,
    *,
    qid: Optional[str] = None,
    qid_map: Optional[dict[str, str]] = None,
    include_linked_profiles: bool = False,
    mash_client: Optional[Any] = None,
) -> tuple[dict[str, Any], list[ConformanceNotice]]:
    """Create and charge a packet in one call.

    The default packet scope is the primary profile only. Set
    ``include_linked_profiles=True`` to include directly linked profiles.
    """
    operation_mode = "bulk" if include_linked_profiles else "single"
    packet = create_curation_packet(profile_id, operation_mode=operation_mode)

    resolved_qid_map: dict[str, str] = {}
    if isinstance(qid_map, dict):
        resolved_qid_map.update(qid_map)

    if qid:
        entities = packet.get("data", {}).get("entities", [])
        if isinstance(entities, list):
            for entity in entities:
                if not isinstance(entity, dict):
                    continue
                entity_id = entity.get("id")
                profile_name = entity.get("profile")
                if isinstance(entity_id, str) and entity_id:
                    resolved_qid_map[entity_id] = qid
                if isinstance(profile_name, str) and profile_name:
                    resolved_qid_map[profile_name] = qid

    if not resolved_qid_map:
        raise ValueError("Either qid or qid_map must be provided")

    return charge_packet_from_wikidata_items(
        packet,
        resolved_qid_map,
        mash_client=mash_client,
    )


def _resolve_linked_entity_graph_from_primary(
    packet: dict[str, Any],
    primary_qid: str,
    mash_client: Any,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Phase 1: Resolve which linked entities the primary entity references.

    Args:
        packet: Curation packet with metadata profiles assembled
        primary_qid: Wikidata QID of the primary entity (e.g., "Q195562")
        mash_client: WikibaseLoader instance for fetching entity JSON

    Returns:
        Tuple of (entity_profile_map, primary_entity_json)
        - entity_profile_map: dict mapping entity URIs/names to profile URIs
        - primary_entity_json: raw primary entity JSON from Wikidata
    """
    entity_profile_map: dict[str, str] = {}

    # Load primary entity JSON
    primary_entity = mash_client.load_entity_data(primary_qid)
    if not isinstance(primary_entity, dict):
        raise ValueError(f"Could not load primary entity {primary_qid}")

    primary_profile = packet.get("metadata", {}).get("primary_profile", {})
    primary_profile_uri = primary_profile.get("id")
    primary_profile_name = primary_profile.get("name_identifier")

    # Add primary to map (both URI and name)
    if isinstance(primary_profile_uri, str):
        entity_profile_map[primary_profile_uri] = primary_profile_uri
    if isinstance(primary_profile_name, str):
        entity_profile_map[primary_profile_name] = primary_profile_uri
    entity_profile_map[primary_qid] = primary_profile_uri

    profiles = packet.get("metadata", {}).get("profiles", [])
    profile_name_by_uri: dict[str, str] = {}
    for profile_meta in profiles:
        if not isinstance(profile_meta, dict):
            continue
        profile_uri = profile_meta.get("id")
        profile_name = profile_meta.get("name_identifier")
        if isinstance(profile_uri, str) and isinstance(profile_name, str):
            profile_name_by_uri[profile_uri] = profile_name

    primary_profile_meta = next(
        (
            profile_meta
            for profile_meta in profiles
            if isinstance(profile_meta, dict)
            and profile_meta.get("id") == primary_profile_uri
        ),
        None,
    )

    if not isinstance(primary_profile_meta, dict):
        return entity_profile_map, primary_entity

    # Scan primary entity claims using primary-profile linkage routes.
    primary_claims = primary_entity.get("claims", {})
    for route in _profile_statement_routes(primary_profile_meta):
        target_profiles = route.get("target_profiles", [])
        property_ids = route.get("property_ids", [])
        if not isinstance(target_profiles, list) or not isinstance(property_ids, list):
            continue

        for target_profile_uri in target_profiles:
            if not isinstance(target_profile_uri, str) or not target_profile_uri:
                continue
            target_profile_name = profile_name_by_uri.get(target_profile_uri)

            for prop_key in property_ids:
                if not isinstance(prop_key, str) or not prop_key:
                    continue
                claims_for_prop = primary_claims.get(prop_key, [])
                if not isinstance(claims_for_prop, list):
                    continue

                for claim in claims_for_prop:
                    if not isinstance(claim, dict):
                        continue
                    mainsnak = claim.get("mainsnak", {})
                    if not isinstance(mainsnak, dict):
                        continue
                    datavalue = mainsnak.get("datavalue", {})
                    if not isinstance(datavalue, dict):
                        continue
                    value = datavalue.get("value", {})
                    if not isinstance(value, dict):
                        continue

                    linked_qid = value.get("id")
                    if isinstance(linked_qid, str):
                        entity_profile_map[linked_qid] = target_profile_uri
                        if isinstance(target_profile_name, str):
                            entity_profile_map[target_profile_name] = target_profile_uri

    return entity_profile_map, primary_entity


def _load_and_evaluate_linked_entities(
    packet: dict[str, Any],
    entity_profile_map: dict[str, str],
    primary_entity: dict[str, Any],
    primary_qid: str,
    mash_client: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Phase 2: Load linked entities, populate data, and evaluate conformance.

    Args:
        packet: Curation packet with metadata
        entity_profile_map: Mapping from entity ID/name to profile URI
        primary_entity: Raw primary entity JSON
        primary_qid: QID of primary entity
        mash_client: WikibaseLoader instance

    Returns:
        Tuple of (data_entities, statement_evaluations)
        - data_entities: list of {id, entity} with raw Wikibase JSON
        - statement_evaluations: list of conformance evaluation records
    """
    data_entities: list[dict[str, Any]] = []
    statement_evaluations: list[dict[str, Any]] = []

    # Add primary entity
    data_entities.append(
        {
            "id": primary_qid,
            "entity": primary_entity,
        }
    )

    profile_name_identifiers: set[str] = set()
    profiles_meta = packet.get("metadata", {}).get("profiles", [])
    if isinstance(profiles_meta, list):
        for profile_meta in profiles_meta:
            if not isinstance(profile_meta, dict):
                continue
            profile_name = profile_meta.get("name_identifier")
            if isinstance(profile_name, str) and profile_name.strip():
                profile_name_identifiers.add(profile_name.strip())

    # Determine which linked entities to load
    linked_qids: set[str] = set()
    for key, profile_uri in entity_profile_map.items():
        if (
            key.startswith("Q")
            and not key.startswith("https://")
            and key != primary_qid
            and key not in profile_name_identifiers
        ):
            linked_qids.add(key)

    # Batch load linked entities
    linked_entities_by_qid: dict[str, dict[str, Any]] = {}
    for linked_qid in linked_qids:
        try:
            entity_data = mash_client.load_entity_data(linked_qid)
            if isinstance(entity_data, dict):
                linked_entities_by_qid[linked_qid] = entity_data
                data_entities.append(
                    {
                        "id": linked_qid,
                        "entity": entity_data,
                    }
                )
        except Exception:
            pass

    # Evaluate conformance: statements only (skip labels/descriptions/aliases)
    profiles_by_uri: dict[str, dict[str, Any]] = {}
    profiles = packet.get("metadata", {}).get("profiles", [])
    for profile_meta in profiles:
        if isinstance(profile_meta, dict):
            profile_uri = profile_meta.get("id")
            if isinstance(profile_uri, str):
                profiles_by_uri[profile_uri] = profile_meta

    # Evaluate primary entity + all loaded linked entities
    all_entities = {primary_qid: primary_entity}
    all_entities.update(linked_entities_by_qid)

    for entity_qid, entity_json in all_entities.items():
        profile_uri = entity_profile_map.get(entity_qid)
        if not isinstance(profile_uri, str):
            continue

        profile_meta = profiles_by_uri.get(profile_uri)
        if not isinstance(profile_meta, dict):
            continue

        profile_statements = profile_meta.get("statements", [])
        if not isinstance(profile_statements, list):
            continue

        statement_by_property, profile_props = _profile_statement_map(profile_meta)

        # Evaluate each claim in entity against profile
        entity_claims = entity_json.get("claims", {})
        for prop_key, claims_list in entity_claims.items():
            if not isinstance(claims_list, list):
                continue

            for claim_idx, claim in enumerate(claims_list):
                if not isinstance(claim, dict):
                    continue

                # Build JSON path for this claim
                json_path = f"$.entity.claims.{prop_key}[{claim_idx}]"

                # Check if this property is in the profile
                is_conformant = prop_key in profile_props

                matching_stmt_uri = statement_by_property.get(prop_key)

                status = "conformant" if is_conformant else "nonconformant"

                evaluation = {
                    "entity_id": entity_qid,
                    "json_path": json_path,
                    "statement_uri": matching_stmt_uri or f"unknown/{prop_key}",
                    "status": status,
                }

                if not is_conformant:
                    evaluation["issues"] = ["statement not in profile"]

                statement_evaluations.append(evaluation)

    return data_entities, statement_evaluations


def charge_packet_from_wikidata_items(
    packet: dict[str, Any],
    qid_map: dict[str, str],
    *,
    mash_client: Optional[Any] = None,
) -> tuple[dict[str, Any], list[ConformanceNotice]]:
    """Charge a curation packet with raw Wikibase entity JSON and conformance evaluation.

    This is the primary charging entry point. It orchestrates two phases:
    1. Resolve linked entity graph from primary entity claims
    2. Load linked entities and populate data section with raw Wikibase JSON

    Raw entity JSON is stored unmodified in data.entities[].entity.
    Conformance evaluation (statement-level alignment vs. profile) is stored separately
    in conformance.statement_evaluations using JSON paths.
    Labels, descriptions, and aliases are passed through without conformance evaluation.

    Args:
        packet: Curation packet assembled by build_curation_packet_from_json_profile()
        qid_map: Mapping from profile entity URI or profile name_identifier to
            Wikidata QID (e.g., {"https://datadistillery.wikibase.cloud/entity/Q4": "Q195562"})
        mash_client: Optional WikibaseLoader; if None, uses default

    Returns:
        Tuple of (charged_packet, notices) with:
        - charged_packet: packet with data.entities populated with raw Wikibase JSON,
                         conformance section with entity_profile_map and statement_evaluations
        - notices: list of ConformanceNotice (integration point for fermenter)
    """
    try:
        from gkc.mash import WikibaseLoader
    except ImportError:
        raise RuntimeError(
            "mash module required for Wikidata charging. "
            "Ensure gkc is installed with full dependencies."
        )

    if mash_client is None:
        mash_client = WikibaseLoader()

    # Determine primary entity QID from qid_map
    primary_profile = packet.get("metadata", {}).get("primary_profile", {})
    primary_profile_uri = primary_profile.get("id")
    primary_profile_name = primary_profile.get("name_identifier")

    primary_qid = None
    if isinstance(primary_profile_uri, str):
        primary_qid = qid_map.get(primary_profile_uri)
    if not primary_qid and isinstance(primary_profile_name, str):
        primary_qid = qid_map.get(primary_profile_name)

    if not primary_qid:
        raise ValueError(
            f"Could not resolve primary entity QID from qid_map. "
            f"Expected key for profile URI or name_identifier: "
            f"{primary_profile_uri}, {primary_profile_name}"
        )

    # Phase 1: Resolve linked entity graph from primary entity
    entity_profile_map, primary_entity = _resolve_linked_entity_graph_from_primary(
        packet, primary_qid, mash_client
    )

    # Phase 2: Load linked entities and evaluate conformance
    data_entities, statement_evaluations = _load_and_evaluate_linked_entities(
        packet, entity_profile_map, primary_entity, primary_qid, mash_client
    )

    # Build charged packet with new structure
    charged = deepcopy(packet)

    # Populate data section with raw Wikibase JSON
    charged["data"] = {"entities": data_entities}

    # Populate conformance section
    conformance = {
        "entity_profile_map": entity_profile_map,
        "statement_evaluations": statement_evaluations,
    }
    charged["conformance"] = conformance

    # For now, return empty notices (will be populated by fermenter integration)
    notices: list[ConformanceNotice] = []

    return charged, notices


def _extract_statement_ids(entity: dict[str, Any]) -> set[str]:
    """Extract statement identifiers from an entity slot.

    Supports both old format (profile_structure.statements with id field)
    and new format (top-level statements with entity field).
    """
    # New format: top-level statements list
    statements = entity.get("statements", [])
    if isinstance(statements, list) and len(statements) > 0:
        new_format_ids = {
            stmt.get("entity")
            for stmt in statements
            if isinstance(stmt, dict) and stmt.get("entity")
        }
        if new_format_ids:  # Only return if we found something
            return new_format_ids

    # Old format: profile_structure.statements
    structure = entity.get("profile_structure", {})
    old_statements = structure.get("statements", [])

    if isinstance(old_statements, list):
        return {
            str(stmt.get("id"))
            for stmt in old_statements
            if isinstance(stmt, dict) and stmt.get("id")
        }
    if isinstance(old_statements, dict):
        return set(old_statements.keys())

    return set()


def _entity_payload_for(
    entity: dict[str, Any],
    source_values: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Resolve source values for an entity using URI-keyed resolution.

    Resolution order:
    1. Exact entity.get("id") (intra-packet UUID) match in source_values
    2. Exact entity.get("profile_entity") (full URI) match in source_values
    3. QID-only fallback: extract QID from profile_entity URI
    4. Fallback to entity.get("profile") (profile-name) for backward compatibility
    """
    # 1. Check intra-packet UUID
    entity_id = entity.get("id")
    if entity_id and entity_id in source_values:
        return source_values[entity_id]

    # 2. Check full profile_entity URI
    profile_entity_uri = entity.get("profile_entity")
    if profile_entity_uri and profile_entity_uri in source_values:
        return source_values[profile_entity_uri]

    # 3. Extract QID and check that
    if profile_entity_uri:
        qid = (
            profile_entity_uri.split("/")[-1]
            if "/" in profile_entity_uri
            else profile_entity_uri
        )
        if qid in source_values:
            return source_values[qid]

    # 4. Backward compatibility: check old profile (name) format
    profile_id = entity.get("profile")
    if profile_id and profile_id in source_values:
        return source_values[profile_id]

    return None


def charge_curation_packet(
    packet: dict[str, Any],
    source_values: dict[str, dict[str, Any]],
    *,
    specificationless: bool = True,
) -> tuple[dict[str, Any], ChargeReport]:
    """Fill packet entities with real source values.

    Args:
        packet: Curation packet generated from profile scaffolds.
        source_values: Mapping keyed by entity ID, profile_entity URI, QID, or profile name.
            Each value is expected to include a ``statements`` mapping and optional metadata
            (labels/descriptions/aliases).
        specificationless: When ``True``, allows unknown statements and records
            warnings instead of blocking charging.

    Returns:
        Tuple of (charged_packet, report).
    """
    charged = deepcopy(packet)
    report = ChargeReport()

    entities = charged.get("entities", [])
    for entity in entities:
        entity_id = str(entity.get("id", ""))
        payload = _entity_payload_for(entity, source_values)
        if not payload:
            report.entities_skipped += 1
            continue

        entity.setdefault("data", {})
        entity_data = entity["data"]
        allowed_statement_ids = _extract_statement_ids(entity)

        payload_statements = payload.get("statements", {})
        if not isinstance(payload_statements, dict):
            report.issues.append(
                ChargeIssue(
                    severity="error",
                    entity_id=entity_id,
                    field="statements",
                    message="Expected 'statements' payload to be a mapping.",
                )
            )
            report.entities_skipped += 1
            continue

        unknown_statement_ids = [
            statement_id
            for statement_id in payload_statements
            if allowed_statement_ids and statement_id not in allowed_statement_ids
        ]

        if unknown_statement_ids and not specificationless:
            report.issues.append(
                ChargeIssue(
                    severity="error",
                    entity_id=entity_id,
                    field="statements",
                    message=(
                        "Unknown statements for profile scaffold: "
                        + ", ".join(sorted(unknown_statement_ids))
                    ),
                )
            )
            report.entities_skipped += 1
            continue

        if unknown_statement_ids and specificationless:
            report.issues.append(
                ChargeIssue(
                    severity="warning",
                    entity_id=entity_id,
                    field="statements",
                    message=(
                        "Specificationless charging accepted unknown statements: "
                        + ", ".join(sorted(unknown_statement_ids))
                    ),
                )
            )

        for key in ("labels", "descriptions", "aliases", "sitelinks"):
            if key in payload:
                entity_data[key] = payload[key]

        entity_data.setdefault("statements", {})
        entity_data["statements"].update(payload_statements)
        report.entities_charged += 1

    return charged, report
