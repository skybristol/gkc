# GKC Entity Profiles: Architecture and Authoring Reference

**Plain Meaning:** GKC Entity Profiles are the declarative source of truth for entity structure, validation shape, and I/O routing across the Global Knowledge Commons.

## Overview

A profile package defines:

- What data is collected for an entity type.
- How values are constrained and validated.
- How statements map to inbound and outbound systems.
- How references and qualifiers are collected for provenance and context.

Profiles are curator-facing documents and machine-readable contracts. Runtime components (`still_charger`, `cooperage`, `shipper`, and validation layers) consume profile structure directly.

## Implementation Status

Implemented and architecturally committed:

- JSON Entity Profile loading from SpiritSafe (`profiles/<QID>.json`).
- Statement/value/reference/qualifier schema structures in exported profile artifacts.
- SPARQL-driven allowed-items hydration with cached fallbacks (`cache/queries/<QID>.json`).
- Directional mapping architecture via `io_map`.
- URI/QID-aware profile graph traversal from embedded profile metadata.

## Theoretical Design Notes

The following directions are architecturally planned but may be implemented incrementally:

- Resolver-backed transform catalogs referenced by `value_transform`.
- Extended directional mapping forms (`to-through`, `from-through`) for multi-hop routing.
- Deeper profile graph traversal policies and orchestration-driven packet expansion.

These notes are design guidance for Wizard Engineer and Validation Agent implementation planning.

## Profile Artifact Structure

Current SpiritSafe publication artifacts use QID-keyed JSON profile files:

```text
profiles/<QID>.json
```

Each profile artifact contains:

- `entity`
- `identification`
- `statements`
- `metadata`

`metadata` includes `profile_graph` and `value_list_graph` summaries used by packet scaffolding and registry indexing.

The SpiritSafe manifest (`cache/manifest.json`) is generated as an artifact index over these files.

## Profile Anatomy

### Top-Level Keys (`profile.yaml`)

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| `name` | string | YES | Human-readable profile name |
| `description` | string | YES | Profile scope and domain description |
| `labels` | object | NO | Multilingual label prompt and constraints |
| `descriptions` | object | NO | Multilingual description prompt and constraints |
| `aliases` | object | NO | Multilingual alias prompt and constraints |
| `sitelinks` | object | NO | Sitelink capture and validation guidance |
| `statements` | array | YES | Statement definitions |
| `profile_graph` | object | NO | Cross-profile relationship declarations |
| YAML anchors | any | NO | Reusable patterns for references/constraints |

### Statement Keys

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| `id` | string | YES | Stable statement identifier (snake_case) |
| `label` | string | YES | Curator-facing statement name |
| `input_prompt` | string | NO | Prompt shown in wizard-style UIs |
| `guidance` | string | NO | Additional curation instructions |
| `type` | string | YES | Statement role (`statement`, `qualifier`, `reference`) |
| `io_map` | array | YES | Directional route definitions (`to`/`from`) |
| `max_count` | integer/null | NO | Statement multiplicity limit |
| `validation_policy` | string | NO | Strictness policy for validation flows |
| `behavior` | object | NO | Value/reference/qualifier editability semantics |
| `value` | object | YES | Datatype and constraint definition |
| `qualifiers` | array | NO | Nested qualifier definitions |
| `references` | object | NO | Nested reference definitions |
| `entity_profile` | string | NO | Linked profile identifier for secondary entities |

## IO Mapping Architecture

`io_map` is the canonical mapping model for all routes.

### Canonical Shape

```yaml
- id: instance_of
  label: Instance of
  type: statement
  io_map:
    - to: https://www.wikidata.org/entity/P31
      value_transform: null
    - to: https://datadistillery.wikibase.cloud/entity/P1
      value_transform: null
    - from: resolvable_input_fetcher
      value_transform: normalize_to_item
  value:
    type: item
```

### Entry Contract

Each `io_map` entry must include exactly one directional key:

- `to`: outbound destination identifier.
- `from`: inbound source identifier.

Optional fields:

- `value_transform`: transform resolver target (`null` for identity behavior).

### Identifier Rules

Use resolvable identifiers as first-class routing keys.

- Full IRIs for systems that expose stable entity/property IRIs.
- Resolver keys for abstracted ingestion routes when no stable IRI is available.

Examples:

- `https://www.wikidata.org/entity/P31`
- `https://datadistillery.wikibase.cloud/entity/P1`
- `csv:tribe_status_column`
- `api:tribal_directory.classification`

### Runtime Semantics

- `from` mappings are inbound transformation routes (fermentation stage).
- `to` mappings are outbound serialization routes (bottling stage).
- Internal inferencing/distillation remains runtime-owned and may consume declared transform references.

### Validation Requirements

Validation of `io_map` should enforce:

- `io_map` exists and is non-empty.
- Each entry has exactly one of `to` or `from`.
- No duplicate `to` routes in a statement.
- No duplicate `from` routes in a statement.
- `value_transform` is either `null` or a valid resolver target format.

## Validation Policy

`validation_policy` controls strictness when processing existing and newly entered data.

Supported policy values:

