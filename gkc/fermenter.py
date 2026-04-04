"""
Fermenter: Validation and coercion layer for GKC curation pipelines.

The fermenter is the atomic validation and coercion layer. It does not assemble packets
or coordinate pipelines — it validates and normalizes individual values against
profile-defined constraints. Both the still charger and the write-planning layer consume it.

All validation surfaces return a shared ConformanceNotice envelope for consistent error
reporting across wizard, CLI, and bulk pipelines.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from gkc.mash import (
    WikibaseApiClient,
    fetch_commons_file_info,
    fetch_url_resource,
)
from gkc.wikibase import (
    build_meta_wikibase_semantic_anchor_contract,
    canonicalize_wikibase_datatype,
    get_wikibase_datatype_spec,
    is_wikibase_item_datatype,
)


@dataclass
class ValidationResult:
    """Internal validation result type used within the fermenter.

    Before wrapping into ConformanceNotice, fermenter functions use this to track
    validation state, normalized values, and detailed error/warning lists.
    """

    valid: bool
    value: Any
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    uncertainty: float = 0.0
    uncertainty_reasons: list[str] = field(default_factory=list)


@dataclass
class ConformanceNotice:
    """Shared result envelope for validation and coercion operations.

    Replaces split ChargeIssue/BarrelIssue types for consistent reporting across
    wizard, CLI, and bulk pipelines.

    Attributes:
        severity: "error", "warning", or "info"
        entity_ref: Full URI or intra-packet entity ID
        statement_ref: Statement entity URI or None (for entity-level notices)
        code: Short machine-readable code (e.g., "fixed_value_violation")
        message: Human-readable message
        normalized_value: The coerced output, if coercion succeeded
    """

    severity: str
    entity_ref: str
    code: str
    message: str
    statement_ref: Optional[str] = None
    normalized_value: Any = None


# Backward compatibility aliases for transition period
ChargeIssue = ConformanceNotice
BarrelIssue = ConformanceNotice


class ValidationPolicy(str, Enum):
    """Validation depth policy for structure and online checks."""

    STRUCTURE = "structure"
    HEARTBEAT = "heartbeat"
    ACTIONABLE = "actionable"


@dataclass
class ValidationPolicyConfig:
    """Configurable transport and endpoint options for validation policies."""

    policy: ValidationPolicy = ValidationPolicy.STRUCTURE
    wikibase_api_url: str = "https://www.wikidata.org/w/api.php"
    commons_api_url: str = "https://commons.wikimedia.org/w/api.php"
    timeout_seconds: int = 10
    allow_redirects: bool = True
    request_accept: Optional[str] = None


@dataclass
class SemanticAnchorValidationResult:
    """Validation outcome for a semantic-anchor artifact."""

    valid: bool
    required_anchor_count: int
    matched_anchor_count: int
    evaluated_anchor_count: int
    notices: list[ConformanceNotice] = field(default_factory=list)
    freshness_checked: bool = False
    freshness_match: Optional[bool] = None


def _resolve_validation_policy_config(
    validation_policy: ValidationPolicy,
    policy_config: Optional[ValidationPolicyConfig],
) -> ValidationPolicyConfig:
    if policy_config is None:
        return ValidationPolicyConfig(policy=validation_policy)
    return ValidationPolicyConfig(
        policy=validation_policy,
        wikibase_api_url=policy_config.wikibase_api_url,
        commons_api_url=policy_config.commons_api_url,
        timeout_seconds=policy_config.timeout_seconds,
        allow_redirects=policy_config.allow_redirects,
        request_accept=policy_config.request_accept,
    )


_DOMAIN_LIKE_PATTERN = re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(:\d+)?(/.*)?$")
_WIKIBASE_DEFAULT_CALENDAR_MODEL = "http://www.wikidata.org/entity/Q1985727"
_WIKIBASE_DEFAULT_GLOBE = "http://www.wikidata.org/entity/Q2"
_TIME_COMPONENT_PATTERN = re.compile(
    r"^(?P<sign>[+-])?(?P<year>\d{1,16})(?:[-/](?P<month>\d{1,2})(?:[-/](?P<day>\d{1,2})(?:[T ](?P<hour>\d{1,2})(?::(?P<minute>\d{1,2})(?::(?P<second>\d{1,2}))?)?(?:Z)?)?)?)?$"
)
_COORD_DECIMAL_HEMISPHERE_PATTERN = re.compile(
    r"^\s*([+-]?\d+(?:\.\d+)?)\s*([NSEW])?\s*$",
    flags=re.IGNORECASE,
)
_COORD_DMS_PATTERN = re.compile(
    r"^\s*(?P<deg>[+-]?\d+(?:\.\d+)?)\D+(?P<min>\d+(?:\.\d+)?)?(?:\D+(?P<sec>\d+(?:\.\d+)?))?\D*(?P<hem>[NSEW])?\s*$",
    flags=re.IGNORECASE,
)
_INTERNAL_NAME_IDENTIFIER_BODY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


def validate_semantic_anchor_document(
    anchor_document: dict[str, Any],
    *,
    internal_name_identifier_prefix: str | None = None,
    current_anchor_document: dict[str, Any] | None = None,
) -> SemanticAnchorValidationResult:
    """Validate a semantic-anchor document against the package-owned init contract."""

    contract = build_meta_wikibase_semantic_anchor_contract(
        internal_name_identifier_prefix=internal_name_identifier_prefix
    )
    notices: list[ConformanceNotice] = []
    required_anchor_count = len(contract.requirements)

    if not isinstance(anchor_document, dict):
        notices.append(
            ConformanceNotice(
                severity="error",
                entity_ref="semantic_anchors",
                code="artifact_shape_invalid",
                message="Semantic anchor document must be a JSON object",
            )
        )
        return SemanticAnchorValidationResult(
            valid=False,
            required_anchor_count=required_anchor_count,
            matched_anchor_count=0,
            evaluated_anchor_count=0,
            notices=notices,
            freshness_checked=current_anchor_document is not None,
            freshness_match=None,
        )

    metadata = anchor_document.get("metadata")
    entities = anchor_document.get("entities")

    if not isinstance(metadata, dict):
        notices.append(
            ConformanceNotice(
                severity="error",
                entity_ref="semantic_anchors",
                code="artifact_shape_invalid",
                message="Semantic anchor document is missing metadata",
            )
        )

    if not isinstance(entities, dict):
        notices.append(
            ConformanceNotice(
                severity="error",
                entity_ref="semantic_anchors",
                code="artifact_shape_invalid",
                message="Semantic anchor document is missing entities",
            )
        )
        return SemanticAnchorValidationResult(
            valid=False,
            required_anchor_count=required_anchor_count,
            matched_anchor_count=0,
            evaluated_anchor_count=0,
            notices=notices,
            freshness_checked=current_anchor_document is not None,
            freshness_match=None,
        )

    evaluated_anchor_count = len(entities)
    matched_anchor_count = 0
    active_prefix = contract.internal_name_identifier_prefix

    for anchor_name, payload in entities.items():
        if not isinstance(anchor_name, str) or not anchor_name:
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref="semantic_anchors",
                    code="anchor_identifier_invalid",
                    message="Semantic anchor keys must be non-empty strings",
                )
            )
            continue

        if not anchor_name.startswith(active_prefix):
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_identifier_invalid",
                    message=(
                        f"Internal name identifier '{anchor_name}' must start with "
                        f"configured prefix '{active_prefix}'"
                    ),
                )
            )
            continue

        remainder = anchor_name[len(active_prefix) :]
        if not remainder or not _INTERNAL_NAME_IDENTIFIER_BODY_PATTERN.fullmatch(
            remainder
        ):
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_identifier_invalid",
                    message=(
                        f"Internal name identifier '{anchor_name}' has an invalid "
                        "body after the configured prefix"
                    ),
                )
            )

        if not isinstance(payload, dict):
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_shape_invalid",
                    message="Semantic anchor entries must be JSON objects",
                )
            )

    for anchor_name, requirement in contract.requirements.items():
        payload = entities.get(anchor_name)
        if not isinstance(payload, dict):
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_missing",
                    message=f"Required semantic anchor '{anchor_name}' is missing",
                )
            )
            continue

        matched_anchor_count += 1
        anchor_id = payload.get("id")
        if not isinstance(anchor_id, str) or not anchor_id:
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_id_missing",
                    message=f"Semantic anchor '{anchor_name}' is missing its id",
                )
            )
            continue

        expected_prefix = "P" if requirement.kind == "property" else "Q"
        if not (
            anchor_id.startswith(expected_prefix) and anchor_id[1:].isdigit()
        ):
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_kind_mismatch",
                    message=(
                        f"Semantic anchor '{anchor_name}' must resolve to a "
                        f"{requirement.kind} id"
                    ),
                    normalized_value={"id": anchor_id, "expected_kind": requirement.kind},
                )
            )

        if requirement.kind != "property":
            continue

        datatype = payload.get("datatype")
        if not isinstance(datatype, str) or not datatype.strip():
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_datatype_missing",
                    message=f"Property anchor '{anchor_name}' is missing datatype",
                )
            )
            continue

        try:
            normalized_datatype = canonicalize_wikibase_datatype(datatype, strict=True)
        except KeyError:
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_datatype_invalid",
                    message=(
                        f"Property anchor '{anchor_name}' uses unknown datatype "
                        f"'{datatype}'"
                    ),
                )
            )
            continue

        if normalized_datatype != requirement.datatype:
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=anchor_name,
                    code="anchor_datatype_mismatch",
                    message=(
                        f"Property anchor '{anchor_name}' must use datatype "
                        f"'{requirement.datatype}', found '{normalized_datatype}'"
                    ),
                    normalized_value={
                        "expected": requirement.datatype,
                        "actual": normalized_datatype,
                    },
                )
            )

    extra_anchors = sorted(set(entities) - set(contract.requirements))
    if extra_anchors:
        notices.append(
            ConformanceNotice(
                severity="info",
                entity_ref="semantic_anchors",
                code="anchor_extra",
                message=(
                    f"Semantic anchor artifact contains {len(extra_anchors)} "
                    "non-required internal anchors"
                ),
                normalized_value=extra_anchors,
            )
        )

    freshness_checked = current_anchor_document is not None
    freshness_match: Optional[bool] = None
    if current_anchor_document is not None:
        current_entities = current_anchor_document.get("entities")
        if not isinstance(current_entities, dict):
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref="semantic_anchors",
                    code="freshness_source_invalid",
                    message="Current semantic anchor comparison source is missing entities",
                )
            )
            freshness_match = None
        else:
            freshness_match = entities == current_entities
            if freshness_match:
                notices.append(
                    ConformanceNotice(
                        severity="info",
                        entity_ref="semantic_anchors",
                        code="artifact_current",
                        message="Semantic anchor artifact matches the current cache-derived document",
                    )
                )
            else:
                missing_in_artifact = sorted(set(current_entities) - set(entities))
                extra_in_artifact = sorted(set(entities) - set(current_entities))
                changed_entries = sorted(
                    key
                    for key in (set(entities) & set(current_entities))
                    if entities[key] != current_entities[key]
                )
                notices.append(
                    ConformanceNotice(
                        severity="error",
                        entity_ref="semantic_anchors",
                        code="artifact_stale",
                        message=(
                            "Semantic anchor artifact does not match the current "
                            "cache-derived document"
                        ),
                        normalized_value={
                            "missing_in_artifact": missing_in_artifact,
                            "extra_in_artifact": extra_in_artifact,
                            "changed_entries": changed_entries,
                        },
                    )
                )

    valid = not any(notice.severity == "error" for notice in notices)
    return SemanticAnchorValidationResult(
        valid=valid,
        required_anchor_count=required_anchor_count,
        matched_anchor_count=matched_anchor_count,
        evaluated_anchor_count=evaluated_anchor_count,
        notices=notices,
        freshness_checked=freshness_checked,
        freshness_match=freshness_match,
    )


def _coerce_wikibase_item_reference(
    value: Any,
) -> tuple[Optional[str], list[str], list[str]]:
    """Coerce common item reference formats to a canonical QID."""
    warnings: list[str] = []
    uncertainty_reasons: list[str] = []

    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None, warnings, ["Empty item reference string"]

        if candidate.startswith(("http://", "https://")):
            qid_candidate = candidate.rstrip("/").split("/")[-1]
            if qid_candidate.upper().startswith("Q") and qid_candidate[1:].isdigit():
                qid = qid_candidate.upper()
                warnings.append("Coerced item URI to QID")
                uncertainty_reasons.append("item_uri_input")
                return qid, warnings, uncertainty_reasons

        normalized = candidate.upper()
        if normalized.startswith("Q") and normalized[1:].isdigit():
            if normalized != candidate:
                warnings.append("Normalized lowercase qid to uppercase")
                uncertainty_reasons.append("qid_case_normalized")
            return normalized, warnings, uncertainty_reasons

        return (
            None,
            warnings,
            [f"Invalid QID format: {value}. Expected Q-prefixed numeric ID."],
        )

    if isinstance(value, dict):
        for key in ("id", "item"):
            ref = value.get(key)
            if isinstance(ref, str):
                qid, child_warnings, child_uncertainty = (
                    _coerce_wikibase_item_reference(ref)
                )
                if qid:
                    warnings.extend(child_warnings)
                    uncertainty_reasons.extend(child_uncertainty)
                    if key != "id" or child_warnings or child_uncertainty:
                        warnings.append(
                            f"Coerced wikibase-item from dict field '{key}'"
                        )
                        uncertainty_reasons.append("dict_item_reference")
                    return qid, warnings, uncertainty_reasons

    return (
        None,
        warnings,
        [
            f"wikibase-item must be a string/URI or dict with id/item, got {type(value).__name__}"
        ],
    )


def _coerce_url_candidate(value: Any) -> tuple[Optional[str], list[str], list[str]]:
    """Coerce flexible URL-like inputs into explicit HTTP(S) URLs."""
    warnings: list[str] = []
    uncertainty_reasons: list[str] = []

    if value is None:
        return None, warnings, ["url value cannot be null"]

    if not isinstance(value, str):
        original_type = type(value).__name__
        try:
            value = str(value)
            warnings.append(f"Coerced {original_type} to string")
            uncertainty_reasons.append("non_string_url_input")
        except Exception as exc:
            return None, warnings, [f"url must be coercible to string: {exc}"]

    candidate = value.strip()
    if not candidate:
        return None, warnings, ["url value cannot be empty"]

    if candidate.startswith("www."):
        candidate = f"https://{candidate}"
        warnings.append("Added https:// scheme to URL beginning with www.")
        uncertainty_reasons.append("scheme_added_from_www")
    elif _DOMAIN_LIKE_PATTERN.match(candidate):
        candidate = f"https://{candidate}"
        warnings.append("Added https:// scheme to bare domain URL")
        uncertainty_reasons.append("scheme_added_from_domain")

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, warnings, ["url must include a valid http(s) scheme and host"]

    return candidate, warnings, uncertainty_reasons


def _uncertainty_score(reasons: list[str]) -> float:
    if not reasons:
        return 0.0
    return min(1.0, 0.2 + (0.15 * len(set(reasons))))


def _count_decimal_places(value: str) -> int:
    candidate = value.strip()
    if not candidate or "." not in candidate:
        return 0
    fractional = candidate.split(".", 1)[1]
    digits = "".join(ch for ch in fractional if ch.isdigit())
    return len(digits)


def _format_wikibase_time(
    *,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
) -> str:
    sign = "+" if year >= 0 else "-"
    year_abs = str(abs(year)).rjust(4, "0")
    return (
        f"{sign}{year_abs}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"
    )


def _coerce_time_value(
    value: Any,
) -> tuple[Optional[dict[str, Any]], list[str], list[str]]:
    """Coerce common user time inputs into full Wikibase time payloads."""
    warnings: list[str] = []
    uncertainty_reasons: list[str] = []

    if value is None:
        return None, warnings, ["time value cannot be null"]

    timezone = 0
    before = 0
    after = 0
    calendarmodel = _WIKIBASE_DEFAULT_CALENDAR_MODEL

    if isinstance(value, dict) and "time" in value:
        raw_time = value.get("time")
        if not isinstance(raw_time, str) or not raw_time.strip():
            return None, warnings, ["time dict field 'time' must be a non-empty string"]
        candidate = raw_time.strip()
        timezone = int(value.get("timezone", 0) or 0)
        before = int(value.get("before", 0) or 0)
        after = int(value.get("after", 0) or 0)
        calendarmodel = value.get("calendarmodel") or _WIKIBASE_DEFAULT_CALENDAR_MODEL
        if any(
            k not in value for k in ("timezone", "before", "after", "calendarmodel")
        ):
            warnings.append("Filled missing Wikibase time fields with defaults")
            uncertainty_reasons.append("time_defaults_filled")
    elif isinstance(value, dict) and any(k in value for k in ("year", "month", "day")):
        year = value.get("year")
        if year is None:
            return (
                None,
                warnings,
                ["time dict with component fields must include 'year'"],
            )
        month = value.get("month", 1)
        day = value.get("day", 1)
        hour = value.get("hour", 0)
        minute = value.get("minute", 0)
        second = value.get("second", 0)
        try:
            year_i = int(year)
            month_i = int(month)
            day_i = int(day)
            hour_i = int(hour)
            minute_i = int(minute)
            second_i = int(second)
        except (TypeError, ValueError):
            return None, warnings, ["time component fields must be numeric"]

        if not (1 <= month_i <= 12):
            return None, warnings, [f"month must be between 1 and 12, got {month_i}"]
        if not (1 <= day_i <= 31):
            return None, warnings, [f"day must be between 1 and 31, got {day_i}"]
        if not (0 <= hour_i <= 23):
            return None, warnings, [f"hour must be between 0 and 23, got {hour_i}"]
        if not (0 <= minute_i <= 59):
            return None, warnings, [f"minute must be between 0 and 59, got {minute_i}"]
        if not (0 <= second_i <= 59):
            return None, warnings, [f"second must be between 0 and 59, got {second_i}"]

        if "precision" in value:
            precision = int(value["precision"])
        elif "second" in value:
            precision = 14
        elif "minute" in value:
            precision = 13
        elif "hour" in value:
            precision = 12
        elif "day" in value:
            precision = 11
        elif "month" in value:
            precision = 10
        else:
            precision = 9

        return (
            {
                "time": _format_wikibase_time(
                    year=year_i,
                    month=month_i,
                    day=day_i,
                    hour=hour_i,
                    minute=minute_i,
                    second=second_i,
                ),
                "timezone": int(value.get("timezone", 0) or 0),
                "before": int(value.get("before", 0) or 0),
                "after": int(value.get("after", 0) or 0),
                "precision": precision,
                "calendarmodel": value.get("calendarmodel")
                or _WIKIBASE_DEFAULT_CALENDAR_MODEL,
            },
            ["Coerced time component fields to Wikibase time payload"],
            ["time_component_input"],
        )
    elif isinstance(value, int):
        candidate = str(value)
        warnings.append("Coerced numeric year to Wikibase time payload")
        uncertainty_reasons.append("time_numeric_year_input")
    elif isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None, warnings, ["time value cannot be empty"]
    else:
        return (
            None,
            warnings,
            [f"time must be a dict/string/year, got {type(value).__name__}"],
        )

    match = _TIME_COMPONENT_PATTERN.match(candidate)
    if not match:
        return (
            None,
            warnings,
            [
                "time must be in YYYY, YYYY-MM, YYYY-MM-DD, or YYYY-MM-DDTHH:MM[:SS] format"
            ],
        )

    sign = match.group("sign") or "+"
    year_i = int(match.group("year"))
    if sign == "-":
        year_i = -year_i

    month_s = match.group("month")
    day_s = match.group("day")
    hour_s = match.group("hour")
    minute_s = match.group("minute")
    second_s = match.group("second")

    month_i = int(month_s) if month_s is not None else 1
    day_i = int(day_s) if day_s is not None else 1
    hour_i = int(hour_s) if hour_s is not None else 0
    minute_i = int(minute_s) if minute_s is not None else 0
    second_i = int(second_s) if second_s is not None else 0

    if not (1 <= month_i <= 12):
        return None, warnings, [f"month must be between 1 and 12, got {month_i}"]
    if not (1 <= day_i <= 31):
        return None, warnings, [f"day must be between 1 and 31, got {day_i}"]
    if not (0 <= hour_i <= 23):
        return None, warnings, [f"hour must be between 0 and 23, got {hour_i}"]
    if not (0 <= minute_i <= 59):
        return None, warnings, [f"minute must be between 0 and 59, got {minute_i}"]
    if not (0 <= second_i <= 59):
        return None, warnings, [f"second must be between 0 and 59, got {second_i}"]

    if second_s is not None:
        precision = 14
    elif minute_s is not None:
        precision = 13
    elif hour_s is not None:
        precision = 12
    elif day_s is not None:
        precision = 11
    elif month_s is not None:
        precision = 10
    else:
        precision = 9

    return (
        {
            "time": _format_wikibase_time(
                year=year_i,
                month=month_i,
                day=day_i,
                hour=hour_i,
                minute=minute_i,
                second=second_i,
            ),
            "timezone": timezone,
            "before": before,
            "after": after,
            "precision": precision,
            "calendarmodel": calendarmodel,
        },
        warnings,
        uncertainty_reasons,
    )


def _parse_coordinate_component(
    raw: Any,
    *,
    is_latitude: bool,
) -> tuple[Optional[float], Optional[float], Optional[str]]:
    """Parse a coordinate component into decimal degrees and a precision hint."""
    if isinstance(raw, (int, float)):
        return float(raw), None, None

    if not isinstance(raw, str):
        return (
            None,
            None,
            f"coordinate component must be numeric/string, got {type(raw).__name__}",
        )

    candidate = raw.strip()
    if not candidate:
        return None, None, "coordinate component cannot be empty"

    decimal_match = _COORD_DECIMAL_HEMISPHERE_PATTERN.match(candidate)
    if decimal_match:
        numeric_text = decimal_match.group(1)
        hemisphere = decimal_match.group(2).upper() if decimal_match.group(2) else None
        value = float(numeric_text)
        if hemisphere in {"S", "W"}:
            value = -abs(value)
        elif hemisphere in {"N", "E"}:
            value = abs(value)
        decimals = _count_decimal_places(numeric_text)
        precision_hint = 10 ** (-decimals) if decimals > 0 else 1.0
        return value, precision_hint, None

    dms_match = _COORD_DMS_PATTERN.match(candidate)
    if dms_match:
        numbers = re.findall(r"[+-]?\d+(?:\.\d+)?", candidate)
        if not numbers:
            return None, None, "DMS coordinate did not contain numeric parts"

        degrees = float(numbers[0])
        minutes = float(numbers[1]) if len(numbers) > 1 else 0.0
        seconds = float(numbers[2]) if len(numbers) > 2 else 0.0

        hemisphere = None
        for ch in reversed(candidate.upper()):
            if ch in {"N", "S", "E", "W"}:
                hemisphere = ch
                break

        if minutes < 0 or minutes >= 60:
            return None, None, f"DMS minutes out of range: {minutes}"
        if seconds < 0 or seconds >= 60:
            return None, None, f"DMS seconds out of range: {seconds}"

        absolute = abs(degrees) + (minutes / 60.0) + (seconds / 3600.0)
        sign = -1.0 if degrees < 0 else 1.0
        if hemisphere in {"S", "W"}:
            sign = -1.0
        elif hemisphere in {"N", "E"}:
            sign = 1.0

        precision_hint = 1.0
        if len(numbers) > 2:
            precision_hint = 1.0 / 3600.0
        elif len(numbers) > 1:
            precision_hint = 1.0 / 60.0

        return sign * absolute, precision_hint, None

    axis = "latitude" if is_latitude else "longitude"
    return None, None, f"could not parse {axis} coordinate: {raw}"


def _coerce_globe_coordinate_value(
    value: Any,
) -> tuple[Optional[dict[str, Any]], list[str], list[str]]:
    """Coerce broad coordinate input forms into Wikibase globe-coordinate payloads."""
    warnings: list[str] = []
    uncertainty_reasons: list[str] = []

    lat_raw: Any = None
    lon_raw: Any = None
    altitude: Any = None
    precision_input: Any = None
    globe: Any = _WIKIBASE_DEFAULT_GLOBE

    if value is None:
        return None, warnings, ["globe-coordinate value cannot be null"]

    if isinstance(value, dict):
        lat_raw = value.get("latitude", value.get("lat", value.get("y")))
        lon_raw = value.get(
            "longitude", value.get("lon", value.get("lng", value.get("x")))
        )
        altitude = value.get("altitude")
        precision_input = value.get("precision")
        globe = value.get("globe", _WIKIBASE_DEFAULT_GLOBE)
        if (
            "lat" in value
            or "lon" in value
            or "lng" in value
            or "x" in value
            or "y" in value
        ):
            warnings.append(
                "Normalized shorthand coordinate keys to latitude/longitude"
            )
            uncertainty_reasons.append("coordinate_shorthand_keys")
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        lat_raw = value[0]
        lon_raw = value[1]
        altitude = value[2] if len(value) > 2 else None
        warnings.append("Coerced coordinate sequence to globe-coordinate object")
        uncertainty_reasons.append("coordinate_sequence_input")
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None, warnings, ["globe-coordinate value cannot be empty"]

        if "," in text:
            parts = [p.strip() for p in text.split(",") if p.strip()]
        else:
            parts = text.split()

        if len(parts) < 2:
            return (
                None,
                warnings,
                ["globe-coordinate string must include latitude and longitude"],
            )

        lat_raw = parts[0]
        lon_raw = parts[1]
        warnings.append("Coerced coordinate string to globe-coordinate object")
        uncertainty_reasons.append("coordinate_string_input")
    else:
        return (
            None,
            warnings,
            [f"globe-coordinate must be dict/list/string, got {type(value).__name__}"],
        )

    if lat_raw is None:
        return None, warnings, ["globe-coordinate dict must contain latitude/lat/y"]
    if lon_raw is None:
        return (
            None,
            warnings,
            ["globe-coordinate dict must contain longitude/lon/lng/x"],
        )

    lat, lat_precision_hint, lat_error = _parse_coordinate_component(
        lat_raw, is_latitude=True
    )
    if lat_error:
        return None, warnings, [lat_error]

    lon, lon_precision_hint, lon_error = _parse_coordinate_component(
        lon_raw, is_latitude=False
    )
    if lon_error:
        return None, warnings, [lon_error]

    if not (-90 <= lat <= 90):
        return None, warnings, [f"latitude must be between -90 and 90, got {lat}"]
    if not (-180 <= lon <= 180):
        return None, warnings, [f"longitude must be between -180 and 180, got {lon}"]

    if precision_input is not None:
        try:
            precision = float(precision_input)
        except (TypeError, ValueError):
            return None, warnings, [f"precision must be numeric, got {precision_input}"]
        if precision <= 0:
            return None, warnings, [f"precision must be > 0, got {precision}"]
    else:
        hints = [h for h in (lat_precision_hint, lon_precision_hint) if h is not None]
        precision = min(hints) if hints else 1.0
        warnings.append(
            f"Derived coordinate precision from input granularity: {precision}"
        )
        uncertainty_reasons.append("coordinate_precision_derived")

    normalized = {
        "latitude": lat,
        "longitude": lon,
        "altitude": altitude,
        "precision": precision,
        "globe": globe or _WIKIBASE_DEFAULT_GLOBE,
    }
    return normalized, warnings, uncertainty_reasons


class ConformanceOutcome(str, Enum):
    """Statement and entity conformance classification outcomes."""

    CONFORMANT = "conformant"
    NON_CONFORMANT_MAPPABLE = "non_conformant_mappable"
    TO_BE_DEFINED = "to_be_defined"
    MISSING = "missing"


@dataclass
class StatementEvaluation:
    """Atomic evaluation result for a single statement instance."""

    outcome: ConformanceOutcome
    statement_ref: Optional[str]
    property_ref: Optional[str]
    normalized_value: Any
    raw_claims: list[dict[str, Any]]
    notices: list[ConformanceNotice] = field(default_factory=list)
    qualifier_evaluations: list["StatementEvaluation"] = field(default_factory=list)
    reference_evaluations: list["StatementEvaluation"] = field(default_factory=list)


def conformance_notice_payloads(
    notices: list[ConformanceNotice],
) -> list[dict[str, Any]]:
    """Serialize fermenter notices for packet/UI consumers."""
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


def statement_evaluation_to_record(
    evaluation: StatementEvaluation,
    profile_statement: dict[str, Any],
    *,
    entity_id: str,
    json_path: str,
) -> dict[str, Any]:
    """Serialize one atomic statement evaluation to the packet conformance shape."""
    status = (
        "conformant"
        if evaluation.outcome == ConformanceOutcome.CONFORMANT
        else "nonconformant"
    )
    statement_uri = _statement_ref_from_profile_statement(profile_statement)
    statement_id = profile_statement.get("name_identifier")
    if not isinstance(statement_id, str) or not statement_id:
        statement_id = (
            statement_uri.rstrip("/").split("/")[-1]
            if isinstance(statement_uri, str) and statement_uri
            else None
        )

    record: dict[str, Any] = {
        "entity_id": entity_id,
        "gkc_entity_statement": {
            "id": statement_id,
            "uri": statement_uri or f"unknown/{evaluation.property_ref or 'statement'}",
        },
        "json_path": json_path,
        "statement_uri": statement_uri
        or f"unknown/{evaluation.property_ref or 'statement'}",
        "status": status,
        "outcome": evaluation.outcome.value,
    }

    if isinstance(statement_id, str) and statement_id:
        record["statement_id"] = statement_id

    if evaluation.normalized_value is not None:
        record["normalized_value"] = evaluation.normalized_value

    if evaluation.notices:
        record["notices"] = conformance_notice_payloads(evaluation.notices)

    qualifier_records: list[dict[str, Any]] = []
    qualifier_defs = profile_statement.get("qualifiers", [])
    if isinstance(qualifier_defs, list):
        qualifier_def_by_ref = {
            _statement_ref_from_profile_statement(q): q
            for q in qualifier_defs
            if isinstance(q, dict)
            and isinstance(_statement_ref_from_profile_statement(q), str)
        }
        for child_eval in evaluation.qualifier_evaluations:
            child_profile = qualifier_def_by_ref.get(child_eval.statement_ref)
            if not isinstance(child_profile, dict):
                child_profile = {
                    "entity": child_eval.statement_ref,
                    "name_identifier": child_eval.statement_ref,
                }
            child_property_ref = (
                _statement_property_ref(child_profile) or child_eval.property_ref
            )
            child_path = f"{json_path}.qualifiers.{child_property_ref or 'unknown'}"
            qualifier_records.append(
                statement_evaluation_to_record(
                    child_eval,
                    child_profile,
                    entity_id=entity_id,
                    json_path=child_path,
                )
            )
    if qualifier_records:
        record["qualifiers"] = qualifier_records

    reference_records: list[dict[str, Any]] = []
    reference_defs = profile_statement.get("references", [])
    if isinstance(reference_defs, list):
        reference_def_by_ref = {
            _statement_ref_from_profile_statement(r): r
            for r in reference_defs
            if isinstance(r, dict)
            and isinstance(_statement_ref_from_profile_statement(r), str)
        }
        for child_eval in evaluation.reference_evaluations:
            child_profile = reference_def_by_ref.get(child_eval.statement_ref)
            if not isinstance(child_profile, dict):
                child_profile = {
                    "entity": child_eval.statement_ref,
                    "name_identifier": child_eval.statement_ref,
                }
            child_property_ref = (
                _statement_property_ref(child_profile) or child_eval.property_ref
            )
            child_path = f"{json_path}.references.{child_property_ref or 'unknown'}"
            reference_records.append(
                statement_evaluation_to_record(
                    child_eval,
                    child_profile,
                    entity_id=entity_id,
                    json_path=child_path,
                )
            )
    if reference_records:
        record["references"] = reference_records

    return record


@dataclass
class EntityEvaluation:
    """Aggregate evaluation result for one entity against profile statements."""

    entity_ref: str
    profile_ref: str
    conformant: list[StatementEvaluation] = field(default_factory=list)
    non_conformant_mappable: list[StatementEvaluation] = field(default_factory=list)
    to_be_defined: list[StatementEvaluation] = field(default_factory=list)
    missing: list[StatementEvaluation] = field(default_factory=list)

    @property
    def all_notices(self) -> list[ConformanceNotice]:
        notices: list[ConformanceNotice] = []
        for bucket in (
            self.conformant,
            self.non_conformant_mappable,
            self.to_be_defined,
            self.missing,
        ):
            for evaluation in bucket:
                notices.extend(evaluation.notices)
        return notices

    @property
    def is_conformant(self) -> bool:
        return not self.non_conformant_mappable and not self.missing


def _canonical_json_digest(payload: dict[str, Any]) -> str:
    """Return deterministic SHA256 digest for JSON payloads."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _statement_ref_from_profile_statement(
    profile_statement: dict[str, Any],
) -> Optional[str]:
    for key in ("id", "entity", "name_identifier"):
        value = profile_statement.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _statement_property_ref(profile_statement: dict[str, Any]) -> Optional[str]:
    io_map = profile_statement.get("io_map")
    if not isinstance(io_map, list):
        return None

    for mapping in io_map:
        if not isinstance(mapping, dict):
            continue
        target = mapping.get("to")
        if isinstance(target, str) and target:
            return target.rsplit("/", 1)[-1]
    return None


