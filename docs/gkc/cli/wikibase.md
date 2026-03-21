# Wikibase CLI

The `gkc wikibase` command group supports Data Distillery foundation ontology maintenance and write-plan orchestration.

Current scope includes:

- read-only conformance auditing (`audit`)
- foundation initialization planning and execution (`init`)
- profile-driven write-plan preview (`plan-write`)
- authenticated write replay with dry-run-by-default execution control (`execute-write`)

## Prerequisites

Set Data Distillery runtime variables:

```bash
export DD_WB_API_URL="https://datadistillery.wikibase.cloud/w/api.php"
export DD_WB_SPARQL_ENDPOINT="https://datadistillery.wikibase.cloud/query/sparql"
export DD_WB_USERNAME="your_dd_username"
export DD_WB_PASSWORD="your_dd_password"
```

You can inspect all options with:

```bash
gkc wikibase --help
gkc wikibase audit --help
gkc wikibase init --help
gkc wikibase plan-write --help
gkc wikibase execute-write --help
```

## `gkc wikibase audit`

Audit checks the current Wikibase instance against foundation profiles under `gkc/wikibase/foundation_profiles/` by default.

### Common usage

```bash
# authenticated if credentials are present and valid
poetry run gkc wikibase audit

# fail fast if auth cannot be established
poetry run gkc wikibase audit --require-auth

# override profiles path and capture full JSON report
poetry run gkc wikibase audit \
  --foundation-profiles ./gkc/wikibase/foundation_profiles \
  --output /tmp/foundation_audit.json
```

### Key options

- `--foundation-profiles`: directory containing `foundation_entities.yaml` and `foundation_properties.yaml`
- `--language`: label language for matching (default `en`)
- `--output`: write full JSON report artifact
- `--require-auth`: stop on authentication failure instead of anonymous fallback

## `gkc wikibase init`

Init runs audit first, then plans and optionally applies missing foundation creates.

### Execution model

- dry-run is the default mode
- use `--execute` for live writes
- authentication is required

### Common usage

```bash
# preview planned creates/skips (default dry-run)
poetry run gkc wikibase init

# execute writes
poetry run gkc wikibase init --execute

# execute with explicit summary and JSON artifact
poetry run gkc wikibase init \
  --execute \
  --summary "Initialize foundation ontology terms" \
  --output /tmp/foundation_init.json
```

### Key options

- `--execute`: enable write mode
- `--summary`: edit summary used for `wbeditentity` requests
- `--bot`: mark edits as bot edits
- `--interactive`: prompt for credentials if not found or if login fails
- `--api-url`: override Data Distillery API URL for this run
- `--foundation-profiles`: profile directory override
- `--language`: label language for matching
- `--output`: write full JSON report artifact

## Output Artifacts

When `--output` is used, command output includes:

- `metadata` section with runtime context (`api_url`, timestamp, and mode)
- `summary` counters
- detailed records (`records` for audit, `actions` for init)

## Troubleshooting

- **Init reports auth requirement**: set `DD_WB_USERNAME` and `DD_WB_PASSWORD`, or run with `--interactive`.
- **Audit warns and falls back to anonymous mode**: add `--require-auth` during CI or strict checks.
- **Unexpected no-op/skipped actions**: inspect JSON report records/actions and run with `--verbose` for additional preview detail.

## `gkc wikibase plan-write`

`plan-write` runs the shared pipeline:

- `still_charger.create_curation_packet`
- `still_charger.charge_curation_packet`
- `wikibase.orchestration.barrel_curation_packet_to_wikibase_plan`
- optional `shipper.plan_batch`

### Common usage

```bash
# build packet -> charge -> write plan only
poetry run gkc wikibase plan-write \
  --profile TribalGovernmentUS \
  --source-values-file /tmp/gkc_plan_source_values.json \
  --mode single
```

