# Data Distillery Wikibase Ontology Orientation

This document captures the current shared orientation for how gkc should interact with the Data Distillery Wikibase ontology.

It is intended to keep implementation work aligned across Profile Architect, Validation Agent, Wizard Engineer, and related contributors.

## Source Of Truth And Access Pattern

The Data Distillery Wikibase is the authoritative source for profile ontology and semantic contracts.

SpiritSafe remains the materialized runtime cache used for deterministic loading in downstream workflows.

Practical note: the main page can be blocked by browser bot protection, but the MediaWiki API endpoint is queryable and can be used for machine-readable retrieval.

## Current Ontology Module Scope In gkc

The current implementation in `gkc/wikibase/ontology.py` provides two complementary extraction layers:

**Ontology Index (`DDOntologyIndex`):** A SPARQL-derived discovery layer that identifies all classified items and properties in the Wikibase by QID/PID. Fetched via a combined union query that covers all items subclassed under Q1 and all properties with P1 class assignments. Used as the starting point for profile graph traversal.

**Profile Graph (`DDProfileGraph`):** A full item JSON payload built by breadth-first traversal from GKC Entity Profile items (P1 → Q3). Fetches complete `wbgetentities` records for all reachable nodes — profile items, statement items, primitive property items, reference spec items, and value spec items. All language variants are preserved exactly as stored.

The legacy compatibility layer has been removed. Consumers should use `fetch_ontology_index()` and `fetch_profile_graph()`.

## Core Foundation Relationships

The Wikibase main page currently documents these foundation relationships:

- P1: instance of.
- P2: subclass of.
- P3: see also.
- P5: linked wikidata property.

For ontology snapshot classification in the current implementation, P1 is the main relationship in use.

## Guidance And Messaging Properties

The documented guidance/message properties currently include:

- P188: label prompt.
- P185: label guidance.
- P189: description prompt.
- P186: description guidance.
- P190: alias prompt.
- P187: alias guidance.
- P171: statement prompt.
- P169: statement guidance.
- P168: error message.
- P170: consequences message.

Important: P170 is only one guidance channel. It should not be treated as the sole guidance contract for all consumer contexts.

## Language And Text Policy

All language variants are fetched and preserved exactly as stored in the Wikibase. Language keys are returned as-is (no normalization).

`mul` (multilingual) is the architectural default for monolingual text statements. This solves the practical problem of setting a single language tag that applies broadly — labels are stored in `mul` and `en` for primary items, with Spanish translations in progress.

When a configured consumer default language is absent from an item's labels, a runtime warning is emitted and extraction falls back to `mul`. This is not a hard failure. It is the consumer's responsibility to select which language to render for display.

## Guidance Precedence Model

When resolving guidance text for a statement in a profile context, the precedence order is:

1. Profile-level qualifier guidance — qualifier text on the matching `P157` claim in the profile item (most specific override).
2. Statement item guidance — the GKC Entity Statement item's own guidance claims (shared default across profiles).
3. Primitive property/template guidance — the linked primitive/template item guidance, used as a broad fallback.

## Working Assumptions For Near-Term Development

- Wikibase stays authoritative. SPARQL is for discovery; item JSON is for authoritative detail.
- All language keys are preserved as stored. No normalization in the extraction layer.
- `mul` is the default language for monolingual text statements.
- Snapshot fetches should remain deterministic and inspectable.
- All ranks, qualifiers, and references are preserved as-is in `DDProfileGraph.raw_items`.
- Guidance and validation messaging are fully configured from the Wikibase, not hard-coded in Python.
- Profile-level guidance overrides statement-item defaults when available.
- Traversal is bounded by internal wikibase-entityid links (cross-Wikibase external refs use different datatypes and are not traversed).

## Theoretical Design Notes

These notes describe architecturally plausible next steps that are not yet fully implemented and should be treated as provisional.

### Guidance Profile Expansion

Purpose: allow consumers to request a specific guidance channel set (for example, prompt-only, validation-only, or full guidance bundle) rather than hard-coding one property.

Open questions:

- Should guidance channels be represented as a named profile in YAML or Python config?
- Should snapshot structure expose one combined guidance map or channel-specific maps?

### Language Fallback Policy

Purpose: define deterministic fallback behavior when requested language text is missing.

Open questions:

- Should fallback order be request language -> `en` -> any available language?
- Should fallback be resolved in SPARQL query time or in Python post-processing?

### Message-Key And Template Resolution

Purpose: support localized runtime message rendering with placeholders and context-aware selection.

Open questions:

- Which properties represent message keys versus display text?
- Where should placeholder interpolation be enforced: validation layer, wizard layer, or both?

### Typed Guidance Contracts

Purpose: ensure downstream consumers can distinguish suggestion, guidance, error, and consequence text without string heuristics.

Open questions:

- Should typed guidance be represented via explicit property buckets in the snapshot dataclass?
- Should this contract be versioned in SpiritSafe cache manifests?
