# GKC Architecture Overview

## Introduction

The **Global Knowledge Commons (GKC)** is a framework for understanding and working with structured knowledge across multiple open public platforms. The initial design focuses on Wikidata, Wikimedia Commons, Wikipedia templates, and OpenStreetMap.

The project uses a **data distillery** metaphor to describe the pipeline that converts raw, heterogeneous inputs into validated, platform-ready outputs. Mash Bills describe incoming structure, Modulation Profiles guide transformation, GKC Entity Profiles define canonical entity forms, and Barrel Profiles represent downstream platform-specific targets.

The GKC is built on three foundational architectural components that work together to transform declarative entity definitions into actionable curation workflows:

1. **GKC Entity Profiles** — Declarative YAML definitions of entity structure and semantics
2. **GKC Entity JSON Schemas** — Machine-readable, serializable representations of profiles
3. **GKC Curation Packets** — Actionable bundles of 1+ entities flowing through curation workflows

These components enable a consistent pattern: **define once, use everywhere**. A profile written in YAML drives wizard UI generation, validation logic, bulk data operations, API contracts, and cross-platform serialization—all from a single source of truth.

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

**Implementation:** Profiles exist as YAML files in the SpiritSafe registry (`profiles/<ProfileID>/profile.yaml`) and are loaded into Pydantic models at runtime, serving as the authoritative source of truth for:

- **Entity structure** — What statements, qualifiers, and references constitute the entity
- **Validation rules** — Constraints, datatypes, cardinality, required vs optional fields
- **Cross-platform semantics** — Mappings to Wikidata properties, Wikimedia Commons categories, OSM tags
- **UI generation** — Field labels, guidance text, input prompts, allowed-items lists
- **Profile relationships** — How entities link to other entity types (profile graphs)

**Key Characteristics:**

- **Declarative, not imperative** — Profiles describe *what* an entity is, not *how* to build it
- **Human-readable and machine-executable** — YAML is both documentation and runtime specification
- **Version-controlled** — Managed in SpiritSafe repository with CHANGELOG tracking
- **Profile-driven workflows** — Wizards, validation engines, and serializers consume profiles directly

**Related Documentation:**

- [Entity Profiles: Construction and Reference](../gkc/profiles.md)
- [SpiritSafe Registry](SpiritSafe.md)

### GKC Entity JSON Schemas

**Definition:** GKC Entity JSON Schemas are machine-readable, serializable representations of GKC Entity Profiles that provide stable contracts for API routes, external tools, and inter-profile composition.

**Implementation:** Generated programmatically from Pydantic models (which are in turn loaded from YAML profiles), JSON Schemas:

- **Define data contracts** — External tools can validate GKC Entity JSON without importing Python code
- **Enable profile composition** — Profiles reference one another via `entity_profile` statements, forming graphs
- **Support dynamic UI generation** — Web frontends can generate forms from JSON Schema definitions
- **Provide type safety** — IDE autocomplete, validation, and API documentation all derive from schemas

**Relationship to Profiles:**

```
Profile YAML → Pydantic Model → JSON Schema → API Contract
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
- **Packet metadata** — Creation timestamps, curator username, status tracking
- **Local reference system** — `packet_id` identifiers (e.g., `ent-001-primary`, `ent-002-office`) that resolve to Wikidata QIDs post-shipping

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

### SpiritSafe

**SpiritSafe** is the profile registry and supporting query/cache infrastructure. It stores profile packages (`profile.yaml`, `metadata.yaml`, docs, and `queries/`) and provides a source for GKC runtime loading in local or GitHub-backed modes.

For complete documentation on SpiritSafe, see [SpiritSafe Registry](SpiritSafe.md).

---

## Architectural Data Flow

### Profile → Wizard → Packet → Wikidata

```
┌─────────────────────────────────────────────────────────────────┐
│                     SpiritSafe Registry                         │
│  profiles/TribalGovernmentUS/profile.yaml                       │
│  profiles/OfficeHeldByHeadOfState/profile.yaml                  │
└────────────────────┬────────────────────────────────────────────┘
                     │ Load profiles
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                  GKC Spirit Safe Module                         │
│  - Parse YAML → Pydantic EntityProfile models                   │
│  - Build profile graph (TribalGov → Office linkage)             │
│  - Hydrate SPARQL allowed-items lists                           │
└────────────────────┬────────────────────────────────────────────┘
                     │ Provide profile models
                     ↓
