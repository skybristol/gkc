# Semantic Anchors

Semantic anchors are the transformed runtime artifact that binds authored ontology semantics in `meta_wb_init.yaml` to concrete Meta-Wikibase entity URIs.

Plain meaning: runtime code resolves internal names such as `_has_statement` and `_name_identifier` from one deterministic artifact file, instead of hardcoding P/Q ids.

## Source Contract And Artifact

The architecture has two distinct layers that must stay synchronized.

### Source Contract

`gkc/registry/meta_wb_init.yaml` is the source contract.

It defines the required ontology entities, required authored fields, expected datatypes for properties, and value-list classes.

### Transformed Artifact

`SpiritSafe/config/semantic_anchors.json` is the transformed runtime artifact.

It is generated from the source contract plus live Meta-Wikibase resolution and contains stable runtime lookup records keyed by internal name identifier.

The artifact stores `id` as the full entity URI.

If a simple QID/PID token is needed, resolver helpers derive that from the URI.

## Operational Lifecycle

The contract lifecycle is:

1. Load and normalize `meta_wb_init.yaml`.

2. Resolve each declared entity against Meta-Wikibase state (via SpiritSafe cache-backed workflows).

3. Produce a conformance plan and report required corrections.

4. Optionally execute corrective actions.

5. Transform resolved entities into `semantic_anchors.json` with deterministic ordering.

6. Use shared resolver APIs in `gkc.spirit_safe` for all runtime semantic lookups.

Default mode is report-only. Execution is opt-in.

## Corrective-Action Semantics

Conformance processing uses this identity precedence:

1. Match by `name identifier` claim.

2. If missing, fallback to label + description (+ datatype for properties).

3. If fallback resolves exactly one entity, repair the `name identifier` claim.

4. If fallback is ambiguous, stop that entity as a hard blocker.

Corrective actions may include:

- create missing items/properties
- repair `name identifier` claim drift
- align labels, descriptions, and declared authored attributes
- align `instance of` and `subclass of` semantics
- align required talk-page payload content for value-list entities

## Value-List Talk-Page Contract

Value-list talk payload extraction is class-coupled.

- `sparql_value_list` expects a `<sparql>` block on the item talk page
- `embedded_value_list` expects a `<syntaxhighlight lang="json">` block on the item talk page

For each block type, only the first matching block is extracted.

Extraction paths are:

- first `<sparql>` -> `SpiritSafe/still/value_lists/<QID>.sparql`
- first JSON `<syntaxhighlight>` -> `SpiritSafe/still/value_lists/cache/<QID>.json`

SPARQL hydration remains a separate workflow from talk-page extraction.

## Runtime Boundary

Runtime code should treat semantic anchors as a required dependency for ontology concept resolution.

Anchor-backed workflows expect:

- a Meta-Wikibase config file under SpiritSafe `config/`
- `config/semantic_anchors.json`

When these are unavailable, workflows should fail explicitly rather than silently falling back to stale assumptions.

## Module Ownership

Ownership split:

- `gkc.wikibase`: normalize source contract and compile required semantic requirements
- `gkc.spirit_safe`: conformance orchestration, artifact transform, and runtime resolver loading
- `gkc.fermenter`: semantic-anchor document validation primitives

## Practical Rules

- Use `meta_wb_init.yaml` as the only authored source for required ontology backbone semantics.
- Do not edit `SpiritSafe/config/semantic_anchors.json` by hand.
- Do not introduce hardcoded metaWikibase P/Q ids where semantic anchors exist.

## Related Documentation

- [Meta-Wikibase Architecture](index.md)
- [SpiritSafe Architecture](../SpiritSafe/index.md)
- [Module Contracts](../module-contracts.md)
- [SpiritSafe CLI](../../gkc/cli/spiritsafe.md)