def _statement_data_type(profile_statement: dict[str, Any]) -> Optional[str]:
    value_block = profile_statement.get("value")
    if not isinstance(value_block, dict):
        return None

    data_type = value_block.get("type")
    if not isinstance(data_type, str) or not data_type:
        return None

    return canonicalize_wikibase_datatype(data_type)


def _statement_max_count(profile_statement: dict[str, Any]) -> Optional[int]:
    max_count = profile_statement.get("max_count")
    if isinstance(max_count, int):
        return max_count
    if isinstance(max_count, float) and max_count.is_integer():
        return int(max_count)
    if isinstance(max_count, str) and max_count.isdigit():
        return int(max_count)
    return None


def _statement_is_required(profile_statement: dict[str, Any]) -> bool:
    required = profile_statement.get("required")
    if isinstance(required, bool):
        return required

    max_count = _statement_max_count(profile_statement)
    return isinstance(max_count, int) and max_count > 0


def _statement_fixed_value(profile_statement: dict[str, Any]) -> Any:
    value_block = profile_statement.get("value")
    if not isinstance(value_block, dict):
        return None

    fixed_value = value_block.get("fixed_value")
    if fixed_value is not None:
        return fixed_value

    value_list = value_block.get("value_list")
    if isinstance(value_list, list) and len(value_list) == 1:
        return value_list[0]
    return None