┌─────────────────────────────────────────────────────────────────┐
│                     GKC Wizard                                  │
│  - Generate 5-step UI from profile metadata                     │
│  - Create curation packet (ent-001 primary, ent-002 office)     │
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
│  - Resolve cross-entity references (ent-002 → create office, get QID) │
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
2. Reads `value.profile_name: OfficeHeldByHeadOfState`
3. Loads `OfficeHeldByHeadOfState` profile recursively
4. Builds profile graph: `TribalGovernmentUS` → `OfficeHeldByHeadOfState`
5. Creates packet with placeholders for both entities

Future metadata enhancement will make this explicit via `metadata.yaml` `profile_graph` section (see [Multi-Profile Configuration](../gkc/profiles.md#profile-graphs-cross-references)).

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

- Profile YAML loading and Pydantic model generation
- SPARQL allowed-items hydration with fallback lists
- Single-entity curation packets
- Wikidata JSON serialization
- Statement, qualifier, reference validation

**In Development (Wizard MVP):**

- Multi-entity packets with cross-entity references
- Profile graph metadata (`metadata.yaml` enhancements)
- Wizard multi-tab UI for related entities
- Status tracking lifecycle

**Planned (Post-MVP):**

- QID-based packet hydration (load existing Wikidata items into packets)
- Cross-entity validation rules
- Bulk operations with statement filtration
- Recursive profile graph loading (depth > 1)
- Round-trip transformation (Wikidata → GKC Entity JSON → Wikidata)

---

## Detailed Architecture Documents

This architecture section includes detailed documentation on specific subsystems:

- [Profile Loading Architecture](profile-loading.md)
- [SpiritSafe Registry](SpiritSafe.md)
- [Validation Architecture](validation-architecture.md)

---

## Related Documentation

### Core Concepts

- [GKC Entity Profiles: Construction and Reference](../gkc/profiles.md)
- [GKC Entity JSON Schema](../gkc/entity-json-schema.md)
- [GKC Wizard Documentation](../gkc/wizard.md)
- [SpiritSafe Registry](SpiritSafe.md)

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
| **Profile** | YAML definition of entity structure in SpiritSafe registry |
| **Packet** | Bundle of 1+ entities being curated together |
| **Entity** | Single real-world thing represented in GKC (tribal government, office, person) |
| **Statement** | Single property-value assertion about an entity (analogous to Wikidata claim) |
| **Profile Graph** | Network of profiles linked via `entity_profile` statements |
| **packet_id** | Local identifier (e.g., `ent-001`) used within a packet before QID assignment |
| **creation_path** | Breadcrumb showing how entity was created (e.g., `primary.office`) |
| **Shipper** | Module that serializes packets to platform-specific formats (Wikidata JSON, etc.) |
| **Allowed Items** | SPARQL-driven choice lists for statement values (e.g., Federal Register issues) |

---

## Theoretical Design Notes

The following are directionally important but not yet fully implemented as stable architecture in GKC:

- Wizard execution environments beyond current local Python interfaces.
- Expanded profile composition and branching workflow semantics.
- Additional cross-platform publishing orchestration beyond current shipping abstractions.

These are retained as design intent for follow-on implementation work by the Wizard Engineer and Validation Agent.

---

**Last Updated:** March 3, 2026  
**Maintainer:** Profile Architect  
**Status:** Stable (subject to enhancement as architecture evolves)
