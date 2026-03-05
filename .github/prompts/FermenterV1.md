# Fermenter V1 Plan

## Decision Log

**[confirmed]** 2026-03-05: Adopt phased migration strategy for fermenter (build new contracts/coercers first, then refactor legacy pathways through adapters and progressive delegation).
  Source: Q1.2 on issue #120

**[confirmed]** 2026-03-05: Fermenter uses submodule architecture; datatype constraints profile-driven, fermenter owns executable logic.
  Source: Q1.1, Q1.3 on issue #120

**[confirmed]** 2026-03-05: Interleaved atomic `coerce_and_validate` flow at statement scope; support both eager and batch validation modes.
  Source: Q2.1, Q2.2 on issue #120

**[confirmed]** 2026-03-05: Fallback allowed-items: check cache/index first, tertiary mash network fetch, profile-defined fallback lists, per-profile/statement pass-through config (defaults true).
  Source: Q2.3, Q5.1, Q5.2, Q5.3 on issue #120

**[confirmed]** 2026-03-05: Unified issue model for validation/coercion outcomes; include actionable feedback per profile; plan for localization (possibly via Data Distillery Wikibase).
  Source: Q4.1, Q4.2, Q4.3, Q4.4 on issue #120

**[confirmed]** 2026-03-05: Coercion philosophy: aggressive framework capacity, start moderate, fail fast with structured choices for ambiguous cases.
  Source: Q3.1, Q3.2 on issue #120

**[confirmed]** 2026-03-05: Mystery data inference grounded in active profile/packet context; stub likely statements when profile-aligned mapping detectable.
  Source: Q3.3, Q8.3 on issue #120

**[confirmed]** 2026-03-05: Fermenter directly depends on `gkc.spirit_safe` for all cache/hydration access; also integrates with `gkc.profiles`, `gkc.sparql`, identify co-dev gaps with Profile Architect.
  Source: Q5.1, Q9.1 on issue #120

