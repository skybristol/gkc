# Wikibase Datatypes

Wikibase datatypes are the first governance layer for statement values in `gkc`.

They are not the full validation story, but they are the base contract on which later rules depend.

The project treats Wikidata as the primary Commons Partner where curated data and metadata are expected to land first, with distribution outward to other partner systems after that. Because of that, `gkc` needs a precise and stable understanding of the datatype vocabulary used by Wikibase statements.

## Why This Matters

The fundamental information unit in `gkc` is the statement.

A statement includes everything the Wikibase statement architecture supports.

- mainsnak value
- qualifiers
- references
- rank and related statement-level semantics

Every value inside those structures begins with a Wikibase datatype contract.

That base datatype does not answer every validation question, but it does define the lowest common layer of meaning for a value. Higher-order constraints in `gkc` build on top of that foundation.

## Layered Governance

Datatype governance in `gkc` is layered.

1. The Wikibase datatype layer defines the primitive datatype contract such as `wikibase-item`, `url`, `time`, or `monolingualtext`.

2. The raw claim serialization layer defines how values appear in raw Wikibase JSON, including `datavalue.type` details such as `wikibase-entityid`, `time`, `quantity`, or `string`.

3. The statement-level rule layer adds constraints attached to a particular statement concept, such as whether a value must resolve to an item, whether it must come from a specific value list, or whether it must match a fixed value.

4. The profile-level rule layer adds scoped rules for how a statement behaves within a particular entity profile, including cardinality, reference expectations, qualifiers, and workflow-specific conformance behavior.

The package-owned datatype registry only owns the first two layers. It does not encode full validation or workflow behavior.

## Package-Owned Registry

`gkc` ships a package-owned Wikibase datatype registry under `gkc/registry/`.

The registry exists to give the codebase one stable internal reference for:

- canonical runtime datatype tokens
- authoritative Wikibase ontology URI mappings
- raw `datavalue.type` expectations used in Wikibase JSON processing

This registry is intentionally small. It is not a behavior engine and it is not meant to replace profile-driven validation.

## What Belongs In The Registry

For each canonical datatype token, the current registry stores:

- `ontology_uri`
- `datavalue_type`
- optional `entity_value_kind` when the datatype resolves to a specific Wikibase entity kind such as `item`

This is enough to separate semantic reference from runtime processing without mixing registry concerns with validator or serializer behavior.

## What Does Not Belong Here

The registry does not decide:

- which validator function should be called
- which widget should be rendered
- which coercion behavior should be applied
- which shipping rules should be enforced

Those remain code responsibilities in the appropriate modules.

## Module Relationship

- `wikibase` owns the package-facing access layer for the registry.
- `fermenter` consumes normalized datatype semantics when validating and coercing values.
- `bottler` consumes datatype semantics when shaping claim payloads.
- `shipper` depends on the canonical runtime datatype vocabulary for property creation and comparison.
- `spirit_safe` and later ontology-seed work may use the same registry to normalize authored datatype declarations into the runtime contract.

This separation keeps the datatype registry a stable guidepost rather than an overloaded processing layer.