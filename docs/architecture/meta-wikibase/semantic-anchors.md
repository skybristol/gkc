# Semantic Anchors

Semantic anchors are the bridge between the authored internal ontology in the Meta-Wikibase and the stable IDs that runtime code needs to use.

Plain meaning: a semantic anchor says that an internal concept such as `_entity_profile`, `_has_statement`, or `_value_list` currently resolves to a specific Wikibase entity ID such as `Q3`, `P157`, or `Q7`.

They exist so that runtime code can depend on semantic names instead of baking Data Distillery-specific `P` and `Q` IDs into implementation logic.

## Why They Exist

The project needs three things at once:

- an authored ontology that lives in a Meta-Wikibase
- deterministic runtime artifacts that can be stored in SpiritSafe
- runtime code that stays aligned with the authored ontology even if concrete IDs change

Semantic anchors are the narrow contract that connects those layers.

Instead of asking runtime code to know that `_has_value` means `P161`, we generate and validate an artifact that says so explicitly.

## Core Idea

There are three different things involved, and keeping them separate matters.

### 1. Package-Owned Ontology Seed

`gkc/registry/meta_wb_init.yaml` defines the minimum authored ontology backbone that `gkc` expects to exist.

This layer defines internal semantic names such as:

- `_entity`
- `_entity_profile`
- `_has_statement`
- `_has_value`
- `_value_list`

At this layer, we are defining concepts and expected datatypes, not binding to a specific running Wikibase instance.

### 2. SpiritSafe Semantic-Anchor Artifact

`cache/config/semantic_anchors.json` is the materialized artifact that maps those internal names to the concrete IDs currently present in the Meta-Wikibase-backed cache.

Typical shape:

```json
{
  "metadata": {
    "generated_at": "2026-04-04T00:00:00Z",
    "property_count": 12,
    "item_count": 8
  },
  "entities": {
    "_has_statement": {
      "id": "P157",
      "entity": "https://datadistillery.wikibase.cloud/entity/P157",
      "datatype": "wikibase-item"
    },
    "_entity_profile": {
      "id": "Q3",
      "entity": "https://datadistillery.wikibase.cloud/entity/Q3"
    }
  }
}
```

This is the runtime-facing lookup document.

### 3. Runtime Resolver

Runtime code in `gkc.spirit_safe` loads the semantic-anchor artifact, validates it against the package-owned contract, and resolves the IDs it needs through a shared resolver.

That means runtime code asks for `_has_statement` or `_value_list`, not for a hardcoded `P157` or `Q7`.

## Lifecycle

The intended flow is:

1. Define the required ontology backbone in `meta_wb_init.yaml`.

2. Author and maintain the concrete ontology terms in the Meta-Wikibase.

3. Materialize cache entities in SpiritSafe.

4. Build `cache/config/semantic_anchors.json` from those cached entities.

5. Validate that artifact against the package-owned contract.

6. Load the artifact in runtime code and resolve internal concepts through the shared lookup layer.

This keeps the authored semantic layer, the materialized artifact layer, and the runtime layer synchronized while preserving clear boundaries between them.

## What Semantic Anchors Do And Do Not Do

Semantic anchors do:

- map internal semantic names to concrete property and item IDs
- preserve expected property datatypes for runtime checks
- give runtime consumers one stable lookup mechanism
- let tests and ad hoc callers provide a synthetic anchor document explicitly when they are not operating inside a full SpiritSafe checkout

Semantic anchors do not:

- replace the authored ontology in the Meta-Wikibase
- validate the full ontology hierarchy or all semantic modeling choices
- define endpoint URLs, credentials, or other environment configuration
- eliminate the need for SpiritSafe materialization

## Runtime Contract

Anchor-backed runtime workflows assume two things are present under a local SpiritSafe root:

- `config/dd-wikibase.yaml` or another supported Meta-Wikibase config filename under `config/`
- `cache/config/semantic_anchors.json`

The config file supplies the semantic convention needed to interpret internal names:

- `semantic_conventions.name_identifier_property_id`
- `semantic_conventions.internal_name_identifier_prefix`

The semantic-anchor artifact supplies the actual ID bindings.

When both are available, runtime consumers such as profile export, value-list hydration, and entity-index generation can resolve internal ontology labels consistently.

When they are not available, anchor-backed workflows fail deliberately rather than silently falling back to stale assumptions.

## Synthetic And Test-Only Use

Not every caller works from a full SpiritSafe checkout.

For tests or ad hoc tooling that only has a temporary `cache/entities` directory, the relevant APIs accept an explicit `semantic_anchor_document` argument.

Use that route when:

- constructing synthetic cache fixtures in tests
- exercising one runtime helper in isolation
- running outside the standard SpiritSafe directory layout

Do not treat that override path as the normal production contract. The normal production contract is the validated artifact under `cache/config/semantic_anchors.json`.

## Where To Look In The Codebase

The main ownership split is:

- `gkc.wikibase`: compile the package-owned semantic-anchor contract from `meta_wb_init.yaml`
- `gkc.fermenter`: validate semantic-anchor documents against that contract
- `gkc.spirit_safe`: build, load, and consume semantic-anchor artifacts during runtime workflows

The main operator-facing CLI routes are:

- `gkc spiritsafe semantic-anchors build`
- `gkc spiritsafe semantic-anchors validate`

The main runtime consumers currently relying on semantic anchors are:

- JSON profile export
- value-list discovery and hydration
- SpiritSafe entity-index generation

## Practical Rule Of Thumb

If you are working on authored ontology structure, start with the package-owned init fixture and the Meta-Wikibase.

If you are working on SpiritSafe artifact maintenance, start with the semantic-anchor build and validate routes.

If you are working on runtime code, never introduce new hardcoded internal `P` or `Q` IDs when the concept should instead resolve through a semantic anchor.

## Related Documentation

- [Meta-Wikibase Architecture](index.md)
- [SpiritSafe Architecture](../SpiritSafe/index.md)
- [SpiritSafe CLI](../../gkc/cli/spiritsafe.md)
- [SpiritSafe API](../../gkc/api/spirit_safe.md)
- [Fermenter API](../../gkc/api/fermenter.md)