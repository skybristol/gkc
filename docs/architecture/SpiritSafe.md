# SpiritSafe Registry Architecture

SpiritSafe is the artifact registry for GKC Entity Profiles and value-list caches.

## Purpose

SpiritSafe provides deterministic, version-controlled artifacts consumed by `gkc` without requiring live Wikibase reads at packet assembly time.

## Repository Shape

- `profiles/<QID>.json` - JSON Entity Profiles.
- `queries/<QID>.sparql` - value-list query definitions.
- `cache/entities/*.json` - Wikibase cache substrate.
- `cache/queries/<QID>.json` - hydrated value-list artifacts.
- `cache/manifest.json` - URI-keyed artifact index.

## Build Pipeline

1. Refresh `cache/entities` from Wikibase.
2. Export JSON profiles to `profiles/<QID>.json`.
3. Export and hydrate value-list queries.
4. Build `cache/manifest.json` from artifacts.

`cache/manifest.json` is built by:

```bash
gkc --json spiritsafe manifest build --source local --local-root .
```

## Runtime Consumption Model

`gkc` consumes:

- profile definitions from `profiles/<QID>.json`
- value-list items from `cache/queries/<QID>.json`
- manifest index from `cache/manifest.json` for registry/discovery tooling

Packet assembly routes (`create_curation_packet`) do not require manifest lookups.

## Manifest Sections

- `generated_at`
- `source`
- `profiles`
- `entities`
- `queries`
- `value_lists`

This structure supports CLI registry operations and downstream wizard discovery without rehydrating source data.

## Governance Notes

- SpiritSafe artifacts are generated outputs and should not be hand-edited.
- Workflow automation commits artifact updates with `[skip ci]` suffixes to prevent looped runs.

## Theoretical Design Notes

- Additional manifest facets for UI-index optimization are possible but not currently committed.
- Future registry analytics may derive from manifest deltas, but this remains exploratory.
