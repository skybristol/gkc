"""Cooperage: Barreling transforms from charged packet to shippable payloads.

This module now hosts reusable transformation logic that prepares charged
curation packets for shipper delivery targets.

Backward-compatible schema/RDF helper re-exports remain available.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

# Re-export functions from their new homes for backward compatibility
from gkc.mash import (
    fetch_entity_rdf,
    fetch_entity_schema_json,
)
from gkc.mash import (
    fetch_entity_schema_specification as fetch_schema_specification,
)
from gkc.utilities import get_entity_uri, validate_entity_reference


# CooperageError is deprecated; mash functions raise RuntimeError instead
class CooperageError(Exception):
    """
    DEPRECATED: Use RuntimeError instead.

    Raised when entity/schema fetch operations fail. This exception is provided
    for backward compatibility but new code should catch RuntimeError instead.

    See: gkc.mash for fetch functions that raise RuntimeError.
    """

    pass


@dataclass
class BarrelIssue:
    severity: str
    entity_id: str
    field: str
    message: str


@dataclass
class BarrelPlanReport:
    operations_created: int = 0
    entities_skipped: int = 0
    issues: list[BarrelIssue] = field(default_factory=list)


def _normalize_mono_map(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for lang, raw in value.items():
        if isinstance(raw, str):
            normalized[lang] = {"language": lang, "value": raw}
        elif isinstance(raw, dict):
            raw_lang = str(raw.get("language") or lang)
            raw_value = raw.get("value")
            if isinstance(raw_value, str):
                normalized[lang] = {"language": raw_lang, "value": raw_value}
    return normalized


def _normalize_aliases(value: Any) -> dict[str, list[dict[str, str]]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[dict[str, str]]] = {}
    for lang, raw in value.items():
        values: list[str] = []
        if isinstance(raw, str):
            values = [raw]
        elif isinstance(raw, list):
            values = [v for v in raw if isinstance(v, str)]
        elif isinstance(raw, dict) and isinstance(raw.get("value"), str):
            values = [raw["value"]]
        if values:
            normalized[lang] = [{"language": lang, "value": v} for v in values]
    return normalized


def _property_id_from_io_map(io_map: Any) -> Optional[str]:
    if not isinstance(io_map, list):
        return None

    for entry in io_map:
        if not isinstance(entry, dict):
            continue
        target = entry.get("to")
        if not isinstance(target, str):
            continue

        value = target.strip().rstrip("/")
        if value.upper().startswith("P") and value[1:].isdigit():
            return value.upper()

        segment = value.split("/")[-1]
        if segment.upper().startswith("P") and segment[1:].isdigit():
            return segment.upper()

    return None


def _statement_pid_map(entity: dict[str, Any]) -> dict[str, str]:
    structure = entity.get("profile_structure", {})
    statements = structure.get("statements", [])
    result: dict[str, str] = {}

    if isinstance(statements, list):
        for stmt in statements:
            if not isinstance(stmt, dict):
                continue
            statement_id = stmt.get("id")
            property_id = _property_id_from_io_map(stmt.get("io_map"))
            if isinstance(statement_id, str) and isinstance(property_id, str):
                result[statement_id] = property_id
    elif isinstance(statements, dict):
        for statement_id, stmt in statements.items():
            if not isinstance(statement_id, str) or not isinstance(stmt, dict):
                continue
            property_id = _property_id_from_io_map(stmt.get("io_map"))
            if isinstance(property_id, str):
                result[statement_id] = property_id

    return result


def _claim_datavalue(value: Any) -> Optional[tuple[str, Any]]:
    if isinstance(value, str) and validate_entity_reference(value):
        entity_id = value.upper()
        entity_type = "item" if entity_id.startswith("Q") else "property"
        return (
            "wikibase-entityid",
            {
                "entity-type": entity_type,
                "id": entity_id,
                "numeric-id": int(entity_id[1:]),
            },
        )

    if isinstance(value, str):
        return ("string", value)

    if isinstance(value, bool):
        return ("boolean", value)

    if isinstance(value, int):
        return ("quantity", {"amount": str(value), "unit": "1"})

    if isinstance(value, float):
        return ("quantity", {"amount": str(value), "unit": "1"})

    if isinstance(value, dict):
        if isinstance(value.get("id"), str) and validate_entity_reference(value["id"]):
            return _claim_datavalue(value["id"])
        if "value" in value:
            return _claim_datavalue(value["value"])

    return None


def _claim_statement(property_id: str, raw_value: Any) -> Optional[dict[str, Any]]:
    datavalue = _claim_datavalue(raw_value)
    if datavalue is None:
        return None
    data_type, data_value = datavalue
    return {
        "mainsnak": {
            "snaktype": "value",
            "property": property_id,
            "datavalue": {
                "type": data_type,
                "value": data_value,
            },
        },
        "type": "statement",
        "rank": "normal",
    }


def _resolve_property_id(
    statement_id: str,
    *,
    per_entity_map: dict[str, str],
    global_map: Optional[dict[str, str]],
) -> Optional[str]:
    if validate_entity_reference(statement_id) and statement_id.upper().startswith("P"):
        return statement_id.upper()

    mapped = per_entity_map.get(statement_id)
    if mapped:
        return mapped

    if global_map:
        global_mapped = global_map.get(statement_id.casefold())
        if global_mapped:
            return global_mapped.upper()

    return None


def barrel_curation_packet_to_wikibase_plan(
    packet: dict[str, Any],
    *,
    property_id_map: Optional[dict[str, str]] = None,
) -> tuple[list[dict[str, Any]], BarrelPlanReport]:
    """Convert charged curation packet content into Wikibase plan operations.

    Output operations are compatible with ``WikibaseShipper.plan_batch``.
    """
    operations: list[dict[str, Any]] = []
    report = BarrelPlanReport()

    for entity in packet.get("entities", []):
        entity_id = str(entity.get("id", ""))
        data = entity.get("data")
        if not isinstance(data, dict) or not data:
            report.entities_skipped += 1
            continue

        labels = _normalize_mono_map(data.get("labels"))
        descriptions = _normalize_mono_map(data.get("descriptions"))
        aliases = _normalize_aliases(data.get("aliases"))

        per_entity_statement_map = _statement_pid_map(entity)
        raw_statements = data.get("statements", {})
        claims: list[dict[str, Any]] = []

        if isinstance(raw_statements, dict):
            for statement_id, values in raw_statements.items():
                property_id = _resolve_property_id(
                    statement_id,
                    per_entity_map=per_entity_statement_map,
                    global_map=property_id_map,
                )
                if not property_id:
                    report.issues.append(
                        BarrelIssue(
                            severity="warning",
                            entity_id=entity_id,
                            field=f"statements.{statement_id}",
                            message="No property ID mapping found; statement skipped.",
                        )
                    )
                    continue

                value_list = values if isinstance(values, list) else [values]
                for value in value_list:
                    statement = _claim_statement(property_id, value)
                    if statement is None:
                        report.issues.append(
                            BarrelIssue(
                                severity="warning",
                                entity_id=entity_id,
                                field=f"statements.{statement_id}",
                                message="Unsupported statement value shape; value skipped.",
                            )
                        )
                        continue
                    claims.append(statement)

        payload: dict[str, Any] = {}
        if labels:
            payload["labels"] = labels
        if descriptions:
            payload["descriptions"] = descriptions
        if aliases:
            payload["aliases"] = aliases
        if claims:
            payload["claims"] = claims

        if not payload:
            report.entities_skipped += 1
            continue

        entity_data_id = data.get("wikibase_id") or data.get("entity_id")
        operation_label = ""
        if isinstance(labels.get("en"), dict):
            operation_label = labels["en"].get("value", "")

        operations.append(
            {
                "kind": "item",
                "label": operation_label,
                "entity_id": (
                    entity_data_id if isinstance(entity_data_id, str) else None
                ),
                "payload": payload,
                "metadata": {
                    "packet_id": packet.get("packet_id"),
                    "packet_entity_id": entity_id,
                    "profile": entity.get("profile"),
                },
            }
        )
        report.operations_created += 1

    return operations, report


# Deprecated function (never used externally; kept for completeness)
def fetch_entity_schema_metadata(
    eid: str, language: str = "en", user_agent=None
) -> dict:
    """
    DEPRECATED: Fetch metadata for a Wikidata EntitySchema.

    This function is no longer actively maintained. For basic entity schema
    retrieval, use fetch_entity_schema_json() instead.

    To be removed in v0.3.0.
    """
    # This function is rarely/never used. If needed, implement via fetch_entity_schema_json
    raise NotImplementedError(
        "fetch_entity_schema_metadata has been removed. "
        "Use fetch_entity_schema_json() and extract metadata directly."
    )


__all__ = [
    # New cooperage payload planning surface
    "BarrelIssue",
    "BarrelPlanReport",
    "barrel_curation_packet_to_wikibase_plan",
    # Re-exported from mash
    "fetch_entity_rdf",
    "fetch_entity_schema_json",
    "fetch_schema_specification",
    # Re-exported from utilities
    "get_entity_uri",
    "validate_entity_reference",
    # Deprecated exception (for backward compat)
    "CooperageError",
]
