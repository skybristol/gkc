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

The packet pipeline has two stages: **build** assembles a scaffold from a JSON Entity Profile, and **charge** fills that scaffold with data from a source such as Wikidata.

### Quick Start: Build → Charge

```bash
# 1. Build a packet from a local SpiritSafe profile
gkc --json packet build \
  --profile Q4 \
  --source local \
  --local-root /path/to/SpiritSafe \
  -o /tmp/packet.json

# 2. Inspect the packet scaffold
gkc --json packet info --packet-file /tmp/packet.json

# 3. Charge with a Wikidata item (e.g., Cherokee Nation Q195562)
gkc --json packet charge \
  --packet-file /tmp/packet.json \
  --source wikidata \
  --qid Q195562 \
  -o /tmp/charged.json

# 4. Inspect the charged packet
gkc --json packet info --packet-file /tmp/charged.json
```

### `gkc packet build`

Assemble a curation packet scaffold from a JSON Entity Profile stored in SpiritSafe.
Produces the frozen URI-keyed packet contract containing entity slots, statement slots, cross-references, and value-list routes.

```bash
gkc packet build --profile Q4 --source local --local-root /path/to/SpiritSafe
gkc packet build --profile Q4 --source local --local-root /path/to/SpiritSafe -o /tmp/packet.json
gkc packet build --profile Q4 --source github --repo skybristol/SpiritSafe --ref main
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `--profile` | Yes | Profile QID (e.g., `Q4`) or full entity URI |
| `--source` | No | `local` or `github` (default: runtime config) |
| `--local-root` | When `--source local` | Path to local SpiritSafe checkout |
| `--repo` | When `--source github` | GitHub repo slug (e.g., `owner/SpiritSafe`) |
| `--ref` | No | Git ref for GitHub source (default: `main`) |
| `-o` / `--output` | No | Write packet JSON to file instead of stdout |

The output packet includes:

- `packet_id` — UUID for this packet
- `operation_mode` — Scaffold mode indicator
- `metadata.primary_profile` — Full URI and identifier for the source profile
- `metadata.graph.edges[]` — Linked-profile graph edges for packet traversal
- `data.entities[]` — Entity slots with statement slots pre-scaffolded

### `gkc packet charge`

Charge a packet scaffold with source data. Fetches the Wikidata item and populates each entity slot's `data` field with labels, descriptions, aliases, and statement values.

```bash
# Charge all entities in the packet from a single Wikidata QID
gkc packet charge \
  --packet-file /tmp/packet.json \
  --source wikidata \
  --qid Q195562 \
  -o /tmp/charged.json

# Charge using an explicit entity-to-QID mapping file
gkc packet charge \
  --packet-file /tmp/packet.json \
  --source wikidata \
  --mapping-file /tmp/qid_map.json \
  -o /tmp/charged.json
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `--packet-file` | Yes | Path to the packet JSON file produced by `packet build` |
| `--source` | No | `wikidata` (default) or `local` |
| `--qid` | When source=wikidata and no mapping | Wikidata QID to charge all entities with |
| `--mapping-file` | Alternatively to `--qid` | JSON file mapping entity IDs to QIDs |
| `-o` / `--output` | No | Write charged packet JSON to file instead of stdout |

The output is the charged packet with each entity slot's `data` populated and `notices[]` listing any `ConformanceNotice` items raised during charging.

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

### `gkc packet create` (Legacy)

Create curation packets using the legacy profile-name-based contract. Preserved for
existing integrations. New workflows should use `packet build` instead.

```bash
gkc packet create --profile Q4 --mode bulk --depth 1 --source local --local-root /path/to/SpiritSafe
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