def _resolve_statement_value_list_path(
    profile_statement: dict[str, Any],
    *,
    value_list_root: Optional[Path],
) -> Optional[Path]:
    if value_list_root is None:
        return None

    value_block = profile_statement.get("value")
    if not isinstance(value_block, dict):
        return None

    reference = value_block.get("value_list_reference")
    if not isinstance(reference, str) or not reference:
        return None

    reference_path = Path(reference)
    if reference_path.is_absolute():
        return reference_path
    return value_list_root / reference_path


def _snak_to_claim(snak: Any) -> Optional[dict[str, Any]]:
    if not isinstance(snak, dict):
        return None
    return {"mainsnak": snak}


def _claim_qualifiers_by_property(
    raw_claim: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    qualifiers = raw_claim.get("qualifiers", {})
    if not isinstance(qualifiers, dict):
        return {}

    normalized: dict[str, list[dict[str, Any]]] = {}
    for property_id, snaks in qualifiers.items():
        if not isinstance(property_id, str) or not property_id:
            continue
        if not isinstance(snaks, list):
            continue
        normalized[property_id] = [
            wrapped
            for snak in snaks
            if isinstance((wrapped := _snak_to_claim(snak)), dict)
        ]
    return normalized


def _claim_references_by_property(
    raw_claim: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    references = raw_claim.get("references", [])
    if not isinstance(references, list):
        return {}

    normalized: dict[str, list[dict[str, Any]]] = {}
    for reference_block in references:
        if not isinstance(reference_block, dict):
            continue
        snaks = reference_block.get("snaks", {})
        if not isinstance(snaks, dict):
            continue
        for property_id, property_snaks in snaks.items():
            if not isinstance(property_id, str) or not property_id:
                continue
            if not isinstance(property_snaks, list):
                continue
            normalized.setdefault(property_id, []).extend(
                wrapped
                for snak in property_snaks
                if isinstance((wrapped := _snak_to_claim(snak)), dict)
            )
    return normalized


def _missing_nested_statement_evaluation(
    profile_statement: dict[str, Any],
    *,
    entity_ref: str,
    code: str,
    message: str,
) -> StatementEvaluation:
    statement_ref = _statement_ref_from_profile_statement(profile_statement)
    property_ref = _statement_property_ref(profile_statement)
    return StatementEvaluation(
        outcome=ConformanceOutcome.MISSING,
        statement_ref=statement_ref,
        property_ref=property_ref,
        normalized_value=None,
        raw_claims=[],
        notices=[
            ConformanceNotice(
                severity="warning",
                entity_ref=entity_ref,
                statement_ref=statement_ref,
                code=code,
                message=message,
            )
        ],
    )


def evaluate_statement_instance(
    profile_statement: dict[str, Any],
    raw_claim: dict[str, Any],
    *,
    entity_ref: str = "",
    value_list_root: Optional[Path] = None,
) -> StatementEvaluation:
    """Evaluate one raw Wikidata statement claim against the full profile shape.

    This is the atomic fermenter surface used by packet conformance reporting.
    It validates the statement value itself plus any profile-defined qualifiers and
    references present on the raw claim.
    """
    base_evaluation = evaluate_statement_claim(
        profile_statement,
        [raw_claim],
        entity_ref=entity_ref,
        value_list_root=value_list_root,
    )
    if not isinstance(raw_claim, dict):
        return base_evaluation

    qualifier_evaluations: list[StatementEvaluation] = []
    reference_evaluations: list[StatementEvaluation] = []
    qualifiers_by_property = _claim_qualifiers_by_property(raw_claim)
    references_by_property = _claim_references_by_property(raw_claim)

    qualifier_defs = profile_statement.get("qualifiers", [])
    qualifier_property_ids: set[str] = set()
    if isinstance(qualifier_defs, list):
        for qualifier_def in qualifier_defs:
            if not isinstance(qualifier_def, dict):
                continue
            qualifier_property = _statement_property_ref(qualifier_def)
            if not qualifier_property:
                continue
            qualifier_property_ids.add(qualifier_property)
            qualifier_claims = qualifiers_by_property.get(qualifier_property, [])
            if qualifier_claims:
                child_eval = evaluate_statement_claim(
                    qualifier_def,
                    qualifier_claims,
                    entity_ref=entity_ref,
                    value_list_root=value_list_root,
                )
            else:
                child_eval = _missing_nested_statement_evaluation(
                    qualifier_def,
                    entity_ref=entity_ref,
                    code="qualifier_missing",
                    message="Expected qualifier is missing from this statement value.",
                )
            qualifier_evaluations.append(child_eval)

    for property_id, qualifier_claims in qualifiers_by_property.items():
        if property_id in qualifier_property_ids:
            continue
        qualifier_evaluations.append(
            StatementEvaluation(
                outcome=ConformanceOutcome.TO_BE_DEFINED,
                statement_ref=f"unknown/{property_id}",
                property_ref=property_id,
                normalized_value=None,
                raw_claims=qualifier_claims,
                notices=[
                    ConformanceNotice(
                        severity="warning",
                        entity_ref=entity_ref,
                        statement_ref=f"unknown/{property_id}",
                        code="qualifier_unexpected",
                        message=(
                            f"Qualifier {property_id} is not defined in profile statement."
                        ),
                    )
                ],
            )
        )

    reference_defs = profile_statement.get("references", [])
    reference_property_ids: set[str] = set()
    defined_reference_evaluations: list[StatementEvaluation] = []
    if isinstance(reference_defs, list):
        for reference_def in reference_defs:
            if not isinstance(reference_def, dict):
                continue
            reference_property = _statement_property_ref(reference_def)
            if not reference_property:
                continue
            reference_property_ids.add(reference_property)
            reference_claims = references_by_property.get(reference_property, [])
            if reference_claims:
                child_eval = evaluate_statement_claim(
                    reference_def,
                    reference_claims,
                    entity_ref=entity_ref,
                    value_list_root=value_list_root,
                )
            else:
                child_eval = _missing_nested_statement_evaluation(
                    reference_def,
                    entity_ref=entity_ref,
                    code="reference_missing",
                    message="Expected reference not provided.",
                )
            reference_evaluations.append(child_eval)
            defined_reference_evaluations.append(child_eval)

    for property_id, reference_claims in references_by_property.items():
        if property_id in reference_property_ids:
            continue
        reference_evaluations.append(
            StatementEvaluation(
                outcome=ConformanceOutcome.TO_BE_DEFINED,
                statement_ref=f"unknown/{property_id}",
                property_ref=property_id,
                normalized_value=None,
                raw_claims=reference_claims,
                notices=[
                    ConformanceNotice(
                        severity="warning",
                        entity_ref=entity_ref,
                        statement_ref=f"unknown/{property_id}",
                        code="reference_unexpected",
                        message=(
                            f"Reference {property_id} is not defined in profile statement."
                        ),
                    )
                ],
            )
        )

    base_evaluation.qualifier_evaluations = qualifier_evaluations
    base_evaluation.reference_evaluations = reference_evaluations

    qualifier_failure = any(
        child_eval.outcome != ConformanceOutcome.CONFORMANT
        for child_eval in qualifier_evaluations
    )

    reference_group_failure = False
    if defined_reference_evaluations:
        has_conformant_reference = any(
            child_eval.outcome == ConformanceOutcome.CONFORMANT
            for child_eval in defined_reference_evaluations
        )
        reference_group_failure = not has_conformant_reference
        if reference_group_failure:
            base_evaluation.notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=entity_ref,
                    statement_ref=base_evaluation.statement_ref,
                    code="reference_group_missing",
                    message=(
                        "At least one profile-defined reference is required for this statement."
                    ),
                )
            )

    unexpected_nested_failure = any(
        child_eval.outcome == ConformanceOutcome.TO_BE_DEFINED
        for child_eval in qualifier_evaluations + reference_evaluations
    )

    if base_evaluation.outcome == ConformanceOutcome.CONFORMANT and (
        qualifier_failure or reference_group_failure or unexpected_nested_failure
    ):
        base_evaluation.outcome = ConformanceOutcome.NON_CONFORMANT_MAPPABLE

    return base_evaluation


