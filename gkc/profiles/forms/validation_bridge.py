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


def _merge_wikibase_item_metadata(original: Any, normalized: Any) -> Any:
    """Preserve wizard-selected URI/label metadata after datatype normalization."""
    if not isinstance(normalized, dict):
        return normalized

    merged = dict(normalized)
    if isinstance(original, dict):
        item_uri = original.get("item")
        item_label = original.get("itemLabel")
        if isinstance(item_uri, str) and item_uri:
            merged["item"] = item_uri
        if isinstance(item_label, str) and item_label:
            merged["itemLabel"] = item_label
    elif isinstance(original, str) and original.startswith(("http://", "https://")):
        merged["item"] = original
    return merged


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
        normalized = result.value
        if datatype in {"item", "wikibase-item"}:
            normalized = _merge_wikibase_item_metadata(value, normalized)
        return normalized, notices
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


def _empty_nested_statement_entry(value: Any = None) -> dict[str, Any]:
    return {
        "value": value,
        "qualifiers": {},
        "references": {},
    }


def _normalize_nested_statement_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return _empty_nested_statement_entry(entry)

    if not any(key in entry for key in ("value", "qualifiers", "references")):
        return _empty_nested_statement_entry(entry)

    normalized = {
        "value": entry.get("value"),
        "qualifiers": entry.get("qualifiers", {}),
        "references": entry.get("references", {}),
    }
    if not isinstance(normalized["qualifiers"], dict):
        normalized["qualifiers"] = {}
    if not isinstance(normalized["references"], dict):
        normalized["references"] = {}
    return normalized


def _normalize_nested_statement_map(raw: Any) -> dict[str, list[dict[str, Any]]]:
    """Normalize nested qualifier/reference packet data to URI-keyed lists."""
    normalized: dict[str, list[dict[str, Any]]] = {}

    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            statement_ref = entry.get("property") or entry.get("statement")
            if not isinstance(statement_ref, str) or not statement_ref:
                continue
            normalized.setdefault(statement_ref, []).append(
                _normalize_nested_statement_entry({"value": entry.get("value")})
            )
        return normalized

    if not isinstance(raw, dict):
        return normalized

    for statement_ref, payload in raw.items():
        if not isinstance(statement_ref, str) or not statement_ref:
            continue
        if isinstance(payload, list):
            entries = [_normalize_nested_statement_entry(entry) for entry in payload]
        else:
            entries = [_normalize_nested_statement_entry(payload)]
        normalized[statement_ref] = entries

    return normalized


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
                normalized_value = datatype_result.value
                if datatype in {"item", "wikibase-item"}:
                    normalized_value = _merge_wikibase_item_metadata(
                        candidate,
                        normalized_value,
                    )
                statement_value["value"] = normalized_value

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

            raw_qualifiers = statement_value.get("qualifiers", {})
            qualifiers = _normalize_nested_statement_map(raw_qualifiers)
            statement_value["qualifiers"] = qualifiers
            if raw_qualifiers not in ({}, None) and not qualifiers:
                notices.append(
                    ConformanceNotice(
                        severity="error",
                        entity_ref=entity_ref,
                        statement_ref=statement_ref,
                        code="qualifiers_shape_invalid",
                        message="Qualifiers must be stored as a URI-keyed mapping.",
                    )
                )

            for qualifier_ref, qualifier_def in qualifier_defs.items():
                q_datatype = qualifier_def.get("value", {}).get("type", "string")
                q_entries = qualifiers.get(qualifier_ref, [])
                if not q_entries:
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

                q_max_count = qualifier_def.get("max_count")
                if isinstance(q_max_count, int) and len(q_entries) > q_max_count:
                    notices.append(
                        ConformanceNotice(
                            severity="error",
                            entity_ref=entity_ref,
                            statement_ref=qualifier_ref,
                            code="qualifier_max_count_exceeded",
                            message=(
                                f"Qualifier has {len(q_entries)} values, "
                                f"but max_count is {q_max_count}."
                            ),
                        )
                    )

                normalized_entries: list[dict[str, Any]] = []
                for q_index, q_entry in enumerate(q_entries):
                    q_entry_normalized = _normalize_nested_statement_entry(q_entry)
                    normalized_entries.append(q_entry_normalized)
                    q_value = q_entry_normalized.get("value")

                    if q_value in (None, "", {}, []):
                        notices.append(
                            ConformanceNotice(
                                severity="warning",
                                entity_ref=entity_ref,
                                statement_ref=qualifier_ref,
                                code="qualifier_missing_value",
                                message=(
                                    "Qualifier entry exists but has no value "
                                    f"({qualifier_def.get('label', qualifier_ref)}) "
                                    f"at position {q_index + 1}."
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
                        normalized_qualifier = q_result.value
                        if q_datatype in {"item", "wikibase-item"}:
                            normalized_qualifier = _merge_wikibase_item_metadata(
                                q_value,
                                normalized_qualifier,
                            )
                        q_entry_normalized["value"] = normalized_qualifier

                qualifiers[qualifier_ref] = normalized_entries

            for qualifier_ref in qualifiers.keys():
                if qualifier_ref not in qualifier_defs:
                    notices.append(
                        ConformanceNotice(
                            severity="warning",
                            entity_ref=entity_ref,
                            statement_ref=qualifier_ref,
                            code="qualifier_unexpected",
                            message=f"Qualifier {qualifier_ref} is not defined in profile statement.",
                        )
                    )

            raw_references = statement_value.get("references", {})
            references = _normalize_nested_statement_map(raw_references)
            statement_value["references"] = references
            if raw_references not in ({}, None, []) and not references:
                notices.append(
                    ConformanceNotice(
                        severity="error",
                        entity_ref=entity_ref,
                        statement_ref=statement_ref,
                        code="references_shape_invalid",
                        message="References must be stored as a URI-keyed mapping.",
                    )
                )

            present_reference_props = set(references.keys())
            for ref_prop, ref_entries in references.items():
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
                r_max_count = ref_def.get("max_count")
                if isinstance(r_max_count, int) and len(ref_entries) > r_max_count:
                    notices.append(
                        ConformanceNotice(
                            severity="error",
                            entity_ref=entity_ref,
                            statement_ref=ref_prop,
                            code="reference_max_count_exceeded",
                            message=(
                                f"Reference has {len(ref_entries)} values, "
                                f"but max_count is {r_max_count}."
                            ),
                        )
                    )

                normalized_entries: list[dict[str, Any]] = []
                for ref_index, ref_entry in enumerate(ref_entries):
                    ref_entry_normalized = _normalize_nested_statement_entry(ref_entry)
                    normalized_entries.append(ref_entry_normalized)
                    ref_value = ref_entry_normalized.get("value")
                    if ref_value in (None, "", {}, []):
                        notices.append(
                            ConformanceNotice(
                                severity="warning",
                                entity_ref=entity_ref,
                                statement_ref=ref_prop,
                                code="reference_missing_value",
                                message=(
                                    "Reference entry exists but has no value "
                                    f"at position {ref_index + 1}."
                                ),
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
                        normalized_reference = r_result.value
                        if r_datatype in {"item", "wikibase-item"}:
                            normalized_reference = _merge_wikibase_item_metadata(
                                ref_value,
                                normalized_reference,
                            )
                        ref_entry_normalized["value"] = normalized_reference

                references[ref_prop] = normalized_entries

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
