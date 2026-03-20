"""
Fermenter: Validation and coercion layer for GKC curation pipelines.

The fermenter is the atomic validation and coercion layer. It does not assemble packets
or coordinate pipelines — it validates and normalizes individual values against
profile-defined constraints. Both the still charger and the write-planning layer consume it.

All validation surfaces return a shared ConformanceNotice envelope for consistent error
reporting across wizard, CLI, and bulk pipelines.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


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


# ============================================================================
# Wikibase datatype validators (all 8 primitive types)
# ============================================================================


def validate_wikibase_item(value: Any) -> ValidationResult:
    """Validate a wikibase-item value.

    Expected Wikibase JSON structure:
        {"entity-type": "item", "numeric-id": 123, "id": "Q123"}

    Accepts either a dict matching the structure above or a QID string (will coerce).
    """
    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["wikibase-item value cannot be null"]
        )

    # If it's already a dict, validate structure
    if isinstance(value, dict):
        if (
            "id" in value
            and isinstance(value["id"], str)
            and value["id"].startswith("Q")
        ):
            normalized = {
                "entity-type": "item",
                "numeric-id": (
                    int(value["id"][1:]) if value["id"][1:].isdigit() else None
                ),
                "id": value["id"],
            }
            return ValidationResult(valid=True, value=normalized)
        return ValidationResult(
            valid=False,
            value=value,
            errors=["wikibase-item dict must contain 'id' field with Q-prefixed QID"],
        )

    # If it's a string, treat as QID
    if isinstance(value, str):
        if value.startswith("Q") and value[1:].isdigit():
            return ValidationResult(
                valid=True,
                value={
                    "entity-type": "item",
                    "numeric-id": int(value[1:]),
                    "id": value,
                },
            )
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"Invalid QID format: {value}. Expected Q-prefixed numeric ID."],
        )

    return ValidationResult(
        valid=False,
        value=value,
        errors=[f"wikibase-item must be a dict or string, got {type(value).__name__}"],
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


def validate_monolingualtext(value: Any) -> ValidationResult:
    """Validate a monolingualtext value.

    Expected structure:
        {"language": "en", "text": "English text"}
    """
    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["monolingualtext value cannot be null"]
        )

    if not isinstance(value, dict):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"monolingualtext must be a dict, got {type(value).__name__}"],
        )

    if "language" not in value or "text" not in value:
        return ValidationResult(
            valid=False,
            value=value,
            errors=["monolingualtext must have 'language' and 'text' fields"],
        )

    if not isinstance(value["language"], str) or not isinstance(value["text"], str):
        return ValidationResult(
            valid=False,
            value=value,
            errors=["'language' and 'text' fields must be strings"],
        )

    return ValidationResult(valid=True, value=value)


def validate_url(value: Any) -> ValidationResult:
    """Validate a URL value.

    Accepts string URLs. Validates basic URL structure (starts with http:// or https://).
    """
    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["url value cannot be null"]
        )

    if not isinstance(value, str):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"url must be a string, got {type(value).__name__}"],
        )

    # Basic URL validation
    if not (value.startswith("http://") or value.startswith("https://")):
        return ValidationResult(
            valid=False, value=value, errors=["url must start with http:// or https://"]
        )

    return ValidationResult(valid=True, value=value)


def validate_time(value: Any) -> ValidationResult:
    """Validate a time value.

    Expected Wikibase structure:
        {
            "time": "+2020-01-15T00:00:00Z",
            "timezone": 0,
            "before": 0,
            "after": 0,
            "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
        }
    """
    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["time value cannot be null"]
        )

    if not isinstance(value, dict):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"time must be a dict, got {type(value).__name__}"],
        )

    required_fields = ["time", "timezone", "before", "after", "calendarmodel"]
    for field_name in required_fields:
        if field_name not in value:
            return ValidationResult(
                valid=False,
                value=value,
                errors=[f"time dict must contain '{field_name}' field"],
            )

    return ValidationResult(valid=True, value=value)


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
    """Validate a globe-coordinate value.

    Expected Wikibase structure:
        {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "altitude": None,
            "precision": 0.0001,
            "globe": "http://www.wikidata.org/entity/Q2"  # Earth
        }
    """
    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["globe-coordinate value cannot be null"]
        )

    if not isinstance(value, dict):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"globe-coordinate must be a dict, got {type(value).__name__}"],
        )

    required_fields = ["latitude", "longitude", "precision", "globe"]
    for field_name in required_fields:
        if field_name not in value:
            return ValidationResult(
                valid=False,
                value=value,
                errors=[f"globe-coordinate dict must contain '{field_name}' field"],
            )

    # Validate lat/long ranges
    lat = value.get("latitude")
    lon = value.get("longitude")

    if not isinstance(lat, (int, float)) or not (-90 <= lat <= 90):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"latitude must be between -90 and 90, got {lat}"],
        )

    if not isinstance(lon, (int, float)) or not (-180 <= lon <= 180):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"longitude must be between -180 and 180, got {lon}"],
        )

    return ValidationResult(valid=True, value=value)


def validate_commons_media(value: Any) -> ValidationResult:
    """Validate a commonsMedia value.

    Accepts a string representing a Wikimedia Commons filename.
    """
    if value is None:
        return ValidationResult(
            valid=False, value=None, errors=["commonsMedia value cannot be null"]
        )

    if not isinstance(value, str):
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"commonsMedia must be a string, got {type(value).__name__}"],
        )

    if not value.strip():
        return ValidationResult(
            valid=False, value=value, errors=["commonsMedia filename cannot be empty"]
        )

    return ValidationResult(valid=True, value=value)


# Dispatcher for datatype validators
_DATATYPE_VALIDATORS = {
    "wikibase-item": validate_wikibase_item,
    "string": validate_string,
    "monolingualtext": validate_monolingualtext,
    "url": validate_url,
    "time": validate_time,
    "quantity": validate_quantity,
    "globe-coordinate": validate_globe_coordinate,
    "commonsMedia": validate_commons_media,
}


def validate_by_datatype(datatype: str, value: Any) -> ValidationResult:
    """Dispatch validation to the appropriate datatype validator."""
    validator = _DATATYPE_VALIDATORS.get(datatype)
    if not validator:
        return ValidationResult(
            valid=False, value=value, errors=[f"Unknown datatype: {datatype}"]
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
