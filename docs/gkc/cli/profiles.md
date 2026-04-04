# Profiles CLI

Plain meaning: Work with SpiritSafe-backed Entity Profiles and manifest artifacts from the command line.

## Overview

The `gkc profile` command group handles profile export, value-list hydration, and profile package loading.

Current subcommands:

- `gkc profile export-json`
- `gkc profile value-lists hydrate`
- `gkc profile package load`
- `gkc profile package validate`

## Profile Commands

### `gkc profile export-json`

Build JSON Entity Profiles from `cache/entities` and write `<QID>.json` files.

```bash
gkc profile export-json --source local --local-root /path/to/SpiritSafe --output /path/to/SpiritSafe/profiles
```

Common options:

- `--cache-entities-dir`: Override the cache entity directory.
- `--profile-id`: Restrict export to one or more specific profile QIDs.
- `-o`, `--output`: Output directory for per-profile JSON files.
- `--summary-output`: Optional summary JSON file for export diagnostics.
- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.

### `gkc profile value-lists hydrate`

Export value-list queries and hydrate `cache/queries/<QID>.json`.

```bash
gkc profile value-lists hydrate --source local --local-root /path/to/SpiritSafe
```

Common options:

- `--cache-entities-dir`: Override the cache entity directory.
- `--queries-dir`: Override the output directory for exported SPARQL query files.
- `--cache-queries-dir`: Override the hydrated value-list cache directory.
- `--value-list-id`: Restrict hydration to one or more specific value-list QIDs.
- `--api-url`: API URL used for talk-page retrieval.
- `--endpoint`: SPARQL endpoint used for hydration.
- `--page-size`: Query page size for pagination.
- `--max-results`: Maximum total results per value list query.
- `--continue-on-error`: Keep hydrating other value lists if one fails.
- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.

### `gkc profile package load`

Load a primary JSON profile and related profiles from embedded `metadata.profile_graph`.

```bash
gkc profile package load --profile Q4 --depth 1 --source local --local-root /path/to/SpiritSafe
```

### `gkc profile package validate`

Validate package structure fields.

```bash
gkc profile package validate --profile Q4 --depth 1 --source local --local-root /path/to/SpiritSafe
```

Common options for package commands:

- `--profile`: Primary profile QID or entity URI.
- `--depth`: Related profile depth.
- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.

## Common Source Flags

Most `gkc profile` routes support:

- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

## Output Flags

- `--json`
- `--verbose`

## Related Commands

- `gkc packet build`
- `gkc spiritsafe manifest build`
- `gkc wizard`