- `allow_existing_nonconforming`
- `strict`

### `allow_existing_nonconforming`

Use when preserving existing external data is operationally important while still guiding new curation toward conformance.

### `strict`

Use when all encountered values must satisfy profile constraints before contribution is accepted.

## Statement Behavior

`behavior` controls mutability and responsibility boundaries for value, qualifiers, and references.

Canonical shape:

```yaml
behavior:
  value: editable         # editable | fixed | derived
  qualifiers: editable    # editable | fixed | derived
  references: editable    # editable | fixed | derived
```

## Datatype Reference

Common datatypes:

- `item`
- `string`
- `url`
- `quantity`
- `time`
- `monolingualtext`
- `globecoordinate`
- `external-id`
- `commonsMedia`

Datatype-specific constraints are declared under `value` and follow explicit schema validation rules.

## References and Provenance

Reference definitions are nested under `references` and can be reused with YAML anchors.

Example:

```yaml
standard_reference: &standard_reference
  min_count: 1
  allowed:
    - id: stated_in
      type: item
      io_map:
        - to: https://www.wikidata.org/entity/P248
          value_transform: null
    - id: reference_url
      type: url
      io_map:
        - to: https://www.wikidata.org/entity/P854
          value_transform: null
```

## Qualifiers

Qualifier definitions are nested statement-like structures with their own `io_map`, datatype, and constraints.

Example:

```yaml
qualifiers:
  - id: point_in_time
    label: Point in time
    type: qualifier
    io_map:
      - to: https://www.wikidata.org/entity/P585
        value_transform: null
    value:
      type: time
```

<a id="statement-types-reference"></a>

## Statement Types Reference

Statement `type` currently supports the following roles:

- `statement`: primary claim/value carried by the entity.
- `qualifier`: contextual modifier attached to a statement.
- `reference`: provenance/source statement attached to a statement.

Profiles should keep role usage explicit and avoid implicit promotion between roles in runtime code.

## Entity Metadata Blocks

Profiles can define metadata capture structure for:

- `labels`
- `descriptions`
- `aliases`
- `sitelinks`

These blocks define curation prompts and constraints, not mapping routes.

## Secondary Entities and Profile References

Use `entity_profile` on a statement when the value represents a secondary entity curated through another profile package.

This enables orchestrated multi-entity packet assembly while keeping profile boundaries explicit.

## Profile Graphs & Cross-References

`profile_graph` captures inter-profile adjacency and traversal intent.

Current committed usage:

- Declaring neighbors.
- Declaring edge metadata (`target_profile`, `via_statement`, `relationship_type`, cardinality hints).

Future implementations may use graph metadata for packet expansion and cross-profile recommendation logic.

## Profile Metadata Schema (`metadata.yaml`)

Canonical fields:

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| `name` | string | YES | Profile display name |
| `description` | string | YES | Registry-facing summary |
| `version` | string | YES | Semantic version |
| `status` | string | YES | Publication status |
| `published_date` | date | NO | Publication date |
| `authors` | array | NO | Author list |
| `maintainers` | array | NO | Maintainer list |
| `source_references` | array | NO | External conceptual sources |
| `related_profiles` | array | NO | Related profile IDs |
| `profile_graph` | object | NO | Graph metadata mirror |
| `community_feedback` | object | NO | Issue tracker links |
| `datatypes_used` | array | NO | Discovery metadata |

## Best Practices

- Keep statements domain-cohesive and curator-readable.
- Prefer explicit constraints over inferred behavior.
- Reuse anchors for reference structures.
- Keep `io_map` routes explicit and unambiguous.
- Keep transform references declarative; enforce execution policy in code.
- Keep examples synchronized with active schema decisions.

## Complete Example (Minimal)

```yaml
name: Federally Recognized Tribe
description: Canonical profile for federally recognized tribal entities

statements:
  - id: instance_of
    label: Instance of
    type: statement
    io_map:
      - to: https://www.wikidata.org/entity/P31
        value_transform: null
      - to: https://datadistillery.wikibase.cloud/entity/P1
        value_transform: null
    value:
      type: item
      fixed: Q7840353

  - id: official_website
    label: Official website
    type: statement
    io_map:
      - to: https://www.wikidata.org/entity/P856
        value_transform: null
    value:
      type: url
```

## Step-by-Step Authoring Flow

1. Define domain scope and entity boundaries.
2. Define statement set and datatypes.
3. Add constraints and validation policy.
4. Add `io_map` routes for outbound and inbound systems.
5. Add references/qualifiers and reusable anchors.
6. Add metadata, README, and CHANGELOG.
7. Validate profile package and run hydration checks.

## Future Enhancements

- Resolver-backed transform catalogs.
- Extended route operators (`to-through`, `from-through`).
- Richer graph-driven multi-entity packet orchestration.
- Automated linting for route consistency across profile sets.

## See Also

- [Architecture Overview](../architecture/index.md)
- [Profile Loading Architecture](../architecture/profile-loading.md)
- [SpiritSafe Registry](../architecture/SpiritSafe.md)
- [Validation Architecture](../architecture/validation-architecture.md)
