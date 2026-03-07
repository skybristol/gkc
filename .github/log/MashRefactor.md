# Mash Refactor Review and Plan

## Context

The current `gkc.mash` module is the inbound/read layer for GKC, with current implementations for:

- Wikibase/Wikidata entity retrieval and template shaping.
- Wikipedia template retrieval.
- Mash utilities used by CLI, formatters, and other modules.

The module is currently a single file (`gkc/mash.py`) at ~1426 lines and contains API clients, template models, transformation helpers, parsing logic, and source-specific loaders.

## Executive Summary

`gkc.mash` is now too dense for the expansion path (CSV, JSON API, dataframes, and additional source systems). The current shape increases coupling, duplicates logic, and makes it harder to add new inbound sources without touching unrelated concerns.

A package split (similar to the profiles architecture) is recommended now, with direct rename and reference updates throughout the `gkc` package, tests, and docs. We are in experimental mode and do not need legacy name compatibility.

## Current-State Findings

### 1) Density and mixed responsibilities

`gkc/mash.py` currently mixes multiple layers in one file:

- Transport/API client: `WikibaseApiClient`, Wikipedia HTTP access in `WikipediaLoader`.
- Domain/template models: `WikibaseItemTemplate`, `WikibasePropertyTemplate`, `WikibaseEntitySchemaTemplate`, `WikipediaTemplate`, `ClaimSummary`.
- Shared utilities: `fetch_property_labels`, `strip_entity_identifiers`.
- Parsing and mapping logic: `_snak_to_value`, `_statement_to_claim`, template construction.
- Source-specific loader orchestration: `WikibaseLoader`, `WikipediaLoader`.

This density makes new-source onboarding expensive because every addition increases blast radius inside a single module.

### 2) Duplication introduced during Wikidata -> Wikibase evolution

Concrete duplication hotspots:

- Repeated language filtering logic across:
  - `WikibaseItemTemplate.filter_languages`
  - `WikibasePropertyTemplate.filter_languages`
  - `WikibaseEntitySchemaTemplate.filter_languages`
- Repeated entity label/description/alias extraction in:
  - `_build_template`
  - `_build_property_template`
  - `_build_entity_schema_template` (subset)
- Repeated shell/export patterns (`summary`, `to_dict`, `to_shell`) across templates.
- Naming mismatch: generic capability exists (`WikibaseApiClient`) but loader/template naming remains heavily Wikidata-specific, causing ambiguity about intended scope.

### 3) Coupling and dependency pressure

Current consumers import directly from `gkc.mash`:

- `gkc.cli`: `WikibaseLoader`, `WikipediaLoader`
- `gkc.shipper`: `WikibaseApiClient`
- `gkc.wikibase.foundation`: `WikibaseApiClient`
- `gkc.mash_formatters`: `WikibaseItemTemplate`
- tests import many mash symbols directly

This means the refactor must update all intra-package imports comprehensively in one coordinated pass.

### 4) Test/docs alignment risk

- Tests are currently concentrated in `tests/test_mash.py` and expect the single-module import surface.
- API docs in `docs/gkc/api/mash.md` are generated from `gkc.mash.*` symbols.

A split with immediate renaming requires deliberate updates to both tests and mkdocstrings references in the same sprint.

## Why split now

The roadmap explicitly includes multiple inbound formats beyond Wikibase/Wikidata. Keeping all source adapters in one file would:

- Encourage copy/paste patterns (already visible).
- Increase merge conflicts and review complexity.
- Make boundary ownership between mash responsibilities less explicit.
- Slow down onboarding of source-specific logic (CSV/JSON/dataframe adapters).

## Recommended target architecture

Create a package `gkc/mash/` and remove the single-file `gkc/mash.py` implementation by moving content into focused modules and exporting only the new `Wikibase*` names.

Suggested layout:

```text
gkc/mash/
  __init__.py                  # stable public API re-exports
  protocols.py                 # DataTemplate and source contracts
  clients/
    __init__.py
    wikibase_api.py            # WikibaseApiClient
    wikipedia_api.py           # optional Wikipedia API client helper
  templates/
    __init__.py
    common.py                  # shared mixins/helpers for language/shell handling
    wikibase_item.py           # WikibaseItemTemplate
    wikibase_property.py       # WikibasePropertyTemplate
    wikibase_schema.py         # WikibaseEntitySchemaTemplate
    wikipedia_template.py      # WikipediaTemplate
  loaders/
    __init__.py
    wikibase_loader.py         # loader for item/property/schema retrieval
    wikipedia_loader.py        # WikipediaLoader
  parsers/
    __init__.py
    wikibase_claims.py         # ClaimSummary, statement/snak parsing
    wikibase_entity.py         # label/description/alias extraction helpers
  transforms/
    __init__.py
    language_filter.py         # reusable filter functions
    identifier_strip.py        # strip_entity_identifiers
  labels.py                    # fetch_property_labels (or transforms/property_labels.py)
```

