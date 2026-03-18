"""Wizard validation bridge built on fermenter primitives.

This module keeps UI code free from datatype-specific validation logic while still
providing real-time and review-time ConformanceNotice rendering.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from gkc.fermenter import (
    ConformanceNotice,
    ValidationResult,
    enforce_fixed_value,
    validate_by_datatype,
    validate_value_from_list,
)


def _validation_result_notices(
    result: ValidationResult,
    *,
    entity_ref: str,
    statement_ref: str,
    code_prefix: str,
) -> list[ConformanceNotice]:
    notices: list[ConformanceNotice] = []

    for error in result.errors:
        notices.append(
            ConformanceNotice(
                severity="error",
                entity_ref=entity_ref,
                statement_ref=statement_ref,
                code=f"{code_prefix}_invalid",
                message=error,
            )
        )

    for warning in result.warnings:
        notices.append(
            ConformanceNotice(
                severity="warning",
                entity_ref=entity_ref,
                statement_ref=statement_ref,
                code=f"{code_prefix}_coerced",
                message=warning,
                normalized_value=result.value,
            )
        )

    return notices


def validate_inline_value(
    *,
    datatype: str,
    value: Any,
    entity_ref: str,
    statement_ref: str,
) -> tuple[Any, list[ConformanceNotice]]:
    """Run lightweight datatype validation for immediate inline feedback."""
    if value in (None, "", {}, []):
        return value, []

    result = validate_by_datatype(datatype, value)
    notices = _validation_result_notices(
        result,
        entity_ref=entity_ref,
        statement_ref=statement_ref,
        code_prefix="datatype",
    )

    if result.valid:
        return result.value, notices
    return value, notices


def _resolve_value_list_path(
    *,
    statement_def: dict[str, Any],
    packet: dict[str, Any],
    source_root: Optional[Path],
) -> Optional[Path]:
    if source_root is None:
        return None

    statement_ref = statement_def.get("entity")
    route = packet.get("value_list_routes", {}).get(statement_ref, {})
    route_cache = route.get("cache_path") if isinstance(route, dict) else None

    value_block = statement_def.get("value", {})
    statement_cache = value_block.get("value_list_reference")

    cache_path = statement_cache or route_cache
    if not isinstance(cache_path, str) or not cache_path:
        return None

    return source_root / cache_path


def validate_entity_packet_data(
    *,
    entity_slot: dict[str, Any],
    packet: dict[str, Any],
    source_root: Optional[Path],
) -> list[ConformanceNotice]:
    """Run full validation pass for one packet entity slot.

    Validation policy for Wizard phase B:
    - malformed datatype/value-list/fixed-value => error
    - missing expected data => warning
    """
    notices: list[ConformanceNotice] = []

    entity_ref = entity_slot.get("id") or entity_slot.get("profile_entity") or "unknown"
    statement_defs = entity_slot.get("statements", [])
    data = entity_slot.get("data", {})
    data_statements = data.get("statements", {}) if isinstance(data, dict) else {}

    for statement_def in statement_defs:
        if not isinstance(statement_def, dict):
            continue

        statement_ref = statement_def.get("entity")
        if not isinstance(statement_ref, str) or not statement_ref:
            continue

        value_block = statement_def.get("value", {})
        datatype = value_block.get("type", "string")
        if datatype == "globe-coordinate":
            datatype = "globe-coordinate"

        configured_values = data_statements.get(statement_ref, [])
        if not isinstance(configured_values, list):
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=entity_ref,
                    statement_ref=statement_ref,
                    code="statement_shape_invalid",
                    message="Statement values must be a list in packet entity data.",
                )
            )
            continue

        if len(configured_values) == 0:
            notices.append(
                ConformanceNotice(
                    severity="warning",
                    entity_ref=entity_ref,
                    statement_ref=statement_ref,
                    code="statement_missing",
                    message="No values entered for this expected statement.",
                )
            )
            continue

        max_count = statement_def.get("max_count")
        if isinstance(max_count, int) and len(configured_values) > max_count:
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=entity_ref,
                    statement_ref=statement_ref,
                    code="max_count_exceeded",
                    message=(
                        f"Statement has {len(configured_values)} values, "
                        f"but max_count is {max_count}."
                    ),
                )
            )

        fixed_flag = bool(statement_def.get("fixed"))
        fixed_value = None
        value_list = value_block.get("value_list")
        if fixed_flag and isinstance(value_list, list) and value_list:
            first = value_list[0]
            if isinstance(first, dict):
                fixed_value = first.get("item") or first.get("id")
            else:
                fixed_value = first

        value_list_path = _resolve_value_list_path(
            statement_def=statement_def,
            packet=packet,
            source_root=source_root,
        )

        qualifier_defs = {
            q.get("entity"): q
            for q in statement_def.get("qualifiers", [])
            if isinstance(q, dict) and isinstance(q.get("entity"), str)
        }

        reference_defs = {
            r.get("entity"): r
            for r in statement_def.get("references", [])
            if isinstance(r, dict) and isinstance(r.get("entity"), str)
        }

        for idx, statement_value in enumerate(configured_values):
            if not isinstance(statement_value, dict):
                notices.append(
                    ConformanceNotice(
                        severity="error",
                        entity_ref=entity_ref,
                        statement_ref=statement_ref,
                        code="statement_entry_invalid",
                        message=f"Value entry {idx + 1} must be an object.",
                    )
                )
                continue

            candidate = statement_value.get("value")

            if fixed_flag and fixed_value is not None:
                fixed_result, fixed_notice = enforce_fixed_value(
                    candidate,
                    fixed_value,
                    statement_ref,
                )
                if fixed_notice is not None:
                    fixed_notice.entity_ref = entity_ref
                    notices.append(fixed_notice)
                if fixed_result.valid:
                    candidate = fixed_result.value
                    statement_value["value"] = fixed_result.value

            datatype_result = validate_by_datatype(datatype, candidate)
            notices.extend(
                _validation_result_notices(
                    datatype_result,
                    entity_ref=entity_ref,
                    statement_ref=statement_ref,
                    code_prefix="datatype",
                )
            )

            if datatype_result.valid:
                statement_value["value"] = datatype_result.value

            if value_list_path is not None and datatype_result.valid:
                list_result = validate_value_from_list(candidate, value_list_path)
                notices.extend(
                    _validation_result_notices(
                        list_result,
                        entity_ref=entity_ref,
                        statement_ref=statement_ref,
                        code_prefix="value_list",
                    )
                )

            qualifiers = statement_value.get("qualifiers", {})
            if not isinstance(qualifiers, dict):
                notices.append(
                    ConformanceNotice(
                        severity="error",
                        entity_ref=entity_ref,
                        statement_ref=statement_ref,
                        code="qualifiers_shape_invalid",
                        message="Qualifiers must be stored as a mapping.",
                    )
                )
                qualifiers = {}

            for qualifier_ref, qualifier_def in qualifier_defs.items():
                q_datatype = qualifier_def.get("value", {}).get("type", "string")
                q_value = qualifiers.get(qualifier_ref)
                if q_value in (None, "", {}, []):
                    notices.append(
                        ConformanceNotice(
                            severity="warning",
                            entity_ref=entity_ref,
                            statement_ref=statement_ref,
                            code="qualifier_missing",
                            message=(
                                "Expected qualifier is missing from this statement value "
                                f"({qualifier_def.get('label', qualifier_ref)})."
                            ),
                        )
                    )
                    continue

                q_result = validate_by_datatype(q_datatype, q_value)
                notices.extend(
                    _validation_result_notices(
                        q_result,
                        entity_ref=entity_ref,
                        statement_ref=str(qualifier_ref),
                        code_prefix="qualifier",
                    )
                )
                if q_result.valid:
                    qualifiers[qualifier_ref] = q_result.value

            references = statement_value.get("references", [])
            if not isinstance(references, list):
                notices.append(
                    ConformanceNotice(
                        severity="error",
                        entity_ref=entity_ref,
                        statement_ref=statement_ref,
                        code="references_shape_invalid",
                        message="References must be stored as a list.",
                    )
                )
                references = []

            present_reference_props = set()
            for ref_entry in references:
                if not isinstance(ref_entry, dict):
                    continue
                ref_prop = ref_entry.get("property")
                ref_value = ref_entry.get("value")
                if not isinstance(ref_prop, str):
                    continue
                present_reference_props.add(ref_prop)

                ref_def = reference_defs.get(ref_prop)
                if not ref_def:
                    notices.append(
                        ConformanceNotice(
                            severity="warning",
                            entity_ref=entity_ref,
                            statement_ref=statement_ref,
                            code="reference_unexpected",
                            message=f"Reference {ref_prop} is not defined in profile statement.",
                        )
                    )
                    continue

                r_datatype = ref_def.get("value", {}).get("type", "string")
                if ref_value in (None, "", {}, []):
                    notices.append(
                        ConformanceNotice(
                            severity="warning",
                            entity_ref=entity_ref,
                            statement_ref=ref_prop,
                            code="reference_missing_value",
                            message="Reference entry exists but has no value.",
                        )
                    )
                    continue

                r_result = validate_by_datatype(r_datatype, ref_value)
                notices.extend(
                    _validation_result_notices(
                        r_result,
                        entity_ref=entity_ref,
                        statement_ref=str(ref_prop),
                        code_prefix="reference",
                    )
                )
                if r_result.valid:
                    ref_entry["value"] = r_result.value

            for ref_prop, ref_def in reference_defs.items():
                if ref_prop not in present_reference_props:
                    notices.append(
                        ConformanceNotice(
                            severity="warning",
                            entity_ref=entity_ref,
                            statement_ref=statement_ref,
                            code="reference_missing",
                            message=(
                                "Expected reference not provided "
                                f"({ref_def.get('label', ref_prop)})."
                            ),
                        )
                    )

    return notices
