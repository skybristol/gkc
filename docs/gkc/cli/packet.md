# Packet CLI

Plain meaning: Build, inspect, validate, and charge curation packets.

## Overview

The `gkc packet` command group manages packet-shaped curation artifacts.

Current subcommands:

- `gkc packet create`
- `gkc packet info`
- `gkc packet validate`
- `gkc packet build`
- `gkc packet charge`

The packet workflow has two current tracks:

- `build` and `charge` for the current JSON Entity Profile based packet contract.
- `create` for the legacy profile-name-based packet contract.

## Quick Start

Build a packet scaffold from a profile:

```bash
gkc packet build --profile Q4 --source local --local-root /path/to/SpiritSafe -o /tmp/packet.json
```

Inspect the scaffold:

```bash
gkc packet info --packet-file /tmp/packet.json
```

Charge the packet with Wikidata data:

```bash
gkc packet charge --packet-file /tmp/packet.json --qid Q195562 -o /tmp/charged.json
```

Validate the resulting packet structure:

```bash
gkc packet validate --packet-file /tmp/charged.json
```

## `gkc packet build`

Build a curation packet from a JSON Entity Profile.

```bash
gkc packet build --profile Q4 --source local --local-root /path/to/SpiritSafe
```

Common options:

- `--profile`: Profile QID or full entity URI.
- `--source`: Profile source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.
- `-o`, `--output`: Write packet JSON to a file instead of stdout.

## `gkc packet charge`

Charge a curation packet with Wikidata item data.

```bash
gkc packet charge --packet-file /tmp/packet.json --qid Q195562 -o /tmp/charged.json
```

You can also build and charge in one call by providing a profile:

```bash
gkc packet charge \
  --profile Q4 \
  --profile-source local \
  --profile-local-root /path/to/SpiritSafe \
  --qid Q195562 \
  -o /tmp/charged.json
```

Common options:

- `--packet-file`: Existing packet JSON file to charge.
- `--profile`: Profile QID or URI to create and charge in one call.
- `--include-linked-profiles`: Include directly linked profiles during on-the-fly packet creation.
- `--source`: Data source for charging, either `wikidata` or `local`.
- `--qid`: Wikidata item ID to use when charging from Wikidata.
- `--mapping-file`: JSON file mapping entity IDs or profile keys to QIDs.
- `--profile-source`: Profile source override for on-the-fly packet creation.
- `--profile-local-root`: Local SpiritSafe root for on-the-fly packet creation.
- `--profile-repo`: GitHub repository slug for on-the-fly packet creation.
- `--profile-ref`: Git ref for on-the-fly packet creation.
- `-o`, `--output`: Write charged packet JSON to a file instead of stdout.

## `gkc packet info`

Show packet metadata and summary information.

```bash
gkc packet info --packet-file /tmp/packet.json
```

Required option:

- `--packet-file`: Path to the packet JSON file.

## `gkc packet validate`

Validate packet structure.

```bash
gkc packet validate --packet-file /tmp/packet.json
```

Required option:

- `--packet-file`: Path to the packet JSON file.

## `gkc packet create`

Create a curation packet using the legacy packet contract.

```bash
gkc packet create --profile Q4 --mode bulk --depth 1 --source local --local-root /path/to/SpiritSafe
```

Common options:

- `--profile`: Primary profile ID for the packet.
- `--mode`: Packet mode, either `single` or `bulk`.
- `--depth`: Related profile depth for bulk mode.
- `--source`: Profile source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.
- `-o`, `--output`: Write packet JSON to a file instead of stdout.

Use `create` only for workflows that still depend on the legacy packet shape. New work should prefer `build` and `charge`.

## Related Commands

- `gkc profile export-json`
- `gkc profile package load`
- `gkc wizard`
