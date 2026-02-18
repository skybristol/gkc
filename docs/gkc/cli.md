# CLI

Plain meaning: Run GKC tasks from your terminal.

## Overview

The CLI is a lightweight entry point for common workflows. The initial scope focuses on authentication checks for Wikiverse and OpenStreetMap.

## Installation

If you have GKC installed, the `gkc` command should be available. When developing locally, use Poetry to run the CLI:

```bash
poetry run gkc --help
```

## Commands

### Wikiverse authentication

```bash
gkc auth wikiverse login
```

Logs into Wikiverse using bot password credentials.

```bash
gkc auth wikiverse status
```

Checks whether credentials are available and whether a CSRF token can be obtained.

```bash
gkc auth wikiverse token
```

Retrieves a CSRF token for debugging. Use `--show-token` to display the full token.

### OpenStreetMap authentication

```bash
gkc auth osm login
```

Confirms whether OpenStreetMap credentials are present.

```bash
gkc auth osm status
```

Reports whether OpenStreetMap credentials are available.

## Flags

- `--interactive`: prompt for credentials if environment variables are missing.
- `--api-url`: override the Wikiverse API URL.
- `--json`: emit machine-readable JSON output.
- `--verbose`: show additional details.
- `--show-token`: show the full CSRF token for the `token` command.

## Environment variables

### Wikiverse

- `WIKIVERSE_USERNAME`
- `WIKIVERSE_PASSWORD`
- `WIKIVERSE_API_URL`

### OpenStreetMap

- `OPENSTREETMAP_USERNAME`
- `OPENSTREETMAP_PASSWORD`

## Output format

The CLI returns a single JSON object when `--json` is used. Tokens are redacted unless `--show-token` is provided.

## Build and test commands

- Build docs: `poetry run mkdocs build`
- Run tests: `poetry run pytest`
