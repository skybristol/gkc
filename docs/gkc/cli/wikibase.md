# Wikibase CLI

The `gkc wikibase` command group supports Data Distillery foundation ontology maintenance.

Current phase scope includes:

- read-only conformance auditing (`audit`)
- foundation initialization planning and execution (`init`)

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
## Output Artifacts
