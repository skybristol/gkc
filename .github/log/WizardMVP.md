# Wizard Engineer: Streamlit-Based Entity Curation MVP

**Date:** 2026-03-02  
**Session:** Pivot to Streamlit Framework  
**Previous Status:** Textual MVP stalled on layout/UX issues; re-scoping to web-based forms

---

## 🎯 Strategic Decision: Streamlit as UI Framework

### Why Streamlit Over Textual?

| Aspect | Textual | Streamlit | Winner |
|--------|---------|-----------|--------|
| Layout consistency | Platform-variable | Rock-solid | ✅ Streamlit |
| Form widgets | Limited, buggy | Rich, proven | ✅ Streamlit |
| Pick-list/autocomplete | Rudimentary | Mature, polished | ✅ Streamlit |
| Session state | Manual | Built-in, automatic | ✅ Streamlit |
| Development speed | Slow (debugging CSS) | Fast (pre-built widgets) | ✅ Streamlit |
| Curator UX | Uncertain | Professional | ✅ Streamlit |
| CLI-native | ✅ Yes | ❌ No (HTTP server) | ❌ Textual |
| Deployment complexity | Simple | Moderate | ⚠️ Trade-off |

**Verdict:** Streamlit's form/widget maturity + session state management outweighs the server deployment trade-off. Better to get curator UX right from the start.

### MVP Widget Strategy: QID Text Input over Autocomplete

**Decision (2026-03-02):** Defer autocomplete/type-ahead for wikidata-item properties until post-MVP.

**Rationale:**
- Wikidata's type-ahead searches across all 100M+ items with labels + aliases
- Matching that UX requires either:
  - Pre-caching massive datasets (not feasible for MVP)
  - Live SPARQL queries on every keystroke (too slow)
- SpiritSafe caching can support *constrained* type-ahead (e.g., "select country from cached list"), but requires mature cache infrastructure
- **For MVP:** Curators enter QIDs directly (e.g., "Q42"), which is:
  - Always valid workflow (expert mode; used by many Wikidata editors)
  - Simple to implement (text input + QID format validator)
  - Sufficient for testing full wizard flow

**Future Enhancement:** Add SpiritSafe-powered type-ahead when:
1. Cache hydration architecture is production-ready
2. Profile-driven constraints enable manageable choice lists
3. UX patterns for "wide-open search" vs. "constrained pick-list" are clear

**Implementation:** All `wikibase-item` datatypes → `st.text_input()` with QID regex validator (`^Q\d+$`)

---

## 🏗️ Architecture: Streamlit-Based Multi-Step Wizard

### High-Level Flow

```
┌────────────────────────────────────────────────────────────────┐
│                     Streamlit App Entry Point                  │
│              (gkc/profiles/forms/streamlit_app.py)             │
└────────────────────────────────────────────────────────────────┘
                              │
                    Session State Init
                    └─ draft_data dict
                    └─ current_step
                    └─ validation_errors
                    └─ profile loaded
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ Step Selection   │  │ Step Rendering   │
        │ (top sidebar)    │  │ (main content)   │
        └──────────────────┘  └──────────────────┘
                    │                   ▲
                    │         ┌─────────┴────────────────┐
                    │         │                          │
                    ▼         ▼                          │
        ┌─────────────────────────────┐        ┌────────────────┐
        │ Step Runners (per step):    │        │ Widget Builders│
        ├─────────────────────────────┤        ├────────────────┤
        │ • PlanStep                  │        │ • TextInput    │
        │ • IdentificationStep        │        │ • Multiselect  │
        │ • StatementsStep            │◄───────┤ • DatePicker   │
        │ • SitelinksStep             │        │ • NumberInput  │
        │ • ReviewStep                │        │ • (Streamlit   │
        └─────────────────────────────┘        │   native)      │
                    │                          └────────────────┘
                    │
                    ▼
        ┌─────────────────────────────┐
        │ Data Serialization & Export │
        │ • Serialize to Wikidata JSON│
        │ • Draft persistence         │
        │ • Validation aggregation    │
        └─────────────────────────────┘
```

### Component Responsibilities

**`streamlit_app.py` (Main App)**
- Initialize session state (draft_data, current_step, profile metadata)
- Render two-column layout: sidebar (step selector) + main (step content)
- Handle step navigation (Next/Back/Skip buttons)
- Coordinate auto-save and draft loading
- Display validation results banner
- Export button routing

**`wizard/` Package (Step Implementations)**
- `step_base.py` — Abstract step interface (adapts Textual pattern to Streamlit context)
- `steps.py` — Five step implementations (PlanStep, IdentificationStep, StatementsStep, SitelinksStep, ReviewStep)
- Each step: renders widgets, collects data, returns data dict + validation messages