Design intent:

- Keep concerns isolated by layer: client, parse, template, loader, transform.
- Make it obvious where new inbound source adapters should live.
- Reuse shared transform functions instead of duplicating template methods.
- Keep `WikipediaLoader` inside mash as a first-class source adapter (do not split to `gkc.wikipedia`).

## API migration strategy

### Target public API contract (post-refactor)

After migration, only these names are public from `gkc.mash`:

- `WikibaseApiClient`
- `WikibaseLoader`, `WikipediaLoader`
- `WikibaseItemTemplate`, `WikibasePropertyTemplate`, `WikibaseEntitySchemaTemplate`
- `ClaimSummary`, `fetch_property_labels`, `strip_entity_identifiers`

### Migration approach

- `gkc/mash/__init__.py` becomes the canonical export surface.
- Remove legacy `Wikidata*` names instead of aliasing.
- Update all imports/references in `gkc/`, `tests/`, and docs in the same sprint.

## Refactor phases

## Phase 0: Lock behavior before movement

- Add/confirm test coverage around current behavior of:
  - language filtering semantics
  - shell stripping
  - claim/snak parsing
  - loader error handling
  - API client request/response error wrapping
- Add one import-contract test for the *new* `Wikibase*` symbol surface in `gkc.mash`.

Exit criteria:

- Tests reliably capture today’s behavior so file movement doesn’t create regressions.

## Phase 1: Mechanical package extraction (no behavior change)

- Introduce `gkc/mash/` package and move code into focused modules.
- Keep function/class bodies behavior-identical.
- Export only the new `Wikibase*` public names in package `__init__.py`.
- Update CLI/docs/tests to use new import paths and symbols.

Exit criteria:

- Existing tests pass after explicit rename updates.
- `docs/gkc/api/mash.md` mkdocstrings references updated to the new symbol names.

## Phase 2: Deduplicate core logic

- Remove legacy in-place template mutators `filter_languages` and `filter_properties` entirely.
- Extract shared language-resolution helper (`gkc.get_languages()` normalization).
- Extract shared label/description/aliases flattening helper.
- Replace mutator behavior at call sites with explicit non-mutating handling in the relevant orchestration layer.
- Update CLI behavior that currently depends on these mutators.
- Update/replace tests that currently assert mutator methods.
- Update docs examples and API docs to remove mutator references.

Exit criteria:

- No duplicated language filtering code across template classes.
- Reduced repeated extraction code in loader builders.
- No remaining `filter_languages` or `filter_properties` methods on mash templates.
- CLI, tests, and docs contain no references to removed mutators.

## Phase 3: Introduce explicit source plugin contracts

- Define a minimal loader/source protocol (e.g., `SourceLoader` or `MashSourceAdapter`) to support future CSV/JSON/dataframe loaders.
- Keep Wikibase/Wikipedia loaders as first implementations.
- Document adapter contract and expected template shape boundaries.

Exit criteria:

- New source loaders can be added with minimal changes outside their own module.

## Testing strategy

During implementation:

- Start targeted:
  - `poetry run pytest tests/test_mash.py -q`
  - `poetry run pytest tests/test_mash_formatters.py -q`
  - `poetry run pytest tests/test_cli.py -q`
- Then broader:
  - `poetry run pytest tests/ -q`

Additions:

- Import surface contract test for the new `Wikibase*` symbols in `gkc.mash`.
- Optional parametric test for language filtering helper across template types.

## Documentation updates needed after implementation

- `docs/gkc/mash.md` (new):
  - Follow example from `docs/gkc/profiles.md`
  - Higher level documentation of the mash module
  - Be sure to include documentation of the mash source adapters, including outlining what a skeleton should look like for a new adapter
- `docs/gkc/api/mash.md`:
  - update examples and mkdocstrings references to `Wikibase*` names.
  - add brief architecture map of package internals.
- `notebooks/mash.ipynb`:
  - Rewrite the entire notebook after updating all codeblocks to document public-facing mash functionality in the API doc
  - Notebook cells should mimic the API quick start code examples to begin with
- `docs/gkc/cli/mash.md`:
  - Update with all changes at the CLI mash command route
- `docs/architecture/module-contracts.md`:
  - retain boundary statements; update internals to package paths if needed.
- Sweep all other docs under `docs/` for `Wikidata*` references in mash API examples and update to `Wikibase*`.

## Risks and mitigations

- Import breakage risk:
  - Mitigation: single coordinated rename pass plus import contract tests on new symbols.
- Hidden behavior drift during dedup:
  - Mitigation: phase behavior-lock tests before dedup.
- Over-generalization too early:
  - Mitigation: keep protocols minimal; avoid premature abstraction for unimplemented sources.

