"""Wikibase orchestration pipelines for profile-driven write planning."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from gkc.shipper import WriteResult
from gkc.spirit_safe import Manifest, create_curation_packet
from gkc.still_charger import (
    ChargeReport,
    build_curation_packet_from_json_profile,
    charge_curation_packet,
)
from gkc.utilities import validate_entity_reference


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
    """Extract a mapping from statement identifiers to Wikidata property IDs.

    Supports both:
    - New format: top-level statements with entity field (statement URI)
    - Old format: profile_structure.statements with id field
    """
    result: dict[str, str] = {}

    statements = entity.get("statements", [])
    if isinstance(statements, list):
        for stmt in statements:
            if not isinstance(stmt, dict):
                continue
            statement_uri = stmt.get("entity")
            property_id = _property_id_from_io_map(stmt.get("io_map"))
            if isinstance(statement_uri, str) and isinstance(property_id, str):
                result[statement_uri] = property_id
        if result:
            return result

    structure = entity.get("profile_structure", {})
    old_statements = structure.get("statements", [])

    if isinstance(old_statements, list):
        for stmt in old_statements:
            if not isinstance(stmt, dict):
                continue
            statement_id = stmt.get("id")
            property_id = _property_id_from_io_map(stmt.get("io_map"))
            if isinstance(statement_id, str) and isinstance(property_id, str):
                result[statement_id] = property_id
    elif isinstance(old_statements, dict):
        for statement_id, stmt in old_statements.items():
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
                    "profile_entity": entity.get("profile_entity"),
                    "profile": entity.get("profile"),
                },
            }
        )
        report.operations_created += 1

    return operations, report


@dataclass
class WikibaseWritePlanResult:
    """Result container for the packet -> charge -> barrel -> plan pipeline."""

    packet: dict[str, Any]
    charged_packet: dict[str, Any]
    charge_report: ChargeReport
    operations: list[dict[str, Any]]
    barrel_report: BarrelPlanReport
    diff_plan: Optional[Any] = None


@dataclass
class WikibaseWriteExecutionResult:
    """Result container for plan replay through shipper write operations."""

    plan: WikibaseWritePlanResult
    write_results: list[WriteResult]
    write_summary: dict[str, int]


def build_wikibase_write_plan(
    profile_id: Optional[str] = None,
    source_values: Optional[dict[str, dict[str, Any]]] = None,
    *,
    profile_entity: Optional[str] = None,
    json_profile_doc: Optional[dict] = None,
    source_root: Optional[Path] = None,
    operation_mode: str = "single",
    load_wikidata_qids: bool = False,
    depth: int = 1,
    manifest: Optional[Manifest] = None,
    specificationless: bool = True,
    property_id_map: Optional[dict[str, str]] = None,
    shipper: Optional[Any] = None,
    language: str = "en",
) -> WikibaseWritePlanResult:
    """Build a Wikibase write plan from profile and source values.

    Pipeline:
    1) Create curation packet from profile scaffolds (old or new method)
    2) Charge packet with concrete values
    3) Barrel charged packet into shipper-compatible operations
    4) Optionally compute diff plan using WikibaseShipper.plan_batch

    Args:
        profile_id: (deprecated) Profile name string for old create_curation_packet path
        source_values: Source values mapping for charging
        profile_entity: Full profile entity URI for new path
        json_profile_doc: Pre-loaded JSON profile document for new path
        source_root: Optional path root for value list cache hydration
        operation_mode: Mode for packet assembly
        manifest: Old manifest (for transitional create_curation_packet)
        Other args: same as before
    """

    if source_values is None:
        source_values = {}

    # New path: build packet from JSON profile
    if json_profile_doc is not None and profile_entity is not None:
        packet = build_curation_packet_from_json_profile(
            profile_entity=profile_entity,
            json_profile_doc=json_profile_doc,
            source_root=source_root,
        )
    # Old path: build packet from profile_id + manifest (transitional)
    elif profile_id is not None:
        packet = create_curation_packet(
            profile_id=profile_id,
            operation_mode=operation_mode,
            load_wikidata_qids=load_wikidata_qids,
            depth=depth,
            manifest=manifest,
        )
    else:
        raise ValueError(
            "Either (profile_entity + json_profile_doc) or profile_id must be provided"
        )

    charged_packet, charge_report = charge_curation_packet(
        packet,
        source_values,
        specificationless=specificationless,
    )

    operations, barrel_report = barrel_curation_packet_to_wikibase_plan(
        charged_packet,
        property_id_map=property_id_map,
    )

    diff_plan = None
    if shipper is not None and operations:
        diff_plan = shipper.plan_batch(operations, language=language)

    return WikibaseWritePlanResult(
        packet=packet,
        charged_packet=charged_packet,
        charge_report=charge_report,
        operations=operations,
        barrel_report=barrel_report,
        diff_plan=diff_plan,
    )


def execute_wikibase_write_plan(
    profile_id: str,
    source_values: dict[str, dict[str, Any]],
    *,
    shipper: Any,
    operation_mode: str = "single",
    load_wikidata_qids: bool = False,
    depth: int = 1,
    manifest: Optional[Manifest] = None,
    specificationless: bool = True,
    property_id_map: Optional[dict[str, str]] = None,
    language: str = "en",
    write_summary: str = "gkc wikibase execute-write",
    dry_run: bool = True,
    bot: bool = False,
) -> WikibaseWriteExecutionResult:
    """Build a plan and replay its operations through shipper writes.

    Pipeline:
    1) Build plan from profile/source values
    2) Replay each operation through shipper.write_item/write_property
    3) Return operation-level results and status summary
    """

    plan = build_wikibase_write_plan(
        profile_id=profile_id,
        source_values=source_values,
        operation_mode=operation_mode,
        load_wikidata_qids=load_wikidata_qids,
        depth=depth,
        manifest=manifest,
        specificationless=specificationless,
        property_id_map=property_id_map,
        shipper=shipper,
        language=language,
    )

    write_results: list[WriteResult] = []
    for operation in plan.operations:
        kind = str(operation.get("kind") or "").strip().lower()
        payload = operation.get("payload")
        if not isinstance(payload, dict):
            payload = {}

        operation_entity_id = operation.get("entity_id")
        entity_id = (
            operation_entity_id if isinstance(operation_entity_id, str) else None
        )

        metadata = operation.get("metadata")
        normalized_metadata = metadata if isinstance(metadata, dict) else {}

        op_label = str(operation.get("label") or "").strip()
        op_summary = write_summary
        if op_label:
            op_summary = f"{write_summary}: {op_label}"

        if kind == "item":
            result = shipper.write_item(
                payload=payload,
                summary=op_summary,
                entity_id=entity_id,
                dry_run=dry_run,
                bot=bot,
                metadata=normalized_metadata,
            )
            write_results.append(result)
            continue

        if kind == "property":
            datatype_value = operation.get("datatype")
            datatype = datatype_value if isinstance(datatype_value, str) else ""
            if not entity_id and not datatype:
                write_results.append(
                    WriteResult(
                        entity_id=None,
                        revision_id=None,
                        status="blocked",
                        warnings=[
                            "Property operation missing datatype for property creation"
                        ],
                        api_response={},
                        request_payload=payload,
                        metadata=normalized_metadata,
                    )
                )
                continue

            result = shipper.write_property(
                payload=payload,
                summary=op_summary,
                datatype=datatype,
                entity_id=entity_id,
                dry_run=dry_run,
                bot=bot,
                metadata=normalized_metadata,
            )
            write_results.append(result)
            continue

        write_results.append(
            WriteResult(
                entity_id=entity_id,
                revision_id=None,
                status="blocked",
                warnings=[f"Unsupported operation kind: {kind or 'unknown'}"],
                api_response={},
                request_payload=payload,
                metadata=normalized_metadata,
            )
        )

    summary = {
        "total": len(write_results),
        "submitted": sum(1 for result in write_results if result.status == "submitted"),
        "dry_run": sum(1 for result in write_results if result.status == "dry_run"),
        "validated": sum(1 for result in write_results if result.status == "validated"),
        "blocked": sum(1 for result in write_results if result.status == "blocked"),
        "error": sum(1 for result in write_results if result.status == "error"),
    }

    return WikibaseWriteExecutionResult(
        plan=plan,
        write_results=write_results,
        write_summary=summary,
    )