```bash
# include shipper diff planning
poetry run gkc wikibase plan-write \
  --profile TribalGovernmentUS \
  --source-values-file /tmp/gkc_plan_source_values.json \
  --mode single \
  --with-shipper-plan
```

```bash
# strict charging and JSON artifact output
poetry run gkc wikibase plan-write \
  --profile TribalGovernmentUS \
  --source-values-file /tmp/gkc_plan_source_values.json \
  --strict-charging \
  --output /tmp/wikibase_plan_write.json
```

### Key options

- `--profile`: primary profile ID used for packet generation
- `--source-values-file`: JSON mapping of entity/profile IDs to values
- `--property-map-file`: optional statement ID to property ID mapping
- `--mode`: `single` or `bulk`
- `--depth`: related-profile traversal depth for bulk mode
- `--strict-charging`: disable specificationless charging behavior
- `--with-shipper-plan`: run `shipper.plan_batch` and include diff summary
- `--api-url`: override Data Distillery API URL for shipper planning
- `--interactive`: prompt for Data Distillery credentials when needed
- `--require-auth`: fail if authenticated shipper planning cannot be established
- `--source` and `--local-root`: override SpiritSafe source mode
- `--output`: write full logical path + reports + operations JSON

### Output details

Without `--with-shipper-plan`, output includes logical path, packet/charge/barrel summary, and operation preview.

With `--with-shipper-plan`, output also includes:

- `shipper_plan_summary` with create/update/noop/ambiguous/blocked counts
- `shipper_plan_preview` operation-level diff details
- authentication context (`auth_mode`, optional warning)

## `gkc wikibase execute-write`

`execute-write` reuses the same shared pipeline as `plan-write` and then replays operations through shipper write methods.

Execution path:

- `still_charger.create_curation_packet`
- `still_charger.charge_curation_packet`
- `wikibase.orchestration.barrel_curation_packet_to_wikibase_plan`
- `shipper.write_item` / `shipper.write_property`

Authentication is required for this command.

### Common usage

```bash
# default: authenticated dry-run replay (no write submission)
poetry run gkc wikibase execute-write \
  --profile TribalGovernmentUS \
  --source-values-file /tmp/gkc_plan_source_values.json
```

```bash
# authenticated write submission
poetry run gkc wikibase execute-write \
  --profile TribalGovernmentUS \
  --source-values-file /tmp/gkc_plan_source_values.json \
  --summary "Create TribalGovernmentUS seed item" \
  --execute
```

```bash
# strict charging plus JSON artifact output
poetry run gkc wikibase execute-write \
  --profile TribalGovernmentUS \
  --source-values-file /tmp/gkc_plan_source_values.json \
  --strict-charging \
  --output /tmp/wikibase_execute_write.json
```

### Key options

- `--profile`: primary profile ID used for packet generation
- `--source-values-file`: JSON mapping of entity/profile IDs to values
- `--property-map-file`: optional statement ID to property ID mapping
- `--mode`: `single` or `bulk`
- `--depth`: related-profile traversal depth for bulk mode
- `--strict-charging`: disable specificationless charging behavior
- `--execute`: submit writes (default behavior is dry-run replay)
- `--summary`: edit summary prefix used for each write operation
- `--bot`: mark edits as bot edits
- `--interactive`: prompt for Data Distillery credentials if missing or invalid
- `--api-url`: override Data Distillery API URL for this run
- `--source` and `--local-root`: override SpiritSafe source mode
- `--output`: write full logical path + reports + write-results JSON

### Output details

Output includes:

- `write_summary` counters (`submitted`, `dry_run`, `validated`, `blocked`, `error`)
- `write_results_preview` operation-level write statuses
- full packet/charge/barrel diagnostics aligned with `plan-write`

### Relationship to `plan-write`

- `plan-write` remains the mandatory preflight stage
- `execute-write` is the authenticated promotion stage using the same logical pipeline and operation payloads
- logical path/reporting remains consistent so users can trace plan-to-execute parity