## Architectural questions for decision

1. Naming direction:
   - Do we keep public class names `Wikidata*` for now, or introduce `Wikibase*` names immediately with aliases?

    > Move to `Wikibase*` immediately and replace all of the older `Wikidata*` stuff. No need to maintain backward compatibility on this, but we'll need to work all through documentation as well. We do not need to touch the notebooks as I'll deal with those separately.

2. Compatibility horizon:
   - How long should legacy names remain supported (one minor release, one major cycle, or indefinite aliases)?

    > Get rid of them now. We're in purely experimental dev mode right now.

3. Loader boundary:
   - Should `WikibaseLoader` continue handling EntitySchema via `cooperage.fetch_entity_schema_json`, or should schema retrieval be moved into a dedicated mash client/parser boundary?

    > Entity Schema stuff was moved into mash already. Treat it like a specialized part of Wikibase loading.

4. Template mutability:
   - Do we keep in-place mutating filters (`filter_languages`, `filter_properties`) or introduce immutable/functional variants for safer composability?

    > These were two specialized features that were built when we were starting to experiment with what it would look like to grab a Wikidata item and use it as a template for new items. Since then, we have moved to the Curation Packet concept where this kind of functionality would now plug in. We need to look at any place that these functions are called and then decide what to do with them.

  Decision captured for implementation: remove `filter_languages` and `filter_properties` from mash templates during refactor and update all dependent CLI paths, tests, and docs in the same sprint.

5. Wikipedia placement:
   - Keep Wikipedia loader in mash package as first-class source adapter, or split to `gkc.wikipedia` later while re-exporting via mash?

    > You might be thinking about this like gkc.wikibase, but these are very different concepts. Mash is where we want all the load-source-for-processing functionality. The wikibase module is specifically for managing the Data Distillery Wikibase (we should perhaps consider a renaming at some point). That is a specialized wikibase instance that we are using as the semantic registry layer for the whole Data Distillery architecture.

  Decision captured for implementation: keep `WikipediaLoader` in mash as part of source-loading adapters. Do not split to `gkc.wikipedia` in this refactor.

6. New source adapter contract:
   - Should new loaders return source-specific templates only, or a normalized intermediate template protocol for cross-source downstream transforms?

   > I think the intermediate template is actually going to be the Entity Profile-driven Curation Packet construct. We may need to eventually do something at the mash layer to do a basic churn of some types of sources into something more digestible. But not for now.

7. Deprecation policy mechanics:
   - Should we emit runtime `DeprecationWarning` for legacy class names immediately, or wait until new names are documented and adopted in CLI/docs?

   > Let's just go all the way on this stuff, incrementally enough that we take care of dependencies within the package. There are no major external dependencies to worry about at this point.

## Recommended immediate next step

Implement Phase 1 as package extraction plus immediate `Wikidata*` -> `Wikibase*` rename in one sprint, then run a full dependency/docs/test sweep before dedup and contract work.

## Handoff Summary

- Scope completed: Architecture review and phased refactor plan for mash modularization.
- Primary module targeted next: mash implementation (`gkc/mash/` package extraction).
- Public contracts to deliver: new `Wikibase*` naming surface from `gkc.mash`.
- Key assumptions: no legacy alias or deprecation layer is required in this cycle.
- Open risks: import/doc breakage if dependency sweep is incomplete.
- Next owner: implementation pass (Code Cleaner / core maintainer).
- Inputs required: none for naming/compatibility; decisions already captured.

---

## Completion Notes (Moved to Sprint Log)

This sprint plan has been completed and is now archived as implementation log history.

### Completed Scope

- Package extraction completed for mash into `gkc/mash/` with stable exports from `gkc/mash/__init__.py`.
- Public naming migration completed from `Wikidata*` mash symbols to `Wikibase*` mash symbols.
- Legacy in-template mutators removed from mash templates (`filter_languages`, `filter_properties`).
- Explicit filtering helpers implemented and adopted at call sites:
  - `apply_template_language_filter()`
  - `apply_item_property_filters()`
- `MashSourceAdapter` protocol implemented and exported as the plugin contract.
- First adapter implementations completed:
  - `WikibaseMashSourceAdapter`
  - `WikipediaMashSourceAdapter`
- Documentation updates completed for mash overview, mash API, mash CLI, and notebook rewrite.

### Validation Outcomes

- Focused and full regression test runs completed successfully.
- Pre-merge checks pass, including docs build and packaging checks.
- Remaining mypy issues are existing non-blocking repository-wide debt and not specific regressions from this sprint.

### Follow-on Work Enabled

- New source adapters (CSV, JSON API, dataframe) can now be added via `MashSourceAdapter` with minimal cross-module impact.

## Proposed Commit Message

`docs(log): archive MashRefactor plan with completion notes and migration outcomes`