**`widgets.py` (Widget Builders)**
- Map Wikidata datatypes → Streamlit widgets
- **MVP Simplification:** All wikidata-item properties use QID text input (no autocomplete)
- QID format validation for item inputs
- Return collected values in normalized format

**`draft_manager.py` (Portable Logic)** ✅ Already exists
- Auto-save draft to JSON after each step
- Load draft from file on app startup
- Track session metadata (profile, created_at, last_saved)

**`validation_bridge.py` (New)**
- Call ProfileValidator at step boundaries
- Aggregate validation warnings for Review step
- Non-blocking validation (all messages advisory)

### Profile Model Contract (from docs/gkc/profiles.md)

- `labels`, `descriptions`, and `aliases` are `dict[str, MetadataDefinition]` keyed by language code.
- `sitelinks` is `SitelinksDefinition` with nested `languages` map.
- Step 2 must read metadata from each section independently (do not infer all language scopes from `labels` only).
- Step 2 should surface `input_prompt` and `guidance` from profile metadata in the UI.
- `required` on metadata languages indicates expected coverage and should be enforced according to the current wizard validation policy.


---

## 📋 Phase Breakdown: From Now to Working MVP

### Phase 0: Cleanup ✅ COMPLETE (2026-03-02)
**Objective:** Remove Textual code; establish clean foundation for Streamlit  
**Completion Log:** See [.github/log/Phase0.cleanup.complete.md](.github/log/Phase0.cleanup.complete.md)

#### 0.1 Dependency Management ✅
- [x] Remove `textual` from `pyproject.toml` dependencies
- [x] Add `streamlit` to dependencies
- [x] Update poetry lock file
- [x] Remove Textual import statements from all files

#### 0.2 File Cleanup ✅
- [x] Delete `gkc/profiles/forms/textual_generator.py` (WizardApp, CSS, Textual-specific logic)
- [x] Delete `gkc/profiles/forms/wizard/` directory (Textual step implementations)
- [x] ~~Preserve `gkc/profiles/forms/widgets.py`~~ Deleted (will recreate Streamlit-native version)
- [x] Extract `gkc/profiles/forms/draft_manager.py` (portable; now standalone file)
- [x] Update `gkc/profiles/forms/__init__.py` (exports only DraftManager)

#### 0.3 Test Cleanup ✅
- [x] Archive `tests/test_textual_forms.py` → `.github/log/test_textual_forms.archive.py`
- [x] Update `tests/test_cli.py` to reflect wizard under construction

#### 0.4 CLI Update ✅
- [x] Update CLI docstring to mention Streamlit server startup
- [x] Replace TextualFormGenerator import with streamlit_app stub
- [x] Add "under construction" error message (placeholder for Phase 1)

---

### Phase 1: Streamlit Foundation ✅ COMPLETE (2026-03-02)
**Objective:** Build minimal Streamlit app with session state & navigation

✅ Streamlit app skeleton created (`streamlit_app.py`)
✅ Session state initialization (draft_data, current_step, profile)
✅ Profile loading and selection
✅ 5-step navigation framework functional
✅ Plan step fully implemented
✅ CLI integration working (`gkc profile form` launches Streamlit)
✅ Dependency updates: Bumped to Python 3.10+ for Streamlit support

---

### Phase 2: Profile-Driven Wizard UI ✅ COMPLETE (2026-03-02)
**Objective:** Eliminate hardcoded text; drive all UI elements from profile metadata

✅ Abstract `Step` base class created (`step_base.py`)
✅ Profile metadata loading (`load_profile_metadata()` → metadata.yaml)
✅ Removed app title/subtitle (reduces real estate waste)
✅ Removed Session Notes (not needed for MVP)
✅ Step headers standardized: emoji + title on all steps
✅ Profile name + short description displayed on all step screens
✅ Plan step redesigned:
   - Shows profile name as subheader
   - Extended description from metadata.yaml
   - Full metadata in expandable section
   - Statements listed as bullets (not count)
✅ Language detection: `get_profile_languages()` scans labels/descriptions/aliases
✅ `IdentificationStep` fully profile-driven:
   - Labels/descriptions/aliases pull `input_prompt` and `guidance` from profile
   - Language tabs for multi-language profiles
   - MetadataDefinition.required enforced for validation
   - Dynamic alias list (add/delete) with proper state management
   - Cleanup helper `_clean_empty_aliases()` for export
