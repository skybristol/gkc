# GKC Architecture Overview

## Introduction

The **Global Knowledge Commons (GKC)** is a framework for understanding and working with structured knowledge across multiple open public platforms. The initial design focuses on Wikidata, Wikimedia Commons, Wikipedia templates, and OpenStreetMap.

The project uses a **data distillery** metaphor to describe the pipeline that converts heterogeneous inputs into validated, platform-ready outputs. GKC Entity Profiles define canonical entity forms made up of individual statements backed by evidence (references). Distilled data are bottled for outlets - GKC Partners - and shipped via authenticated Application Programming Interfaces (APIs).

GKC architecture is best understood through two coordinated lenses:

1. **Infrastructure components** — where semantic definitions are authored, materialized, and executed.
2. **Architectural components** — the core semantic/data units that flow through curation and shipping.

Infrastructure components:

1. **Meta-wikibase** — semantic authoring system of record for profiles, statements, value lists, and linkage semantics.
2. **SpiritSafe repository** — materialized artifact registry (JSON profiles, query files, hydrated caches, and supporting generated artifacts).
3. **GKC Python package** — runtime engine that consumes SpiritSafe artifacts to assemble packets (`still_charger`), validate/coerce (`fermenter`), plan writes, and ship.

Architectural components:

1. **GKC Entity Profiles** — declarative definitions of entity structure and context.
2. **GKC Entity Statements** — reusable statement primitives used as claims, qualifiers, and references.
3. **GKC Value Lists** — curated allowed-item domains used to guide and constrain selection.
4. **GKC Curation Packets** — actionable packet structures combining metadata rulesets and fillable data slots.

This pairing enables a consistent pattern: **define in a meta-wikibase, materialize in SpiritSafe, execute in gkc**.

The JSON Schema layer remains important as a machine-facing contract derived from these components, but it is a representation layer rather than a top-level architectural component.

