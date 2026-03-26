# Fermenter API

## Overview

The `gkc.fermenter` module is the atomic validation and coercion layer for GKC curation pipelines.
It validates and normalizes individual values against profile-defined constraints.
Both the still charger and the Wikibase write-planning layer consume it, and all wizard and CLI pipelines share its output envelope.

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

### Validation Policy (Structure + Online Tiers)

`validate_wikibase_item()`, `validate_url()`, and `validate_commons_media()` support staged validation through `ValidationPolicy`.

```python
from gkc.fermenter import ValidationPolicy, ValidationPolicyConfig

policy = ValidationPolicy.HEARTBEAT
config = ValidationPolicyConfig(
    wikibase_api_url="https://www.wikidata.org/w/api.php",
    commons_api_url="https://commons.wikimedia.org/w/api.php",
    timeout_seconds=10,
)
```

Tiers:

- `STRUCTURE`: shape and coercion checks only (default, offline)
- `HEARTBEAT`: online resource responds to a basic alive check
- `ACTIONABLE`: online resource can be retrieved for intended interaction context

`ValidationPolicyConfig` accepts `commons_api_url` to redirect Commons checks to an alternate MediaWiki API (useful for testing or alternative Commons deployments).

`ValidationResult` now includes uncertainty metadata:

- `uncertainty`: float in `[0.0, 1.0]`
- `uncertainty_reasons`: list of machine-readable uncertainty causes

This supports curator-facing decision paths where coercion and online checks are successful but confidence is not maximal.

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

# From full entity URI (coerced to QID)
result = validate_wikibase_item("https://www.wikidata.org/entity/Q195562")
# result.valid → True, result.value["id"] → "Q195562"

# Online validation against custom Wikibase instance
config = ValidationPolicyConfig(
    wikibase_api_url="https://datadistillery.wikibase.cloud/w/api.php",
)
result = validate_wikibase_item(
    "Q195562",
    validation_policy=ValidationPolicy.HEARTBEAT,
    policy_config=config,
)
```

Notes:

- Coercion accepts QIDs, full entity URIs, and dict references with `id` or `item` fields.
- Normalized output includes `wikibase-api-url` so downstream logic can preserve instance context.

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

### `validate_with_pattern(value, pattern, *, flags=0)`

Validates a string-like value against a regex pattern sourced from profile or statement constraints.

This validator first applies `validate_string()` and then checks the normalized value with
`re.search`, so profile-authored patterns can control whether matching is anchored or partial.

```python
import re
from gkc.fermenter import validate_with_pattern

result = validate_with_pattern("AB-1234", r"^[A-Z]{2}-\d{4}$")
# result.valid -> True

result = validate_with_pattern(2024, r"^2024$")
# result.valid -> True
# result.value -> "2024"

result = validate_with_pattern(
    "cherokee nation",
    r"CHEROKEE",
    flags=re.IGNORECASE,
)
# result.valid -> True

result = validate_with_pattern("invalid", r"^[A-Z]{2}-\d{4}$")
# result.valid -> False
# result.errors -> ["String does not match required pattern: ^[A-Z]{2}-\\d{4}$"]
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
# result.valid → True (coerced to https://www.cherokee.org)

# HEARTBEAT online check
result = validate_url(
    "https://www.cherokee.org",
    validation_policy=ValidationPolicy.HEARTBEAT,
)
# Performs HEAD request through mash.fetch_url_resource

# ACTIONABLE online check with content retrieval
config = ValidationPolicyConfig(
    request_accept="text/html,application/xhtml+xml",
)
result = validate_url(
    "https://www.cherokee.org",
    validation_policy=ValidationPolicy.ACTIONABLE,
    policy_config=config,
)
# Performs GET request and records content-type warning metadata
```

Coercion accepts a wider input set while preserving uncertainty signals:

- `www.example.org` → `https://www.example.org`
- `example.org/resource` → `https://example.org/resource`

---

### `validate_time(value)`

Validates and coerces user-style time inputs into a full Wikibase time payload.

Accepted input shapes include:

- Full Wikibase dict (`time`, `timezone`, `before`, `after`, `calendarmodel`)
- Minimal dict with only `time`
- Component dict (`year`, optional `month`/`day`/`hour`/`minute`/`second`)
- Year integer (`2024`)
- Date/time strings (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-MM-DDTHH:MM[:SS]`)

```python
from gkc.fermenter import validate_time

result = validate_time("2024")
# result.value -> {
#   "time": "+2024-01-01T00:00:00Z",
#   "timezone": 0,
#   "before": 0,
#   "after": 0,
#   "precision": 9,
#   "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
# }

result = validate_time("2024-05")
# precision derived from granularity -> 10 (month)

result = validate_time({"year": 2024, "month": 5, "day": 6})
# precision derived from provided components -> 11 (day)

result = validate_time({"time": "+2020-01-15T00:00:00Z"})
# missing timezone/before/after/calendarmodel auto-filled

# Full explicit dict still supported
result = validate_time({
    "time": "+2020-01-15T00:00:00Z",
    "timezone": 0,
    "before": 0,
    "after": 0,
    "precision": 11,
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

Validates and coerces broad coordinate input forms into Wikibase globe-coordinate payloads.

Accepted input shapes include:

- Full coordinate dict (`latitude`, `longitude`, optional `altitude`, optional `precision`, optional `globe`)
- Shorthand dict keys (`lat`/`lon`/`lng`)
- String pair (`"42.1234,-121.5000"`)
- Sequence pair (`[42.1234, -121.5]`)
- DMS-style coordinate strings (`"42 30 0 N"`, `"121 30 0 W"`)

If `precision` is omitted, it is derived from input granularity (decimal places or DMS resolution).
Latitude must be in `[-90, 90]` and longitude in `[-180, 180]` after coercion.

```python
from gkc.fermenter import validate_globe_coordinate

result = validate_globe_coordinate("42.1234,-121.5000")
# precision derived from decimal granularity

result = validate_globe_coordinate({"lat": "42.5", "lng": "-121.25"})
# shorthand keys normalized to latitude/longitude

result = validate_globe_coordinate({
    "latitude": "42 30 0 N",
    "longitude": "121 30 0 W",
})
# DMS input converted to decimal degrees

# Full explicit dict remains supported
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

Validates a Wikimedia Commons filename against the Commons MediaWiki API.
Accepts filenames with or without the `File:` prefix—the canonical form is always returned.

```python
from gkc.fermenter import validate_commons_media, ValidationPolicy, ValidationPolicyConfig

# STRUCTURE (default, offline) — normalizes filename only
result = validate_commons_media("Cherokee Nation seal.svg")
# result.valid → True
# result.value → "File:Cherokee Nation seal.svg"

# HEARTBEAT — confirms the file exists on Commons
result = validate_commons_media(
    "Cherokee Nation seal.svg",
    validation_policy=ValidationPolicy.HEARTBEAT,
)
# Calls Commons API action=query&prop=imageinfo for the file
# result.valid → False + error if the file is not found

# ACTIONABLE — retrieves full file metadata
result = validate_commons_media(
    "File:Cherokee Nation seal.svg",
    validation_policy=ValidationPolicy.ACTIONABLE,
)
# result.warnings may include:
#   "Commons resource URL: https://upload.wikimedia.org/..."
#   "Commons MIME type: image/svg+xml"
#   "Commons file size: 12345 bytes"

# Custom Commons API endpoint (e.g., for testing)
config = ValidationPolicyConfig(
    commons_api_url="https://test.commons.example.org/w/api.php",
)
result = validate_commons_media(
    "File:Example.jpg",
    validation_policy=ValidationPolicy.HEARTBEAT,
    policy_config=config,
)
```

Coercion behavior:

- Filenames without `File:` prefix receive it automatically.
- Lowercase `file:` prefix is normalized to `File:` with a warning.
- Non-string values are coerced to string with a warning and uncertainty signal.

Online checks use `gkc.mash.fetch_commons_file_info()` via a `WikibaseApiClient` pointed at
`commons_api_url`, keeping the retrieval layer consistent with other Wikibase API consumers in mash.

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

## Conformance Outcome Types

Fermenter now provides explicit conformance outcome types for statement- and entity-level evaluation.

### `ConformanceOutcome`

```python
from gkc.fermenter import ConformanceOutcome

print(ConformanceOutcome.CONFORMANT.value)              # "conformant"
print(ConformanceOutcome.NON_CONFORMANT_MAPPABLE.value) # "non_conformant_mappable"
print(ConformanceOutcome.TO_BE_DEFINED.value)           # "to_be_defined"
print(ConformanceOutcome.MISSING.value)                 # "missing"
```

### `StatementEvaluation`

Atomic statement evaluation envelope:

| Field | Type | Description |
|---|---|---|
| `outcome` | `ConformanceOutcome` | Classification of statement evaluation result |
| `statement_ref` | `str \| None` | Statement id/entity/name_identifier reference |
| `property_ref` | `str \| None` | Mapped property identifier (for example, PID) |
| `normalized_value` | `Any` | Normalized/coerced value payload |
| `raw_claims` | `list[dict]` | Original inbound claim objects used for evaluation |
| `notices` | `list[ConformanceNotice]` | Statement-scoped notices emitted during evaluation |

### `EntityEvaluation`

Aggregate entity envelope with outcome buckets:

| Field | Type | Description |
|---|---|---|
| `entity_ref` | `str` | Entity being evaluated |
| `profile_ref` | `str` | Active profile reference |
| `conformant` | `list[StatementEvaluation]` | Statements that conform to profile rules |
| `non_conformant_mappable` | `list[StatementEvaluation]` | Recognized statements with retained non-conforming values |
| `to_be_defined` | `list[StatementEvaluation]` | Statements present in source but not defined by profile |
| `missing` | `list[StatementEvaluation]` | Statements expected by profile but absent in input |

Convenience properties:

- `all_notices` returns a flattened list of notices across all buckets.
- `is_conformant` is `True` only when both `non_conformant_mappable` and `missing` are empty.

## Statement and Entity Evaluation

### `normalize_claim_value(raw_claim, data_type)`

Normalizes a raw claim payload and dispatches validation through datatype validators.

- Handles `snaktype=novalue` and `snaktype=somevalue` safely.
- Returns `ValidationResult` with normalized value, warnings, and errors.

```python
from gkc.fermenter import normalize_claim_value

raw_claim = {
    "mainsnak": {
        "snaktype": "value",
        "datavalue": {
            "value": {
                "entity-type": "item",
                "numeric-id": 5,
                "id": "Q5",
            }
        },
    }
}

result = normalize_claim_value(raw_claim, "wikibase-item")
print(result.valid)          # True
print(result.value["id"])    # Q5
```

### `evaluate_statement_claim(profile_statement, raw_claim_list, *, entity_ref="", value_list_root=None)`

Evaluates one profile statement against claim candidates and profile constraints.

Checks include:

- required/missing evaluation
- datatype normalization
- fixed-value enforcement
- value-list cache validation
- max-count handling

```python
from gkc.fermenter import evaluate_statement_claim

statement = {
    "id": "https://datadistillery.wikibase.cloud/entity/Q16",
    "max_count": 1,
    "value": {"type": "wikibase-item"},
    "io_map": [{"to": "http://www.wikidata.org/entity/P31"}],
}

claims = [{
    "mainsnak": {
        "snaktype": "value",
        "datavalue": {"value": {"entity-type": "item", "numeric-id": 5, "id": "Q5"}},
    }
}]

evaluation = evaluate_statement_claim(statement, claims, entity_ref="Q195562")
print(evaluation.outcome.value)  # "conformant"
```

### `evaluate_entity(profile_statements, wikidata_item, *, io_map_index, entity_ref="", value_list_root=None)`

Evaluates one source entity against all active profile statements and classifies output into the four conformance buckets.

```python
from gkc.fermenter import evaluate_entity

entity_eval = evaluate_entity(
    profile_statements=[...],
    wikidata_item={"id": "Q195562", "claims": {...}},
    io_map_index={"P31": {...}, "P17": {...}},
    entity_ref="Q195562",
)

print(len(entity_eval.conformant))
print(len(entity_eval.non_conformant_mappable))
print(len(entity_eval.to_be_defined))
print(len(entity_eval.missing))
```

## Packet Integrity and Validation Entry Points

### `check_packet_integrity(packet)`

Verifies metadata digest integrity before any data validation.

- Returns `None` when digest is valid.
- Returns an `error` `ConformanceNotice` on missing metadata integrity fields or digest mismatch.

```python
import hashlib
import json
from gkc.fermenter import check_packet_integrity

metadata = {
    "primary_profile": {"id": "https://datadistillery.wikibase.cloud/entity/Q4"},
    "profiles": [],
    "graph": {"nodes": [], "edges": []},
    "mint": {"minted_at": "2026-03-26T00:00:00Z", "generator": "example"},
}
digest = hashlib.sha256(
    json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()

packet = {
    "packet_id": "pkt-example",
    "metadata": {
        **metadata,
        "integrity": {
            "metadata_canonicalization": "json-sort-keys-v1",
            "metadata_digest_algorithm": "sha256",
            "metadata_digest": digest,
        },
    },
    "data": {"entities": []},
}

notice = check_packet_integrity(packet)
print(notice is None)  # True
```

### `validate_packet_inline(packet, *, value_list_root=None)`

Validates an in-memory packet object.

- Performs integrity check first.
- On integrity mismatch, hard-fails immediately and returns only the integrity notice.
- On success, returns `(True, [info notice])` with `packet_integrity_pass`.

```python
from gkc.fermenter import validate_packet_inline

packet = {
    "packet_id": "pkt-example",
    "metadata": {
        "primary_profile": {"id": "https://datadistillery.wikibase.cloud/entity/Q4"},
        "profiles": [],
        "graph": {"nodes": [], "edges": []},
        "mint": {"minted_at": "2026-03-26T00:00:00Z", "generator": "example"},
        "integrity": {
            "metadata_canonicalization": "json-sort-keys-v1",
            "metadata_digest_algorithm": "sha256",
            "metadata_digest": "replace-with-computed-digest",
        },
    },
    "data": {"entities": []},
}

ok, notices = validate_packet_inline(packet)
print(ok)
print([n.code for n in notices])
```

### `validate_packet_from_file(path, *, value_list_root=None)`

Loads packet JSON from file, then delegates to `validate_packet_inline`.

This provides file/inline parity for notebook and CLI testing workflows.

```python
from pathlib import Path
from gkc.fermenter import validate_packet_from_file, validate_packet_inline

packet = {...}
ok_inline, notices_inline = validate_packet_inline(packet)
ok_file, notices_file = validate_packet_from_file(Path("/tmp/packet.json"))
```

## Local Test Coverage

New evaluator and packet-validation behavior is covered in:

- `tests/test_fermenter_evaluator.py`

This suite exercises:

- conformant, non-conformant, missing, and to-be-defined classification paths
- value-list mismatch handling in statement evaluation
- packet integrity pass/fail behavior
- file-vs-inline validation parity