✅ `SitelinksStep` implemented per current profile schema:
   - Language multiselect + title input
   - Aligned with profile.sitelinks.languages structure
   - Non-blocking validation (validates selected languages)
✅ Auto-save on step navigation working
✅ Validation warning display in expandable sections
✅ All imports verified and working

**Key Architectural Decisions:**
- Step titles/descriptions are app config, NOT profile-driven (consistency across profiles)
- Profile metadata provides context-specific information (name, description, statements)
- Form field metadata (input_prompt, guidance, required) comes from profile sections
- Future: App config should be externalizable for i18n support

**Bug Fixes:**
- Fixed aliases state management: keep all values during editing, filter empty strings only on export
- Streamlit render cycle properly preserves intermediate user input

**Profile Architect Handoff Created:**
- Documented 10 items for profile schema enhancements
- Captured URL-based sitelinks architecture for post-MVP
- Identified form_policy semantics gap
- Questions about sub-wizard configuration and guidance structure

---

### Phase 3: IdentificationStep ⏸️ DEFERRED (Implemented in Phase 2)
**Objective:** Render labels, descriptions, aliases with language scoping

**Status:** ✅ Already complete within Phase 2 (language scoping, labels, descriptions, aliases)

---

### Phase 4: StatementsStep (3-4 hours) ⏳ NEXT
**Objective:** Complex statement rendering with qualifiers/references

#### 4.1 Statement List & Tabs
- [ ] Show tabs for each statement type (from profile.statements[])
- [ ] For each tab: list current values + "Add another" button
- [ ] Expandable cards for editing/reviewing each statement

#### 4.2 Widget Mapping
- [ ] Create new `WidgetFactory` for Streamlit (simpler than Textual version)
- [ ] Map all Wikidata datatypes to Streamlit widgets:
  - `wikibase-item` → **text input (QID format)** + validator ✅ **MVP: No autocomplete**
  - `string` → text input
  - `time` → date picker
  - `quantity` → number + unit selector (two inputs)
  - `globe-coordinate` → coordinate input (lat/lon fields)
  - `url` → URL input with validator
  - `commonsMedia` → text input (filename)
  - `monolingualtext` → text + language code inputs
  - `externalid` → text input

#### 4.3 Qualifiers & References
- [ ] For each statement value: nested container for qualifiers
- [ ] For each statement: container for references (optional)
- [ ] Same widget mapping for qualifier/reference values

#### 4.4 Dynamic Addition
- [ ] Track max count from profile.statement.max_count
- [ ] Disable "Add another" if count reached
- [ ] Allow removal of individual statements (with confirmation)

#### 4.5 Sub-Wizard Branching (MVP: Stub Only)
- [ ] Reserve logic for future: "Edit related item" button per statement
- [ ] MVP: just document where this goes; don't implement yet

---

### Phase 5: SitelinksStep Architecture & MVP Implementation ✅ COMPLETE (2026-03-02)
**Objective:** Implement MVP sitelinks; architect future URL-based approach

**Status:** ✅ MVP complete; future direction documented

**MVP Implementation:**
- Language dropdown + title input per current profile schema
- Aligned with `SitelinksDefinition.languages` structure
- Non-blocking validation for selected languages

**Future Architecture (Post-MVP):**
- URL-based entry: users paste Wikipedia/sister project URLs
- System parses: language code, project type, article title
- Validates URL existence via `requests.head()`
- Two-part structure: URL + semantic relationship indicator
- Addresses Wikidata model gap: no relationship semantics for sitelinks/external IDs
- Documented in `.github/prompts/ProfileArchitect.working.md`
- Awaiting Profile Architect decisions on:
  - Relationship type vocabulary (primary, shared, contextual, same_as)
  - Validation rules and allowed domains
  - Bidirectional transformation logic (Wikidata ↔ editable URLs)

**Note:** MVP keeps current functionality; architectural pivot will happen after profile schema updates.

---

### Phase 6: GKC Entity JSON Schema & Validation (2-3 hours) ✅ COMPLETE
**Objective:** Establish the canonical internal data format for entity curation. This schema governs how the wizard stores/loads entity data and serves as the contract for all downstream processing (validation, shipping, editing).

**Status:** ✅ Complete (2026-03-02)

#### 6.1 Schema Documentation ✅
- [x] Created `docs/gkc/entity-json-schema.md`
  - Complete specification with multilingual field structure
  - Datatype-specific value examples (all 9 Wikidata types)
  - Completeness calculation formula: `2 + num_statements + (2 * num_languages)`
  - Curation packet format (multi-entity support)
  - Wizard integration contract

