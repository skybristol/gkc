# Validation Architecture

## Implementation Status

This page documents the currently implemented validation model and committed architectural direction.

## Validation Layers

Validation in GKC is layered around profile-defined constraints:

- **Profile definition validation**: YAML is parsed into typed profile models.
- **Entity data validation**: Item/statement content is checked against profile requirements.
- **Hydration input validation**: Query references and templates are resolved before execution.

## Profile-Driven Rules

Entity profiles remain the source of truth for validation behavior, including:

- Required statements and cardinality.
- Datatype matching for statement values.
- Qualifier and reference rules.
- Allowed-items constraints and fallback behavior.

## Runtime Validation Policy

Current policy behavior includes both permissive and strict paths depending on context:

- Existing non-conforming data can be tolerated where policy allows.
- New curation inputs are expected to follow profile-defined constraints.

## Serialization Alignment

Validation and profile models are designed to support downstream serialization workflows without inventing ad hoc Wikidata JSON structures.

## Theoretical Design Notes

- Expanded cross-statement semantic validation is still evolving.
- Additional wizard-step-specific validation orchestration remains future work.
- A centralized, reusable constraint message library for all interfaces is not yet fully formalized.
