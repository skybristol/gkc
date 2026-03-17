# Fermenter API

## Overview

The `gkc.fermenter` module is the atomic validation and coercion layer for GKC curation pipelines.
It validates and normalizes individual values against profile-defined constraints.
Both the still charger and the cooperage/barrel layer consume it, and all wizard and CLI pipelines share its output envelope.

All validation surfaces return a `ConformanceNotice` (or internal `ValidationResult`) for consistent error reporting across wizard, CLI, and bulk pipelines.

## `ConformanceNotice`

Shared result envelope for all validation and coercion operations.

```python
from gkc.fermenter import ConformanceNotice

notice = ConformanceNotice(
    severity="error",
    entity_ref="https://datadistillery.wikibase.cloud/entity/Q4",
    code="fixed_value_violation",
    message="Statement requires fixed value Q7840353 but received Q9592",
    statement_ref="https://datadistillery.wikibase.cloud/entity/P5",
    normalized_value=None,
)
```

**Fields:**

| Field | Type | Description |
|---|---|---|
| `severity` | `str` | `"error"`, `"warning"`, or `"info"` |
| `entity_ref` | `str` | Full URI or intra-packet entity ID |
| `code` | `str` | Short machine-readable code (e.g., `fixed_value_violation`) |
| `message` | `str` | Human-readable description |
| `statement_ref` | `str \| None` | Statement entity URI, or `None` for entity-level notices |
| `normalized_value` | `Any` | Coerced output if coercion succeeded, `None` otherwise |

`ChargeIssue` and `BarrelIssue` are aliases for `ConformanceNotice` (transition compatibility).

## Datatype Validators

Each validator accepts a raw value and returns an internal `ValidationResult` with `valid`, `value`, `errors`, and `warnings` fields. Use `validate_by_datatype()` as the primary dispatcher.

### `validate_by_datatype(datatype, value)`

Dispatch to the appropriate validator based on the Wikibase primitive datatype string.

```python
from gkc.fermenter import validate_by_datatype

result = validate_by_datatype("wikibase-item", "Q195562")
print(result.valid)   # True
print(result.value)   # {"entity-type": "item", "numeric-id": 195562, "id": "Q195562"}

result = validate_by_datatype("url", "not-a-url")
print(result.valid)   # False
print(result.errors)  # ["url must start with http:// or https://"]
```

Supported datatypes: `wikibase-item`, `string`, `monolingualtext`, `url`, `time`, `quantity`, `globe-coordinate`, `commonsMedia`.

Returns a `ValidationResult(valid=False, ...)` with an error message for unrecognized datatypes.

---

### `validate_wikibase_item(value)`

Validates a Wikibase item reference. Accepts a QID string (coerces to full Wikibase JSON) or a dict already containing an `"id"` key.

```python
from gkc.fermenter import validate_wikibase_item

# From QID string
result = validate_wikibase_item("Q195562")
# result.value → {"entity-type": "item", "numeric-id": 195562, "id": "Q195562"}

# From existing Wikibase dict
result = validate_wikibase_item({"entity-type": "item", "id": "Q195562"})
# result.valid → True
```

---

### `validate_string(value)`

Validates a plain string value. Coerces non-string values to string where possible and emits a warning.

```python
from gkc.fermenter import validate_string

result = validate_string("Cherokee Nation")
# result.valid → True, result.value → "Cherokee Nation"

result = validate_string(12345)
# result.valid → True, result.value → "12345", result.warnings → ["Coerced int to string"]
```

---

### `validate_monolingualtext(value)`

Validates a monolingual text dict. Requires both `"language"` and `"text"` string fields.

```python
from gkc.fermenter import validate_monolingualtext

result = validate_monolingualtext({"language": "en", "text": "Cherokee Nation"})
# result.valid → True
```

---

### `validate_url(value)`

Validates a URL string. Must start with `http://` or `https://`.