def normalize_claim_value(
    raw_claim: dict[str, Any], data_type: str
) -> ValidationResult:
    """Normalize and validate a single raw Wikidata claim value."""
    if not isinstance(raw_claim, dict):
        return ValidationResult(
            valid=False,
            value=None,
            errors=["Raw claim must be a dictionary"],
        )

    mainsnak = raw_claim.get("mainsnak", {})
    if not isinstance(mainsnak, dict):
        return ValidationResult(
            valid=False,
            value=None,
            errors=["Claim mainsnak must be a dictionary"],
        )

    snaktype = mainsnak.get("snaktype")
    if snaktype == "novalue":
        return ValidationResult(valid=True, value=None)
    if snaktype == "somevalue":
        return ValidationResult(
            valid=True,
            value=None,
            warnings=["Claim uses somevalue; no concrete value to validate"],
        )

    datavalue = mainsnak.get("datavalue", {})
    if not isinstance(datavalue, dict) or "value" not in datavalue:
        return ValidationResult(
            valid=False,
            value=None,
            errors=["Claim is missing mainsnak.datavalue.value"],
        )

    return validate_by_datatype(data_type, datavalue.get("value"))


def evaluate_statement_claim(
    profile_statement: dict[str, Any],
    raw_claim_list: list[dict[str, Any]],
    *,
    entity_ref: str = "",
    value_list_root: Optional[Path] = None,
) -> StatementEvaluation:
    """Evaluate one statement against claim candidates using profile constraints."""
    statement_ref = _statement_ref_from_profile_statement(profile_statement)
    property_ref = _statement_property_ref(profile_statement)
    data_type = _statement_data_type(profile_statement)
    fixed_value = _statement_fixed_value(profile_statement)
    max_count = _statement_max_count(profile_statement)
    value_list_path = _resolve_statement_value_list_path(
        profile_statement,
        value_list_root=value_list_root,
    )

    notices: list[ConformanceNotice] = []
    normalized_values: list[Any] = []
    claim_candidates = raw_claim_list if isinstance(raw_claim_list, list) else []

    if not claim_candidates:
        if fixed_value is not None:
            result, notice = enforce_fixed_value(None, fixed_value, statement_ref or "")
            if notice is not None:
                notice.entity_ref = entity_ref
                notices.append(notice)
            return StatementEvaluation(
                outcome=ConformanceOutcome.CONFORMANT,
                statement_ref=statement_ref,
                property_ref=property_ref,
                normalized_value=result.value,
                raw_claims=[],
                notices=notices,
            )

        if _statement_is_required(profile_statement):
            notices.append(
                ConformanceNotice(
                    severity="error",
                    entity_ref=entity_ref,
                    statement_ref=statement_ref,
                    code="statement_missing",
                    message="Expected statement is missing from input data",
                )
            )
            return StatementEvaluation(
                outcome=ConformanceOutcome.MISSING,
                statement_ref=statement_ref,
                property_ref=property_ref,
                normalized_value=None,
                raw_claims=[],
                notices=notices,
            )

        return StatementEvaluation(
            outcome=ConformanceOutcome.CONFORMANT,
            statement_ref=statement_ref,
            property_ref=property_ref,
            normalized_value=None,
            raw_claims=[],
            notices=notices,
        )

    if (
        isinstance(max_count, int)
        and max_count > 0
        and len(claim_candidates) > max_count
    ):
        notices.append(
            ConformanceNotice(
                severity="warning",
                entity_ref=entity_ref,
                statement_ref=statement_ref,
                code="max_count_exceeded",
                message=(
                    f"Received {len(claim_candidates)} values but max_count is {max_count}; "
                    "extra values retained in raw_claims"
                ),
            )
        )
        claim_candidates = claim_candidates[:max_count]

    if not data_type:
        notices.append(
            ConformanceNotice(
                severity="error",
                entity_ref=entity_ref,
                statement_ref=statement_ref,
                code="statement_type_missing",
                message="Profile statement has no value.type for validation",
            )
        )
        return StatementEvaluation(
            outcome=ConformanceOutcome.NON_CONFORMANT_MAPPABLE,
            statement_ref=statement_ref,
            property_ref=property_ref,
            normalized_value=None,
            raw_claims=raw_claim_list,
            notices=notices,
        )

    for raw_claim in claim_candidates:
        result = normalize_claim_value(raw_claim, data_type)
        if not result.valid:
            for error in result.errors:
                notices.append(
                    ConformanceNotice(
                        severity="error",
                        entity_ref=entity_ref,
                        statement_ref=statement_ref,
                        code="datatype_mismatch",
                        message=error,
                    )
                )
            continue

        for warning in result.warnings:
            notices.append(
                ConformanceNotice(
                    severity="warning",
                    entity_ref=entity_ref,
                    statement_ref=statement_ref,
                    code="datatype_coercion_warning",
                    message=warning,
                    normalized_value=result.value,
                )
            )
        normalized_values.append(result.value)

    if not normalized_values:
        return StatementEvaluation(
            outcome=ConformanceOutcome.NON_CONFORMANT_MAPPABLE,
            statement_ref=statement_ref,
            property_ref=property_ref,
            normalized_value=None,
            raw_claims=raw_claim_list,
            notices=notices,
        )

    if fixed_value is not None:
        for idx, value in enumerate(normalized_values):
            result, notice = enforce_fixed_value(
                value, fixed_value, statement_ref or ""
            )
            if notice is not None:
                notice.entity_ref = entity_ref
                notices.append(notice)
            if not result.valid:
                return StatementEvaluation(
                    outcome=ConformanceOutcome.NON_CONFORMANT_MAPPABLE,
                    statement_ref=statement_ref,
                    property_ref=property_ref,
                    normalized_value=normalized_values[idx],
                    raw_claims=raw_claim_list,
                    notices=notices,
                )
            normalized_values[idx] = result.value

    if value_list_path is not None:
        for value in normalized_values:
            list_result = validate_value_from_list(value, value_list_path)
            if not list_result.valid:
                for error in list_result.errors:
                    notices.append(
                        ConformanceNotice(
                            severity="error",
                            entity_ref=entity_ref,
                            statement_ref=statement_ref,
                            code="value_list_miss",
                            message=error,
                        )
                    )
                return StatementEvaluation(
                    outcome=ConformanceOutcome.NON_CONFORMANT_MAPPABLE,
                    statement_ref=statement_ref,
                    property_ref=property_ref,
                    normalized_value=value,
                    raw_claims=raw_claim_list,
                    notices=notices,
                )

    normalized_payload: Any
    if len(normalized_values) == 1:
        normalized_payload = normalized_values[0]
    else:
        normalized_payload = normalized_values

    if any(notice.code == "max_count_exceeded" for notice in notices):
        return StatementEvaluation(
            outcome=ConformanceOutcome.NON_CONFORMANT_MAPPABLE,
            statement_ref=statement_ref,
            property_ref=property_ref,
            normalized_value=normalized_payload,
            raw_claims=raw_claim_list,
            notices=notices,
        )

    return StatementEvaluation(
        outcome=ConformanceOutcome.CONFORMANT,
        statement_ref=statement_ref,
        property_ref=property_ref,
        normalized_value=normalized_payload,
        raw_claims=raw_claim_list,
        notices=notices,
    )