#### 6.2 Validator Implementation ✅
- [x] Created `gkc/profiles/validators/entity_json_validator.py`
  - `EntityJSONValidator.validate_schema()`: Schema compliance checking
  - `EntityJSONValidator.calculate_completeness()`: Progress metrics per entity
  - `EntityJSONValidationResult`: Structured issue reporting
  - `CompletenessInfo`: Progress percentage, missing fields, language coverage

#### 6.3 Wizard Integration Setup ✅
- [x] Updated `streamlit_app.py` to load/save using schema validator
- [x] Created entity packet on app startup (default: single primary entity)
- [x] Modified step renderers to work with per-entity draft data
- [x] Added schema validation on draft load (graceful error if corrupted)

#### 6.4 Save Draft Integration ✅
- [x] Implemented persistent draft save to disk (JSON curation packet)
- [x] Added "Save Draft" button to Review step with user feedback
- [x] On app restart, load existing draft with full validation
- [x] Tested round-trip: wizard → JSON → load → wizard (data integrity verified)
- [x] Track current draft path in session state (updates same file instead of creating duplicates)
- [x] Display draft file info (location, last modified timestamp)
- [x] Auto-save on step navigation + manual save button in Review

**Save Draft Behavior:**
- **Auto-save**: Triggers automatically when navigating between steps
- **Manual save**: "Save Draft" button in Review step force-saves and shows confirmation
- **Draft persistence**: Uses single timestamped file per session (updates same file for all saves)
- **Storage location**: `~/.gkc/drafts/` (Streamlit-standard home directory approach)
- **Draft loading**: On startup, loads most recent draft for the profile
- **User feedback**: Shows draft filename and last modified timestamp in Review step

**Note:** Drafts are for state persistence/crash recovery. For exporting data, see Post-MVP Export Functionality section.

#### 6.5 MVP Completion Criteria for Phase 6 ✅
- [x] All entities follow schema structure consistently
- [x] Completeness calculation works for variable language counts
- [x] Save/load cycle preserves all entity data without corruption
- [x] Schema errors display clearly with actionable messages
- [x] Debug panel displays compliant GKC Entity JSON

**Key Changes:**
- Refactored session state to use curation packet format with entities array
- Updated all step renderers (IdentificationStep, StatementsStep, SitelinksStep) to work with entity-level data
- Added `get_primary_entity()` helper for MVP single-entity workflow
- Implemented draft loading with validation on app startup
- Review step now shows completeness metrics and schema validation results
- Fixed bug in `calculate_completeness()` to properly iterate over statement definitions

**Key Decision**: This phase establishes the contract that will be used by future phases (multi-entity UI, validation integration, shipper module).

---

### Phase 7: Multi-Entity Status Widget + Review UI (3-5 hours) ✅ COMPLETE
**Objective:** Implement sidebar status widget and richer review page that display multi-entity progress and completeness without attempting Wikidata JSON output.

**Status:** COMPLETE — All UI enhancements implemented

#### 7.1 Multi-Entity Packet Architecture ✅
- [x] Refactored `st.session_state.draft_data` to be a curation packet (array of entities) — **DONE in Phase 6**
- [x] Initialize with single primary entity; secondary entities added via sub-wizard (future) — **DONE in Phase 6**
- [x] Only entities existing in packet appear in status widget/review (data-driven UI) — **DONE**

#### 7.2 Sidebar Status Widget ✅
- [x] Added `render_status_widget()` function showing entity progress
- [x] Show per-entity summary with:
  - Display label priority: curator label → fallback `New <profile name>` ✅
  - Truncate long labels with ellipsis (>30 chars) ✅
  - Show progress: `X of Y completed` ✅
  - Include progress bar visualization ✅
- [x] Widget displays after Configuration section, before step navigation
- [x] Lightweight implementation; always visible during navigation

#### 7.3 Review Step Upgrade ✅
- [x] Enhanced progress display with larger format in review step
- [x] Added statement-level completeness breakdown:
  - List all profile statements with filled/missing indicators (✅/❌/⚪)
  - Show statement labels and input prompts
  - Color-coded status (green=completed, red=required missing, gray=optional)
- [x] Organize by profile order (follows `profile.statements` sequence)
- [x] Language coverage displayed in expandable section

#### 7.4 Validation Display Integration ✅
- [x] Schema validation runs on entity via `EntityJSONValidator.validate_schema()`
- [x] Validation issues displayed with severity color-coding (error/warning/info)
- [x] Shows suggestions when available
- [x] Wikidata JSON export deferred to post-MVP (documented)
- [x] Debug panel preserved for raw-data visibility

