# Profiles CLI

Plain meaning: Work with SpiritSafe-backed Entity Profiles and manifest artifacts from the command line.

## Overview

The `gkc` CLI exposes profile validation, JSON profile export, value-list hydration, registry inspection, package loading, packet generation, and manifest indexing.

Top-level command groups:

- `gkc profile`
- `gkc registry`
- `gkc packet`
- `gkc spiritsafe manifest`

## Profile Commands

### `gkc profile export-json`

Build JSON Entity Profiles from `cache/entities` and write `<QID>.json` files.

```bash
gkc profile export-json --source local --local-root /path/to/SpiritSafe --output /path/to/SpiritSafe/profiles
```

### `gkc profile value-lists hydrate`

Export value-list queries and hydrate `cache/queries/<QID>.json`.

```bash
gkc profile value-lists hydrate --source local --local-root /path/to/SpiritSafe
```

### `gkc profile package load`

Load a primary JSON profile and related profiles from embedded `metadata.profile_graph`.

```bash
gkc profile package load --profile Q4 --depth 1 --source local --local-root /path/to/SpiritSafe
```

### `gkc profile package cardinality`

Show linkage/cardinality metadata derived from loaded package graph edges.

```bash
gkc profile package cardinality --profile Q4 --depth 1 --source local --local-root /path/to/SpiritSafe
```

### `gkc profile package validate`

Validate package structure fields.

```bash
gkc profile package validate --profile Q4 --depth 1 --source local --local-root /path/to/SpiritSafe
```

## Registry Commands

### `gkc registry list`

List manifest-indexed profiles (`qid`, `entity`, labels, descriptions, statement counts).

```bash
gkc registry list --source local --local-root /path/to/SpiritSafe
```

### `gkc registry info`

Show detailed manifest entry for a profile (`QID` or entity URI).

```bash
gkc registry info --profile Q4 --source local --local-root /path/to/SpiritSafe
```

### `gkc registry validate`

Validate new manifest sections and counts.

```bash
gkc registry validate --source local --local-root /path/to/SpiritSafe
```

## Packet Commands

### `gkc packet create`

Create curation packets from JSON profiles.

```bash
gkc packet create --profile Q4 --mode bulk --depth 1 --source local --local-root /path/to/SpiritSafe
```

### `gkc packet info`

Inspect packet metadata.

```bash
gkc packet info --packet-file packet.json
```

### `gkc packet validate`

Validate packet structure and entity linkage consistency.

```bash
gkc packet validate --packet-file packet.json
```

## SpiritSafe Manifest Commands

### `gkc spiritsafe manifest build`

Build `cache/manifest.json` from the current local SpiritSafe artifact state.

```bash
gkc --json spiritsafe manifest build --source local --local-root /path/to/SpiritSafe
```

```bash
gkc --json spiritsafe manifest build --source local --local-root /path/to/SpiritSafe --output /tmp/manifest.json
```

This route requires local mode.

## Common Source Flags

Most profile/registry/packet/manifest routes support:

- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

## Output Flags

- `--json`
- `--verbose`
