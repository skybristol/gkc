"""Wikibase orchestration pipelines for profile-driven write planning."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from gkc.cooperage import BarrelPlanReport, barrel_curation_packet_to_wikibase_plan
from gkc.shipper import WriteResult
from gkc.spirit_safe import Manifest, create_curation_packet
from gkc.still_charger import (
    ChargeReport,
    build_curation_packet_from_json_profile,
    charge_curation_packet,
)


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