#### 7.5 MVP Completion Criteria for Phase 7 ✅
- [x] Sidebar accurately reflects progress for primary entity
- [x] Review screen shows complete/missing breakdown for all statements
- [x] Multiple entities can exist in packet (architecture supports it)
- [x] Progress calculation respects language requirements from profile

---

### Phase 8: Integration & Testing (2-3 hours) ✅ COMPLETE
**Objective:** Wire everything together; validate end-to-end flow with new schema + multi-entity architecture.

**Status:** COMPLETE — Comprehensive test suite created and passing

#### 8.1 Full App Test with Schema ✅
- [x] Streamlit app launches successfully with TribalGovernmentUS profile
- [x] All steps render correctly with entity-level data
- [x] Draft auto-save produces valid GKC Entity JSON format
- [x] Session state management working (tracked via DraftManager)

#### 8.2 Save/Load Round-Trip ✅
- [x] DraftManager saves to `~/.gkc/drafts/` with timestamped filenames
- [x] Load on startup works (most recent draft auto-loaded)
- [x] Schema validation on load with graceful error handling
- [x] Manual save button provides success feedback
- [x] All data preserved through save/load cycle (verified in Phase 6)

#### 8.3 Completeness Calculation ✅
- [x] Created comprehensive test suite covering partial data scenarios
- [x] Labels-only progress calculation tested
- [x] Language-aware calculation verified (label + description = completed language)
- [x] Statement counts included in denominator (formula: 2 + statements + 2*languages)
- [x] All 18 EntityJSONValidator tests passing

#### 8.4 Multi-Entity Readiness ✅
- [x] Packet architecture supports multiple entities (array structure)
- [x] `get_primary_entity()` helper accesses "ent-001-primary" for MVP
- [x] Status widget displays primary entity progress
- [x] Review displays primary entity completeness
- [x] Sub-wizard creation deferred to Phase 9 (post-MVP)

#### 8.5 Test Suite ✅
- [x] Created `tests/test_entity_json_validator.py` (18 tests):
  - 7 schema validation tests (required fields, structure validation)
  - 7 completeness calculation tests (various configs)
  - 4 edge case/error handling tests
- [x] All 208 tests passing (190 existing + 18 new)
- [x] EntityJSONValidator coverage: 65% (up from 21%)
- [x] Phase 6 validator bug fix included (statement iteration)

**Test Results:**
```
=================== 208 passed, 3 warnings in 77.63s ===================
```
- [ ] Reuse logic tests from old Textual suite (adapt CI assertions only)

---

## 📁 Repository Structure After Pivot

### Deleted Files
```
gkc/profiles/forms/textual_generator.py
gkc/profiles/forms/wizard/  (old Textual implementation)
gkc/profiles/forms/__pycache__/
tests/test_textual_forms.py  (archive to: .github/log/test_textual_forms.archive.py)
```

### New Structure
```
gkc/profiles/forms/
├── __init__.py
├── streamlit_app.py           ← MAIN APP (Streamlit entry point)
├── widgets.py                 ← Wikidata datatype → widget mapping
├── draft_manager.py           ← REUSE (portable)
├── validators.py              ← REUSE (portable)
├── validation_bridge.py        ← NEW (ProfileValidator integration)
├── wizard/
│   ├── __init__.py
│   ├── step_base.py           ← Abstract step interface
│   ├── steps.py               ← Five step implementations
│   └── __init__.py

tests/
├── test_streamlit_wizard.py   ← NEW (comprehensive test suite)
```

---

## 🔄 Preservation: Core Logic That Stays

The following code/concepts transition unchanged or minimally adapted:

| Component | Location | Status |
|-----------|----------|--------|
| Draft format | `DraftManager` | ✅ Unchanged |
| Profile loading | `spirit_safe.py` | ✅ Unchanged |
| Validation logic | `ProfileValidator` | ✅ Unchanged |
| Language scoping | `gkc/profiles/__init__.py` | ✅ Unchanged |
| Widget mapping logic | `WidgetFactory` | 🔄 Recreate (Streamlit-native; simpler than Textual) |
| SPARQL hydration | `sparql.py` | ⏭️ **MVP: Deferred** (not needed for QID input) |
| CLI integration | `cli.py` | 🔄 Minimal updates |

---

## ⚙️ Technical Details: Streamlit Setup

### Local Development
```bash
# Install Streamlit
poetry add streamlit

# Run the app
streamlit run gkc/profiles/forms/streamlit_app.py \
  --logger.level=debug

# Access at: http://localhost:8501
```

