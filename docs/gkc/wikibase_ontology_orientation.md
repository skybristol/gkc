# Data Distillery Wikibase Ontology Orientation

This document defines the current structure of the Data Distillery Wikibase ontology as it relates to GKC Entity Profile representation. It is the authoritative reference for how profile structure, constraints, guidance, and linkages are encoded in Wikibase items and properties, and how they translate to the materialized JSON cache in SpiritSafe.

It is intended to keep implementation work aligned across Profile Architect, Validation Agent, Wizard Engineer, and related contributors.

## Source Of Truth And Access Pattern

The Data Distillery Wikibase is the authoritative source for profile ontology and semantic contracts.

SpiritSafe is the materialized runtime cache used for deterministic loading in downstream workflows. It is version-controlled and offline-capable — gkc runtime code does not depend on live Wikibase availability.

Practical note: the Wikibase main page may be blocked by browser bot protection, but the MediaWiki API endpoint is queryable for machine-readable retrieval.

## Entity Class Hierarchy

All entity classes in the DD Wikibase are organized under a root class using `P2` (subclass of) relationships. The root class is Q1. The following entity classes are actively used in profile modeling:

| QID | Label | Role |
|-----|-------|------|
| Q1 | Root class | Ancestor of all DD Wikibase entity classes |
| Q3 | GKC Entity Profile | Each profile item has `P1 = Q3` |
| Q5 | GKC Entity Statement | Statement definitions linked from profiles via P157, P158, and P211 |
| Q7 | GKC Value List | Value list items linked via P161; may simultaneously classify a profile item |
| Q44 | Wikibase Property Template | Primitive datatype definitions linked from GKC Entity Statements via P194 |
| Q50 | Manual Refresh | Refresh policy item used in GKC Value List P210 claims |
| Q52 | Wikidata Entity | Fixed-value reference items linked via P161; carry a P212 (same as) URL pointing to the Wikidata entity |

Most GKC Entity Profile items are also simultaneously classed as GKC Value List items (dual `P1 = Q3` and `P1 = Q7` claims). This enables conforming entities to be surfaced as a type-ahead pick list wherever that entity type is a valid statement value.

The SPARQL query for exploring the full class tree:

```sparql
PREFIX wd: <https://datadistillery.wikibase.cloud/entity/>
PREFIX wdt: <https://datadistillery.wikibase.cloud/prop/direct/>

SELECT ?item ?itemLabel ?itemDescription
WHERE {
  ?item wdt:P2* wd:Q1 .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

## Property Reference

The following properties are in active use for profile modeling. Properties use the `/prop/` namespace URI (e.g., `https://datadistillery.wikibase.cloud/prop/P1`).

### Classification And Linkage

| PID | Label | Datatype | Used On | Role |
|-----|-------|----------|---------|------|
| P1 | instance of | wikibase-item | All items | Assigns an item to an entity class |
| P2 | subclass of | wikibase-item | Class items | Defines entity class hierarchy under Q1 |
| P3 | see also | wikibase-item | Any item | Cross-reference to related items |
| P5 | to wikidata | url | GKC Entity Statement (Q5) | URL of the corresponding Wikidata property (e.g., `http://www.wikidata.org/entity/P31`) |
| P157 | has statement | wikibase-item | GKC Entity Profile (Q3) | Links a profile to a GKC Entity Statement; carries profile-specific qualifier configuration |
| P158 | has qualifier | wikibase-item | qualifier on P157 | Links to a GKC Entity Statement specifying an expected qualifier type for that statement |
| P161 | has value | wikibase-item | qualifier on P157; claim on Q5 items | Value specification; target class determines semantics: Q52 = fixed, Q3 = linked profile, Q7 = value list |
| P194 | statement type | wikibase-item | GKC Entity Statement (Q5) | Links to a Wikibase Property Template (Q44) encoding the primitive Wikibase datatype |
| P205 | applies to profile | wikibase-item | qualifier on statement-level directive claims | Scopes statement-level P161/P158/P211/P213 behavior to one or more profiles |
| P163 | applies to statement | wikibase-item | qualifier on statement-level directive claims; qualifier on profile-level P158/P211 claims | Scopes directives to specific parent statement contexts |
| P210 | refresh policy | wikibase-item | GKC Value List (Q7) | Required; links to a refresh policy item (e.g., Q50 manual refresh) |
| P211 | has reference | wikibase-item | qualifier on P157; claim on Q5 items; claim on Q3 items | Links to expected reference statement definitions; supports statement-level defaults and profile-level targeted overrides |
| P212 | same as | url | Wikidata Entity (Q52) | URL of the specific Wikidata entity (e.g., `http://www.wikidata.org/entity/Q7840353`) |
| P213 | derives default value from | wikibase-item | GKC Entity Statement (Q5) | Declares that when this statement is used as a reference/qualifier on the target statement, its value is derived from the parent statement value |

