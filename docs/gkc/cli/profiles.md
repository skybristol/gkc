# Profiles CLI

Plain meaning: Validate data and generate schemas from YAML profiles.

## Overview

The `profile` command group lets you validate Wikidata items against YAML profiles and export form schemas for CLI or UI workflows.

## Commands

### Validate a Wikidata Item

```bash
gkc profile validate --profile .dev/TribalGovernmentUS.yaml --qid Q123
```

Validate a local JSON file:

```bash
gkc profile validate --profile .dev/TribalGovernmentUS.yaml --item-json path/to/item.json
```

Use strict validation:

```bash
gkc profile validate --profile .dev/TribalGovernmentUS.yaml --qid Q123 --policy strict
```

### Generate a Form Schema

```bash
gkc profile form-schema --profile .dev/TribalGovernmentUS.yaml
```

Write schema to a file:

```bash
gkc profile form-schema --profile .dev/TribalGovernmentUS.yaml --output form_schema.json
```

## Flags

- `--profile`: Path to the YAML profile definition
- `--qid`: Wikidata item ID to fetch and validate
- `--item-json`: Path to a Wikidata item JSON file
- `--policy`: Validation policy (`strict` or `lenient`)
- `--output`: Output file path for form schemas

## See Also

- [Profiles API](../api/profiles.md) - Programmatic profile usage
- [Mash CLI](mash.md) - Load Wikidata items for validation