### Session State Pattern
```python
# Streamlit's session state persists data across script reruns
if "draft_data" not in st.session_state:
    st.session_state.draft_data = load_existing_draft() or {}

# All step changes update session_state
st.session_state.draft_data["labels"]["en"] = st.text_input("...")

# Auto-save after each step
save_draft(st.session_state.draft_data)
```

### Profile Parameter Passing
Consider two approaches:
1. **Query params**: `?profile=TribalGovernmentUS&source=local`
2. **Sidebar selector**: Dropdown to choose profile within app

**Recommendation for MVP:** Sidebar selector (simpler, more flexible for exploratory work)

---

## 🚀 MVP Success Criteria

✅ **Must Have:**
- Streamlit app launches without errors
- All 5 steps render and navigate
- Data persists across step transitions
- GKC Entity JSON schema validates correctly
- Draft auto-saves to disk and loads back
- Review step displays entity completeness
- Test suite validates end-to-end flow

⚠️ **Should Have (lower priority):**
- Dynamic "Add another" for statements (MVP: aim for basic implementation)
- Validation warning display (MVP: on Review step only)
- Multi-language label/description support (deferred to Phase 9)

🚫 **MVP Simplifications (Deliberate Scoping):**
- **No autocomplete/type-ahead** for item selection (QID text input only)
- **No SPARQL choice list preloading** (defer SpiritSafe caching integration)

❌ **Out of Scope for MVP:**
- Sub-wizard branching
- Edit mode (--qid pre-population)
- Direct Wikidata API submission
- Wikimedia Commons integration
- OpenStreetMap integration
- Advanced styling/theming

---

## 📅 Current Status & Next Steps

**✅ Phase 0 COMPLETE** (2026-03-02)
- All Textual code removed
- Streamlit dependency added
- DraftManager extracted to standalone file
- Tests updated for new architecture
- See: [.github/log/Phase0.cleanup.complete.md](.github/log/Phase0.cleanup.complete.md)

**✅ Phase 1 COMPLETE** (2026-03-02)
- Streamlit foundation app built (`streamlit_app.py`)
- Session state & profile loading working
- 5-step navigation framework functional
- Plan step fully implemented with session notes
- CLI integration complete (`gkc profile form` launches Streamlit)

**✅ Phase 2 COMPLETE** (2026-03-02) — **Profile-Driven UI Overhaul**
- Removed all hardcoded text; wizard now completely profile-driven
- Profile metadata loading and display throughout app
- Removed app title/subtitle and Session Notes (UI cleanup)
- Step headers standardized (emoji + title on all screens)
- Profile name + description displayed on all steps
- Plan step shows statement list and full metadata
- Language detection via `get_profile_languages()` (scans all sections)
- IdentificationStep fully profile-driven:
  - Field labels/prompts/guidance from MetadataDefinition
  - Language tabs for multi-language profiles
  - Dynamic alias list with proper state management
  - Fixed state persistence bug (empty strings filtered only on export)
- SitelinksStep implemented per current profile schema
- Auto-save and validation warnings working
- Created ProfileArchitect.working.md with 10 handoff items

**✅ Phase 5 COMPLETE** (2026-03-02) — **Sitelinks Architecture**
- MVP implementation aligned with current profile schema
- Documented future URL-based entry architecture
- Identified semantic relationship gap in Wikidata model
- Handoff to Profile Architect for schema decisions

**✅ Phase 4 COMPLETE** (2026-03-02) — **StatementsStep & Complex Properties**
- ✅ WidgetFactory (329 lines): Maps 9 Wikidata datatypes to Streamlit widgets
  - All datatypes: item, string, url, time, quantity, monolingualtext, globecoordinate, external-id, commonsMedia
- ✅ StatementsStep (702 lines): Full implementation with qualifiers, references, dynamic values
- ✅ Deep-linking: Plan screen → specific statements
- ✅ Expander state: Auto-open when working on statement
- ✅ Bug fixes:
  - Fixed Pydantic `fixed=None` handling (explicit None checks, not hasattr)
  - Fixed GitHub rate limiting with caching (1-hour TTL)
  - Removed unnecessary profile selector (CLI-driven)
  - Fixed navigation button save function reference
- ✅ Real-time data entry working end-to-end with test data
- ✅ Validator handoff: Created ValidationAgent.working.md for coercion integration

**⏱️ Phase 4 Duration:** 6 hours (complex datatype handling + bug fixing cycle)

**🎯 Ready for Phase 6:** ReviewStep (2-3 hours)

---

## 🧪 Testing Current Implementation

To test the completed steps (Plan, Identification, Sitelinks):

