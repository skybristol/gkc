# Wizard Engineer Working Notes

**Date:** 2026-03-01  
**Session:** Initial MVP Planning  
**Handoff from:** Profile Architect (archived to `.github/log/ProfileArchitect.20260301.md`)

## Purpose

Track the necessary work to implement the Textual Forms (TUI) interface for GKC entity data curation. This agent is responsible for consuming Entity Profiles and rendering interactive user-facing forms that guide data collection, validate input client-side, and serialize curated content for submission to Wikidata and other platforms.

---

## 🛑 STRATEGIC PAUSE: Tech Foundation Evaluation (2026-03-01)

### Current State
- **Phase 1 completed**: Basic wizard shell with 5-step navigation working end-to-end
- **Phase 2/4 partial**: IdentificationStep and SitelinksStep rendering with package-language scoping
- **Navigation functional**: Users can move between steps, form fields render, data collects and persists
- **Tests green**: 17 tests passing for wizard structure and language scope resolution

### Textual Framework Findings 🔍
**What Works:**
- Basic form rendering and widget hierarchy
- Event handling and button navigation
- Dynamic widget mounting/unmounting (with careful attention to ordering)
- Package integration via `pip install -e`

**What's Problematic:**
- **Layout inconsistency**: CSS layout behaves differently across terminal sizes and platforms; scrolling/overflow behavior unreliable
- **Platform quirks**: Height calculations and spacing don't respond predictably to `height: 1fr`, `overflow: auto`, etc.
- **Pick-list UX uncertainty**: TypeAheadSelect widget is a partial implementation; autocomplete/type-ahead behavior in Textual is rudimentary and may not meet curator experience standards
- **Complexity-to-value ratio**: Substantial effort spent debugging layout edge cases rather than feature development

### Options Under Consideration
1. **Continue with Textual**: Accept platform variability, focus on features over perfect layout
   - ✅ CLI-native, no external server
   - ❌ Layout wonkiness likely to persist; pick-list UX compromised
   
2. **Pivot to Streamlit**: Web-based form builder with mature form/pick-list libraries
   - ✅ Excellent layout consistency, proven UX patterns, robust form widgets, built-in session state
   - ❌ Requires running local Streamlit server; adds deployment complexity
   - ❌ Different paradigm (web app vs TUI) - UI code becomes completely different

3. **Hybrid approach**: Keep CLI for expert workflows, optional web dashboard for curator workflows
   - ✅ Best of both worlds for user choice
   - ❌ Doubles the UI engineering effort; scope explosion

### Decision Point for Next Session
**Recommend discussion before proceeding**: The UI layer choice significantly impacts downstream architecture (state management, widget library, form rendering logic, validation feedback patterns). Better to make this call deliberately than to invest more time in Textual only to hit a usability wall.

### What's Preserved Regardless
- ✅ **Profile model/structure**: YAML profiles are tool-agnostic
- ✅ **Validation engine**: Works independently of UI framework
- ✅ **Language scoping logic**: `resolve_language_scope()` applies to any rendering context
- ✅ **Data collection/persistence**: DraftManager and draft format are portable
- ✅ **CLI integration**: Profile loading and source resolution are decoupled from UI
- ✅ **Tests for core logic**: test_textual_forms.py tests behavior, not Textual API

If we pivot to Streamlit (or another framework), we'd replace only `gkc/profiles/forms/textual_generator.py` and the step rendering code, not the foundational architecture.

---

## 📋 Resumption Guide for Next Session

### To Pick Up Where We Left Off

**1. Verify Branch State**
```bash
cd /Users/sky/code/gkc
git status  # Should show TextualForms branch with staged changes
```

**2. If Continuing with Textual:** Run the wizard to verify it still works
```bash
poetry run gkc profile form --profile TribalGovernmentUS --source local --local-root /Users/sky/code/SpiritSafe
```
- Should navigate through 5 steps without errors
- Form fields should render and collect data

**3. If Pivoting to Streamlit (or Another Framework):**

**Files to Replace:**
- `gkc/profiles/forms/textual_generator.py` — Entire file (WizardApp, renderer logic, CSS)
- `gkc/profiles/forms/wizard/` — Step implementation code (keep step_base.py interface concept, rewrite step rendering)

**Files Worth Preserving:**
- `gkc/profiles/forms/__init__.py` — Exports API
- `gkc/profiles/forms/wizard/step_base.py` — Step interface (could be adapted for new framework)
- `gkc/profiles/__init__.py` — Language setting logic (`get_languages()`, `set_languages()`)
- `gkc/cli.py` — Profile loading/source resolution (framework-agnostic)
- `tests/test_textual_forms.py` — Logic tests (update UI framework assertions only)

