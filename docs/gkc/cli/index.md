# Command Line Interface (CLI)

Plain meaning: Run GKC tasks from your terminal.

## Overview

The GKC command line interface provides a lightweight entry point for common workflows including authentication, data loading, and transformation tasks. Commands are organized into logical groups for easy discovery and use.

## Installation

If you have GKC installed, the `gkc` command should be available. When developing locally, use Poetry to run the CLI:

```bash
poetry run gkc --help
```

## Global Flags

These flags work with any command:

- `--json`: Emit machine-readable JSON output for all commands
- `--verbose`: Show additional details and diagnostic information

## Command Groups

### [Authentication](auth.md)

Manage credentials and verify authentication for Wikiverse (Wikidata, Wikipedia, Wikimedia Commons) and OpenStreetMap services.

```bash
gkc auth wikiverse status
gkc auth osm status
```

### [Mash](mash.md)

Load Wikidata items as templates for viewing, filtering, and exporting in various formats.

```bash
gkc mash qid Q42
```

### [Profiles](profiles.md)

Validate items against profiles, export JSON Entity Profiles from cache entities, generate form schemas, launch the Textual wizard, hydrate SPARQL value lists, and build SpiritSafe artifact manifests.

```bash
gkc profile package load --profile Q4 --source local --local-root /path/to/SpiritSafe
```

```bash
gkc profile package load --profile Q4 --depth 1 --source local --local-root /path/to/SpiritSafe
```

```bash
gkc profile export-json --cache-entities-dir /path/to/SpiritSafe/cache/entities --output /path/to/SpiritSafe/profiles
```

```bash
gkc profile value-lists hydrate --source local --local-root /path/to/SpiritSafe

gkc --json spiritsafe manifest build --source local --local-root /path/to/SpiritSafe
```

### [Wikibase](wikibase.md)

Audit and initialize Data Distillery foundation ontology terms from profile definitions, and build profile-driven write plans.

```bash
gkc wikibase audit --require-auth
gkc wikibase init --execute
gkc wikibase plan-write --profile TribalGovernmentUS --source-values-file /tmp/gkc_plan_source_values.json
```

## Quick Start Examples

Check authentication status:
```bash
gkc auth wikiverse status
```

Load a Wikidata item as a template:
```bash
gkc mash qid Q42 --output summary
```

Get raw Wikidata JSON output for scripting:
```bash
gkc --json mash qid Q42 --output json
```


Launch the interactive profile wizard:

```bash
gkc wizard --profile Q4 --local-root /path/to/SpiritSafe
```

## Getting Help

Use `--help` with any command or subcommand to see available options:

```bash
gkc --help
gkc auth --help
gkc mash qid --help
```

## Build and Test Commands

Build documentation:
```bash
poetry run mkdocs build
```

Run tests:
```bash
poetry run pytest
```
