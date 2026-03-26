# Validation Architecture

## Implementation Status

This page documents the currently implemented validation model and the committed architectural direction for upcoming validation and coercion work.

The immediate direction is to make the fermenter module the canonical runtime evaluation layer for profile-aware validation, data coercion, and conformance classification.

## Architectural Core

Validation is built around two equally important semantic components:

- GKC Entity Profile
- GKC Entity Statement

Profiles organize statement instances and apply profile-specific context.

Statements are reusable compound data objects that can participate across many profiles and can stand on their own as semantic units.

For validation architecture, the minimum statement shape is:

- value
- reference
- provenance

At minimum, provenance must capture presentation circumstances: how, when, and by whom a statement was stated.

## Validation Layers

Validation in GKC is layered around profile-defined constraints:

- Profile definition validation: YAML is parsed into typed profile models.
- Entity data validation: item and statement content is checked against profile requirements.
- Hydration input validation: query references and templates are resolved before execution.
- Packet evaluation validation: packet metadata integrity is verified before data evaluation runs.

Runtime entity validation now also distinguishes:

- offline validation (shape, coercion, and rule checks without network retrieval)
- policy-driven online validation (resolvability and retrieval checks for referenced assets)

## Profile-Driven Rules

Entity profiles remain the source of truth for validation behavior, including:

- Required statements and cardinality.
- Datatype matching for statement values.
- Qualifier and reference rules.
- Allowed-items constraints and fallback behavior.

As packet evaluation evolves, profiles define the rule set while fermenter owns runtime interpretation and enforcement.

This separation is intentional:

- Profiles define what is valid.
- Fermenter determines whether concrete input conforms, can be coerced, must be flagged, or remains outside current profile coverage.

## Runtime Validation Policy

Current policy behavior includes both permissive and strict paths depending on context:

- Existing non-conforming data can be tolerated where policy allows.
- New curation inputs are expected to follow profile-defined constraints.

The next runtime model will make this policy explicit through statement-level and profile-level outcome classification.

## Multi-Tier Validation Policy

For reference-bearing datatypes (for example, Wikibase items and URLs), validation supports a staged policy model:

- `STRUCTURE`: local structural checks only
- `HEARTBEAT`: quick online "are you alive" checks
- `ACTIONABLE`: richer online retrieval for intended interactions

The goal is to preserve deterministic offline behavior while enabling optional ACTIONABLE checks when network and policy context allow.

Validation policy must remain configurable per operation context so bulk ingestion, notebook review, and interactive curation can choose appropriate depth.

## Uncertainty Model

Coercion and online validation can produce valid outputs that still carry uncertainty.

Validation results therefore include uncertainty metadata used for curator-facing feedback and policy decisions:

- uncertainty score (`0.0` to `1.0`)
- uncertainty reasons (machine-readable cause tags)

This supports robust automation while preserving explicit review pathways for ambiguous inputs.

## Conformance Outcomes

The fermenter direction is to classify inbound or edited data using four standard outcomes.

### `CONFORMANT`

At the statement level, `CONFORMANT` means the profile defines the statement, the input can be normalized into the expected data shape, and it passes the relevant profile rules.

This includes rules such as datatype checks, allowed-items constraints, fixed-value requirements, count limits, and other custom validation logic derived from the profile.

At the profile level, `CONFORMANT` means the evaluated statement content satisfies the profile contract for that part of the entity.

### `NON_CONFORMANT_MAPPABLE`

At the statement level, `NON_CONFORMANT_MAPPABLE` means the profile clearly recognizes the statement, but the current value does not satisfy one or more profile rules.

This is the retained-but-flagged case. The value still belongs to a known statement slot, so it should not be discarded. Instead, it should be preserved with actionable feedback and, where possible, normalized or coerced for curator review.

Typical causes include datatype mismatch, value-list miss, fixed-value conflict, or cardinality overrun.

At the profile level, `NON_CONFORMANT_MAPPABLE` means the profile covers the statement semantically, but the concrete data does not yet conform.

### `TO_BE_DEFINED`