```bash
# Launch wizard (auto-reloads on code changes)
poetry run streamlit run gkc/profiles/forms/streamlit_app.py
```

**Test Scenarios:**
1. **Plan Step**: View profile metadata, statements list, extended description
2. **Identification Step**: 
   - Fill labels/descriptions in multiple languages (uses language tabs)
   - Add/edit/delete aliases dynamically
   - Verify empty aliases are preserved during editing but filtered on save
3. **Sitelinks Step**: Select languages, add article titles
4. **Navigation**: Move back/forth between steps — data persists ✅
5. **Debug Info**: Expand debug section to see `draft_data` structure

**Verified Working:**
- Profile-driven field labels, prompts, and guidance
- Multi-language support with automatic language detection
- Aliases state management (add/delete without data loss)
- Auto-save on step navigation
- Validation warnings display
- Profile metadata integration throughout

**Known Limitations (MVP scope):**
- GKC Entity JSON schema implemented; Phase 6 integration pending (load/save, validation on startup)
- Sidebar status widget not yet implemented (Phase 7)
- Review step upgrade for packet-level completeness not yet implemented (Phase 7)
- Multi-entity packet creation via sub-wizard not yet implemented (Phase 9)

**Language Detection:**
Languages are automatically detected by scanning the profile's labels, descriptions, and aliases sections. The wizard shows:
- Single-language profiles: No tabs, just labeled sections
- Multi-language profiles: Tabs for each language found in the profile

This replaces the previous manual language configuration approach.

---

## 📚 Appendix: Reusable Code Snippets

### Example: Custom Validation
```python
class IdentificationStep(Step):
    def render(self):
        st.header("Identification")
        st.write("Provide labels, descriptions, and aliases...")
        
        # Render widgets
        for lang in self.resolve_language_scope():
            label = st.text_input(f"Label ({lang})", 
                                  value=self.draft_data.get("labels", {}).get(lang, ""))
            self.draft_data.setdefault("labels", {})[lang] = label
        
        return self.draft_data
    
    def validate(self):
        warnings = {}
        if not any(self.draft_data.get("labels", {}).values()):
            warnings["labels"] = ["At least one label recommended"]
        return warnings
```

### Draft Auto-Save Pattern
```python
# In streamlit_app.py after each step:
def save_step_data():
    draft_manager.save_draft(
        st.session_state.draft_data,
        profile=st.session_state.profile_id
    )

# Called after each step navigation
if st.button("Next"):
    save_step_data()
    st.session_state.current_step = next_step
    st.rerun()
```

---

## 📂 Current File Status

**Fully Implemented (702 lines):**
- `gkc/profiles/forms/wizard/steps.py`
  - `IdentificationStep`, `SitelinksStep`, `StatementsStep` (complete)
  - Utility functions for language/alias handling

**Fully Implemented (317 lines NEW in Phase 4):**
- `gkc/profiles/forms/widgets.py`
  - `WidgetFactory` with 9 Wikidata datatype renderers
  - Validation and user feedback for all datatypes

**Fully Implemented (473 lines):**
- `gkc/profiles/forms/streamlit_app.py`
  - 5-step navigation, profile loading, auto-save
  - Session state management with GitHub API caching
  - Debug information panel

**Phase 4 Infrastructure Fixes:**
- Pydantic model `fixed=None` handling (explicit None checks throughout)
- Expander state management (auto-expand when statement has data)
- GitHub rate limit mitigation (1-hour TTL caching)
- Navigation button save function reference correction

**Phase 6 (NEW) - GKC Entity JSON Schema:**
- ✅ `docs/gkc/entity-json-schema.md` — Complete specification with examples
- ✅ `gkc/profiles/validators/entity_json_validator.py` — Schema validation + completeness calculation
- ⏳ Wizard integration: update streamlit_app.py to use schema on load/save
- ⏳ Save draft to disk: implement persistent packet storage

**Awaiting Implementation:**
- Phase 6: Wizard integration with entity JSON schema (load/save/validate)
- Phase 7: Sidebar status widget + review step upgrade (2-3 hours)
- Phase 8: Integration & testing with new schema (2-3 hours)
- Real-time validation/coercion functions — ValidationAgent (post-MVP)
- Sub-wizard branching for multi-entity creation — Phase 9 (post-MVP)

**Supporting Documentation:**
- `.github/prompts/ProfileArchitect.working.md` — 13 sections, 10 questions
  - Auto-creation pattern, quantity unit behavior, sub-wizard config, missing_consequence