def evaluate_entity(
    profile_statements: list[dict[str, Any]],
    wikidata_item: dict[str, Any],
    *,
    io_map_index: dict[str, dict[str, Any]],
    entity_ref: str = "",
    value_list_root: Optional[Path] = None,
) -> EntityEvaluation:
    """Evaluate one entity item against profile statements and classify outcomes."""
    claims = wikidata_item.get("claims", {})
    if not isinstance(claims, dict):
        claims = {}

    profile_ref = entity_ref or str(wikidata_item.get("id") or "")
    evaluation = EntityEvaluation(
        entity_ref=entity_ref or "unknown", profile_ref=profile_ref
    )
    covered_properties: set[str] = set()

    for profile_statement in profile_statements:
        if not isinstance(profile_statement, dict):
            continue

        statement_property_ids: list[str] = []
        io_map = profile_statement.get("io_map")
        if isinstance(io_map, list):
            for mapping in io_map:
                if not isinstance(mapping, dict):
                    continue
                target = mapping.get("to")
                if isinstance(target, str) and target:
                    statement_property_ids.append(target.rsplit("/", 1)[-1])

        if not statement_property_ids:
            fallback_property = _statement_property_ref(profile_statement)
            if fallback_property:
                statement_property_ids.append(fallback_property)

        raw_claim_list: list[dict[str, Any]] = []
        for property_id in statement_property_ids:
            covered_properties.add(property_id)
            claim_values = claims.get(property_id, [])
            if isinstance(claim_values, list):
                raw_claim_list.extend(
                    claim for claim in claim_values if isinstance(claim, dict)
                )

        statement_eval = evaluate_statement_claim(
            profile_statement,
            raw_claim_list,
            entity_ref=evaluation.entity_ref,
            value_list_root=value_list_root,
        )

        if statement_eval.outcome == ConformanceOutcome.CONFORMANT:
            evaluation.conformant.append(statement_eval)
        elif statement_eval.outcome == ConformanceOutcome.NON_CONFORMANT_MAPPABLE:
            evaluation.non_conformant_mappable.append(statement_eval)
        elif statement_eval.outcome == ConformanceOutcome.TO_BE_DEFINED:
            evaluation.to_be_defined.append(statement_eval)
        elif statement_eval.outcome == ConformanceOutcome.MISSING:
            evaluation.missing.append(statement_eval)

    known_properties = set(covered_properties)
    known_properties.update(
        property_id
        for property_id, statement in io_map_index.items()
        if isinstance(property_id, str) and property_id and isinstance(statement, dict)
    )

    for property_id, claim_values in claims.items():
        if property_id in known_properties:
            continue
        if not isinstance(claim_values, list):
            claim_values = []

        notice = ConformanceNotice(
            severity="info",
            entity_ref=evaluation.entity_ref,
            statement_ref=None,
            code="statement_uncovered",
            message=f"Property {property_id} is not defined in active profile",
        )
        evaluation.to_be_defined.append(
            StatementEvaluation(
                outcome=ConformanceOutcome.TO_BE_DEFINED,
                statement_ref=None,
                property_ref=property_id,
                normalized_value=None,
                raw_claims=[claim for claim in claim_values if isinstance(claim, dict)],
                notices=[notice],
            )
        )

    return evaluation


