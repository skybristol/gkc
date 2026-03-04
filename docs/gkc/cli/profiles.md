# Profiles CLI

Plain meaning: Work with SpiritSafe-backed Entity Profiles from the command line.

## Overview

The `gkc` command provides comprehensive CLI access to profile validation, form generation, lookup hydration, registry operations, profile packages, and curation packets.

Top-level command groups:

- `gkc profile` - Profile validation, form generation, and lookups
- `gkc registry` - SpiritSafe registry operations
- `gkc packet` - Curation packet operations

## Profile Commands

### `gkc profile validate`

Validate a Wikidata item using either a profile path or profile name.

```bash
gkc profile validate --profile /path/to/profile.yaml --qid Q123
```

```bash
gkc profile validate --profile TribalGovernmentUS --qid Q123
```

```bash
gkc profile validate \
  --profile TribalGovernmentUS \
  --source local \
  --local-root /path/to/SpiritSafe \
  --item-json path/to/item.json
```

Supported flags:

- `--profile` (required)
- `--qid`
- `--item-json`
- `--policy {strict,lenient}`
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc profile form-schema`

Generate form schema JSON from a profile.

```bash
gkc profile form-schema --profile TribalGovernmentUS --source local --local-root /path/to/SpiritSafe
```

```bash
gkc profile form-schema --profile /path/to/profile.yaml --output form_schema.json
```

Supported flags:

- `--profile` (required)
- `-o, --output`
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc profile form`

Launch the interactive wizard shell for a profile.

```bash
gkc profile form --profile TribalGovernmentUS
```

```bash
gkc profile form --profile TribalGovernmentUS --qid Q123
```

```bash
gkc profile form \
  --profile TribalGovernmentUS \
  --packet /path/to/packet.json
```

```bash
gkc profile form \
  --profile TribalGovernmentUS \
  --depth 2 \
  --source local \
  --local-root /path/to/SpiritSafe
```

Supported flags:

- `--profile` (required)
- `--qid` - Optional Wikidata item ID for editing
- `--packet` - Path to curation packet JSON for multi-entity workflow
- `--depth` - Related profile depth when creating packet on-the-fly (default: 1)
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc profile lookups hydrate`

Hydrate SPARQL lookup caches from one or more profiles.

```bash
gkc profile lookups hydrate --profile TribalGovernmentUS --dry-run
```

```bash
gkc profile lookups hydrate \
  --profile TribalGovernmentUS \
  --source local \
  --local-root /path/to/SpiritSafe \
  --refresh weekly \
  --page-size 500
```

Supported flags:

- `--profile` (required, repeatable)
- `--refresh {manual,daily,weekly,on_release}`
- `--force-refresh`
- `--page-size`
- `--max-results`
- `--endpoint`
- `--dry-run`
- `--fail-on-query-error`
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc profile package`

Work with profile packages (primary profile plus related profiles).

#### `gkc profile package load`

Load a profile package with dependencies.

```bash
gkc profile package load --profile TribalGovernmentUS --depth 1
```

```bash
gkc profile package load \
  --profile TribalGovernmentUS \
  --depth 2 \
  --source local \
  --local-root /path/to/SpiritSafe
```

Supported flags:

- `--profile` (required) - Primary profile ID
- `--depth` - Depth of related profiles to include (default: 1)
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

#### `gkc profile package cardinality`

Show cardinality report for profile linkages.

```bash
gkc profile package cardinality --profile TribalGovernmentUS
```

Supported flags:

- `--profile` (required)
- `--depth` - Depth of related profiles to include (default: 1)
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

#### `gkc profile package validate`

Validate profile package structure.

```bash
gkc profile package validate --profile TribalGovernmentUS --depth 1
```

Supported flags:

- `--profile` (required)
- `--depth` - Depth of related profiles to include (default: 1)
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

## Registry Commands

### `gkc registry list`

List all profiles in the SpiritSafe registry.

```bash
gkc registry list
```

```bash
gkc registry list --source local --local-root /path/to/SpiritSafe
```

Supported flags:

- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc registry search`

Search profiles by keyword in names, descriptions, or tags.

```bash
gkc registry search tribal
```

```bash
gkc registry search government --source local --local-root /path/to/SpiritSafe
```

Arguments:

- `keyword` (required) - Keyword to search for

Supported flags:

- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc registry info`

Show detailed metadata for a specific profile.

```bash
gkc registry info --profile TribalGovernmentUS
```

Supported flags:

- `--profile` (required)
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc registry validate`

Validate the manifest structure.

```bash
gkc registry validate
```

```bash
gkc registry validate --source local --local-root /path/to/SpiritSafe
```

Supported flags:

- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc registry graph`

Show profile graph relationships.

```bash
# Show full graph
gkc registry graph
```

```bash
# Show neighbors for specific profile
gkc registry graph --profile TribalGovernmentUS
```

Supported flags:

- `--profile` - Optional profile ID to show neighbors for
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

## Packet Commands

### `gkc packet create`

Create a curation packet for multi-entity workflows.

```bash
gkc packet create --profile TribalGovernmentUS --mode single
```

```bash
gkc packet create \
  --profile TribalGovernmentUS \
  --mode bulk \
  --depth 2 \
  --output packet.json
```

Supported flags:

- `--profile` (required) - Primary profile ID
- `--mode {single,bulk}` - Operation mode (default: single)
- `--depth` - Related profile depth for bulk mode (default: 1)
- `-o, --output` - Write packet to file instead of stdout
- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

### `gkc packet info`

Show packet metadata and summary.

```bash
gkc packet info --packet-file packet.json
```

Supported flags:

- `--packet-file` (required) - Path to packet JSON file

### `gkc packet validate`

Validate packet structure and cardinality constraints.

```bash
gkc packet validate --packet-file packet.json
```

Supported flags:

- `--packet-file` (required) - Path to packet JSON file

## Common Flags

Most commands support source override flags to switch between GitHub and local SpiritSafe:

- `--source {github,local}` - Override SpiritSafe source mode
- `--local-root` - Local SpiritSafe root (required with `--source local`)
- `--repo` - GitHub repo slug when `--source github` (e.g., owner/SpiritSafe)
- `--ref` - Git reference when `--source github` (default: main)

## Output Format

All commands support:

- `--json` - Emit machine-readable JSON output
- `--verbose` - Show detailed output

Example:

```bash
gkc registry list --json --verbose
```

## See Also

- [Profiles API](../api/profiles.md)
- [Entity Profiles](../profiles.md)
- [Mash CLI](mash.md)

