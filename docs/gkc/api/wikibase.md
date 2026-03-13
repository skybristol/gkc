# Wikibase API

## Overview

The `gkc.wikibase` module provides Data Distillery orchestration for:

- foundation ontology profile loading, auditing, and initialization
- shared packet-to-write planning (`spirit_safe` → `still_charger` → `cooperage` → optional `shipper.plan_batch`)
- authenticated operation replay (`execute_wikibase_write_plan`) with dry-run-by-default write control

## Public API

### `load_foundation_profiles(profile_dir)`

Loads foundation ontology definitions from profile YAML files.

Expected files:

- `foundation_entities.yaml`
- `foundation_properties.yaml`

### `audit_wikibase_foundation(...)`

Audits a Wikibase instance against foundation profiles.

```python
from gkc.wikibase import audit_wikibase_foundation

report = audit_wikibase_foundation(
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
    profile_dir="./gkc/wikibase/foundation_profiles",
    language="en",
)

print(report.ok)
print(report.summary)
```

`report.to_dict()` returns a JSON-safe structure suitable for CLI artifacts and CI checks.

### `init_wikibase_foundation(...)`

Runs audit, then creates missing foundation entities/properties through `WikibaseShipper`.

```python
from gkc import WikiverseAuth
from gkc.wikibase import init_wikibase_foundation

auth = WikiverseAuth(
    username="my_dd_username",
    password="my_dd_password",
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
)
auth.login()

report = init_wikibase_foundation(
    auth=auth,
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
    profile_dir="./gkc/wikibase/foundation_profiles",
    language="en",
    dry_run=True,
    bot=False,
    summary="Initialize foundation ontology",
)

print(report.ok)
print(report.summary)
```

### `build_wikibase_write_plan(...)`

Builds an end-to-end write plan from profile scaffolds plus source values.

```python
from gkc.wikibase import build_wikibase_write_plan

result = build_wikibase_write_plan(
    profile_id="TribalGovernmentUS",
    source_values={
        "ent-001": {
            "labels": {"en": "Cherokee Nation"},
            "statements": {
                "instance_of": [{"value": "Q7840353"}],
                "official_website": [{"value": "https://www.cherokee.org"}],
            },
        }
    },
    operation_mode="single",
    specificationless=True,
)

print(result.charge_report.entities_charged)
print(result.barrel_report.operations_created)
print(len(result.operations))
```

If a `WikibaseShipper` instance is provided through `shipper=...`, the orchestration also computes `result.diff_plan` via `shipper.plan_batch`.

### `WikibaseWritePlanResult`

Dataclass container returned by `build_wikibase_write_plan()`.

Key fields:

- `packet`: original curation packet scaffold
- `charged_packet`: packet after charging
- `charge_report`: `ChargeReport` diagnostics
- `operations`: list of shippable operation payloads
- `barrel_report`: `BarrelPlanReport` diagnostics
- `diff_plan`: optional `DiffPlan` from shipper planning

### `execute_wikibase_write_plan(...)`

Builds a write plan and replays each operation through `WikibaseShipper` write methods.

```python
from gkc.auth import WikiverseAuth
from gkc.shipper import WikibaseShipper
from gkc.wikibase import execute_wikibase_write_plan

auth = WikiverseAuth(
    username="my_dd_username",
    password="my_dd_password",
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
)
auth.login()

shipper = WikibaseShipper(auth=auth, dry_run_default=True)

result = execute_wikibase_write_plan(
    profile_id="TribalGovernmentUS",
    source_values={"ent-001": {"labels": {"en": "Cherokee Nation"}}},
    shipper=shipper,
    dry_run=True,
    write_summary="gkc wikibase execute-write",
)

print(result.write_summary)
print(result.write_results[0].status)
```

### `WikibaseWriteExecutionResult`

Dataclass container returned by `execute_wikibase_write_plan()`.

Key fields:

- `plan`: underlying `WikibaseWritePlanResult`
- `write_results`: list of `WriteResult` values from shipper writes
- `write_summary`: aggregated status counters (`submitted`, `dry_run`, `validated`, `blocked`, `error`)

## Exceptions

- `FoundationProfileError`: profile directory or YAML structure is invalid
- `FoundationAuditError`: audit request/lookup operations failed
- `FoundationInitError`: init flow failed or required parameters were invalid

## Data Distillery Write Contract Note

For property creation on Data Distillery, shipper requests place property `datatype` in the `data` JSON payload for `new=property` operations.

This instance-specific behavior is surfaced through init and shipper flows and should be preserved when extending write paths.

## Execution Notes

- `execute_wikibase_write_plan(...)` keeps planning and execution as separate API calls while reusing identical operation payloads.
- Dry-run replay is supported through `dry_run=True`; write submission occurs only with `dry_run=False`.
- Operation order currently follows packet/barreling output order.

## See Also

- [Still Charger API](still_charger.md)
- [Cooperage API](cooperage.md)
- [Shipper API](shipper.md)