def check_packet_integrity(packet: dict[str, Any]) -> Optional[ConformanceNotice]:
    """Verify packet metadata digest integrity before evaluating packet data."""
    if not isinstance(packet, dict):
        return ConformanceNotice(
            severity="error",
            entity_ref="packet",
            code="packet_invalid",
            message="Packet payload must be a JSON object",
        )

    metadata = packet.get("metadata")
    if not isinstance(metadata, dict):
        return ConformanceNotice(
            severity="error",
            entity_ref=str(packet.get("packet_id") or "packet"),
            code="metadata_missing",
            message="Packet metadata section is missing",
        )

    integrity = metadata.get("integrity")
    if not isinstance(integrity, dict):
        return ConformanceNotice(
            severity="error",
            entity_ref=str(packet.get("packet_id") or "packet"),
            code="metadata_integrity_missing",
            message="Packet metadata.integrity section is missing",
        )

    declared_digest = integrity.get("metadata_digest")
    if not isinstance(declared_digest, str) or not declared_digest:
        return ConformanceNotice(
            severity="error",
            entity_ref=str(packet.get("packet_id") or "packet"),
            code="metadata_digest_missing",
            message="Packet metadata digest is missing",
        )

    metadata_without_integrity = dict(metadata)
    metadata_without_integrity.pop("integrity", None)
    computed_digest = _canonical_json_digest(metadata_without_integrity)

    if computed_digest != declared_digest:
        return ConformanceNotice(
            severity="error",
            entity_ref=str(packet.get("packet_id") or "packet"),
            code="metadata_digest_mismatch",
            message="Packet metadata digest mismatch; validation halted",
            normalized_value={
                "expected": declared_digest,
                "computed": computed_digest,
            },
        )

    return None


def validate_packet_inline(
    packet: dict[str, Any],
    *,
    value_list_root: Optional[Path] = None,
) -> tuple[bool, list[ConformanceNotice]]:
    """Validate an in-memory packet object with integrity-first gating."""
    del value_list_root

    integrity_notice = check_packet_integrity(packet)
    if integrity_notice is not None:
        return False, [integrity_notice]

    notices: list[ConformanceNotice] = []
    data = packet.get("data")
    entities = data.get("entities") if isinstance(data, dict) else None

    if not isinstance(entities, list):
        notices.append(
            ConformanceNotice(
                severity="error",
                entity_ref=str(packet.get("packet_id") or "packet"),
                code="packet_entities_missing",
                message="Packet data.entities must be a list",
            )
        )
        return False, notices

    notices.append(
        ConformanceNotice(
            severity="info",
            entity_ref=str(packet.get("packet_id") or "packet"),
            code="packet_integrity_pass",
            message="Packet metadata integrity check passed",
        )
    )
    return True, notices


def validate_packet_from_file(
    path: Path,
    *,
    value_list_root: Optional[Path] = None,
) -> tuple[bool, list[ConformanceNotice]]:
    """Validate packet JSON loaded from a file path."""
    packet_path = Path(path)
    try:
        packet_payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return (
            False,
            [
                ConformanceNotice(
                    severity="error",
                    entity_ref=str(packet_path),
                    code="packet_file_load_failed",
                    message=f"Failed to load packet file: {exc}",
                )
            ],
        )

    if not isinstance(packet_payload, dict):
        return (
            False,
            [
                ConformanceNotice(
                    severity="error",
                    entity_ref=str(packet_path),
                    code="packet_file_invalid",
                    message="Packet file must contain a JSON object",
                )
            ],
        )

    return validate_packet_inline(packet_payload, value_list_root=value_list_root)


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
        if is_wikibase_item_datatype(datatype):
            normalized = _merge_wikibase_item_metadata(value, normalized)
        return normalized, notices
    return value, notices


def _resolve_packet_statement_value_list_path(
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

    Validation policy for wizard/runtime packet editing:
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
        datatype = canonicalize_wikibase_datatype(value_block.get("type", "string"))

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

        value_list_path = _resolve_packet_statement_value_list_path(
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
                if is_wikibase_item_datatype(datatype):
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
                q_datatype = canonicalize_wikibase_datatype(
                    qualifier_def.get("value", {}).get("type", "string")
                )
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
                        if is_wikibase_item_datatype(q_datatype):
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

                r_datatype = canonicalize_wikibase_datatype(
                    ref_def.get("value", {}).get("type", "string")
                )
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
                        if is_wikibase_item_datatype(r_datatype):
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


# ============================================================================
# Wikibase datatype validators (all 8 primitive types)
# ============================================================================


def validate_wikibase_item(
    value: Any,
    *,
    validation_policy: ValidationPolicy = ValidationPolicy.STRUCTURE,
    policy_config: Optional[ValidationPolicyConfig] = None,
) -> ValidationResult:
    """Validate a wikibase-item value.

    Expected Wikibase JSON structure:
        {"entity-type": "item", "numeric-id": 123, "id": "Q123"}

    Accepts either a dict matching the structure above or a QID string (will coerce).
    """
    policy = _resolve_validation_policy_config(validation_policy, policy_config)
    qid, warnings, issues = _coerce_wikibase_item_reference(value)
    if not qid:
        return ValidationResult(valid=False, value=value, errors=issues)

    normalized = {
        "entity-type": "item",
        "numeric-id": int(qid[1:]) if qid[1:].isdigit() else None,
        "id": qid,
        "wikibase-api-url": policy.wikibase_api_url,
    }

    uncertainty_reasons = list(issues) if issues else []
    if policy.policy == ValidationPolicy.STRUCTURE:
        return ValidationResult(
            valid=True,
            value=normalized,
            warnings=warnings,
            uncertainty=_uncertainty_score(uncertainty_reasons),
            uncertainty_reasons=uncertainty_reasons,
        )

    try:
        client = WikibaseApiClient(
            api_url=policy.wikibase_api_url,
            timeout=policy.timeout_seconds,
        )
        client.get_entity(qid)
    except Exception as exc:
        return ValidationResult(
            valid=False,
            value=normalized,
            warnings=warnings,
            errors=[
                "Online Wikibase validation failed: "
                f"could not resolve {qid} at {policy.wikibase_api_url}: {exc}"
            ],
            uncertainty=1.0,
            uncertainty_reasons=["online_wikibase_lookup_failed"],
        )

    actionable_warnings: list[str] = []
    if policy.policy == ValidationPolicy.ACTIONABLE:
        actionable_warnings.append(
            "ACTIONABLE policy currently verifies entity resolvability; extended intent checks are pending policy-rule integration"
        )

    return ValidationResult(
        valid=True,
        value=normalized,
        warnings=warnings + actionable_warnings,
        uncertainty=_uncertainty_score(uncertainty_reasons),
        uncertainty_reasons=uncertainty_reasons,
    )


def validate_string(value: Any) -> ValidationResult:
    """Validate a string value.

    Coerces to string if not already one.
    """
    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["string value cannot be null"]
        )

    if isinstance(value, str):
        return ValidationResult(valid=True, value=value)

    # Attempt coercion
    try:
        coerced = str(value)
        return ValidationResult(
            valid=True,
            value=coerced,
            warnings=[f"Coerced {type(value).__name__} to string"],
        )
    except Exception as e:
        return ValidationResult(
            valid=False, value=value, errors=[f"Failed to coerce to string: {e}"]
        )


def validate_with_pattern(
    value: Any,
    pattern: str,
    *,
    flags: int = 0,
) -> ValidationResult:
    """Validate a string-like value against a regex pattern.

    This is a constraint-layer validator intended for profile/statement-sourced
    regex rules. It first applies ``validate_string()`` and then checks the
    normalized string against the supplied regex.

    Pattern semantics use ``re.search`` so profile-authored regexes can choose
    their own anchoring strategy.
    """
    base_result = validate_string(value)
    if not base_result.valid:
        return base_result

    if not isinstance(pattern, str) or not pattern:
        return ValidationResult(
            valid=False,
            value=base_result.value,
            warnings=base_result.warnings,
            errors=["pattern must be a non-empty regex string"],
        )

    try:
        compiled = re.compile(pattern, flags)
    except re.error as exc:
        return ValidationResult(
            valid=False,
            value=base_result.value,
            warnings=base_result.warnings,
            errors=[f"Invalid regex pattern: {exc}"],
        )

    normalized_value = base_result.value
    if not isinstance(normalized_value, str):
        return ValidationResult(
            valid=False,
            value=normalized_value,
            warnings=base_result.warnings,
            errors=["Pattern validation requires a normalized string value"],
        )

    if compiled.search(normalized_value) is None:
        return ValidationResult(
            valid=False,
            value=normalized_value,
            warnings=base_result.warnings,
            errors=[f"String does not match required pattern: {pattern}"],
        )

    return ValidationResult(
        valid=True,
        value=normalized_value,
        warnings=base_result.warnings,
    )


# Language code alias map: ISO 639-2/B, ISO 639-2/T, English names -> BCP-47
_LANGUAGE_ALIASES: dict[str, str] = {
    # Three-letter ISO 639-2 bibliographic codes
    "eng": "en",
    "fra": "fr",
    "deu": "de",
    "spa": "es",
    "zho": "zh",
    "jpn": "ja",
    "kor": "ko",
    "por": "pt",
    "ita": "it",
    "rus": "ru",
    "ara": "ar",
    "hin": "hi",
    "nld": "nl",
    "pol": "pl",
    "tur": "tr",
    "swe": "sv",
    "nor": "no",
    "dan": "da",
    "fin": "fi",
    "ces": "cs",
    "hun": "hu",
    "ron": "ro",
    "bul": "bg",
    "hrv": "hr",
    "slk": "sk",
    "slv": "sl",
    "ukr": "uk",
    "heb": "he",
    "vie": "vi",
    "tha": "th",
    "ind": "id",
    "msa": "ms",
    "cat": "ca",
    "eus": "eu",
    "ell": "el",
    "lat": "la",
    "gle": "ga",
    "cym": "cy",
    "chr": "chr",
    # Three-letter ISO 639-2 terminological codes (same as bibliographic for most)
    "fre": "fr",
    "ger": "de",
    "chi": "zh",
    # English names for common languages
    "english": "en",
    "french": "fr",
    "german": "de",
    "spanish": "es",
    "chinese": "zh",
    "japanese": "ja",
    "korean": "ko",
    "portuguese": "pt",
    "italian": "it",
    "russian": "ru",
    "arabic": "ar",
    "hindi": "hi",
    "dutch": "nl",
    "polish": "pl",
    "turkish": "tr",
    "swedish": "sv",
    "norwegian": "no",
    "danish": "da",
    "finnish": "fi",
    "czech": "cs",
    "hungarian": "hu",
    "romanian": "ro",
    "bulgarian": "bg",
    "croatian": "hr",
    "slovak": "sk",
    "slovenian": "sl",
    "ukrainian": "uk",
    "hebrew": "he",
    "vietnamese": "vi",
    "thai": "th",
    "indonesian": "id",
    "malay": "ms",
    "catalan": "ca",
    "basque": "eu",
    "greek": "el",
    "latin": "la",
    "irish": "ga",
    "welsh": "cy",
    "cherokee": "chr",
}

# BCP-47 language tag pattern: 2-8 letter primary subtag, optional further subtags
_LANG_TAG_RE = re.compile(r"^[a-z]{2,8}(-[a-z0-9]{2,8})*$", re.IGNORECASE)

# Language codes explicitly accepted by Wikibase beyond standard BCP-47
_WIKIBASE_SPECIAL_CODES = frozenset({"mul", "zxx", "und"})


def _normalize_language_code(raw: str) -> tuple[str, list[str]]:
    """Normalize a language code to canonical BCP-47 form.

    Returns ``(normalized_code, warnings)`` where warnings is empty on a clean
    normalization and carries a message when an alias was applied.
    """
    lowered = raw.strip().lower()
    warnings: list[str] = []

    alias = _LANGUAGE_ALIASES.get(lowered)
    if alias is not None:
        warnings.append(
            f"Language code '{raw}' normalized to '{alias}' via alias mapping"
        )
        return alias, warnings

    # Already a valid BCP-47 tag (or Wikibase special code) — return as-is,
    # but lowercase for consistency.
    canonical = lowered
    return canonical, warnings


def _validate_language_code(code: str) -> list[str]:
    """Return error strings for an invalid BCP-47 language code, empty if valid."""
    if code in _WIKIBASE_SPECIAL_CODES:
        return []
    if _LANG_TAG_RE.match(code):
        return []
    return [
        f"'{code}' is not a valid BCP-47 language code; "
        "expected a subtag like 'en', 'zh-hans', or a Wikibase special code like 'mul'"
    ]


def validate_monolingualtext(value: Any) -> ValidationResult:
    """Validate and coerce a monolingualtext value.

    Accepts multiple input forms and normalizes to the canonical Wikibase
    ``{language, text}`` dict:

    - A plain string is coerced to ``{"language": "mul", "text": value}``
      with an uncertainty warning.
    - A dict with ``"lang"`` instead of ``"language"`` has the key renamed.
    - Language codes are normalized via ISO 639-2 alias mapping (e.g. ``"eng"``
      → ``"en"``) and validated against BCP-47.
    """
    warnings: list[str] = []

    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["monolingualtext value cannot be null"]
        )

    # Coerce plain strings to mul-tagged monolingualtext
    if isinstance(value, str):
        if not value.strip():
            return ValidationResult(
                valid=False,
                value=value,
                errors=["monolingualtext text cannot be empty"],
            )
        warnings.append(
            "Plain string coerced to monolingualtext with language 'mul'; "
            "provide an explicit language code when known"
        )
        coerced = {"language": "mul", "text": value.strip()}
        return ValidationResult(
            valid=True,
            value=coerced,
            warnings=warnings,
            uncertainty=0.5,
            uncertainty_reasons=[
                "language code assumed as 'mul' from plain string input"
            ],
        )

    if not isinstance(value, dict):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[
                f"monolingualtext must be a dict or string, got {type(value).__name__}"
            ],
        )

    # Accept "lang" as an alias for "language"
    if "lang" in value and "language" not in value:
        value = dict(value)
        value["language"] = value.pop("lang")
        warnings.append("Key 'lang' renamed to 'language'")

    if "language" not in value or "text" not in value:
        return ValidationResult(
            valid=False,
            value=value,
            errors=["monolingualtext must have 'language' and 'text' fields"],
        )

    lang_raw = value["language"]
    text_raw = value["text"]

    if not isinstance(lang_raw, str):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"'language' must be a string, got {type(lang_raw).__name__}"],
        )

    if not isinstance(text_raw, str):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"'text' must be a string, got {type(text_raw).__name__}"],
        )

    if not text_raw.strip():
        return ValidationResult(
            valid=False,
            value=value,
            errors=["monolingualtext 'text' cannot be empty"],
        )

    normalized_lang, alias_warnings = _normalize_language_code(lang_raw)
    warnings.extend(alias_warnings)

    lang_errors = _validate_language_code(normalized_lang)
    if lang_errors:
        return ValidationResult(
            valid=False, value=value, errors=lang_errors, warnings=warnings
        )

    normalized = {"language": normalized_lang, "text": text_raw}
    uncertainty = 0.2 if alias_warnings else 0.0
    uncertainty_reasons = (
        [f"language code aliased from '{lang_raw}'"] if alias_warnings else []
    )

    return ValidationResult(
        valid=True,
        value=normalized,
        warnings=warnings,
        uncertainty=uncertainty,
        uncertainty_reasons=uncertainty_reasons,
    )