### Cardinality And Value

| PID | Label | Datatype | Used On | Role |
|-----|-------|----------|---------|------|
| P182 | max count | quantity | qualifier on P157 | `novalue` = one or more expected; explicit quantity = that exact count expected |
| P202 | default value | url | GKC Entity Statement (Q5) | Wikidata entity URL to pre-populate as the statement default value |
| P203 | default label | string | qualifier on P202 claim | Human-readable label for the default value entity |

### Guidance And Messaging

All guidance properties are monolingual text. They may appear as independent claims on GKC Entity Profile or GKC Entity Statement items, or as qualifiers on a P157 claim in a profile item. Qualifier-level values override item-level values.

| PID | Label | Used On | Role |
|-----|-------|---------|------|
| P185 | label guidance | GKC Entity Profile (Q3) | Guidance for curators entering the entity label |
| P186 | description guidance | GKC Entity Profile (Q3) | Guidance for curators entering the entity description |
| P187 | alias guidance | GKC Entity Profile (Q3) | Guidance for curators entering entity aliases |
| P188 | label prompt | GKC Entity Profile (Q3) | Prompt text for the label input field |
| P189 | description prompt | GKC Entity Profile (Q3) | Prompt text for the description input field |
| P190 | alias prompt | GKC Entity Profile (Q3) | Prompt text for the alias input field |
| P168 | error message | GKC Entity Statement (Q5) or Q44 item; qualifier on P157 | Error message shown when statement validation fails; at Q44 level covers primitive type failures |
| P169 | statement guidance | GKC Entity Statement (Q5); qualifier on P157 | Contextual guidance for curators filling out a statement value |
| P171 | statement prompt | GKC Entity Statement (Q5); qualifier on P157 | Prompt text for the statement value input |

## GKC Entity Profile Structure

A GKC Entity Profile item (`P1 = Q3`) encodes everything needed to guide data curators in creating or editing a class of entity. All profile rules are derived from Wikibase item JSON at extraction time and materialized into the SpiritSafe JSON cache. No runtime Wikibase dependency is assumed.

### Profile Identification

Each profile item carries a `mul` label, an `en` label, and an `en` description for display in the Wikibase and in downstream interfaces. Additional language labels may be present. A profile is considered "multilingual compliant" when all required prompt and guidance claims are available in a language beyond `mul`.

### Yielded Entity Identification

A valid profile must have the following monolingual text claims to enable curator guidance for entity creation and editing:

| Property | Required | Notes |
|----------|----------|-------|
| P188 (label prompt) | Yes — `mul` required | |
| P185 (label guidance) | Optional | |
| P189 (description prompt) | Yes — `mul` required | |
| P186 (description guidance) | Optional | |
| P190 (alias prompt) | Yes — `mul` required | |
| P187 (alias guidance) | Optional | |

### Profile Statements

Statements in a profile are linked via `has statement` (P157) claims. Each P157 mainsnak targets a `GKC Entity Statement` item (`P1 = Q5`). The qualifiers on that P157 claim within the profile item provide profile-specific configuration: cardinality, value rules, expected qualifiers, expected reference types, and guidance overrides.

