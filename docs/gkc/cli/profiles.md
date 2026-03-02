# Profiles CLI

Plain meaning: Validate data and generate schemas from YAML profiles.

## Overview

The `profile` command group supports three active workflows:

- Validate Wikidata item JSON against an Entity Profile.
- Generate a normalized form schema from an Entity Profile.
- Launch the Textual-based profile wizard shell for guided curation.

It also supports lookup hydration for SPARQL-backed allowed-item lists.

## Commands

### Validate a Wikidata Item

```bash
gkc profile validate --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml --qid Q123
```

Validate by profile name (default GitHub SpiritSafe source):

```bash
gkc profile validate --profile TribalGovernmentUS --qid Q123
```

Validate by profile name from a local SpiritSafe clone:

```bash
gkc profile validate \
  --profile TribalGovernmentUS \
  --source local \
  --local-root /path/to/SpiritSafe \
  --qid Q123
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

Generate from profile name via local SpiritSafe clone:

```bash
gkc profile form-schema \
  --profile TribalGovernmentUS \
  --source local \
  --local-root /path/to/SpiritSafe
```

Write schema to a file:

```bash
gkc profile form-schema --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml --output form_schema.json
```

### Launch the Textual Wizard (Current Phase)

Launch the wizard shell for a profile:

```bash
gkc profile form --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml
```

Launch by profile name via GitHub SpiritSafe source:

```bash
gkc profile form --profile TribalGovernmentUS
```

Launch in edit context with a QID (currently tracked as session metadata):

```bash
gkc profile form --profile /path/to/SpiritSafe/profiles/TribalGovernmentUS/profile.yaml --qid Q123
```

Current implemented behavior in this phase:

- 5-step wizard frame is active (Plan, Identification, Statements, Sitelinks, Review).
- Identification step renders profile-driven labels, descriptions, and aliases.
- Draft data auto-saves on step navigation to `.drafts/<profile>_<timestamp>.json`.

Current known limits in this phase:

- Statements, sitelinks, and review steps are scaffold placeholders.
- No `--resume-draft` CLI flag yet.
- No export/ship action yet from the wizard UI.
- Destination-level checks (for example sitelink uniqueness) are not yet executed in the wizard.

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

- `--profile`: Profile path or profile name
- `--qid`: Wikidata item ID to fetch and validate
- `--item-json`: Path to a Wikidata item JSON file
- `--policy`: Validation policy (`strict` or `lenient`)
- `--output`: Output file path for form schemas
- `--qid` (with `form`): Optional edit-context item ID metadata
- `--source`: SpiritSafe source mode override (`github` or `local`)
- `--local-root`: Local SpiritSafe clone root (required with `--source local`)
- `--repo`: GitHub repo slug override (with `--source github`)
- `--ref`: Git reference override (with `--source github`)

## See Also

- [Profiles API](../api/profiles.md) - Programmatic profile usage
- [Entity Profiles](../profiles.md) - Profile model and wizard architecture notes
- [Mash CLI](mash.md) - Load Wikidata items for validation