def validate_url(
    value: Any,
    *,
    validation_policy: ValidationPolicy = ValidationPolicy.STRUCTURE,
    policy_config: Optional[ValidationPolicyConfig] = None,
) -> ValidationResult:
    """Validate a URL value.

    Accepts string URLs. Validates basic URL structure (starts with http:// or https://).
    """
    policy = _resolve_validation_policy_config(validation_policy, policy_config)
    normalized_url, warnings, issues = _coerce_url_candidate(value)
    if not normalized_url:
        return ValidationResult(valid=False, value=value, errors=issues)

    uncertainty_reasons = list(issues) if issues else []
    uncertainty_reasons.extend(
        reason
        for reason in [
            "url_coerced" if warnings else None,
        ]
        if reason
    )

    if policy.policy == ValidationPolicy.STRUCTURE:
        return ValidationResult(
            valid=True,
            value=normalized_url,
            warnings=warnings,
            uncertainty=_uncertainty_score(uncertainty_reasons),
            uncertainty_reasons=uncertainty_reasons,
        )

    retrieval_mode = "head" if policy.policy == ValidationPolicy.HEARTBEAT else "get"
    retrieval = fetch_url_resource(
        normalized_url,
        mode=retrieval_mode,
        timeout=policy.timeout_seconds,
        allow_redirects=policy.allow_redirects,
        accept=policy.request_accept,
    )

    if not retrieval.ok:
        return ValidationResult(
            valid=False,
            value=normalized_url,
            warnings=warnings,
            errors=[
                f"Online URL validation failed for {normalized_url}: {retrieval.error or retrieval.status_code}"
            ],
            uncertainty=1.0,
            uncertainty_reasons=["online_url_lookup_failed"],
        )

    if retrieval.status_code is not None and retrieval.status_code >= 400:
        return ValidationResult(
            valid=False,
            value=normalized_url,
            warnings=warnings,
            errors=[f"Online URL validation received HTTP {retrieval.status_code}"],
            uncertainty=1.0,
            uncertainty_reasons=["online_url_http_error"],
        )

    actionable_warnings = []
    if policy.policy == ValidationPolicy.ACTIONABLE and retrieval.content_type:
        actionable_warnings.append(f"Retrieved content-type: {retrieval.content_type}")

    return ValidationResult(
        valid=True,
        value=normalized_url,
        warnings=warnings + actionable_warnings,
        uncertainty=_uncertainty_score(uncertainty_reasons),
        uncertainty_reasons=uncertainty_reasons,
    )


def validate_time(value: Any) -> ValidationResult:
    """Validate and coerce a time value to full Wikibase time structure.

    Accepts:
    - Full Wikibase time dicts
    - Partial dicts (for example, only ``time``)
    - Component dicts (``year``, ``month``, ``day``)
    - Year integers
    - Date/time strings (``YYYY``, ``YYYY-MM``, ``YYYY-MM-DD``, ``YYYY-MM-DDTHH:MM[:SS]``)
    """
    normalized, warnings, issues = _coerce_time_value(value)
    if not normalized:
        return ValidationResult(valid=False, value=value, errors=issues)

    return ValidationResult(
        valid=True,
        value=normalized,
        warnings=warnings,
        uncertainty=_uncertainty_score(issues),
        uncertainty_reasons=issues,
    )


def validate_quantity(value: Any) -> ValidationResult:
    """Validate a quantity value.

    Expected Wikibase structure:
        {
            "amount": "+123.45",
            "unit": "1",  # or full URI like "http://www.wikidata.org/entity/Q11573"
            "upperBound": "+123.5",
            "lowerBound": "+123.4"
        }
    """
    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["quantity value cannot be null"]
        )

    if not isinstance(value, dict):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"quantity must be a dict, got {type(value).__name__}"],
        )

    required_fields = ["amount", "unit"]
    for field_name in required_fields:
        if field_name not in value:
            return ValidationResult(
                valid=False,
                value=value,
                errors=[f"quantity dict must contain '{field_name}' field"],
            )

    return ValidationResult(valid=True, value=value)


def validate_globe_coordinate(value: Any) -> ValidationResult:
    """Validate and coerce a globe-coordinate value.

    Accepts:
    - Full Wikibase coordinate dicts
    - Dicts with shorthand keys (``lat``/``lon``/``lng``)
    - Coordinate strings (for example, ``"42.5,-121.3"``)
    - DMS-like coordinate strings (for example, ``"42 30 00 N"``)
    - Coordinate sequences ``[latitude, longitude]``
    """
    normalized, warnings, issues = _coerce_globe_coordinate_value(value)
    if not normalized:
        return ValidationResult(valid=False, value=value, errors=issues)

    return ValidationResult(
        valid=True,
        value=normalized,
        warnings=warnings,
        uncertainty=_uncertainty_score(issues),
        uncertainty_reasons=issues,
    )


_COMMONS_FILE_PREFIX = "File:"


def _coerce_commons_filename(value: Any) -> tuple[Optional[str], list[str], list[str]]:
    """Coerce flexible Commons filename inputs to a canonical ``File:``-prefixed form.

    Normalizes:
    - Non-string values (coerced to string with a warning)
    - Missing ``File:`` prefix (added silently — expected omission in data)
    - Spaces normalized to underscores for API consistency

    Returns:
        Tuple of (canonical_filename, warnings, uncertainty_reasons).
        canonical_filename is None when the value cannot be coerced.
    """
    warnings: list[str] = []
    uncertainty_reasons: list[str] = []

    if value is None:
        return None, warnings, ["commonsMedia value cannot be null"]

    if not isinstance(value, str):
        try:
            value = str(value)
            warnings.append(
                f"Coerced {type(value).__name__} to string for commonsMedia"
            )
            uncertainty_reasons.append("filename_type_coerced")
        except Exception:
            return (
                None,
                warnings,
                [f"commonsMedia must be a string, got {type(value).__name__}"],
            )

    filename = value.strip()
    if not filename:
        return None, warnings, ["commonsMedia filename cannot be empty"]

    if filename.startswith("File:"):
        canonical = filename
    elif filename.startswith("file:"):
        canonical = _COMMONS_FILE_PREFIX + filename[5:]
        warnings.append("Normalized lowercase 'file:' prefix to 'File:'")
        uncertainty_reasons.append("filename_prefix_normalized")
    else:
        canonical = _COMMONS_FILE_PREFIX + filename

    return canonical, warnings, uncertainty_reasons