### Statement Type

Every GKC Entity Statement item must have a `statement type` (P194) claim linking to a `Wikibase Property Template` item (`P1 = Q44`). Statement type encodes the primitive Wikibase datatype (e.g., `wikibase-item`, `string`, `time`, `quantity`, `url`, `monolingualtext`, `external-id`, `geo-shape`). The `mul` and `en` labels of the Q44 item correspond to the Wikibase datatype string identifier. Q44 items carry an `error message` (P168) claim for primitive type validation failures.

### IO Mapping

GKC Entity Statement items that correspond to a Wikidata property carry a `to wikidata` (P5) URL claim linking to the Wikidata property entity URL. This establishes the io mapping used to route curation packet data to Wikidata.

### Cardinality

The `max count` (P182) qualifier on a P157 claim declares the expected number of statement values:

- `novalue` → one or more expected (rendered as `null` in materialized JSON).
- An explicit positive quantity → that exact count is expected.

All profile-specified statements are considered expected. Under-specified entries are accepted with guidance pointing toward improvement, following Wikidata/Wikipedia curation practice.

### Statement Values

Statement values are specified using `has value` (P161) qualifiers on a P157 claim in the profile item, or as independent P161 claims on a GKC Entity Statement item. The profile-level qualifier takes precedence when both are present. The class of the P161 target determines value semantics:

**Fixed Value (P161 → Q52):** The target is a `Wikidata Entity` item (`P1 = Q52`). That item carries a `same as` (P212) URL claim pointing to the specific Wikidata entity URI required as the statement value. Only one fixed value per statement is expected and it is exclusive of options.

**Linked Profile (P161 → Q3):** The target is a GKC Entity Profile item. The statement value should be fulfilled by an existing entity conforming to that profile, or by creating a new one.

**Value List (P161 → Q7):** The target is a GKC Value List item. The list provides a curated set of allowed values optimized for type-ahead delivery. Statement-level P161 defaults may be global (no scoping qualifiers) or context-scoped using `applies to profile` (P205), `applies to statement` (P163), or both.

Multiple P161 qualifiers may appear on a single P157 claim. Profile (Q3) and value list (Q7) targets may coexist and surface together as `options` in the materialized JSON.

### Default Values

A GKC Entity Statement item may carry a `default value` (P202) URL claim pointing to a Wikidata entity to pre-populate. This claim must include a `default label` (P203) string qualifier providing a human-readable label for that entity.

Derived defaults are modeled separately from static defaults. A GKC Entity Statement item may carry `derives default value from` (P213) claims targeting one or more parent statement definitions. This means:

- when the subject statement is used as a qualifier/reference on that parent statement,
- the subject statement value should be populated from the parent statement value.

This pattern is global by default for the targeted parent statement(s). If a derived-default rule must only apply in specific profiles, constrain the P213 claim with `applies to profile` (P205) qualifiers.

### Value Lists And Refresh Policy

GKC Value List items (`P1 = Q7`) must have a `refresh policy` (P210) claim linking to a refresh policy item (e.g., Q50 for manual refresh). Value list SPARQL queries are stored in the item's Wikibase discussion page and run against the Wikidata Query Service or Qlever to hydrate the SpiritSafe value list cache.

### Statement Qualifiers

Expected qualifiers for a statement can be declared from three sources:

- Statement-level defaults via `has qualifier` (P158) claims on the GKC Entity Statement item.
- Profile-local links via P158 qualifiers on the P157 claim.
- Profile-level targeted overrides via P158 claims on the profile item, qualified with `applies to statement` (P163).

All the same structural rules that apply to profile statements — statement type, cardinality, value, and guidance — apply to qualifiers through the targeted GKC Entity Statement item.

For effective resolution, profile-local entries win for nested statement ids they explicitly define; statement-level defaults remain active for nested statement ids not overridden at profile level.