- `.github/prompts/ValidationAgent.working.md` — Real-time coercion architecture
  - Datatype-specific functions (date, quantity, item, url, monolingualtext)
  - Integration points in wizard layer
- `docs/gkc/entity-json-schema.md` (NEW) — Canonical entity data format
  - Packet structure, multilingual fields, completeness calculation
  - Wizard integration contract for load/save

---

## 🚀 Post-MVP Features

### Export Functionality (Post-MVP)
**Objective:** Add export/download capabilities for curated data in multiple formats.

**Target Implementation:** Post-Phase 8, routes through `shipper` module

**Planned Formats:**
1. **GKC Entity JSON** - Native format (already used internally)
   - Direct download of curation packet
   - User takes JSON to external processing
   - Use case: Backup, sharing drafts, custom tooling, reload to wizard

2. **Wikidata JSON** - Ready for MediaWiki API
   - Transform GKC Entity JSON → Wikidata JSON format
   - Resolve cross-entity references to QIDs
   - User uploads to Wikidata via API/tools
   - Use case: Direct import to Wikidata sandbox or production

3. **QuickStatements** - Batch upload format
   - Transform to QuickStatements v1/v2 format
   - User copies to QuickStatements tool
   - Use case: Bulk imports, community review before upload

**UI Design:**
- Add "Export" section to Review step (below Save Draft)
- Radio buttons or tabs for format selection
- Download button triggers format transformation + file download
- Preview section shows first 20 lines of output

**Technical Approach:**
- Leverage existing `shipper` module for Wikidata JSON serialization
- Add new serializers for QuickStatements format
- Implement reference resolution logic (packet_id → QID mapping)
- Handle partial exports (warn about unresolved references)

**Dependencies:**
- Shipper module enhancements (reference resolution)
- QuickStatements format documentation
- Error handling for incomplete/invalid data

---

**Last Updated:** 2026-03-02 (Phase 6 = Entity JSON Schema + Wizard Integration Complete)
**Status:** Phase 6 complete with persistent state management. Ready for Phase 7 (Multi-Entity UI) and Phase 8 (Integration Testing). Export features documented for post-MVP implementation.
---

## 📋 Final Merge Summary: WizardMVP → main

### Completion Status
**All phases complete (Phases 2-8).** GKC Wizard MVP is production-ready with end-to-end entity curation workflow.

### What Was Delivered

#### Phase 6: GKC Entity JSON Schema & Wizard Integration
- ✅ Implemented `EntityJSONValidator` with schema compliance + completeness calculation
- ✅ Refactored draft data structure to curation packet format (metadata + entities array)
- ✅ Integrated validation into save/load workflow with graceful error handling
- ✅ Auto-save on step navigation with manual save button in Review step

#### Phase 7: Multi-Entity Status Widget + Review UI
- ✅ Sidebar status widget showing entity progress (label + progress bar + completion percentage)
- ✅ Enhanced Review step with statement-level completeness breakdown
- ✅ Schema validation display with severity color-coding
- ✅ Language coverage metrics and missing fields list

#### Phase 8: Integration & Testing
- ✅ Created `tests/test_entity_json_validator.py` with 18 comprehensive tests
- ✅ All 208 tests passing (190 existing + 18 new)
- ✅ Full round-trip validation (save → load → validate)
- ✅ Multi-entity packet architecture verified and documented

### Code Quality
- ✅ All linting issues resolved (ruff, black)
- ✅ Pre-merge checks passing
- ✅ Package builds successfully (wheel + sdist)
- ✅ Coverage maintained at 56% overall, 65% for EntityJSONValidator

### User-Facing Features
- Profile-driven dynamic form generation with Streamlit
- Multi-language support (labels, descriptions, aliases)
- Statement editing with qualifiers and references
- Sitelinks management (Wikipedia article linking)
- Progress tracking with completeness calculation
- Draft persistence to `~/.gkc/drafts/` with schema validation
- Error display with suggestions
- Debug panel for raw entity JSON inspection

### Architecture Improvements
- Curation packet structure supports future multi-entity workflows
- Validation decoupled from form generation (clean separation of concerns)
- DraftManager abstraction enables future storage backends
- Extensible step system for future entity types

### Known Limitations (Post-MVP)
- Autocomplete/type-ahead deferred (QID text input only)
- Export to Wikidata JSON, QuickStatements documented but not implemented
- Sub-wizard for creating related entities (Phase 9)
- Multi-user collaboration features not yet designed

### Next Steps
- Merge WizardMVP → main
- Tag v0.2.0 release
- Phase 9: Sub-wizard for related entities
- Implement export functionality via shipper module
- User acceptance testing with real data curators