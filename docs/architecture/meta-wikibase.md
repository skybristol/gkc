# Meta-Wikibase Architecture

A meta-wikibase is the semantic authoring system of record for GKC profile, statement, value-list, and guidance semantics. It is the authoring-side of the SpiritSafe, which stores the materialized artifacts consumed by the runtime.

This document describes the generic contract. The current reference implementation is the [Data Distillery Wikibase](DataDistillery-Wikibase.md).

## Core Role

A meta-wikibase exists to do the parts of the job that a file-only artifact registry does poorly, with an eye toward potential implementation within Wikidata:

- Collaborative semantic authoring.

- Multilingual labels, descriptions, aliases, prompts, and guidance.

- Queryable relationships among profiles, statements, value lists, and reference semantics.

- Discovery of ontology-level conventions that should remain curator-maintained rather than hardcoded in runtime code.

SpiritSafe then materializes those semantics into deterministic artifacts for runtime consumption.

The operating pattern is:

- Define in a meta-wikibase.

- Materialize in SpiritSafe.

- Execute in `gkc`.

## Runtime Integration Contract

The current runtime contract is intentionally narrow.

`gkc.runtime_config` resolves read-oriented meta-wikibase integration settings in this order:

1. `META_WB_CONFIG`, when set explicitly, points to the config file to load.

2. If `META_WB_CONFIG` is not set, `gkc` auto-discovers one of the following paths from the current working directory upward through parent directories:

  - `config/meta-wikibase.yaml`
  - `config/meta-wikibase.yml`
  - `config/dd-wikibase.yaml`
  - `config/dd-wikibase.yml`
  - `meta-wikibase.yaml`
  - `meta-wikibase.yml`
  - `dd-wikibase.yaml`
  - `dd-wikibase.yml`

3. `META_WB_API_URL` overrides the config-file `api_url` value.

4. `META_WB_SPARQL_ENDPOINT` overrides the config-file `sparql_endpoint` value.

5. If no config file or override is present, `gkc` falls back to built-in defaults.

This contract is read-only. It does not define an authentication framework.

## Authentication Boundary

Read-oriented mash operations should remain unauthenticated unless a specific capability requires otherwise.

Authenticated MediaWiki writes remain a separate concern:

- `WikiverseAuth` is the generic MediaWiki authentication client.

- `shipper` and other explicit write flows are the main consumers of authenticated MediaWiki sessions.

- `WIKIVERSE_*` remains the generic environment-based authentication surface when explicit credentials are not passed directly.

This keeps meta-wikibase instance targeting separate from write credentials.

## Config File Shape

The reference YAML shape is:

```yaml
meta_wikibase:
  id: datadistillery-wikibase
  label: Data Distillery Wikibase
  api_url: https://datadistillery.wikibase.cloud/w/api.php
  sparql_endpoint: https://datadistillery.wikibase.cloud/query/sparql

  semantic_conventions:
    name_identifier_property_id: P214
    internal_name_identifier_prefix: "_"
```

Current runtime use is limited to endpoint resolution plus preservation of semantic-convention metadata for downstream consumers.

## Package-Owned Init Fixture

In addition to the instance-targeting config file, `gkc` now ships a package-owned Meta-Wikibase initialization fixture under `gkc/registry/meta_wb_init.yaml`.

This fixture is not environment config. It is a package artifact that defines the authored backbone terms needed to bootstrap a clean Meta-Wikibase with the minimum ontology required by `gkc` and SpiritSafe.

The current fixture covers:

- backbone properties such as `instance_of`, `subclass_of`, `name_identifier`, and profile/statement linkage terms
- backbone item classes such as `entity`, `entity_profile`, `entity_statement`, and `value_list`
- datatype template items such as `wikibase-item`, `url`, `time`, and `monolingualtext`

## Datatype Contract In The Init Fixture

The package fixture uses canonical runtime datatype names, not ontology-name spellings from SPARQL such as `WikibaseItem`, `Url`, or `String`.

That means authored property definitions in `meta_wb_init.yaml` use values such as:

- `wikibase-item`
- `url`
- `string`
- `quantity`
- `monolingualtext`

This keeps the bootstrap artifact aligned with the package-owned datatype registry described in [Wikibase Datatypes](wikibase-datatypes.md).

The supporting `gkc.wikibase` helpers still normalize ontology URI and ontology-name forms when needed, but the checked-in fixture itself should remain in canonical runtime form.

## Runtime Helpers

`gkc.wikibase` owns the package-facing helpers for this fixture.

The initial helper surface includes:

- loading the package-owned init document
- normalizing authored datatype values against the canonical datatype registry
- building a typed index over properties, items, and derived internal name identifiers

This keeps the fixture, datatype registry, and later ontology-init logic aligned behind one Wikibase-specific access layer.

## Continuing Work on Semantic Definition

The current `meta_wb_init.yaml` fixture is intended to capture the minimum authored backbone needed to bootstrap the Meta-Wikibase and support the present runtime architecture.

This means the seed intentionally includes:

- core entity/profile/statement/value-list concepts
- backbone linkage properties
- datatype template items aligned to the canonical runtime datatype registry
- selected operational guidance terms already exercised in code and workflow design

It also intentionally defers some deeper semantic layers until they are hardened through real use cases.

In particular, `gkc` is not currently trying to fully enumerate:

- richer cardinality concepts beyond the lightweight limits already in use
- separate ontology terms for every value-constraint or coercion mode
- the full class hierarchy needed to distinguish abstract statement definitions from profile-context-specific statement use

This is a deliberate design choice, not an omission by accident.

The expectation is that these concepts will be added as contribution workflows, validation primitives, and cross-system shipping behavior become concrete enough to justify stable semantic labels in the Meta-Wikibase and its reference implementation.

## Boundary

The package-owned init fixture is the right place for authored bootstrap ontology terms that should ship with `gkc`.

It is not the place for:

- instance-specific URLs or endpoints
- user credentials
- generated SpiritSafe runtime artifacts
- environment overrides

Those concerns remain outside the fixture and continue to belong to config or materialized artifact layers.

## What Belongs Here

The meta-wikibase config file is the right place for instance-level facts such as:

- Canonical API URL.

- Canonical SPARQL endpoint.

- Stable semantic bootstrap identifiers that are intrinsic to the instance.

- Explicit semantic conventions such as the internal `name_identifier` prefix contract.

It is not the right place for user credentials.

## Reference Implementation

The checked-in reference implementation lives in the SpiritSafe repository as `config/dd-wikibase.yaml`.

For the concrete Data Distillery infrastructure details, see [Data Distillery Wikibase](DataDistillery-Wikibase.md).