**Portable Logic to Reuse:**
- `resolve_language_scope()` function (works in any rendering context)
- `DraftManager` class (file format independent)
- Step data collection patterns (mapping form inputs to draft_data)
- `_persist_current_step_data()` logic (validation + draft update)

**4. Outstanding Issues to Address Next Session**
- **Dynamic alias rows**: Still needs "Add another" UI for IdentificationStep
- **Validation feedback**: Non-blocking validation needs UI integration
- **Statements step**: Rendering not started (complex multi-count statement UX)
- **Sitelinks refinement**: Only showing en:wikipedia, needs full language support
- **Review step**: Display consolidated data + validation results
- **Data export**: Serialize draft → Wikidata JSON format

**5. Test Coverage to Maintain**
- 17 tests currently passing in `test_textual_forms.py`
- Tests cover: step navigation, language scoping, data collection
- If changing framework: rewrite UI-specific assertions, keep behavior tests intact

### Repository State (Current Files Modified)

```
CLI Docs:
  ✏️  docs/gkc/cli/index.md — Updated wizard references
  ✏️  docs/gkc/cli/profiles.md — Added --source/--local-root options

Code Changes:
  ✏️  gkc/cli.py — Profile loading refactor for SpiritSafe source config
  ✏️  gkc/profiles/forms/textual_generator.py — WizardApp implementation
  ✏️  gkc/profiles/forms/__init__.py — Export WizardApp + DraftManager
  ✏️  gkc/profiles/schemas/profile.schema.json — Relaxed statement required constraint
  ✨ gkc/profiles/forms/wizard/ — New package (step_base.py, steps.py, __init__.py)

Tests:
  ✏️  tests/test_textual_forms.py — 17 tests passing (wizard structure + language scoping)
  ✏️  tests/test_cli.py — CLI profile resolution tests
  ✏️  tests/test_profiles_yaml.py — Schema compatibility test

Working Artifacts:
  ✏️  .github/prompts/WizardEngineer.working.md — This file (strategic pause notes added)
  🗑️  .github/prompts/plan-multiStepWizardFormGeneration.prompt.md — DELETED (superseded)
  📁 .drafts/ — Auto-save location for wizard sessions (untracked)
```

---

## Current Reality Check (Revised After Codebase Review)

### What Profile Architect Delivered ✅
- **Profile discovery API**: `list_profiles()`, `profile_exists()`, `get_profile_metadata()`
- **Path/query resolution**: `resolve_profile_path()`, `resolve_query_ref()` with fallback
- **Registrant layout**: `profiles/<ProfileID>/profile.yaml` + metadata + queries
- **Architecture docs**: Split into focused pages under `docs/architecture/`
- **SpiritSafe source-of-truth**: GitHub mode default, local override policy
- **Test fixtures**: Registrant-style fixtures for TribalGovernmentUS and EntityProfileExemplar

### What Actually Exists in Forms Code ✅
- **ProfileFormApp**: Single-screen monolithic form (not wizard-based yet)
- **TextualFormGenerator**: Creates ProfileFormApp, preloads choice lists from cache
- **WidgetFactory**: Maps all Wikidata datatypes to Textual widgets (comprehensive coverage)
- **TypeAheadSelect**: Custom Textual widget for autocomplete selection
- **Widget validators**: QID, URL, time, coordinates, lat/lon validators
- **FormSchemaGenerator**: Builds form schema from ProfileDefinition
- **ProfileValidator**: Validates items against profile constraints
- **CLI integration**: `gkc profile form` command launches ProfileFormApp

### What's Working 🟢
1. **Profile loading from SpiritSafe** (local and GitHub modes)
2. **Datatype widget mapping** (all Wikidata types covered)
3. **SPARQL hydration and caching** (choice lists preloaded)
4. **Basic form rendering** (labels, descriptions, statements with qualifiers/references)
5. **Validation infrastructure** (ProfileValidator ready to integrate)