**[confirmed]** 2026-03-05: Cross-entity constraints (#110, #111, #112) all live in fermenter, called from wizard; supports multi-modal interactions and external tool-builders.
  Source: Q6.1 on issue #120

**[confirmed]** 2026-03-05: Cardinality validation starts simple; reciprocal awareness treated as warnings/rejection based on available Wikidata property constraint data.
  Source: Q6.2, Q6.3 on issue #120

**[confirmed]** 2026-03-05: Leverage existing `ProfilePydanticGenerator` as validation backbone; support all scopes (presence/type/datatype/constraint); permit non-conforming data mode for `allow_existing_nonconforming`.
  Source: Q7.1, Q7.2, Q7.3 on issue #120

**[confirmed]** 2026-03-05: Test fixtures: set up synthetic profiles as primary fixtures early next cycle; coercion framework as modular public functions; defer deep mystery data edge cases.
  Source: Q8.1, Q8.2, Q8.3 on issue #120

**[confirmed]** 2026-03-05: Fermenter provides raw validation results; Wizard translates to UI; shipper owns Wikidata JSON conversion (may introduce some here); Profile Architect to handle versioning.
  Source: Q9.2, Q9.3 on issue #120

**[confirmed]** 2026-03-05: Cross-statement validation means rule framework applied across multiple statements in profile, not interstatement dependencies (those live at qualifier/reference level).
  Source: Q10.1 on issue #120

**[deferred]** 2026-03-05: Wikidata property constraint digestion for cross-statement and reciprocal awareness rules; specialized reference resolvers organized as first-order SpiritSafe entities.
  Source: Q10.2, Q10.3 on issue #120

**[confirmed]** 2026-03-05: Data Distillery Wikibase is active at `datadistillery.wikibase.cloud` and will complement SpiritSafe as canonical, queryable registry infrastructure for property semantics, executable-constraint references, and multilingual validation messaging.
  Source: Infrastructure update, 2026-03-05

## Purpose

The `fermenter` module is the validation and data coercion engine for GKC.

Fermenter will centralize logic currently distributed across profile validation, normalization, and related utility modules, while preserving current behavior during a phased migration.

This document defines the first implementation iteration and migration sequence.

## Guiding Decisions (Confirmed)

### Architecture and Ownership

- Fermenter will use a submodule layout, not a flat single-file/module shape.
- We will use a phased migration approach rather than a single refactor sweep.
- Datatype constraints remain profile-driven (Entity Profile as source of truth), while fermenter owns executable validation/coercion code paths.
- Profile schema extensions required for fermenter hooks/config will be coordinated with the Profile Architect.

### Validation and Coercion Flow

- Canonical flow favors an interleaved model: `coerce_and_validate` at atomic statement scope.
- Processing should stay composable and reasonably atomic, but not split into excessive micro-steps that are hard to maintain or document.
- Fermenter must support both:
	- eager validation/coercion (interactive wizard input)
	- batch/comprehensive validation (review and shipping gates)

### Allowed-Items Validation Strategy

- Primary: Check against hydrated cache/index from SPARQL-driven SpiritSafe.
- Secondary: Check profile-defined fallback lists.
- Tertiary: Invoke mash functionality for live network item fetch.
- Per-profile and per-statement configuration option to permit pass-through of unvalidated entries (defaults to true).
- Fermenter accesses all SpiritSafe resources through `gkc.spirit_safe` module (direct dependency).
- Resolvability checks enforced before shipping, even when cache unavailable.

### Coercion Philosophy

- Framework supports aggressive automatic coercion capability over time.
- V1 implementation begins at moderate coercion, expand iteratively.
- Coercion failures: fail fast, return structured choices for ambiguous cases to support UI rendering.
- Mystery data inference grounded in active profile/packet context; stub likely statements when profile-determined mappings are detectable (e.g., DOI column → DOI identifier statement).
- Coercion framework built as modular, composable building blocks that can be called individually or composed in different orchestration patterns.

### Issue and Feedback Model

- Unified issue model for validation and coercion outcomes.
- Include actionable feedback per profile (e.g., missing_consequences narratives, profile-encoded instruction context).
- Support actionable suggestions structure (e.g., try_alternative, auto_fix_available).
- Localization in scope as forward-compatible requirement; potential Data Distillery Wikibase infrastructure for multilingual error message registry.

### Pydantic Model Generation Integration

- Leverage existing `ProfilePydanticGenerator` as backbone of validation/coercion processing.
- Generated models support all validation scopes: field presence, type checking, datatype-specific validation (regex, ranges), constraint validation (min_count, max_count, allowed-items).
- Support `allow_existing_nonconforming` mode: generate models that permit non-conforming data, but flag and track in validation output; allow pass-through if data structures conform and are serializable.

### Cross-Entity and Packet Validation

- All cross-entity constraints (#110, #111, #112) live in fermenter; called from wizard/packet layer.
- Supports multi-modal interactions (wizard UI, bulk operations, external tool-builder APIs).
- Cardinality validation starts simple; build out as needed.
- Reciprocal awareness treated as warnings vs. rejection based on available Wikidata property constraint data (may not have full coverage early on).
- Cross-statement validation means rule framework applied across multiple statements in profile; dependencies primarily at qualifier/reference level within statements.

### Dependencies and Integration

- Fermenter depends on: `gkc.profiles`, `gkc.spirit_safe`, `gkc.sparql`.
- Fermenter will add Data Distillery registry clients for read-paths to `datadistillery.wikibase.cloud` (property metadata, constraint descriptors, and multilingual message lookup).
- Identify integration gaps through co-development session with Profile Architect.
- Fermenter provides raw validation results; Wizard Engineer translates to UI.
- Shipper owns Wikidata JSON format conversion (may introduce complementary functionality here if gaps identified).
- Profile Architect handles schema versioning (post-V1 concern).

## Outstanding Design Inputs (Deferred)

The following are explicitly deferred for post-V1 planning:

- Schema versioning and migration strategy (Profile Architect owns, vision still forming)
- Wikidata property constraint digestion for expanded cross-statement and reciprocal validation rules
- Specialized reference resolver organization as first-order SpiritSafe entities and cache hydration strategy

Data Distillery Wikibase hosting decision is now complete. Post-V1 planning remains needed for the deeper resolver graph and high-volume sync pipelines.

## Phase Plan

### Phase 1 - Foundation Contracts

Deliverables:

- Fermenter package scaffold with submodules
- Unified issue contract and return envelopes
- Coercion dispatcher/registry contract
- Baseline adapter shims from legacy validation entry points to new contracts (non-breaking behavior)
- Data Distillery integration contracts (read-only interfaces for property/constraint/message retrieval, with explicit fallback behavior to SpiritSafe/profile-local metadata)

Scope anchors:

- Issue #102 (ValidationIssue model and coercion return contract)
- Issue #103 (Coercion dispatcher and datatype registry)
- New issue: Fermenter ↔ Data Distillery registry client contract

Exit criteria:

- New contracts are importable and test-covered.
- Existing top-level validation paths remain operational.
- Registry interface can resolve at least one property metadata payload and one localized validation message payload from `datadistillery.wikibase.cloud` with deterministic fallback behavior.

Target API Patterns:

```python
# Core contracts
from gkc.fermenter.contracts import ValidationIssue, CoercionResult, CoercionPolicy

# ValidationIssue model usage
issue = ValidationIssue(
    severity="error",
    message="Invalid QID format",
    statement_id="instance_of",
    property_id="P31"
)

# Result envelope
result: CoercionResult = CoercionResult(
    success=False,
    value=None,
    issues=[issue],
    suggestions=[]
)

# Dispatcher registry
from gkc.fermenter.dispatcher import get_coercer
coercer = get_coercer('item')  # Returns callable or raises
```

Target CLI Patterns:

```bash
# Test contract availability
gkc fermenter contracts --validate

# List available datatype coercers (empty in Phase 1)
gkc fermenter coercers list
```

### Phase 2 - Datatype Coercion Core

Deliverables:

- Datatype coercers implemented under fermenter for initial priority set:
	- time
	- item/QID
	- monolingual text
	- URL
- Coercion + validation outcomes aligned to unified issue contract
- Datatype coercers can consume Data Distillery-backed property semantics where available (without requiring network availability for all paths)

Scope anchors:

- Issue #104
- Issue #105
- Issue #106
- Issue #107

Exit criteria:

- Datatype coercers runnable in isolation and through dispatcher.
- Behavior parity established for supported scenarios via targeted tests.
- Coercer behavior with and without Data Distillery lookup is test-covered for deterministic outcomes.

Target API Patterns:

```python
# Direct coercer imports
from gkc.fermenter.coercers import (
    coerce_time, coerce_qid, coerce_monolingualtext, coerce_url
)

# Unified signature per coercer
result: CoercionResult = coerce_qid(
    value="q123",
    policy=CoercionPolicy(eager=True),
    allowed_items_cache=None  # Optional
)

# Result structure
assert result.success
assert result.value == "Q123"
assert len(result.issues) == 0

# Dispatcher usage
from gkc.fermenter.dispatcher import dispatch_coerce
result = dispatch_coerce(
    datatype="item",
    value=raw_input,
    policy=CoercionPolicy()
)
```

Target CLI Patterns:

```bash
# Test individual coercers
gkc fermenter coerce time --value "2026-03-05" --policy eager
gkc fermenter coerce qid --value "q123" --allowed-items-cache ./cache.json
gkc fermenter coerce url --value "http://example.com"

# List registered coercers
gkc fermenter coercers list

# Test dispatcher routing
gkc fermenter dispatcher test --datatype item --value "Q123"
```

### Phase 3 - Runtime Integration

Deliverables:

- Wizard inline hooks for value/qualifier/reference coercion paths
- Review-stage comprehensive validation pass routed through fermenter contracts
- Compatibility layer to keep existing flow stable during migration
- Runtime message resolution pipeline for multilingual actionable feedback (Data Distillery first, then profile/SpiritSafe fallback)

Scope anchors:

- Issue #108
- Issue #109

Exit criteria:

- Wizard-facing and review-facing pathways can consume fermenter outputs consistently.
- Legacy pathways either delegate to fermenter or are explicitly marked for deprecation.
- Validation issue payloads include stable message keys plus resolved localized text when available.

Target API Patterns:

```python
# Statement-level validation and coercion
from gkc.fermenter.validators import validate_statement_value

statement_def = profile.get_statement('instance_of')
result = validate_statement_value(
    value=raw_input,
    statement_def=statement_def,
    allowed_items_cache=cache,
    policy=ValidationPolicy(eager=True, mode='coerce')
)

# Entity-level comprehensive validation
from gkc.fermenter.validators import validate_entity

entity_result = validate_entity(
    entity_data=wikidata_json,
    profile=profile,
    policy=ValidationPolicy(mode='lenient')
)

assert entity_result.ok  # Boolean shorthand
assert len(entity_result.errors) == 0
assert len(entity_result.warnings) <= expected_count

# Structured feedback for wizard
for issue in entity_result.issues:
    if issue.suggestions:
        # Render choice UI
        pass
```

Target CLI Patterns:

```bash
# Validate statement within profile
gkc fermenter validate statement \
  --profile ./profile.yaml \
  --statement instance_of \
  --value "Q123" \
  --policy eager

# Validate full entity
gkc fermenter validate entity \
  --profile ./profile.yaml \
  --entity ./item.json \
  --policy lenient \
  --output json

# Coerce and validate combo
gkc fermenter coerce-validate statement \
  --profile ./profile.yaml \
  --statement office_held \
  --value "q789" \
  --render-suggestions
```

### Phase 4 - Packet and Cross-Entity Rules

Deliverables:

- Packet-level cardinality validation
- Cross-reference and reciprocal consistency checks
- Cross-entity constraint framework extension points
- Optional cross-entity rule resolvers backed by Data Distillery property and relationship metadata

Scope anchors:

- Issue #110
- Issue #111
- Issue #112

Exit criteria:

- Multi-entity packet validation can run as a dedicated pass with structured issue output.
- Cross-entity checks can execute in offline mode (cache/profile fallback) and online mode (Data Distillery-enriched) with explicit provenance in issue metadata.

Target API Patterns:

```python
# Packet-level comprehensive validation
from gkc.fermenter.validators import validate_packet

packet_result = validate_packet(
    packet=curation_packet,
    profile_bundle=profiles,
    policy=ValidationPolicy(mode='strict')
)

assert packet_result.ok
assert len(packet_result.entity_issues) == 0  # Per-entity issues
assert len(packet_result.cross_entity_issues) == 0  # Cross-entity issues

# Cross-entity constraint checks
from gkc.fermenter.validators import check_packet_cardinality

card_issues = check_packet_cardinality(
    packet=packet,
    profile_bundle=profiles
)

# Reciprocal consistency checks
from gkc.fermenter.validators import check_reciprocal_links

recip_issues = check_reciprocal_links(
    packet=packet,
    profile_bundle=profiles
)
```

Target CLI Patterns:

```bash
# Validate entire packet
gkc fermenter validate packet \
  --packet ./curation_packet.json \
  --profiles ./profiles/ \
  --policy strict \
  --output json

# Check specific cross-entity constraints
gkc fermenter check packet-cardinality \
  --packet ./curation_packet.json \
  --profiles ./profiles/

gkc fermenter check reciprocal-links \
  --packet ./curation_packet.json \
  --profiles ./profiles/

# Validation summary
gkc fermenter validate packet \
  --packet ./curation_packet.json \
  --profiles ./profiles/ \
  --summary
```

### Phase 5 - Test Matrix and Hardening

Deliverables:

- Synthetic profile fixture suite established as primary test vehicles (to be set up early in next dev cycle per Q8.1)
- Validation/coercion matrix spanning atomic datatypes and multi-entity packet scenarios
- Fixture set expansion for regressions and failure-mode clarity
- Contract-focused tests for wizard/review integration paths
- Modular coercion building blocks tested as public functions and composed orchestrations
- Integration test fixtures for Data Distillery-dependent and fallback-only paths

Scope anchors:

- Issue #113

Exit criteria:

- Test matrix demonstrates expected behavior across strict/lenient and eager/batch contexts.
- Synthetic profiles cover key coercion scenarios without relying on production profiles.
- Regression coverage demonstrates equivalent validation outcomes when Data Distillery is unavailable and fallback policies are engaged.

Target API Patterns:

```python
# Full end-to-end workflow
from gkc.fermenter import (
    coerce_value, validate_value, validate_statement,
    validate_entity, validate_packet
)

# Modular public functions for composable workflows
coerced, issues = coerce_value(
    datatype='time',
    value=raw_input,
    policy=policy
)

validation_result = validate_entity(
    entity_data=item_json,
    profile=profile,
    eager_coerce=True  # Run coercion during validation
)

packet_result = validate_packet(
    packet=packet,
    profiles=bundle,
    batch_mode=True  # Comprehensive pass
)
```

Target CLI Patterns:

```bash
# End-to-end test workflows
gkc fermenter test workflow \
  --name eager-validation \
  --profile ./profiles/test_profile.yaml

# Matrix test runner
gkc fermenter test matrix \
  --policies strict,lenient \
  --modes eager,batch \
  --fixtures ./tests/fixtures/ \
  --report ./test_report.json

# Fixture validation
gkc fermenter test fixtures \
  --fixtures ./tests/fermenter/fixtures/ \
  --profile-pattern "*/profile.yaml"

# Performance baseline
gkc fermenter bench coerce \
  --datatype qid \
  --iterations 1000 \
  --output ./benchmark.json
```

## Initial Fermenter Module Layout (V1)

Proposed package structure:

- `gkc/fermenter/__init__.py`
- `gkc/fermenter/contracts.py` (issue/result models, enums, policy surfaces)
- `gkc/fermenter/dispatcher.py` (datatype registry and routing)
- `gkc/fermenter/coercers/` (datatype coercion implementations)
- `gkc/fermenter/validators/` (statement/entity/packet validators)
- `gkc/fermenter/adapters/` (temporary bridges from legacy call sites)
- `gkc/fermenter/testing/` (synthetic fixtures for development and testing)

V1 boundary notes:

- Fermenter accesses SpiritSafe resources exclusively through `gkc.spirit_safe` module imports.
- Fermenter consumes profile-defined constraints and external providers (spirit_safe, sparql, profiles) via explicit interfaces.
- Fermenter consumes Data Distillery resources through a dedicated integration layer (no direct UI coupling), with strict timeout, provenance tagging, and fallback contracts.
- UI rendering decisions remain outside fermenter; fermenter emits structured actionable feedback.
- Coercion and validation logic built as modular, independently-callable functions composable in multiple orchestration patterns.

## Migration Strategy

Refactor strategy is incremental and test-gated.

Approach:

1. Build fermenter contracts and dispatcher first.
2. Implement initial coercers in fermenter without deleting legacy implementations.
3. Introduce adapter/delegation points from current modules.
4. Switch call paths progressively (wizard/review/packet).
5. Introduce Data Distillery-backed read paths behind feature flags and fallback policies.
6. Retire duplicated legacy logic only after parity is verified.

This keeps current behavior stable while moving toward a single validation/coercion engine callable from multiple routes.

## Risks and Mitigations

- Risk: Duplicate logic during migration introduces drift.
	- Mitigation: Prefer delegation wrappers early; avoid parallel long-term implementations.

- Risk: Profile schema lag blocks richer constraints.
	- Mitigation: Track explicit schema dependencies and coordinate changes with Profile Architect.

- Risk: Cache/index absence causes inconsistent allowed-items behavior.
	- Mitigation: Formalize fallback policies and ensure final shipping gate performs resolvability checks.

- Risk: Wizard integration complexity introduces UX inconsistency.
	- Mitigation: Keep fermenter output structured and UI-agnostic; align contracts early with Wizard Engineer.

- Risk: Data Distillery network or schema drift causes nondeterministic validation behavior.
  - Mitigation: Use explicit fallback precedence, provenance tagging, timeouts, and contract tests against stable fixture snapshots.

- Risk: Multilingual message keys diverge between profile guidance and Wikibase registry entries.
  - Mitigation: Define canonical message-key namespace and validate key presence during CI for both SpiritSafe and Data Distillery exports.

## Handoffs

### Profile Architect

Inputs needed:

- Proposed profile schema extensions for fermenter constraint hooks
- Strategy for profile-level instructional metadata evolution that can feed actionable feedback

### Wizard Engineer

Inputs needed:

- Consumption contract for structured choices and actionable issue payloads
- Integration expectations for eager vs review-stage validation surfaces

### Semantic Engineer

Inputs needed:

- Data model and item/property instantiation plan in `datadistillery.wikibase.cloud` for:
  - validation message registry (multilingual labels/descriptions/aliases)
  - property registry records and constraint descriptors used by fermenter
  - profile manifest projection from SpiritSafe to Wikibase entities (full or selective scope)
- Query contract definitions (SPARQL/API patterns) and stability guarantees required for fermenter read-path integration
- Export/snapshot strategy so fermenter can validate in offline/fallback mode with deterministic behavior

## Data Distillery Wikibase Integration (Active)

`datadistillery.wikibase.cloud` is now an active part of the architecture and complements SpiritSafe.

Integration intent for fermenter V1:

- Keep SpiritSafe profile YAML as primary source of truth for profile constraints and form/validation shape.
- Use Data Distillery as canonical queryable registry for reusable property metadata, executable-constraint references, and multilingual validation messaging.
- Require deterministic fallback behavior to SpiritSafe/profile-local guidance whenever Data Distillery lookup is unavailable or incomplete.
- Record provenance in issue payloads (`source=profile|spiritsafe|datadistillery`) so downstream wizard and shipping layers can reason about trust and rendering.

Planned implementation sequencing:

1. Define read contracts and message-key conventions.
2. Implement thin client/resolver layer with timeout and fallback semantics.
3. Add fixture-driven tests for online and offline parity.
4. Expand to richer cross-entity resolver usage in post-V1 phases.
