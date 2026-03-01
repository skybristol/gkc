# Profiles CLI

Plain meaning: Validate data and generate schemas from YAML profiles.

## Overview

The `profile` command group lets you validate Wikidata items against YAML profiles and export form schemas for CLI or UI workflows.

## Commands

### Validate a Wikidata Item

```bash
gkc profile validate --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml --qid Q123
```

Validate a local JSON file:

```bash
gkc profile validate --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml --item-json path/to/item.json
```

Use strict validation:

```bash
gkc profile validate --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml --qid Q123 --policy strict
```

### Generate a Form Schema

```bash
gkc profile form-schema --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml
```

Write schema to a file:

```bash
gkc profile form-schema --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml --output form_schema.json
```

### Hydrate SPARQL Lookups

Use profile names with default GitHub source mode:

```bash
gkc profile lookups hydrate --profile TribalGovernmentUS --dry-run
```

Use a local SpiritSafe clone (recommended for branch development):

```bash
gkc profile lookups hydrate \
  --profile TribalGovernmentUS \
  --source local \
  --local-root /path/to/SpiritSafe \
  --dry-run
```

Override GitHub repo/ref for testing:

```bash
gkc profile lookups hydrate \
  --profile TribalGovernmentUS \
  --source github \
  --repo skybristol/SpiritSafe \
  --ref main \
  --dry-run
```

## Flags

- `--profile`: Profile path or profile name (repeatable for `lookups hydrate`)
- `--qid`: Wikidata item ID to fetch and validate
- `--item-json`: Path to a Wikidata item JSON file
- `--policy`: Validation policy (`strict` or `lenient`)
- `--output`: Output file path for form schemas
- `--source`: SpiritSafe source mode override (`github` or `local`) for hydration
- `--local-root`: Local SpiritSafe clone root (required with `--source local`)
- `--repo`: GitHub repo slug override for hydration (with `--source github`)
- `--ref`: Git reference override for hydration (with `--source github`)

## See Also

- [Profiles API](../api/profiles.md) - Programmatic profile usage
- [Mash CLI](mash.md) - Load Wikidata items for validation