def validate_commons_media(
    value: Any,
    *,
    validation_policy: ValidationPolicy = ValidationPolicy.STRUCTURE,
    policy_config: Optional[ValidationPolicyConfig] = None,
) -> ValidationResult:
    """Validate a commonsMedia value against Wikimedia Commons.

    Accepts a string representing a Wikimedia Commons filename, with or without
    the ``File:`` prefix.

    - STRUCTURE: structural coercion and format check only (offline)
    - HEARTBEAT: confirms the file exists on Commons via the MediaWiki API
    - ACTIONABLE: retrieves full file metadata (MIME type, size, SHA-1, resource URL)
    """
    policy = _resolve_validation_policy_config(validation_policy, policy_config)
    canonical, warnings, issues = _coerce_commons_filename(value)
    if not canonical:
        return ValidationResult(valid=False, value=value, errors=issues)

    uncertainty_reasons = list(issues) if issues else []

    if policy.policy == ValidationPolicy.STRUCTURE:
        return ValidationResult(
            valid=True,
            value=canonical,
            warnings=warnings,
            uncertainty=_uncertainty_score(uncertainty_reasons),
            uncertainty_reasons=uncertainty_reasons,
        )

    fetch_mode = (
        "heartbeat" if policy.policy == ValidationPolicy.HEARTBEAT else "actionable"
    )
    try:
        client = WikibaseApiClient(
            api_url=policy.commons_api_url,
            timeout=policy.timeout_seconds,
        )
        result = fetch_commons_file_info(client, canonical, mode=fetch_mode)
    except Exception as exc:
        return ValidationResult(
            valid=False,
            value=canonical,
            warnings=warnings,
            errors=[f"Online Commons validation failed for {canonical}: {exc}"],
            uncertainty=1.0,
            uncertainty_reasons=["online_commons_lookup_failed"],
        )

    if not result.ok or not result.exists:
        return ValidationResult(
            valid=False,
            value=canonical,
            warnings=warnings,
            errors=[result.error or f"File not found on Commons: {canonical}"],
            uncertainty=1.0,
            uncertainty_reasons=["online_commons_lookup_failed"],
        )

    actionable_warnings: list[str] = []
    if policy.policy == ValidationPolicy.ACTIONABLE:
        if result.resource_url:
            actionable_warnings.append(f"Commons resource URL: {result.resource_url}")
        if result.mime_type:
            actionable_warnings.append(f"Commons MIME type: {result.mime_type}")
        if result.size is not None:
            actionable_warnings.append(f"Commons file size: {result.size} bytes")

    return ValidationResult(
        valid=True,
        value=canonical,
        warnings=warnings + actionable_warnings,
        uncertainty=_uncertainty_score(uncertainty_reasons),
        uncertainty_reasons=uncertainty_reasons,
    )


_SPECIAL_DATATYPE_VALIDATORS = {
    "wikibase-item": validate_wikibase_item,
    "monolingualtext": validate_monolingualtext,
    "url": validate_url,
    "time": validate_time,
    "quantity": validate_quantity,
    "globe-coordinate": validate_globe_coordinate,
    "commonsMedia": validate_commons_media,
}


def validate_by_datatype(
    datatype: str,
    value: Any,
    *,
    validation_policy: ValidationPolicy = ValidationPolicy.STRUCTURE,
    policy_config: Optional[ValidationPolicyConfig] = None,
) -> ValidationResult:
    """Dispatch validation to the appropriate datatype validator."""
    try:
        canonical_datatype = canonicalize_wikibase_datatype(datatype, strict=True)
    except (AttributeError, KeyError):
        return ValidationResult(
            valid=False, value=value, errors=[f"Unknown datatype: {datatype}"]
        )

    validator = _SPECIAL_DATATYPE_VALIDATORS.get(canonical_datatype)
    if validator is None:
        spec = get_wikibase_datatype_spec(canonical_datatype)
        if spec.datavalue_type == "string":
            validator = validate_string

    if validator is None:
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"No validator registered for datatype: {canonical_datatype}"],
        )

    if canonical_datatype in {"wikibase-item", "url", "commonsMedia"}:
        return validator(
            value,
            validation_policy=validation_policy,
            policy_config=policy_config,
        )
    return validator(value)


# ============================================================================
# Value list cache validator
# ============================================================================


def _normalize_item_to_uri(value: Any) -> Optional[str]:
    """Normalize an item value to a full Wikidata entity URI.

    Supports:
    - Full URI string: "http://www.wikidata.org/entity/Q12345"
    - Wizard dict with "item" key: {"item": "<full URI>", "itemLabel": "..."}
    - Wikibase dict with "id" key: {"id": "Q12345", ...}
    - Bare QID string: "Q12345"
    """
    if isinstance(value, str):
        if value.startswith("http://") or value.startswith("https://"):
            return value
        if value.startswith("Q") and value[1:].isdigit():
            return f"http://www.wikidata.org/entity/{value}"
    if isinstance(value, dict):
        # Wizard format: {"item": "<full URI>", "itemLabel": "..."}
        item_field = value.get("item")
        if isinstance(item_field, str):
            return _normalize_item_to_uri(item_field)
        # Wikibase snakvalue format: {"id": "Q12345", ...}
        id_field = value.get("id")
        if isinstance(id_field, str):
            return _normalize_item_to_uri(id_field)
    return None


def _extract_cache_uris_and_labels(
    cache_data: dict,
) -> tuple[set[str], list[tuple[str, str]]]:
    """Extract item URIs and (uri, label) pairs from a SpiritSafe cache artifact.

    Supports both formats:
    - SpiritSafe items format: {"items": [{"item": "<uri>", "itemLabel": "<label>"}]}
    - Raw SPARQL bindings format: {"results": {"bindings": [{"item": {"value": "<uri>"}, ...}]}}
    """
    uris: set[str] = set()
    uri_labels: list[tuple[str, str]] = []

    # SpiritSafe materialized items format
    for entry in cache_data.get("items", []):
        if not isinstance(entry, dict):
            continue
        uri = entry.get("item", "")
        if isinstance(uri, str) and uri:
            uris.add(uri)
            label = entry.get("itemLabel", "")
            if isinstance(label, str) and label:
                uri_labels.append((uri, label.lower()))

    # Raw SPARQL results-bindings format (hydration pipeline intermediate)
    for binding in cache_data.get("results", {}).get("bindings", []):
        if not isinstance(binding, dict):
            continue
        item_node = binding.get("item")
        if isinstance(item_node, dict):
            uri = item_node.get("value", "")
            if isinstance(uri, str) and uri:
                uris.add(uri)
                label_node = binding.get("itemLabel", {})
                label = (
                    label_node.get("value", "") if isinstance(label_node, dict) else ""
                )
                if label:
                    uri_labels.append((uri, label.lower()))

    return uris, uri_labels


def validate_value_from_list(
    value: Any, value_list_path: Path, match_policy: str = "strict"
) -> ValidationResult:
    """Validate a candidate item value against a cached value list.

    Args:
        value: The item value to validate. Accepts:
            - Full Wikidata URI string: "http://www.wikidata.org/entity/Q12345"
            - Wizard dict: {"item": "<full URI>", "itemLabel": "..."}
            - Wikibase snakvalue dict: {"id": "Q12345", ...}
            - Bare QID string: "Q12345"
        value_list_path: Path to the cached value list JSON file.
        match_policy: "strict" (URI/QID exact match) or "fuzzy" (label match fallback).

    Returns:
        ValidationResult with valid=True if value is in the list, False otherwise.

    If the value is empty/None, returns valid=True with no errors (unentered fields
    are not a validation error at this layer; presence requirements are enforced
    upstream by the packet validation logic).

    If the cache file is absent, returns a ValidationResult with an error rather
    than attempting live resolution (offline-first design).
    """
    # Empty/unentered values pass through — presence enforcement is handled upstream.
    if value in (None, "", {}, []):
        return ValidationResult(valid=True, value=value)

    if not value_list_path.exists():
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"Value list cache unavailable: {value_list_path}"],
        )

    try:
        cache_data = json.loads(value_list_path.read_text())
    except Exception as e:
        return ValidationResult(
            valid=False, value=value, errors=[f"Failed to load value list cache: {e}"]
        )

    target_uri = _normalize_item_to_uri(value)
    if target_uri is None:
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"Cannot normalize value to item URI for list matching: {value!r}"],
        )

    cache_uris, uri_labels = _extract_cache_uris_and_labels(cache_data)

    if target_uri in cache_uris:
        return ValidationResult(valid=True, value=value)

    if match_policy == "fuzzy":
        # Fuzzy: check if any cache label matches a label on the incoming value
        target_label = None
        if isinstance(value, dict):
            raw_label = value.get("itemLabel") or value.get("label")
            if isinstance(raw_label, str):
                target_label = raw_label.lower()

        if target_label:
            for _uri, cached_label in uri_labels:
                if cached_label == target_label:
                    return ValidationResult(valid=True, value=value)

    return ValidationResult(
        valid=False,
        value=value,
        errors=[f"Value {target_uri} not found in value list"],
    )


# ============================================================================
# Fixed value enforcement
# ============================================================================


def enforce_fixed_value(
    user_value: Any, fixed_value: Any, statement_ref: str
) -> tuple[ValidationResult, ConformanceNotice]:
    """Enforce a fixed value constraint on a statement.

    Args:
        user_value: The value supplied by the user (may be None)
        fixed_value: The required fixed value from the profile
        statement_ref: URI reference to the statement (for notice generation)

    Returns:
        (ValidationResult, ConformanceNotice) tuple.
        - If user supplies None: inject fixed_value, emit info notice
        - If user supplies matching value: accept
        - If user supplies different value: reject with error notice
    """
    if user_value is None:
        # Inject the fixed value
        notice = ConformanceNotice(
            severity="info",
            entity_ref="",  # Will be filled in by caller
            statement_ref=statement_ref,
            code="fixed_value_injected",
            message="Value populated from profile fixed value",
            normalized_value=fixed_value,
        )
        return ValidationResult(valid=True, value=fixed_value), notice

    # Check if values match
    if _values_equal(user_value, fixed_value):
        return ValidationResult(valid=True, value=fixed_value), None

    # Values don't match
    notice = ConformanceNotice(
        severity="error",
        entity_ref="",  # Will be filled in by caller
        statement_ref=statement_ref,
        code="fixed_value_violation",
        message=f"User value does not match required fixed value. Expected: {fixed_value}, got: {user_value}",
    )
    return (
        ValidationResult(valid=False, value=user_value, errors=[notice.message]),
        notice,
    )


def _values_equal(val1: Any, val2: Any) -> bool:
    """Check equality between two values, handling Wikibase structures."""
    if val1 == val2:
        return True

    # Normalize Wikibase item-like values to canonical URI when possible.
    # This aligns profile-side wizard item dicts ({"item": ...}) with
    # Wikidata claim-side snakvalue dicts ({"id": ...}) and QID/URI strings.
    uri1 = _normalize_item_to_uri(val1)
    uri2 = _normalize_item_to_uri(val2)
    if uri1 is not None and uri2 is not None:
        return uri1 == uri2

    # Special handling for wikibase-item dicts
    if isinstance(val1, dict) and isinstance(val2, dict):
        if "id" in val1 and "id" in val2:
            return val1["id"] == val2["id"]

    # Handle string QID vs dict comparison
    if isinstance(val1, str) and val1.startswith("Q") and isinstance(val2, dict):
        return val1 == val2.get("id")
    if isinstance(val2, str) and val2.startswith("Q") and isinstance(val1, dict):
        return val2 == val1.get("id")

    return False
