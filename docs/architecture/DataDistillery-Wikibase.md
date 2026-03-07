# Data Distillery Wikibase

Data Distillery Wikibase (`datadistillery.wikibase.cloud`) is the semantic registry for GKC ontology terms, profile metadata relationships, and multilingual guidance content that must be queryable and collaboratively maintained.

## Why This Exists

The runtime and collaboration needs are different:

- SpiritSafe YAML is optimized for offline execution and deterministic profile consumption.
- Wikibase is optimized for semantic relationships, multilingual fields, and query-oriented discovery.

The Data Distillery uses a hybrid model where both sides are maintained in sync.

## Current Architecture Contract

### Source-of-Truth Position

- Profile YAML remains the actionable artifact consumed by runtime code.
- Wikibase stores semantic linkage and metadata that improve queryability and collaboration.
- Transformations between Wikibase and SpiritSafe must be lossless and testable.

### Foundation Modeling

- Foundation ontology definitions are represented as machine-readable profiles in `gkc/wikibase/foundation_profiles/`.
- `gkc wikibase audit` validates conformance against those profiles.
- `gkc wikibase init` performs creation planning and optional writes for missing foundation terms.

### Operational Modes

- Offline-first operation is a hard requirement.
- Network access to Data Distillery is an optional enhancement, not a runtime dependency for core profile-driven workflows.
- SpiritSafe cache and manifest artifacts support deterministic fallback behavior.

## Current CLI Behavior

### `gkc wikibase audit`

- Reads Data Distillery runtime settings from `DD_WB_*` environment variables.
- Uses authenticated mode when credentials are valid.
- Falls back to anonymous session on login failure unless `--require-auth` is provided.
- Produces summary output and optional JSON report via `--output`.

### `gkc wikibase init`

- Runs an audit pass first and builds create/skip action records.
- Defaults to dry-run preview mode.
- Requires explicit `--execute` to submit writes.
- Requires authentication; supports environment credentials or `--interactive` prompt flow.
- Supports explicit edit summaries and bot marking controls (`--summary`, `--bot`).

## Shipper API Contract Notes (Data Distillery)

For property creation with `wbeditentity`, Data Distillery currently requires `datatype` inside the serialized `data` JSON payload for `new=property` requests.

Do not send `datatype` as only a top-level form parameter for this instance.

This behavior is treated as an instance contract until validated across additional Wikibase targets.

## Environment Variables

- `DD_WB_API_URL`
- `DD_WB_SPARQL_ENDPOINT`
- `DD_WB_USERNAME`
- `DD_WB_PASSWORD`

Recommended baseline:

```bash
export DD_WB_API_URL="https://datadistillery.wikibase.cloud/w/api.php"
export DD_WB_SPARQL_ENDPOINT="https://datadistillery.wikibase.cloud/query/sparql"
export DD_WB_USERNAME="your_dd_username"
export DD_WB_PASSWORD="your_dd_password"
```

## Troubleshooting

- **Auth group mismatch**: if credentials authenticate but write requests fail, verify Data Distillery account permissions include edit rights.
- **Write summary missing**: shipper write operations and init flows require a non-empty summary.
- **Property create datatype error**: ensure datatype is embedded in the `data` payload JSON for property creation.

## Related Documentation

- [Setup and Orientation](../gkc/setup.md)
- [Authentication Guide](../gkc/authentication.md)
- [Cross-Module Contracts](module-contracts.md)
- [Shipper API](../gkc/api/shipper.md)
- [CLI Reference](../gkc/cli/index.md)