### What's Missing for MVP 🔴
1. **Multi-step wizard container** (currently single monolithic form)
2. **Step navigation** (Back, Next, Skip, Finish buttons with state management)
3. **Draft persistence** (no save/resume capability)
4. **Aliases rendering** (defined in YAML, not rendered in form)
5. **Sitelinks rendering** (defined in YAML, not rendered in form)
6. **Dynamic statement addition** ("Add another" for multi-count statements)
7. **Validation results display** (validation runs but no UI feedback)
8. **Data serialization to Wikidata JSON** (form collects data but doesn't serialize)
9. **Review/summary step** (no consolidated review before submission)
10. **Edit mode** (--qid flag exists but no pre-population logic)

---

## MVP Definition: Basic Working Wizard

**Goal:** Implement the minimal multi-step wizard that can create a complete TribalGovernmentUS entity and export validated Wikidata JSON.

**Success Criteria:**
- ✅ Wizard navigates through 5 steps (Plan → Identification → Statements → Sitelinks → Review)
- ✅ Each step collects data, validates incrementally, saves draft state
- ✅ No validation blocks progression (warnings accumulate for review)
- ✅ Review step shows all data with validation results
- ✅ Export validated data to Wikidata JSON format
- ✅ Draft auto-save on step navigation, manual resume from draft
- ✅ All Wikidata datatypes handled with appropriate widgets
- ✅ Dynamic "Add another" for multi-count statements

**Out of Scope for MVP:**
- ❌ Direct shipping to Wikidata API (export only)
- ❌ Edit mode (--qid pre-population)
- ❌ Sub-wizard workflows (OfficeHeldByHeadOfState)
- ❌ OpenStreetMap integration
- ❌ Wikimedia Commons file upload
- ❌ Advanced validation (cross-statement semantic rules)
- ❌ Undo/redo navigation
- ❌ Field-level help/documentation panels

---

## Design Decisions Needed

### 1. Multi-Step Architecture Choice ✅ RESOLVED

**Decision:** Option A (start fresh) - Replace ProfileFormApp entirely

**Rationale:**
- ProfileFormApp is a monolithic prototype that never shipped
- The valuable reusable code is already modular:
  - ✅ Keep `WidgetFactory` (separate module, battle-tested)
  - ✅ Keep `TypeAheadSelect` widget (genuinely useful)
  - ✅ Keep widget validators (QID, URL, time, coordinates)
- ProfileFormApp's `_build_form_fields()` is monolithic - would need complete rewrite for per-step rendering anyway
- No users, no releases - clean break costs nothing
- Avoids code orphans: delete ProfileFormApp class, keep reusable widgets

**Implementation:**
- Create new `WizardApp` as main application class
- Import and reuse `WidgetFactory`, `TypeAheadSelect` from existing modules
- Deprecate/delete `ProfileFormApp` class after WizardApp is working

---

### 2. Step State Management ✅ RESOLVED

**Decision:** Option A (centralized draft dict)

**Rationale:**
- Simpler mental model: one source of truth for all wizard state
- Easier serialization for auto-save (just JSON dump the whole dict)
- Steps are thin views over shared data - easier to debug
- Can evolve to Pydantic models post-MVP if type safety becomes issue

**Implementation:**
- `WizardApp.draft_data: dict[str, Any]` contains all collected data
- Steps receive draft_data reference on init/load
- Steps write directly to draft_data (e.g., `draft_data["labels"]["en"] = "..."`)
- Auto-save just serializes `self.draft_data` to JSON file

---

### 3. Validation Philosophy Alignment ✅ CONFIRMED

**Decision:** No blocking validation - all statements fundamentally optional

**Philosophy (from Profile Architect):**
> "required: true marks **recommended** statements, not blockers. All statements are fundamentally optional."

**Implementation for Wizard:**
- `required: true` → generate **warning** if skipped, but **allow progression**
- Missing recommended statements → show in review step **"What's missing"** panel
- Only true errors block shipping:
  - Malformed data (invalid QID format, bad URL, etc.)
  - Type mismatches (string where item expected)
  - Profile constraint violations (regex, range checks)
- User can ship with warnings after explicit confirmation: "You have 3 warnings and 5 missing recommendations. Ship anyway?"

**Rationale:**
- Follows Wikipedia/Wikidata principle: minimal viable items can be created quickly, enhanced later
- Aligns with community expectations for incremental curation and later enrichment

---

### 4. Sitelink Conflict Validation Timing ✅ RESOLVED

**Decision:** Option B - Validate in review step only (MVP scope)

**Rationale:**
- Avoid API calls on every field blur (slow, chatty)
- Sitelink conflicts are rare enough that batch validation is acceptable
- Review step already planned for comprehensive validation display
- Post-MVP: can add real-time validation if curators request it

**Implementation:**
- Sitelinks step collects article titles (no validation)
- Review step runs batch validation:
  - Check format (valid article title structure)
  - Optionally: API call to check uniqueness (defer for MVP if too complex)
  - Display conflicts as errors (blocking) or warnings (if export-only)

**Deferred for post-MVP:** Real-time sitelink conflict detection during data entry

---

### 5. Reference Auto-Derivation Timing ✅ RESOLVED

**Decision:** Derive on review step load

**From profile YAML:**
```yaml
behavior:
  references: auto_derive  # Auto-generate P854 from P856
```

**Rationale:**
- User sees derived references before export/shipping - no surprises
- Can manually edit derived references if needed (override auto-derivation)
- Keeps statements step simpler (no reference inputs for auto_derive behavior)
- Clear separation: data entry (statements) vs. validation/finalization (review)

**Implementation:**
- Statements step: hide reference inputs when `behavior.references: auto_derive`
- Review step: run `_derive_references()` before displaying summary
  - Example: P854 (reference URL) ← P856 (official website URL)
  - Add derived references to draft_data
  - Mark as auto-derived so user can distinguish from manual references
- Export: include all references (manual + auto-derived)

---

### 6. Multi-Count Statement Data Shape ✅ RESOLVED

**Decision:** List of statement instances, each with qualifiers and references

**Data Structure:**
```python
# Single-count statement (max_count: 1)
draft_data["statements"]["instance_of"] = {
    "value": "Q7840353",
    "qualifiers": {},
    "references": [{"stated_in": "Q138391266"}]
}

# Multi-count statement (max_count: null or > 1)
draft_data["statements"]["official_website"] = [
    {
        "value": "https://example.com",
        "qualifiers": {"language_of_work": "Q1860"},
        "references": [{"reference_url": "https://example.com"}]
    },
    {
        "value": "https://ejemplo.mx",
        "qualifiers": {"language_of_work": "Q1321"},
        "references": [{"reference_url": "https://ejemplo.mx"}]
    }
]
```

**UI Pattern:**
- First instance rendered by default
- "Add another [property label]" button appears at bottom
- Clicking adds new instance: duplicates widget group (value + qualifiers + references)
- Each instance has "Remove" button (except when only one instance remains)
- Navigation to next step collects all instances into the list structure

**Rationale:**
- Mirrors Wikidata's multi-value statement model
- Each statement instance is independent (own qualifiers, own references)
- Simple serialization to Wikidata JSON (each list item → one claim)

---

### 7. Draft File Naming ✅ RESOLVED

**Decision:** Use timestamped files: `<profile_id>_<timestamp>.json`

**Format:** `.drafts/TribalGovernmentUS_20260301_143052.json`

**Rationale:**
- Preserves history: multiple drafts can coexist (useful for debugging, recovery)
- Avoids accidental overwrites: each wizard session gets unique draft
- Can implement "resume latest" by sorting timestamps
- Easy cleanup: delete old drafts after export/ship
- No collision risk if running multiple wizard sessions (edge case, but possible)

**Alternative considered:** `<profile_id>_latest.json` - simpler but loses history, can't debug previous sessions

---

## All Design Decisions Resolved ✅

All major architectural choices are now locked in.

## Questions for Profile Architect (Not Blocking MVP)

These are informational questions for future profile schema enhancements. MVP will proceed with hardcoded defaults in wizard code.

### 1. YAML Schema Enhancements for Wizard Metadata

**Current reality:** Profiles have no wizard-specific metadata

**Needed for wizard:**
```yaml
wizard_config:
  enabled: true  # or false for single-form fallback
  step_titles:
    identification: "Tell us about this tribe"
    statements: "Add details and sources"
    sitelinks: "Connect to Wikipedia and other sites"
  estimated_time: "15-20 minutes"
  required_prep:
    - "Official tribal government website URL"
    - "Federal Register notice for recognition"
```

**Question:** Should this be added to profile YAML, or stay in wizard code as defaults?

**Recommendation:** Start with hardcoded defaults in wizard code, defer YAML extension post-MVP

---

### 2. Statement Grouping/Ordering

**Current reality:** Statements appear in YAML order

**For wizard:** Do we need statement grouping metadata?
```yaml
statements:
  - id: instance_of
    wizard_group: "classification"  # optional grouping hint
    wizard_priority: 1  # optional display order
```

**Question:** Is YAML order sufficient, or do we need explicit grouping?

**Recommendation:** YAML order is sufficient for MVP — revisit post-launch based on curator feedback

---

### 3. Choice List Deduplication Across Profiles

**From handoff:**
> "There is still work to do there like handling duplicative SPARQL queries for list items across profiles"

**Question:** Is this blocking for MVP?

**Answer:** No — hydration works, duplication is an optimization concern for future work

---

## Questions for Validation Agent (Not Blocking MVP)

These define the expected contract between Wizard and Validation Agent. MVP will implement based on current `ProfileValidator` API.

### 1. Validation Display Contract

**What Wizard needs from Validation Agent:**
- Validation result format that wizard can render
- Per-field, per-statement, and whole-entity validation levels
- Severity levels: `error` (malformed), `warning` (conformance issue), `suggestion` (missing recommended)

**Proposed ValidationResult format:**
```python
@dataclass
class ValidationIssue:
    severity: Literal["error", "warning", "suggestion"]
    field_id: str  # e.g., "official_website" or "label_en"
    message: str
    suggestion: Optional[str] = None
    
@dataclass
class ValidationResult:
    ok: bool  # True if no errors (warnings/suggestions allowed)
    issues: List[ValidationIssue]
```

**Note for MVP:** Will use existing `ValidationResult` from `gkc.profiles.validation.validator` and adapt display as needed

**Question:** Is this the right contract, or does Validation Agent need different structure?

---

### 2. Validation Timing

**When should validation run?**
- Real-time (on field blur) → need fast, lightweight validation
- Per-step (on Next click) → can be heavier, accumulate issues
- Review step → full validation with all cross-checks

**Question:** Should wizard call different validation methods for each timing, or same method with different modes?

**Note for MVP:** Use existing `ProfileValidator` API, adapt as implementation reveals needs

---

## Handoff Summary for Architecture Changes (Post-MVP)

**If Profile Architect needs to modify YAML schema:**
1. Add `wizard_config` top-level section (defer post-MVP)
2. Add `wizard_group`/`wizard_priority` to statements (defer post-MVP)
3. Clarify `behavior.references` auto-derivation timing semantics

**If Validation Agent needs to modify validation API:**
1. Ensure `ValidationResult` format supports severity levels
2. Support partial validation (incomplete drafts during wizard flow)
3. Provide user-friendly messages (not technical constraint violations)

---

## Special Note for Profile Architect (Track for Post-MVP)

- Wizard implementation will proceed with current profile model and no blocking YAML schema changes.
- Keep `wizard_config` and statement grouping metadata (`wizard_group`, `wizard_priority`) as deferred enhancements.
- Continue documenting profile-level semantics for behaviors like `references: auto_derive` so Wizard and Validation can apply them consistently.
- Non-blocking future enhancement: profile-level hints for validation/coercion presentation (for example, display-first guidance vs strict backend constraints).

---

## Special Note for Validation Agent (Track for Post-MVP)

- Wizard should maximize in-process validation and coercion feedback while curators are still editing.
- Leverage cached choice lists for item-valued statements wherever available to reduce invalid inputs before review.
- Coercion opportunities (for example, datatype normalization and user-friendly repair suggestions) should be surfaced during step validation and again in review.
- Some constraints cannot be guaranteed locally, especially destination-level uniqueness rules such as sitelinks being valid on only one Wikidata item.
- These destination-constrained checks should be represented as:
   - advisory warnings in wizard when possible, and
   - final blocking errors at submission/shipping time when returned by Wikidata or another destination API.
- Validation messaging should clearly distinguish:
   - `error` (malformed/type-invalid),
   - `warning` (non-conforming but shippable),
   - `destination-conflict` (requires external uniqueness/state check).

---

## Implementation Plan: 6 Phases to MVP

## Phase Status Snapshot (Updated 2026-03-01, Strategic Pause)

- ~~Phase 0: Foundation assessment and scope lock~~ ✅ complete
- ~~Phase 1: Wizard infrastructure shell~~ ✅ complete (WizardApp running, 5-step navigation working, tests green)
- Phase 2: Identification step expansion 🔄 partial (basic rendering & language scoping done; dynamic alias rows & validation feedback pending)
- Phase 3: Statements step and dynamic statement UX ⏳ not started
- ~~Phase 4: Plan/Sitelinks/Review fully functional steps~~ 🔄 partial (SitelinksStep basic rendering & language scoping done; review display not started)
- Phase 5: Wizard serialization to Wikidata JSON ⏳ not started
- Phase 6: Polish + documentation completion ⏳ not started

**Phase 1 Delivered (Implemented 2026-03-01):**
- ✅ `WizardApp` shell with 5-step navigation (Plan, Identification, Statements, Sitelinks, Review)
- ✅ Step modularization via `gkc/profiles/forms/wizard/` package
- ✅ `PlanStep`, `IdentificationStep`, `SitelinksStep`, `PlaceholderStep` classes
- ✅ `resolve_language_scope()` helper for package-driven language filtering
- ✅ Draft autosave to `.drafts/<profile>_<timestamp>.json`
- ✅ CLI profile loading refactor for SpiritSafe source resolution
- ✅ Profile schema compatibility (removed `required` constraint on statements)
- ✅ Tests (17 passing in test_textual_forms.py)

**Phase 2 Implementation Status (Identification):**
- ✅ Basic rendering with labels, descriptions, aliases
- ✅ Package-language scoping applied to all three fields
- ✅ Form field binding via unique IDs (label_{lang}, description_{lang}, alias_{lang}_0)
- ✅ Data collection back to draft_data
- ❌ Dynamic alias rows ("Add another") - **NOT YET IMPLEMENTED**
- ❌ Per-field validation feedback - **NOT YET IMPLEMENTED**

**Phase 4 Implementation Status (Sitelinks):**
- ✅ Basic rendering with en:wikipedia form field
- ✅ Package-language scoping applied to sitelinks
- ✅ Data collection back to draft_data
- ❌ Full sitelinks language support (only showing en:wikipedia) - **PARTIAL**
- ❌ Review/validation results display - **NOT YET IMPLEMENTED**

**Blocker: Textual Framework Viability 🚨**
See "STRATEGIC PAUSE: Tech Foundation Evaluation" section above. Layout consistency and pick-list UX concerns identified. Recommend framework decision before proceeding to Phase 2/3 feature depth.

### Phase 0: Foundation Assessment & Cleanup ✅ (Complete)
**Status:** Current session

**Tasks:**
- ✅ Review existing ProfileFormApp, WidgetFactory, TextualFormGenerator
- ✅ Assess Profile Architect deliverables
- ✅ Identify reusable vs obsolete components
- ✅ Define MVP scope and design questions

**Outcome:** This working document with clear MVP definition

---

### ~~Phase 1: Core Wizard Infrastructure (Week 1)~~ ✅ COMPLETE

**Goal:** Build multi-step wizard container and navigation without touching step content

**Deliverables:**
1. **WizardStep base class** (abstract interface for all steps)
   ```python
   class WizardStep:
       def render(self) -> ComposeResult: ...
       def collect_data(self) -> dict[str, Any]: ...
       def validate(self) -> list[ValidationIssue]: ...
       def load_draft(self, draft: dict[str, Any]) -> None: ...
   ```

2. **WizardContainer widget** (navigation chrome)
   - Header: progress indicator, step title
   - Body: dynamic content area (mounts active step)
   - Footer: navigation buttons (Back, Next/Skip, Finish)
   
3. **WizardApp** (replaces ProfileFormApp as main app class)
   - Manages step sequence
   - Handles navigation button events
   - Maintains central `draft_data` dict
   - Triggers auto-save on step transitions

4. **DraftManager** (persistence layer)
   - Save draft to `.drafts/<profile_id>_<timestamp>.json`
   - Load draft from file
   - Auto-save on navigation (non-blocking background write)

**Test Coverage:**
- Navigation through empty steps (just headers, no content yet)
- Draft save/load with mock data
- Back/Next button state management
- Progress indicator updates

**Design Decisions:** ✅ All resolved (see "Design Decisions Needed" section above)

**Estimated Effort:** 3-4 days

---

### Phase 2: Step 2 - Basic Identification (Week 1-2) 🔄 IN PROGRESS

**Goal:** Implement first real step with working data collection

**Language Scope Rule (Package-Driven):**

- Use `gkc.get_languages()` as the wizard language scope for labels, descriptions, and aliases.
- If language setting is single-language (default `"en"`), render only that language with no language chooser UX.
- If language setting is a list (for example `["en", "es"]`), render only those languages.
- If language setting is `"all"`, render all languages defined in the profile for that section.
- If a configured language is absent in the profile section, skip that language silently for MVP.

**Deliverables:**
1. **IdentificationStep** class
   - Renders labels using package language scope (not unconditional all-profile languages)
   - Renders descriptions using package language scope
   - Renders aliases using package language scope with "Add another alias" button
   - Collects data to `draft_data["labels"]`, `draft_data["descriptions"]`, `draft_data["aliases"]`

2. **Dynamic alias addition**
   - "Add another alias" button per language
   - Each alias gets its own Input widget
   - Remove button per alias row

3. **Field-level validation**
   - Required language warnings (non-blocking) for rendered language scope
   - On blur: validate format, show inline feedback
   - On Next: accumulate warnings for review

4. **Integration with existing widgets**
   - Reuse Input widget from ProfileFormApp
   - Use profile `input_prompt` and `guidance` text

**Test Coverage:**
- With default language (`"en"`), render only English label/description/alias inputs
- With language list (for example `["en", "es"]`), render only configured languages present in profile
- With `"all"`, render all profile languages for labels/descriptions/aliases
- Add multiple aliases, verify draft state
- Navigate forward (collect data), backward (restore data)
- Validation warnings display correctly

**Dependencies:**
- Phase 1 complete (wizard navigation working)

**Estimated Effort:** 2-3 days

---

### Phase 3: Step 3 - Statements (Week 2-3)

**Goal:** Implement statement entry with qualifiers, references, and dynamic addition

**Deliverables:**
1. **StatementsStep** class
   - Renders all statements from profile (ordered by YAML)
   - Uses WidgetFactory for datatype-appropriate widgets
   - Renders qualifiers inline under statement value
   - Renders references based on `behavior.references`:
     - `editable`: show reference inputs
     - `auto_derive`: hide, compute on review
     - not specified: show reference inputs (default)
   
2. **Dynamic statement addition**
   - "Add another [property label]" button for `max_count > 1` or `max_count: null`
   - Each instance tracked in `draft_data["statements"]["<stmt_id>"]` as list
   - Remove button for each added instance

3. **Reference auto-derivation**
   - Detect `behavior.references: auto_derive`
   - Skip reference rendering in statements step
   - Implement `_derive_references()` method (called in review step)
   - Example: P854 from P856 (reference URL from official website)

4. **Skip statement workflow**
   - "Skip this statement" button per statement
   - Records skip in draft: `draft_data["skipped_statements"] = ["member_count"]`
   - Review step shows what was skipped

5. **Choice list integration**
   - Pre-loaded choice lists from TextualFormGenerator
   - TypeAheadSelect for item fields with choices
   - Fallback to plain Input if choice list unavailable

**Test Coverage:**
- Render all TribalGovernmentUS statements with proper widgets
- Add multiple member_count statements (quantity + qualifier + references)
- Skip optional statements, verify review shows them as missing
- Choice lists populate TypeAheadSelect correctly
- Auto-derive P854 from P856

**Dependencies:**
- Phase 2 complete (step navigation proven)
- WidgetFactory working (already exists)
- Choice list hydration working (already exists)

**Estimated Effort:** 5-6 days

---

### Phase 4: Steps 1, 4, 5 - Plan, Sitelinks, Review (Week 3-4)

**Goal:** Complete remaining wizard steps

**Deliverables:**

**Step 1: PlanStep**
- Static informational screen (no data collection)
- Shows profile `name` and `description`
- Lists required vs optional statements
- Estimated time and required prep materials
- "Start" button → navigate to Step 2

**Step 4: SitelinksStep**
- Renders sitelink inputs per language from profile `sitelinks`
- Input: article title (e.g., "Muscogee Nation")
- Validation: format check (defer uniqueness to review)
- "Skip sitelinks" button (all sitelinks optional)

**Step 5: ReviewStep**
- **Section 1: Summary of collected data**
  - Labels, descriptions, aliases
  - All statements with qualifiers and references
  - Sitelinks
  - **"What's missing"** panel: skipped recommended statements
  
- **Section 2: Validation results**
  - Run `ProfileValidator.validate_item()` on draft
  - Display errors (red), warnings (yellow), suggestions (blue)
  - Group by section (labels, statements, sitelinks)
  - Each issue shows: field, message, suggestion
  
- **Section 3: Actions**
  - "Edit [step name]" buttons → navigate back to that step
  - "Export to JSON" → serialize to Wikidata JSON, save to file
  - "Ship to Wikidata" (disabled for MVP, show "Coming soon")

**Test Coverage:**
- Plan step displays profile information correctly
- Sitelinks collect article titles for multiple languages
- Review step shows all collected data in organized layout
- Validation results display with correct severity colors
- Export produces valid Wikidata JSON

**Dependencies:**
- Phase 3 complete (all data collection working)
- Validation Agent provides ValidationResult format

**Estimated Effort:** 4-5 days

---

### Phase 5: Serialization to Wikidata JSON (Week 4)

**Goal:** Transform wizard draft data into valid Wikidata JSON format

**Deliverables:**
1. **WizardSerializer** class
   - Consumes `draft_data` dict from wizard
   - Outputs Wikidata JSON structure
   - Handles all datatypes (delegates to existing wikidata_normalizer)
   - Includes qualifiers and references in proper structure

2. **Datatype serialization**
   - Reuse `gkc.bottler` wikidata_normalizer functions where possible
   - Map wizard draft format to Wikidata datavalue structures:
     - `item`: `{"entity-type": "item", "id": "Q123"}`
     - `quantity`: `{"amount": "+42", "unit": "Q123"}`
     - `time`: `{"time": "+2024-01-01T00:00:00Z", "precision": 11}`
     - `monolingualtext`: `{"text": "...", "language": "en"}`
     - `globecoordinate`: `{"latitude": 42.0, "longitude": -71.0, ...}`
     - etc.

3. **Reference chain serialization**
   - Each reference becomes a `snaks` dict
   - Handle auto-derived references
   - Support multiple references per statement

4. **Export command**
   - "Export to JSON" button in review step
   - File save dialog or default to `exports/<profile_id>_<timestamp>.json`
   - Write formatted JSON (indent=2)
   - Show success message with file path

**Test Coverage:**
- Serialize simple statement (label, instance_of)
- Serialize complex statement with qualifiers and references
- Serialize all datatypes (use TribalGovernmentUS as test case)
- Round-trip test: export → validate against Wikidata JSON schema
- Compare exported JSON to expected fixtures

**Dependencies:**
- Phase 4 complete (review step working)
- All data collection proven in steps 2-4

**Estimated Effort:** 3-4 days

---

### Phase 6: Polish & Documentation (Week 5)

**Goal:** Production-ready MVP with complete documentation

**Deliverables:**
1. **Error handling**
   - Graceful handling of missing cache files
   - Helpful error messages for malformed profiles
   - Recovery from validation failures

2. **User experience polish**
   - Loading indicators during SPARQL hydration
   - Keyboard shortcuts (Ctrl+S for save draft, Ctrl+Enter for Next)
   - Focus management (first field focused on step load)
   - Clear visual hierarchy (statement blocks, qualifier nesting)

3. **Documentation**
   - Update `docs/gkc/profiles.md` with wizard implementation details
   - Add wizard architecture page: `docs/architecture/wizard-architecture.md`
   - Update CLI help for `gkc profile form` command
   - Add wizard user guide: `docs/guides/wizard-walkthrough.md`

4. **Test coverage completion**
   - End-to-end test: create tribal government entity through wizard, export JSON
   - Test all navigation paths (forward, backward, skip)
   - Test draft save/resume
   - Test validation display
   - Performance test: large profile (30+ statements)

5. **Demo video/walkthrough**
   - Record screen capture of wizard workflow
   - Document in README or docs site

**Test Coverage:**
- Full regression suite passing
- Coverage > 80% for wizard code
- End-to-end integration test

**Dependencies:**
- Phases 1-5 complete

**Estimated Effort:** 3-4 days

---

## Total Estimated Effort: 4-5 weeks

**Assumes:**
- Single engineer (Copilot + Sky pairing)
- ~6 hours productive time per day
- Minimal scope creep
- Profile Architect and Validation Agent available for handoffs

---

## Risk Assessment

### High Risk 🔴
1. **Serialization complexity** — Wikidata JSON structure is intricate, easy to get wrong
   - **Mitigation:** Reuse existing bottler code, comprehensive test fixtures
   
2. **Validation Agent dependency** — Need ValidationResult format contract
   - **Mitigation:** Define contract early (Phase 1), implement mock validator if needed

### Medium Risk 🟡
3. **Step state synchronization** — Data must persist correctly across navigation
   - **Mitigation:** Thorough testing of draft save/load in Phase 1
   
4. **Textual widget complexity** — Dynamic addition/removal of widgets can be tricky
   - **Mitigation:** Incremental testing, start simple (aliases) before complex (statements)

### Low Risk 🟢
5. **Profile loading** — Already proven by Profile Architect work
6. **Widget rendering** — WidgetFactory already handles all datatypes
7. **Choice list hydration** — Already working in prototype

---

## Success Metrics

**MVP is complete when:**
- ✅ User can launch wizard: `gkc profile form --profile TribalGovernmentUS`
- ✅ User can navigate through all 5 steps without errors
- ✅ User can add aliases, statements with qualifiers/references
- ✅ User can skip optional statements
- ✅ Validation runs in review step, displays issues clearly
- ✅ User can export to Wikidata JSON file
- ✅ Exported JSON validates against Wikidata schema
- ✅ User can save draft mid-session, resume later
- ✅ All tests pass (unit + integration)
- ✅ Documentation complete (architecture + user guide)

**Deferred for post-MVP:**
- Ship to Wikidata API
- Edit mode (pre-populate from QID)
- Sub-wizard workflows
- Advanced cross-statement validation
- Undo/redo
- Field help panels

---

## Next Steps

**Immediate (this session):** ✅ COMPLETE
1. ✅ Review codebase and existing components
2. ✅ Define MVP scope and success criteria
3. ✅ Resolve all design decisions
4. ✅ Delete obsolete plan document
5. ✅ Update working document with clear implementation plan

**Current active work:**

Phase 2 (Identification step completion) is the active thread.

**Immediate next tasks (in order):**

1. Apply package-level language scope in Identification step (`gkc.get_languages()`: single, list, `all`)
2. Implement dynamic alias row add/remove in Identification step
3. Add required-field warning feedback in-step
4. Add tests for language scope behavior plus alias row behavior and required warnings
5. Begin Phase 3 scaffolding for statements step rendering

**Note:** CLI/docs refactor for profile source resolution is complete and verified.

---

## Archived Notes

Legacy exploratory sections that were duplicated or superseded by the current phase plan were removed on 2026-03-01 to keep this working doc execution-focused.

## End of Document