### Statement References

Expected references for a statement can be declared from three sources:

- Statement-level defaults via `has reference` (P211) claims on the GKC Entity Statement item.
- Profile-local links via P211 qualifiers on the P157 claim.
- Profile-level targeted overrides via P211 claims on the profile item, qualified with `applies to statement` (P163).

When multiple P211 entries are present for a statement context, effective reference resolution is computed per nested statement id using the same partial-override rule as qualifiers.

Reference value-derivation rules can appear at the GKC Entity Statement item level via P213. Consumers should apply those rules when reference/qualifier statements are instantiated in profile context, honoring any P205 profile constraints attached to the P213 claim.

### Guidance Precedence

When resolving guidance or prompt text for a statement, the precedence order is:

1. **P157 qualifier level** — the guidance property (P169, P171, P168) as a qualifier on the P157 claim in the profile item. Most specific; always preferred.
2. **GKC Entity Statement item level** — the same property as an independent claim on the Q5 item. Shared default across all profiles that include the statement.
3. **Wikibase Property Template level** — guidance or error messages on the Q44 statement type item. Broadest fallback; primarily applicable to type-level error messages (P168).

## Language And Text Policy

All language variants are preserved as stored in the Wikibase — language keys are not normalized in extraction.

`mul` (multilingual) is the primary language code for monolingual text guidance and prompt claims. Additional languages are optional and materialized in the JSON cache only when all required guidance and prompt claims are present in that language — partial language overlays are not materialized.

`mul` and `en` labels are expected on all primary items. `en` description is expected. `mul` description is not currently available in the DD Wikibase instance.

When a consumer's requested language is absent, runtime behavior should fall back to `mul`. This is not a hard failure — consumers are responsible for selecting the language to render.

## Extraction Implementation Notes

The current extraction implementation in `gkc/wikibase/ontology.py` provides two layers used during the SpiritSafe cache refresh workflow:

**Ontology Index (`DDOntologyIndex`):** A SPARQL-derived discovery layer that identifies all classified items and properties in the Wikibase by QID/PID. Used as the starting point for profile graph traversal.

**Profile Graph (`DDProfileGraph`):** Builds a full item JSON payload via breadth-first traversal from GKC Entity Profile items. Fetches complete `wbgetentities` records for all reachable nodes and preserves all language variants as stored.

These layers are used during the extraction and materialization stage only. Runtime gkc code consumes the materialized SpiritSafe JSON cache and has no live Wikibase dependency.

Consumers should use `fetch_ontology_index()` and `fetch_profile_graph()`.

## Theoretical Design Notes

These notes capture architecturally plausible next steps not yet fully implemented.

### Processing Policies And Logical Coercion

Properties for encoding statement-level logical processing or coercion policies exist in the Wikibase but are not currently active in the profile model. If fermenter-layer policy linkage is needed, those properties should be revisited before introducing new ones. Deferred until the Validation Agent's fermenter contract is stable enough to define required inputs.

### Guidance Channel Configuration

Purpose: allow consumers to request a specific guidance property subset (e.g., prompt-only vs. full guidance bundle) rather than always materializing all four guidance properties.

Open questions:

- Should guidance channel selection be a Python config parameter, a materialization option, or a Wikibase-level specification?

### Language Fallback Policy

Purpose: define deterministic fallback behavior when the requested language is absent.

Open questions:

- Fallback order: request language → `mul` → `en` → any, or request language → `en` → `mul` → any? The `mul` vs. `en` priority is not yet settled.
- Should fallback be enforced in post-processing Python or in SPARQL query construction?

### Typed Guidance Contracts

Purpose: allow downstream consumers (Validation Agent, Wizard Engineer) to distinguish prompt, guidance, error, and consequence channels without inspecting PIDs directly.

Open questions:

- Should materialized JSON expose guidance as a typed map rather than separate top-level fields?
- Should this contract be versioned in SpiritSafe cache manifests?
