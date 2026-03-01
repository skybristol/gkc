# Wizard Engineer Working Notes

**Date:** 2026-03-01

**Handoff from:** Profile Architect (archived to `.github/log/ProfileArchitect.20260301.md`)

## Purpose

Track the necessary work to implement the Textual Forms (TUI) interface for GKC entity data curation. This agent is responsible for consuming Entity Profiles and rendering interactive user-facing forms that guide data collection, validate input client-side, and serialize curated content for submission to Wikidata and other platforms.

## Current Reality Check

- **Profile Architect delivered:** Profile discovery API, path/query resolution, registrant layout, architecture docs, SpiritSafe source-of-truth policy, comprehensive test fixtures.
- **Textual integration status:** `gkc/profiles/forms/textual_generator.py` exists but is minimal; form generation logic not yet implemented.
- **Form pipeline:** Not yet defined—unclear how profiles map to widgets, how qualifiers/references render, how validation flows, how data serializes.
- **State of TextualForms branch:** Contains only foundational work; no working end-to-end form exists yet.

## Remaining Blockers for Textual Forms Implementation

### 1) Entity Profile YAML schema consumption is not architected for form generation

**What blocks progress**

- Wizard Engineer needs a clear mental model of Entity Profile structure (statements, datatypes, constraints, qualifiers, references, allowed items, SPARQL sources).
- No documented mapping exists from YAML profile concepts to form UI concepts (e.g., which datatype maps to which Textual widget; how qualifiers become nested input sections).
- Form generation libraries may expect certain interfaces/signatures that Profile YAML does not yet provide.

**Why this matters**

- Form rendering requires understanding the profile's intent and constraints—misinterpretation could produce forms that don't enforce profile rules or confuse users.

**What Wizard Engineer needs from Profile Architect**

- ✅ Available now: [Architecture docs](../architecture/) explain profile structure and validation layer.
- ✅ Available now: [API reference](../../docs/gkc/api/profiles.md) documents profile loading and datatype structures.
- ✅ Available now: Test fixtures in `tests/fixtures/profiles/` (registrant layout with real example profiles).
- ⚠️ **Needs specification:** Explicit form generation contract—what does a profile expose to form builders? (e.g., `profile.datatype_for_statement()`, `profile.allowed_items_for_statement()`, etc.)

**Theoretical next design step**

- Extend `EntityProfile` dataclass (or Pydantic model if generated) with form-focused helper methods:
  - `statement_widget_type(statement_id: str) -> WidgetType` - return the canonical Textual widget type for this statement
  - `statement_is_required(statement_id: str) -> bool`
  - `statement_allowed_items(statement_id: str) -> list[str]` or `AsyncIterator` for SPARQL sources
  - `statement_help_text(statement_id: str) -> str`
  - Similar helpers for qualifiers and references within statements

---

### 2) No form widget type mapping is defined (datatype → Textual widget)

**What blocks progress**

- `FundamentalType` enum exists (`text`, `item`, `itemlist`, `url`, `number`, `datetime`, `boolean`), but no definitive mapping to Textual widgets exists.
- Unclear how complex types like `itemlist` with SPARQL hydration should render (dropdown? multi-select? searchable autocomplete?).
- Unclear how optional vs required fields differ in UI (mandatory highlight? validation feedback?).

**Why this matters**

- Without this mapping, form generation is ad-hoc and inconsistent; users will see different interaction patterns for the same datatype across forms.

**What Wizard Engineer needs**

- ⚠️ **Needs specification:** Form widget type matrix (datatype + context → widget class).
- Example minimal matrix:
  ```
  text → Input(validate=regex_from_profile)
  number → InputInteger()
  boolean → Checkbox()
  item → Select() or SearchableSelect(allowed_items_list)
  itemlist → SelectMultiple() or TagInput()
  url → Input(validate=URLValidator)
  datetime → DatetimeInput() or ManualEntry()
  ```

**Theoretical design notes**