```python
from gkc.fermenter import validate_url

result = validate_url("https://www.cherokee.org")
# result.valid → True

result = validate_url("www.cherokee.org")
# result.valid → False
```

---

### `validate_time(value)`

Validates a Wikibase time dict. Requires `time`, `timezone`, `before`, `after`, and `calendarmodel` fields.

```python
from gkc.fermenter import validate_time

result = validate_time({
    "time": "+2020-01-15T00:00:00Z",
    "timezone": 0,
    "before": 0,
    "after": 0,
    "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
})
# result.valid → True
```

---

### `validate_quantity(value)`

Validates a Wikibase quantity dict. Requires `amount` and `unit` fields.

```python
from gkc.fermenter import validate_quantity

result = validate_quantity({
    "amount": "+3500",
    "unit": "http://www.wikidata.org/entity/Q11573",
})
# result.valid → True
```

---

### `validate_globe_coordinate(value)`

Validates a globe-coordinate dict. Requires `latitude`, `longitude`, `precision`, and `globe` fields.
Latitude must be in `[-90, 90]` and longitude in `[-180, 180]`.

```python
from gkc.fermenter import validate_globe_coordinate

result = validate_globe_coordinate({
    "latitude": 35.5,
    "longitude": -95.0,
    "altitude": None,
    "precision": 0.0001,
    "globe": "http://www.wikidata.org/entity/Q2",
})
# result.valid → True
```

---

### `validate_commons_media(value)`

Validates a Wikimedia Commons filename string. Must be a non-empty string.

```python
from gkc.fermenter import validate_commons_media

result = validate_commons_media("Cherokee Nation seal.svg")
# result.valid → True
```

---

## Value List Validation

### `validate_value_from_list(value, value_list_path, match_policy)`

Validate a candidate item value against a cached value list JSON file.
Follows an offline-first design: if the cache file is absent, returns an error rather than attempting live resolution.

```python
from pathlib import Path
from gkc.fermenter import validate_value_from_list

result = validate_value_from_list(
    value="Q195562",
    value_list_path=Path("/path/to/SpiritSafe/cache/queries/Q4.json"),
    match_policy="strict",
)
print(result.valid)   # True if Q195562 is in the cached list

# With fuzzy label matching
result = validate_value_from_list(
    value={"id": "Q195562", "label": "Cherokee Nation"},
    value_list_path=Path("/path/to/SpiritSafe/cache/queries/Q4.json"),
    match_policy="fuzzy",
)
```

**Arguments:**

| Argument | Type | Description |
|---|---|---|
| `value` | `Any` | A QID string or dict with an `"id"` key |
| `value_list_path` | `Path` | Path to the cached value list JSON file |
| `match_policy` | `str` | `"strict"` (QID exact match) or `"fuzzy"` (label fallback) |

Returns `ValidationResult(valid=False, errors=["Value list cache unavailable: ..."])` when the cache file does not exist.

---

## Fixed Value Enforcement

### `enforce_fixed_value(user_value, fixed_value, statement_ref)`

Enforce a profile-defined fixed value constraint on a statement.

- If `user_value` is `None` — injects the fixed value and emits an `info` notice
- If `user_value` matches `fixed_value` — accepts
- If `user_value` differs — rejects with an `error` notice

```python
from gkc.fermenter import enforce_fixed_value

# Auto-injection when user provides nothing
result, notice = enforce_fixed_value(
    user_value=None,
    fixed_value="Q7840353",
    statement_ref="https://datadistillery.wikibase.cloud/entity/P5",
)
# result.valid → True, result.value → "Q7840353"
# notice.code → "fixed_value_injected"

# Violation
result, notice = enforce_fixed_value(
    user_value="Q9592",
    fixed_value="Q7840353",
    statement_ref="https://datadistillery.wikibase.cloud/entity/P5",
)
# result.valid → False
# notice.severity → "error", notice.code → "fixed_value_violation"
```

Returns `(ValidationResult, ConformanceNotice | None)`. The notice is `None` when the user value matches the required fixed value exactly.