Entity Statements, Entity Profiles, and Value List semantics are defined and organized within a meta-wikibase. The current reference implementation is the [Data Distillery Wikibase](meta-wikibase/DataDistillery-Wikibase.md). These semantics are exported into [SpiritSafe](https://github.com/skybristol/SpiritSafe), which is then consumed by the GKC runtime package.

---

## Infrastructure Components

### Meta-Wikibase

A meta-wikibase is the semantic source of truth. It is where profile, statement, value-list, and linkage semantics are authored and curated.

The meta-wikibase defines the **foundation form** of architectural components:

- Profile composition directives.
- Reusable statement defaults and scoped overrides.
- Value-list membership and refresh semantics.
- Prompt/guidance/error messaging and multilingual metadata.

For the generic contract, see [Meta-Wikibase Architecture](meta-wikibase/index.md). For the current concrete deployment, see [Data Distillery Wikibase](meta-wikibase/DataDistillery-Wikibase.md).

### SpiritSafe Repository

SpiritSafe is the artifact registry. It stores the **materialized/actionable form** of DD semantics as deterministic files and indexes.

SpiritSafe publishes:

- `still/profiles/<QID>.json` JSON Entity Profile artifacts.
- `still/value_lists/queries/<QID>.sparql` value-list query definitions.
- `still/entities/*.json` raw semantic cache snapshots.
- `still/value_lists/cache/<QID>.json` hydrated value-list artifacts.
- `config/semantic_anchors.json` semantic lookup artifact.
- `partners/wikimedia_sites.json` sitelink source artifact.

### GKC Python Package

The `gkc` Python package is the runtime execution layer. It consumes SpiritSafe artifacts and runs curation workflows end-to-end.

At runtime, `gkc`:

- Loads JSON profiles and profile graph metadata.
- Builds uncharged and charged curation packets.
- Validates/coerces values and emits conformance notices.
- Plans destination writes and executes shipping workflows.

---

## Core Architectural Components

### GKC Entity

A **GKC Entity** is a semantically coherent representation of a real-world thing rooted in the Wikibase/Wikidata model and extended across platforms in the Global Knowledge Commons.

Multiple platforms contribute to and consume a single GKC Entity:

- **Wikibase/Wikidata foundation**: Labels, descriptions, aliases, statements, qualifiers, references, and sitelinks.
- **Linked entities**: Item-valued statements naturally connect entities.
- **Multi-entity workflows**: One curation action may require adding or updating related entities.
- **Cross-platform integration**: Canonical data in Wikidata can drive content in Commons, Wikipedia, and OSM.

### GKC Entity Profile

**Definition:** GKC Entity Profiles are declarative definitions of the canonical structure, semantics, and cross-platform meaning of a real-world entity in the Global Knowledge Commons.

**Implementation:** Profiles are materialized as JSON Entity Profile artifacts in SpiritSafe (`still/profiles/<QID>.json`) and consumed directly by runtime modules, serving as the authoritative source of truth for:

- **Entity structure** — What statements, qualifiers, and references constitute the entity
- **Validation rules** — Constraints, datatypes, cardinality, required vs optional fields
- **Cross-platform semantics** — Mappings to Wikidata properties, Wikimedia Commons categories, OSM tags
- **UI generation** — Field labels, guidance text, input prompts, allowed-items lists
- **Profile relationships** — How entities link to other entity types (profile graphs)

**Key Characteristics:**

- **Declarative, not imperative** — Profiles describe *what* an entity is, not *how* to build it
- **Human-readable and machine-executable** — JSON artifacts provide stable runtime contracts while preserving curator-facing semantics
- **Version-controlled** — Managed in SpiritSafe repository with CHANGELOG tracking
- **Profile-driven workflows** — Wizards, validation engines, and serializers consume profiles directly

**Related Documentation:**

- [Entity Profiles: Construction and Reference](../gkc/profiles.md)
- [SpiritSafe Registry](SpiritSafe/index.md)

### GKC Value List

**Definition:** GKC Value Lists are curated allowed-item domains used by statement value contracts to guide and constrain selection behavior in packet and wizard workflows.

**Foundation in DD Wikibase:** Value List semantics, scope, and refresh policy are curated as first-class entities.

**Materialized form in SpiritSafe:**

- Query definitions in `still/value_lists/queries/<QID>.sparql`.
- Hydrated results in `still/value_lists/cache/<QID>.json`.
- Linkage metadata in profile `metadata.value_list_graph`.

**Runtime role in gkc:** Value Lists provide deterministic allowed-item sets for validation, UX guidance, and offline operation.

### GKC Entity JSON Schemas

**Definition:** GKC Entity JSON Schemas are machine-readable, serializable representations of GKC Entity Profiles that provide stable contracts for API routes, external tools, and inter-profile composition.

**Implementation:** Generated programmatically from materialized JSON Entity Profile contracts and related runtime models, JSON Schemas:

- **Define data contracts** — External tools can validate GKC Entity JSON without importing Python code
- **Enable profile composition** — Profiles reference one another via `entity_profile` statements, forming graphs
- **Support dynamic UI generation** — Web frontends can generate forms from JSON Schema definitions
- **Provide type safety** — IDE autocomplete, validation, and API documentation all derive from schemas

**Relationship to Profiles:**

```
SpiritSafe JSON Profile → Runtime Model → JSON Schema → API Contract
                         ↓               ↓
                    Validation      External Tools
```

Profiles are the *source of truth*; JSON Schemas are the *machine interface*.

**Related Documentation:**

- [GKC Entity JSON Schema](../gkc/entity-json-schema.md)
- [Profile Graphs & Cross-References](../gkc/profiles.md#profile-graphs-cross-references)

### GKC Curation Packets

**Definition:** A GKC Curation Packet is the actionable bundle of information required to create or edit one or more entities. It combines:

- **Primary entity** — The entity being directly curated
- **Related entities** — Secondary entities linked via profile graph (e.g., offices, organizations)
- **Packet metadata** — Profile ruleset, linkage graph, provenance, source context, and integrity sealing
- **Dual-key identity system** — `name_identifier` is the human-facing key while `id` (URI) remains canonical for joins, provenance, and round-trip mapping

**Packet Lifecycle:**

1. **Creation** — Wizard or bulk loader initializes packet from profile(s)
2. **Population** — User (wizard) or automation (bulk op) fills entity data
3. **Validation** — Profile-driven validators check completeness and constraints
4. **Shipping** — Serializers transform packet → Wikidata JSON, resolve cross-entity references
5. **Post-creation** — QIDs returned from Wikidata; packet updated with `status: waiting_for_qid`

**Status Values:**

- `in_progress` — Curator actively editing
- `ready_to_resolve_refs` — All data entered; awaiting cross-entity QID resolution
- `waiting_for_qid` — Shipped to Wikidata; awaiting item creation response

**Creation Path Breadcrumbs:**

The `creation_path` field tracks entity provenance:

- `primary` — Root entity loaded directly by wizard/bulk op
- `primary.office_held_by_head_of_state` — Created via sub-wizard from primary entity's office statement
- `primary.headquarters.location` — Nested entity (location of headquarters of primary)

This enables dependency ordering (ship entities depth-first), audit trails, and rollback logic.

**Related Documentation:**

- [GKC Entity JSON Schema](../gkc/entity-json-schema.md)
- [Wizard Multi-Entity Curation](../gkc/wizard.md#multi-entity-curation-sessions)
- [Still Charger Architecture](still_charger.md)

### SpiritSafe

**SpiritSafe** is the profile registry and supporting query/cache infrastructure. It stores materialized profile artifacts (`still/profiles/<QID>.json`), query files (`still/value_lists/queries/*.sparql`), cache artifacts (`still/entities`, `still/value_lists/cache`), and supporting generated artifacts such as `config/semantic_anchors.json` used by runtime loading in local or GitHub-backed modes.

For complete documentation on SpiritSafe, see [SpiritSafe Registry](SpiritSafe/index.md).

### SpiritSafe Registry Metadata

**Purpose:** Registry/discovery workflows read profile metadata directly from `still/profiles/*.json` instead of relying on a separate manifest or entity-index artifact.

**Usage:** Validation engines, packet builders, and CLI discovery commands consume the embedded profile metadata to render labels, traverse profile graphs, and discover value-list routes without a second indexing layer.

---

## Architectural Data Flow

### Profile → Wizard → Packet → Wikidata

```
┌─────────────────────────────────────────────────────────────────┐
│                     SpiritSafe Registry                         │
│  profiles/Q4.json                                               │
│  profiles/Q39.json                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │ Load profiles
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                  GKC Spirit Safe Module                         │
│  - Load JSON Entity Profiles from SpiritSafe artifacts          │
│  - Build profile graph (TribalGov → Office linkage)             │
│  - Hydrate SPARQL allowed-items lists                           │
└────────────────────┬────────────────────────────────────────────┘
                     │ Provide profile models
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                     GKC Wizard                                  │
│  - Generate 5-step UI from profile metadata                     │
│  - Create curation packet (entity slots keyed by profile/name)  │
│  - Collect user input with real-time validation                 │
└────────────────────┬────────────────────────────────────────────┘
                     │ Curation packet (unsaved)
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                  Validation Engine                              │
│  - Check completeness (required fields filled?)                 │
│  - Validate constraints (datatypes, cardinality, allowed-items) │
│  - Cross-entity validation (future: office.inception ≤ gov.inception) │
└────────────────────┬────────────────────────────────────────────┘
                     │ Validated packet
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Shipper                                    │
│  - Serialize GKC Entity JSON → Wikidata JSON                    │
│  - Resolve cross-entity references via profile statements        │
│  - Ship entities depth-first (office before tribal gov)         │
└────────────────────┬────────────────────────────────────────────┘
                     │ Wikidata API calls
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Wikidata                                     │
│  - Create office item → Q999888 (new QID)                       │
│  - Create tribal gov item → Q999889                             │
│  - Tribal gov.P1906 = Q999888 (office held by head of state)    │
└─────────────────────────────────────────────────────────────────┘
```

### Profile Graph Discovery

When wizard loads `TribalGovernmentUS`, it:

1. Scans statements for `entity_profile` types → finds `office_held_by_head_of_state`
2. Reads profile linkage metadata from statement value definitions
3. Loads related profile artifacts recursively by profile URI/QID
4. Builds profile graph from `metadata.profile_graph` edges
5. Creates packet with placeholders for both entities

Profile graph metadata is already carried in profile artifact `metadata.profile_graph` (see [Multi-Profile Configuration](../gkc/profiles.md#profile-graphs-cross-references)).

### Foundation vs Materialized Forms

For each architectural component, GKC uses a two-form lifecycle:

1. **Foundation form (DD Wikibase)** — authoritative semantic definitions and linkage directives.
2. **Materialized/actionable form (SpiritSafe)** — deterministic JSON/cache artifacts consumed by runtime.

`gkc` runtime workflows operate on the materialized form while preserving canonical linkage back to the DD foundation semantics.

---

## Design Principles

### 1. Profiles Are the Single Source of Truth

No hardcoded entity logic exists in wizards, validators, or serializers. Everything derives from profiles:

- Field labels → `profile.statements[].label`
- Validation rules → `profile.statements[].constraints`
- UI widgets → `profile.statements[].value.type`
- Allowed values → `profile.statements[].value.allowed_items` (SPARQL-driven)

**Anti-pattern:** Wizard code that says "if entity is tribal government, add office field". Instead: Profile declares office statement; wizard reads it.

### 2. Declarative Over Imperative

Profiles describe *what* an entity is, not *how* to build it. The engine interprets profiles and generates behavior dynamically.

### 3. Cross-Platform by Design

Profiles map GKC concepts to multiple platforms simultaneously:

- Wikidata: Property IDs (P31, P1906), datatype semantics
- Wikimedia Commons: Category structure, file upload patterns
- Wikipedia: Sitelinks, article naming conventions
- OpenStreetMap: Relation IDs, tag mappings

Future platform integrations (e.g., DBpedia, Schema.org) extend profiles without changing core architecture.

### 4. Graph-Oriented Entity Modeling

Entities rarely exist in isolation. Profiles model relationships explicitly:

- `TribalGovernmentUS` declares linkage to `OfficeHeldByHeadOfState`
- Packets bundle related entities together
- Validation can span entity boundaries (future)

This mirrors real-world curation: creating a tribal government often requires creating its leadership office.

### 5. Fail Gracefully, Validate Continuously

Following Wikipedia/Wikidata philosophy:

- **Curators can save incomplete entities** — Validation warns but doesn't block
- **Real-time validation** — Feedback on every field blur, not just on submit
- **Progressive enhancement** — Minimal entities ship quickly; enrichment happens iteratively

---

## Implementation Status

**Stable & Production-Ready:**

- JSON Entity Profile loading and runtime model generation
- SPARQL allowed-items hydration with fallback lists
- Single-entity curation packets
- Wikidata JSON serialization
- Statement, qualifier, reference validation

**Additional capabilities under design:**

- Multi-entity packets with cross-entity references
- Expanded profile graph traversal and orchestration policy controls
- Wizard multi-tab UI for related entities
- Status tracking lifecycle

**Future capabilities:**

- QID-based packet hydration (load existing Wikidata items into packets)
- Cross-entity validation rules
- Bulk operations with statement filtration
- Recursive profile graph loading (depth > 1)
- Round-trip transformation (Wikidata → GKC Entity JSON → Wikidata)

---

## Detailed Architecture Documents

This architecture section includes detailed documentation on specific subsystems:

- [Profile Loading Architecture](SpiritSafe/profile-loading.md)
- [SpiritSafe Registry](SpiritSafe/index.md)
- [Validation Architecture](validation-architecture.md)

---

## Related Documentation

### Core Concepts

- [GKC Entity Profiles: Construction and Reference](../gkc/profiles.md)
- [GKC Entity JSON Schema](../gkc/entity-json-schema.md)
- [GKC Wizard Documentation](../gkc/wizard.md)
- [SpiritSafe Registry](SpiritSafe/index.md)

### Specialized Topics

- [Profile Graphs & Multi-Profile Linking](../gkc/profiles.md#profile-graphs-cross-references)
- [Statement Types Reference](../gkc/profiles.md#statement-types-reference)
- [Multi-Entity Curation Workflows](../gkc/wizard.md#multi-entity-curation-sessions)

### Developer Guides

- [Shipping Entities to Wikidata](../gkc/shipping.md)

---

## Glossary

| Term | Definition |
|------|------------|
| **Profile** | JSON Entity Profile artifact defining entity structure in SpiritSafe |
| **Value List** | Curated allowed-item domain materialized as query + hydrated cache artifacts |
| **Packet** | Bundle of 1+ entities being curated together |
| **Entity** | Single real-world thing represented in GKC (tribal government, office, person) |
| **Statement** | Single property-value assertion about an entity (analogous to Wikidata claim) |
| **Profile Graph** | Network of profiles linked via `entity_profile` statements |
| **packet_id** | UUID packet identifier used to track a specific packet instance |
| **creation_path** | Breadcrumb showing how entity was created (e.g., `primary.office`) |
| **Shipper** | Module that serializes packets to platform-specific formats (Wikidata JSON, etc.) |
| **Allowed Items** | SPARQL-driven choice lists for statement values (e.g., Federal Register issues) |

---

## Theoretical Design Notes

The following are directionally important but not yet fully implemented as stable architecture in GKC:

- Wizard execution environments beyond current local Python interfaces.
- Expanded profile composition and branching workflow semantics.
- Additional cross-platform publishing orchestration beyond current shipping abstractions.

These are retained as design intent for future implementation work.

---

**Last Updated:** March 26, 2026  
**Status:** Stable (subject to enhancement as architecture evolves)