- **Autocomplete for items:** If `itemlist` references a SPARQL source with many results, should the form support incremental search/filtering? This implies:
  - Form needs access to hydrated allowed-item cache (see next blocker)
  - UI needs async/streaming item list (Textual's `OptionList` can support this)
  - User experience: search field + lazy-loaded dropdown
  
- **Qualifier rendering:** Qualifiers themselves have datatypes; should they follow the same widget mapping? Likely yes, but nesting increases complexity.

---

### 3) Hydration and caching of SPARQL-driven allowed items is not integrated with form rendering

**What blocks progress**

- `gkc.spirit_safe.hydrate_profile_lookups()` exists and can fetch remote SPARQL results.
- Form needs access to those hydrated caches (e.g., list of allowed countries, cities, etc.).
- Unclear when/how form should load cache (on form startup? on-demand when field is focused? from file?).

**Why this matters**

- Without hydration, form cannot provide autocomplete or validation against allowed items.
- Hydration happens at CLI/app startup (or on-demand), not at form-render time; form must assume cache is available.

**What Wizard Engineer needs**

- ✅ Available now: `gkc.spirit_safe.hydrate_profile_lookups()` API returns `LookupCache` dict.
- ✅ Available now: Profile metadata includes `sparql_sources` list with SPARQL file refs.
- ⚠️ **Needs design:** How does form access the cache? (e.g., injected at form init? global app state? context manager?)
- ⚠️ **Needs design:** What happens if cache is stale or missing? (fallback to manual entry? error?)

**Implementation hint**

- Form context should include a reference to the active `LookupCache` (probably from app state or form init args).
- When rendering a field with `sparql_source`, form looks up cache key and populates widget's item list.
- If cache key is missing, form either disables the field with a message or allows freeform text entry with validation warning.

---

### 4) Form flow and screen layout for multi-statement entities are not architected

**What blocks progress**

- Entities can have many statements; unclear if form is one monolithic screen or multi-step wizard.
- Unclear how qualifiers and references appear (inline? nested sub-form? modal?).
- Unclear how to handle required vs optional statements (are optional ones collapsed by default?).

**Why this matters**

- Poor form flow leads to cognitive overload; users need clear navigation and visual hierarchy.

**Theoretical design notes**

- **Option A: Monolithic scrollable form.** All statements on one screen, qualifiers nested inline or as expandable sections. Works for small profiles (5-10 statements); may overwhelm large profiles.
  
- **Option B: Multi-step wizard.** Required statements first, then optional in later steps. Clear progression; requires state management across steps.
  
- **Option C: Tabbed/sectioned layout.** Group statements by category (e.g., "Identity", "Locations", "Relationships"). Textual `TabbedContent` or custom pane navigation.

- **Option D: Hybrid.** Required statements in a main form; optional statements in an "Advanced" section (collapsed by default).

**What Wizard Engineer needs to decide**

- Profile schema should optionally include a `form_section` or `form_group` field to hint at grouping (e.g., `form_section: "identity"`).
- Form builder should respect this hint when rendering multi-step or tabbed layouts.

---

### 5) Client-side validation from profiles is not implemented

**What blocks progress**

- `gkc.validation` module exists but is focused on backend validation (preparing for Wikidata serialization).
- Form needs lighter client-side rules derived from profile (e.g., regex patterns, range checks, required checks, datatype coercion).
- Unclear which validation logic lives in profile vs form (profile is source of truth; form may add UI-specific rules).

**Why this matters**

- Poor validation feedback makes forms frustrating (users submit invalid data, get errors, have to re-enter).
- Profile-driven validation ensures consistency with backend validation.

**What Wizard Engineer needs**

- ✅ Available now: `EntityProfile` dataclass has `constraints` field (Pydantic can generate from it if needed).
- ⚠️ **Needs design:** Validation error messaging and field-level feedback in Textual (highlight, error label below field, etc.).
- ⚠️ **Needs test fixtures:** Profiles with various constraint types (regex, range, enum, required/optional).

**Theoretical design note**

- Validation should happen:
  1. On blur (field focus loss) for interactive feedback
  2. On submit (entire form) before serialization
  3. Provide clear, user-friendly error messages (not raw regex patterns)

---

### 6) Qualifier and reference handling patterns are not modeled for UI

**What blocks progress**

- Statements can have qualifiers and references; both are sub-statements with their own datatypes and constraints.
- Unclear how form should render these nested structures (inline? expandable? sub-form?).
- Unclear how user adds/removes qualifiers or references (buttons? drag-drop? context menu?).

**Why this matters**

- Qualifiers and references are essential for Wikidata precision; form must make them discoverable and easy to manage.

**Theoretical design notes**

- **Qualifiers rendering:** Likely inline within the statement (e.g., "Qualifier: [field] [remove button]"). Users can add multiple qualifiers.
  
- **References rendering:** Likely a collapsible subsection ("References") with add/remove buttons for each reference.
  
- **Data structure in form state:** Statement data should include:
  ```python
  {
    "main_value": "...",
    "qualifiers": [
      {"prop": "qualifier_prop_1", "value": "..."},
      {"prop": "qualifier_prop_2", "value": "..."},
    ],
    "references": [
      {"prop": "ref_prop_1", "value": "..."},
      {"prop": "ref_prop_2", "value": "..."},
    ]
  }
  ```

---

### 7) Test coverage for form generation does not exist

**What blocks progress**

- No unit tests for widget mapping, form rendering, validation, or data serialization.
- No fixtures for entity profiles with qualifiers/references/constraints to test against.

**Why this matters**

- Without tests, form logic is fragile and prone to regressions as profile schema evolves.

**What Wizard Engineer needs**

- ✅ Available now: Test fixtures in `tests/fixtures/profiles/` (registrant layout).
- ⚠️ **Needs:** Unit test suite for form generation module.
- ⚠️ **Needs:** Test fixtures covering:
  - Simple statements (text, number, item, itemlist)
  - Statements with SPARQL-driven allowed items
  - Statements with constraints (regex, range, required)
  - Statements with qualifiers and references
  - Entire complex entity profile

**Implementation hint**

- Test pattern: Load profile YAML → call form generator → assert Textual widget tree structure and properties.
- Use Textual's `Pilot` (test utilities) to simulate user interactions and validate state.

---

### 8) Data serialization (form → Wikidata JSON + other platforms) is not architected

**What blocks progress**

- Form collects data in its own internal structure (probably dict/dataclass).
- Unclear how to convert form data to Wikidata JSON format (reference chains, snapshot datavalues, etc.).
- Unclear which statements go to Wikidata vs other platforms (e.g., Wikimedia Commons file metadata).

**Why this matters**

- Serialization is the bridge between curation and publishing; mistakes here lose or corrupt data.

**What Wizard Engineer needs**

- ✅ Available now: `gkc.bottler` module has `entity_to_wikidata_json()` (backend serializer).
- ⚠️ **Needs design:** Form → intermediate format → Wikidata JSON pipeline. Should form serialize directly or hand off to bottler?
- ⚠️ **Needs:** Test fixtures verifying round-trip (profile → form → internal format → Wikidata JSON matches expected).

**Theoretical design note**

- Form should produce a Pydantic model or dataclass that can be passed to `gkc.bottler` for serialization.
- This separation keeps UI logic (form) decoupled from data logic (serialization).

---

## What Profile Architect Has Delivered (Handoff Checklist)

- ✅ **Profile discovery API** (`list_profiles()`, `profile_exists()`, `get_profile_metadata()`)
  - Form init can use this to list available entity types
  
- ✅ **Path/query resolution with fallback** (`resolve_profile_path()`, `resolve_query_ref()`)
  - Form loading of profiles and SPARQL queries works deterministically
  
- ✅ **Registrant package layout** (`profiles/<ProfileID>/profile.yaml` + metadata + queries)
  - Form fixtures can reference real profile structure
  
- ✅ **Architecture documentation** (`docs/architecture/`)
  - Profile schema, validation layer, SpiritSafe infrastructure all documented with implementation/theoretical framing
  
- ✅ **SPARQL hydration API** (`hydrate_profile_lookups()`, `LookupCache`)
  - Form can access allowed-item caches
  
- ✅ **SpiritSafe source-of-truth** (GitHub canonical, local clone override)
  - Form development can use `--source local --local-root /path/to/SpiritSafe` to test against custom profiles
  
- ✅ **Test fixtures** (registrant-style profiles in `tests/fixtures/profiles/`)
  - TribalGovernmentUS, EntityProfileExemplar with real statement/qualifier/reference patterns
  
- ⚠️ **Code generation** (`Pydantic` and `Textual` generators in `gkc/profiles/generators/`)
  - May need expansion/redesign for form-specific code generation

---

## Key Files Wizard Engineer Should Review

**Documentation:**
- [`docs/architecture/index.md`](../architecture/index.md) - System overview and core concepts
- [`docs/architecture/profile-loading.md`](../architecture/profile-loading.md) - How profiles resolve and load
- [`docs/architecture/spiritsafe-infrastructure.md`](../architecture/spiritsafe-infrastructure.md) - Profile registry and discovery
- [`docs/architecture/validation-architecture.md`](../architecture/validation-architecture.md) - Validation layers and constraints
- [`docs/gkc/profiles.md`](../../docs/gkc/profiles.md) - Entity Profile schema reference with "Implementation Status" and "Theoretical Design Notes"
- [`docs/gkc/api/profiles.md`](../../docs/gkc/api/profiles.md) - Python API for profile loading
- [`docs/gkc/api/spirit_safe.md`](../../docs/gkc/api/spirit_safe.md) - SpiritSafe discovery and hydration API

**Code:**
- [`gkc/entity_profile.py`](../../gkc/entity_profile.py) - `EntityProfile` and `ProfileMetadata` dataclasses; statement/qualifier/reference structures
- [`gkc/profiles/forms/textual_generator.py`](../../gkc/profiles/forms/textual_generator.py) - Minimal Textual form generator scaffold
- [`gkc/profiles/generators/`](../../gkc/profiles/generators/) - Code generation utilities (may need form-specific extension)
- [`gkc/spirit_safe.py`](../../gkc/spirit_safe.py) - Profile discovery, path resolution, hydration
- [`gkc/validation.py`](../../gkc/validation.py) - Validation engine (backend reference; form may implement lighter client-side version)

**Tests:**
- [`tests/test_profiles.py`](../../tests/test_profiles.py) - Profile loading/generation tests (reference for form test patterns)
- [`tests/fixtures/profiles/`](../../tests/fixtures/profiles/) - Real entity profiles (TribalGovernmentUS, EntityProfileExemplar) with statements, qualifiers, references
- [`tests/test_entity_profile.py`](../../tests/test_entity_profile.py) - Profile schema tests

---

## Minimal Unblock Sequence for Wizard Engineer

1. **Define form generation contract** - Extend `EntityProfile` with form-helper methods or create a `FormContext` wrapper.
2. **Implement widget type mapping** - Map `FundamentalType` enum to Textual widget classes with constraints/validation.
3. **Integrate with hydration cache** - Form init accepts `LookupCache`; field rendering looks up allowed items.
4. **Design form flow/layout** - Decide on monolithic vs multi-step architecture; implement navigation.
5. **Implement client-side validation** - Map profile constraints to form field validators; render user-friendly errors.
6. **Handle qualifiers/references** - Render nested statement data structures; manage add/remove/edit UX.
7. **Write test suite** - Unit tests for widget generation, validation, data state; integration tests with Pilot.
8. **Implement data serialization** - Form → intermediate format → Wikidata JSON pipeline with test fixtures.

---

## Definition of "Ready for End-to-End Form Testing"

- ✅ Form can load an entity profile from SpiritSafe (by name or explicit path).
- ✅ Form renders all statements with correct widget types.
- ✅ Form respects constraints (required fields, regex patterns, allowed items).
- ✅ Form handles qualifiers and references (nested rendering, add/remove).
- ✅ Form provides real-time validation feedback.
- ✅ Form serializes curated data to Wikidata JSON format.
- ✅ Unit and integration tests pass for all above.
- ✅ User can navigate from profile selection → data entry → review → submit in Textual TUI.

---

## Notes for Next Session

- TextualForms branch currently contains foundational work only; no working end-to-end form yet.
- Profile Architect work is complete and archived; next session should focus on defining the form generation contract (item 1 above).
- Consider starting with a simple, concrete example: render a form for TribalGovernmentUS profile (statement + qualifier + reference) to validate the entire pipeline.
- Hydration cache is available but form must handle the async/streaming aspect if SPARQL sources have large result sets.
