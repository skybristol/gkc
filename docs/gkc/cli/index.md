# Command Line Interface (CLI)

Plain meaning: Run GKC tasks from your terminal.

## Overview

The GKC command line interface provides a lightweight entry point for authentication, source loading, profile maintenance, packet workflows, validation, and SpiritSafe artifact maintenance.

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

### [Profile](profiles.md)

Export JSON Entity Profiles, hydrate value lists, and load profile packages.

```bash
gkc profile package load --profile Q4 --source local --local-root /path/to/SpiritSafe
```

```bash
gkc profile export-json --source local --local-root /path/to/SpiritSafe --output /path/to/SpiritSafe/profiles
```

```bash
gkc profile value-lists hydrate --source local --local-root /path/to/SpiritSafe
```

### [Packet](packet.md)

Build, inspect, validate, and charge curation packets.

```bash
gkc packet build --profile Q4 --source local --local-root /path/to/SpiritSafe -o /tmp/packet.json
```

```bash
gkc packet charge --packet-file /tmp/packet.json --qid Q195562 -o /tmp/charged.json
```

### [SpiritSafe](spiritsafe.md)

Build SpiritSafe support artifacts such as manifests, sitelink sources, and semantic anchors.

```bash
gkc spiritsafe manifest build --source local --local-root /path/to/SpiritSafe
```

```bash
gkc spiritsafe sitelinks sync-wikimedia-sites --source local --local-root /path/to/SpiritSafe
```

```bash
gkc spiritsafe semantic-anchors build --source local --local-root /path/to/SpiritSafe
```

### Registry

The live CLI also includes `gkc registry` for registry inspection and validation. That command group is currently transitional and its cleanup notes are being tracked outside the published CLI pages.

### [Wizard](wizard.md)

Launch the interactive Streamlit curation wizard from a profile reference.

```bash
gkc wizard --profile Q4 --source local --local-root /path/to/SpiritSafe
```

### [Mash](mash.md) revision cache operations

Check Data Distillery Wikibase recentchanges and refresh SpiritSafe entity cache artifacts.

```bash
gkc mash check-wikibase-revisions --since 2026-03-13T16:00:00Z
gkc mash cache-wikibase-revisions --cache-dir /path/to/SpiritSafe/cache/entities
```

## Quick Start Examples

Check authentication status:
```bash
gkc auth wikiverse status
```

Load a Wikidata item as a template:

```bash
gkc mash qid Q42 --summary
```

Get raw Wikidata JSON output for scripting:

```bash
gkc --json mash qid Q42 --raw
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
gkc packet --help
gkc spiritsafe --help
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