At the statement level, `TO_BE_DEFINED` means inbound data contains a statement that the active profile does not currently define.

This does not mean the statement is wrong. It means the profile does not yet provide a rule set or packet slot for handling it. These statements should be preserved separately so they can inform profile expansion, curation review, or future modeling decisions.

At the profile level, `TO_BE_DEFINED` indicates a profile-coverage gap rather than a validation failure. The profile has not yet defined how to interpret that part of the source data.

### `MISSING`

At the statement level, `MISSING` means the profile expects a statement, but no usable value is present in the evaluated data.

This is an absence case, not an invalid-value case. It is distinct from `NON_CONFORMANT_MAPPABLE`, where a candidate value exists but fails validation.

At the profile level, `MISSING` indicates that the profile contract is incomplete for the entity being evaluated because one or more expected statements are absent.

## Curation Packet Role

The Curation Packet is the integration vehicle where profile rules, statement rules, source-data capabilities, and evaluation outputs are materialized together.

A packet can be broad (full entity profile composition) or intentionally thin.

Thin packet operation is an explicit architectural target:

- a packet may represent a single statement sliced across all relevant entities
- the same conformance model must apply regardless of packet breadth
- packet shape must support both profile-centric and statement-centric workflows

## Fermenter Responsibilities

The fermenter module is the canonical home for runtime validation and coercion behavior.

Its responsibilities are:

- datatype-aware normalization of inbound values
- profile-aware statement evaluation
- reusable conformance notice generation
- packet integrity checks before data validation
- file-based and inline-object validation entry points

Its responsibilities do not include:

- assembling curation packet scaffolds
- traversing profile graphs for packet construction
- owning UI-specific rendering or workflow logic

That boundary matters because it keeps the still charger responsible for packet assembly and source-item retrieval while making the fermenter responsible for the actual validation and classification work.

## Planned Evaluation Scaffolding

The next major step is to formalize a reusable evaluator structure inside the fermenter.

The intended progression is:

1. Add shared conformance outcome types and result envelopes for statements and entities.
2. Add atomic claim normalization and statement evaluation functions.
3. Add entity-level aggregation that groups evaluated statements into the four conformance outcomes.
4. Add packet validation entry points for both inline objects and file-based workflows.
5. Integrate still_charger with fermenter evaluators so charged packets are populated from evaluated results rather than direct raw-claim copying.

This scaffolding is meant to support both interactive curation and bulk evaluation without duplicating logic across CLI, notebook, and wizard interfaces.

Evaluator outputs should remain statement-instance anchored so profile context and statement context are both preserved for notices, coercion traces, and downstream policy.

## Packet Validation Direction

Packet validation is moving toward a strict metadata/data separation.

The metadata section will carry:

- profile definitions and packet graph metadata
- mint provenance
- integrity digest information
- packet-level conformance summaries

The data section will carry:

- entity data prepared from the profile scaffold
- conformant values placed directly in their profile-defined slots
- retained non-conformant values and notices where policy allows
- statements that remain `TO_BE_DEFINED`
- empty but expected fields represented as `MISSING`

Validation must first verify that packet metadata has not been altered in ways that break its binding to the profile ruleset. If the packet integrity digest fails, data validation must stop immediately.

## Serialization Alignment

Validation and profile models are designed to support downstream serialization workflows without inventing ad hoc Wikidata JSON structures.

The fermenter will therefore work with profile-defined packet shapes and normalized GKC runtime structures, while preserving enough provenance to support later bottling and shipping decisions.

## Theoretical Design Notes

- Expanded cross-statement semantic validation is still evolving.
- Additional wizard-step-specific validation orchestration remains future work.
- A centralized, reusable constraint message library for all interfaces is not yet fully formalized.
- Linked-profile charging and evaluation should be added only after single-profile evaluator contracts are stable.
- `TO_BE_DEFINED` is an intentional profile-coverage classification, not a data-quality judgment.
- `MISSING` should remain distinct from invalid-value cases so downstream tools can separate absence from non-conformance.
- Statement-level provenance enforcement may evolve from advisory to policy-driven required checks in specific operation modes.
