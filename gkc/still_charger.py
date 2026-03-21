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
    """Load root and related profile documents reachable via profile_graph edges."""
    from gkc.spirit_safe import load_profile

    profile_docs: dict[str, dict[str, Any]] = {root_profile_uri: root_profile_doc}
    visited: set[str] = set()

    def _visit(profile_uri: str, profile_doc: dict[str, Any]) -> None:
        if profile_uri in visited:
            return
        visited.add(profile_uri)

        profile_graph = profile_doc.get("metadata", {}).get("profile_graph", [])
        if not isinstance(profile_graph, list):
            return

        for edge in profile_graph:
            if not isinstance(edge, dict):
                continue
            target_uri = _target_profile_uri_from_edge(edge)
            if not target_uri:
                continue
            target_qid = target_uri.split("/")[-1]

            if target_uri not in profile_docs:
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
                _visit(loaded_uri, loaded)
            else:
                _visit(target_uri, profile_docs[target_uri])

    _visit(root_profile_uri, root_profile_doc)
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


def charge_packet_from_wikidata_items(
    packet: dict[str, Any],
    qid_map: dict[str, str],
    *,
    mash_client: Optional[Any] = None,
) -> tuple[dict[str, Any], list[ConformanceNotice]]:
    """Charge a curation packet with data from Wikidata items.

    This is a specialized charging path that populates packet entity slots with
    data extracted from existing Wikidata items. For each entity in the packet,
    retrieves the corresponding Wikidata item via the qid_map, validates claims
    against the profile-defined statements (via io_map resolution), and populates
    entity.data.statements with typed, validated values.

    Args:
        packet: A curation packet assembled by build_curation_packet_from_json_profile()
        qid_map: Mapping from entity slot id or profile_entity URI to Wikidata QID.
                Example: {"ent-q195562": "Q195562"} or {"https://datadistillery.wikibase.cloud/entity/Q4": "Q195562"}
        mash_client: Optional WikibaseApiClient; if None, uses standard Wikidata client

    Returns:
        Tuple of (charged_packet, notices).
        - charged_packet: packet with entity.data.statements populated
        - notices: list of ConformanceNotice for gaps, mismatches, and validation errors
    """
    try:
        from gkc.mash import WikibaseLoader
    except ImportError:
        raise RuntimeError(
            "mash module required for Wikidata charging. "
            "Ensure gkc is installed with full dependencies."
        )

    charged = deepcopy(packet)
    notices = []

    if mash_client is None:
        mash_client = WikibaseLoader()

    entities = charged.get("data", {}).get("entities")
    if not isinstance(entities, list):
        entities = charged.get("entities", [])

    metadata_profiles = charged.get("metadata", {}).get("profiles", [])
    if not isinstance(metadata_profiles, list):
        metadata_profiles = []

    profile_statements_by_key: dict[str, list[dict[str, Any]]] = {}
    for profile_meta in metadata_profiles:
        if not isinstance(profile_meta, dict):
            continue
        statements = profile_meta.get("statements", [])
        if not isinstance(statements, list):
            continue
        profile_id = profile_meta.get("id")
        name_identifier = profile_meta.get("name_identifier")
        if isinstance(profile_id, str) and profile_id:
            profile_statements_by_key[profile_id] = statements
        if isinstance(name_identifier, str) and name_identifier:
            profile_statements_by_key[name_identifier] = statements

    for entity in entities:
        entity_id = entity.get("id")
        profile_entity = entity.get("profile_entity")
        if not isinstance(profile_entity, str) or not profile_entity:
            if isinstance(entity_id, str) and (
                entity_id.startswith("http://") or entity_id.startswith("https://")
            ):
                profile_entity = entity_id

        entity_profile_name = entity.get("profile")

        # Resolve the QID for this entity
        target_qid = (
            qid_map.get(entity_id)
            or qid_map.get(profile_entity)
            or (profile_entity.split("/")[-1] if profile_entity else None)
        )

        if not target_qid:
            notices.append(
                ConformanceNotice(
                    severity="warning",
                    entity_ref=entity_id or profile_entity or "unknown",
                    statement_ref=None,
                    code="entity_qid_unmapped",
                    message="Entity not found in qid_map, skipping Wikidata charging",
                )
            )
            continue

        try:
            # Load the Wikidata item
            wikidata_item_template = mash_client.load_item(target_qid)
            # Convert WikibaseItemTemplate to dictionary (Wikibase JSON format)
            wikidata_item = wikidata_item_template.to_dict()
        except Exception as e:
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=entity_id or profile_entity or "unknown",
                    statement_ref=None,
                    code="wikidata_load_failed",
                    message=f"Failed to load Wikidata item {target_qid}: {e}",
                )
            )
            continue

        # Extract standard fields
        entity.setdefault("data", {})
        entity_data = entity["data"]

        # Get labels, descriptions, aliases
        if "labels" in wikidata_item:
            entity_data["labels"] = wikidata_item["labels"]
        if "descriptions" in wikidata_item:
            entity_data["descriptions"] = wikidata_item["descriptions"]
        if "aliases" in wikidata_item:
            entity_data["aliases"] = wikidata_item["aliases"]

        # Build a mapping from Wikidata property ID to packet statements
        statements = entity.get("statements", [])
        if isinstance(statements, dict):
            if (
                isinstance(profile_entity, str)
                and profile_entity in profile_statements_by_key
            ):
                statements = profile_statements_by_key[profile_entity]
            elif (
                isinstance(entity_profile_name, str)
                and entity_profile_name in profile_statements_by_key
            ):
                statements = profile_statements_by_key[entity_profile_name]
            else:
                statements = []

        if not isinstance(statements, list):
            statements = []

        io_map_by_property_id = {}
        for stmt in statements:
            if isinstance(stmt, dict):
                io_map = stmt.get("io_map", [])
                for mapping in io_map:
                    if isinstance(mapping, dict):
                        to_uri = mapping.get("to", "")
                        prop_id = to_uri.split("/")[-1] if to_uri else None
                        if prop_id:
                            io_map_by_property_id[prop_id] = stmt

        # Extract and validate claims from Wikidata item
        entity_data.setdefault("statements", {})
        wikidata_claims = wikidata_item.get("claims", {})
        processed_props = set()

        for prop_id, claims in wikidata_claims.items():
            processed_props.add(prop_id)

            if prop_id not in io_map_by_property_id:
                # Statement in Wikidata but not in profile
                notices.append(
                    ConformanceNotice(
                        severity="info",
                        entity_ref=entity_id or profile_entity or "unknown",
                        statement_ref=None,
                        code="statement_unrecognized",
                        message=f"Wikidata property {prop_id} not defined in profile",
                    )
                )
                continue

            stmt_def = io_map_by_property_id[prop_id]
            stmt_uri = stmt_def.get("entity")

            # Extract values from claims (simplified: just take the values)
            values = []
            for claim in claims:
                mainsnak = claim.get("mainsnak", {})
                datavalue = mainsnak.get("datavalue", {})
                value = datavalue.get("value")
                if value:
                    values.append(value)

            if values:
                entity_data["statements"][stmt_uri] = values

        # Check for statements in profile but missing in Wikidata
        for stmt in statements:
            if isinstance(stmt, dict):
                io_map = stmt.get("io_map", [])
                for mapping in io_map:
                    if isinstance(mapping, dict):
                        to_uri = mapping.get("to", "")
                        prop_id = to_uri.split("/")[-1] if to_uri else None
                        if prop_id and prop_id not in processed_props:
                            stmt_uri = stmt.get("entity")
                            # Check if this is required (max_count != 0 implies required)
                            required = stmt.get("max_count") != 0
                            severity = "error" if required else "warning"

                            notices.append(
                                ConformanceNotice(
                                    severity=severity,
                                    entity_ref=entity_id or profile_entity or "unknown",
                                    statement_ref=stmt_uri,
                                    code="statement_missing",
                                    message=f"Property {prop_id} not found in Wikidata item",
                                )
                            )

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
