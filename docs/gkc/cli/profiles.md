# Profiles CLI

Plain meaning: Work with SpiritSafe-backed Entity Profiles and value-list artifacts from the command line.

## Overview

The `gkc profile` command group handles profile export, value-list hydration, and profile package loading.

Profile export and value-list hydration now rely on semantic anchors to resolve internal ontology concepts. For background, see [Semantic Anchors](../../architecture/meta-wikibase/semantic-anchors.md).

Current subcommands:

- `gkc profile export-json`
- `gkc profile value-lists hydrate`
- `gkc profile package load`
- `gkc profile package validate`

## Profile Commands

### `gkc profile export-json`

Build JSON Entity Profiles from `still/entities` and write `<QID>.json` files.

```bash
gkc profile export-json --source local --local-root /path/to/SpiritSafe --output /path/to/SpiritSafe/still/profiles
```

Common options:

- `--cache-entities-dir`: Override the cache entity directory.
- `--profile-id`: Restrict export to one or more specific profile QIDs.
- `-o`, `--output`: Output directory for per-profile JSON files.
- `--summary-output`: Optional summary JSON file for export diagnostics.
- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.

When `--cache-entities-dir` points into a normal local SpiritSafe checkout, this route loads `config/semantic_anchors.json` and local Meta-Wikibase semantic conventions automatically. If you point it at an ad hoc cache directory outside that layout, use the Python API instead and pass an explicit semantic-anchor document.

### `gkc profile value-lists hydrate`

Export value-list queries and hydrate `still/value_lists/cache/<QID>.json`.

```bash
gkc profile value-lists hydrate --source local --local-root /path/to/SpiritSafe
```

Common options:

- `--cache-entities-dir`: Override the cache entity directory.
- `--queries-dir`: Override the output directory for exported SPARQL query files.
- `--cache-queries-dir`: Override the hydrated value-list cache directory.
- `--value-list-id`: Restrict hydration to one or more specific value-list QIDs.
- `--api-url`: API URL used for talk-page retrieval.
- `--endpoint`: SPARQL endpoint used for hydration.
- `--page-size`: Query page size for pagination.
- `--max-results`: Maximum total results per value list query.
- `--continue-on-error`: Keep hydrating other value lists if one fails.
- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.

Like profile export, this route expects semantic-anchor-backed local context when operating from a SpiritSafe checkout.

### `gkc profile package load`

Load a primary JSON profile and related profiles from embedded `metadata.profile_graph`.

```bash
gkc profile package load --profile Q4 --depth 1 --source local --local-root /path/to/SpiritSafe
```

### `gkc profile package validate`

Validate package structure fields.

```bash
gkc profile package validate --profile Q4 --depth 1 --source local --local-root /path/to/SpiritSafe
```

Common options for package commands:

- `--profile`: Primary profile QID or entity URI.
- `--depth`: Related profile depth.
- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.

## Common Source Flags

Most `gkc profile` routes support:

- `--source {github,local}`
- `--local-root`
- `--repo`
- `--ref`

## Output Flags

- `--json`
- `--verbose`

## Related Commands

- `gkc packet build`
- `gkc wizard`
