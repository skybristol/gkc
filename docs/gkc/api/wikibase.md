# Wikibase API

## Overview

The `gkc.wikibase` module currently provides foundation ontology profile loading, auditing, and initialization utilities for Data Distillery.

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

## Exceptions

- `FoundationProfileError`: profile directory or YAML structure is invalid
- `FoundationAuditError`: audit request/lookup operations failed
- `FoundationInitError`: init flow failed or required parameters were invalid

## Data Distillery Write Contract Note

For property creation on Data Distillery, shipper requests place property `datatype` in the `data` JSON payload for `new=property` operations.

This instance-specific behavior is surfaced through init and shipper flows and should be preserved when extending write paths.
