# Issue: Multi-Step Wizard Form Generation

Status: Planning - Design Pivot
Branch: TextualForms
Owner: Sky
Engineer: Copilot

## Goal
Implement a Textual-based multi-step wizard for entity creation and editing from YAML profiles, breaking the overwhelming single-form approach into manageable stages that align with the Entity Profile structure (labels, statements, sitelinks, review).

## Success Criteria
- Multi-step wizard navigates through Entity Profile sections logically
- Each step collects data, validates incrementally, and saves draft state
- Final review step shows all data with quality/conformance notices
- Successfully create and validate tribal government data through wizard
- Support exporting validated data or shipping directly to Wikidata
- Wizard handles all Wikidata datatypes with appropriate widgets per step

## Scope
- In scope:
  - Multi-step wizard container with navigation (Back/Next/Skip/Finish)
  - Step-by-step data collection aligned with Entity Profile YAML structure
  - Per-step validation with incremental draft saving
  - Final review/validation stage with quality summary
  - Data export (JSON) or direct shipping to Wikidata
  - Aliases and sitelinks handling (currently missing)
  - Dynamic statement addition ("Add another" for max_count: null)
  - Sub-profile navigation with breadcrumb tracking
  - YAML structure enhancements to support wizard step metadata
  
- Out of scope:
  - SPARQL query execution at form runtime (already completed via pre-hydration)
  - Web UI alternative (terminal-based only for now)
  - Automated file upload to Wikimedia Commons (stub only)
  - Multi-platform shipping beyond Wikidata (OSM/Commons deferred)

## Links
- Previous phases:
  - [.dev/SpiritSafe_ProfileBase.md](.dev/SpiritSafe_ProfileBase.md) - Profile infrastructure
  - [.dev/GKCForms.md](.dev/GKCForms.md) - SPARQL hydration (completed)
- Textual documentation: https://textual.textualize.io/
- Related code: 
  - [gkc/profiles/generators/textual_generator.py](../gkc/profiles/generators/textual_generator.py) - Current implementation (single-form approach)
  - [gkc/profiles/](../gkc/profiles/) - Profile infrastructure
  - [gkc/spirit_safe.py](../gkc/spirit_safe.py) - Hydration and caching

## Design Pivot Rationale

**What We Discovered:**
The initial single-form implementation (ProfileFormApp) renders all profile sections in one scrollable view. For complex profiles like TribalGovernmentUS with labels, descriptions, aliases, 20+ statements (each with qualifiers/references), and sitelinks, this creates an overwhelming UX that's difficult to navigate and validate.

**New Direction:**
Break the form into a multi-step wizard that mirrors the Entity Profile structure:
1. **Plan of action**: Summarize what the end result will be in terms of the types of entities identified in the profile and the steps the user will go through in the wizard.
2. **Basic Identification of the primary Entity**: Labels, descriptions, aliases (all languages)
3. **Statements about the primary Entity**: All statements with qualifiers and references about the entity
4. **Cross-platform links**: Wikipedia articles and other Wikimedia projects, OpenStreetMap connections, etc.
5. **Review & Validate**: Summary view with quality notices and ship/export options

Each step:
- Collects data for its section
- Validates incrementally and shows improvements needed
- Saves draft state before navigation
- **Can always be advanced**—no statement blocks progression

**Key Philosophy**: Following Wikidata/Wikipedia principles, curators can create minimal entities (even just labels + instance_of) and enhance later. `required: true` marks **recommended** statements, not blockers. All statements are fundamentally optional.

## Usage (Notional)

### API:
```python
from gkc.profiles import ProfileLoader
from gkc.profiles.forms import WizardFormGenerator

# Load profile
profile_loader = ProfileLoader()
tribe_profile = profile_loader.load_from_file(".SpiritSafe/profiles/TribalGovernmentUS.yaml")

# Generate multi-step wizard
wizard_generator = WizardFormGenerator(tribe_profile)
wizard_app = wizard_generator.create_wizard()

# Launch wizard (returns on completion or cancellation)
result = wizard_app.run()

# Result contains validated data ready for export or shipping
if result.completed:
    if result.action == "export":
        with open(result.export_path, 'w') as f:
            json.dump(result.to_wikidata_json(), f, indent=2)
    elif result.action == "ship":
        shipper.ship_to_wikidata(result.to_wikidata_json())
```

### CLI:
```bash
# Launch wizard for new item creation
gkc profile form --profile TribalGovernmentUS --source local --local-root .SpiritSafe --new

# Edit existing item through wizard
gkc profile form --profile TribalGovernmentUS --source local --local-root .SpiritSafe --qid Q1234567

# Export validated data without shipping
gkc profile form --profile TribalGovernmentUS --new --export-path tribal_item.json

# Resume from draft
gkc profile form --profile TribalGovernmentUS --resume-draft .drafts/tribal_Q123.json
```

## Plan

### What's Already Built (Reusable Components)

**✅ Phase 1 Complete - Datatype Expansion:**
- All Wikidata datatypes supported: monolingualtext, globecoordinate, commonsMedia, external-id, quantity with units, time with precision/calendar
- wikidata_normalizer handles all datatypes
- TribalGovernmentUS.yaml expanded with new datatype fields
- Comprehensive test suite (17+ datatype tests, all passing)

**✅ Phase 2 Partial - Widget Infrastructure:**
- `TypeAheadSelect` widget: 1-char trigger, prefix match, 10-item cap, "keep typing" guidance
- `WidgetFactory`: Maps all datatypes to appropriate Textual widgets
- Widget validators: QID, URL, time, coordinates, lat/lon
- Choice list pre-loading from hydrated SPARQL caches
- `ProfileValidator` integration pattern

**⚠️ Needs Refactoring:**
- `ProfileFormApp`: Currently renders entire form in one view (too cumbersome)
  - Extract step-specific rendering logic
  - Add wizard navigation controls
  - Implement draft state management

**❌ Not Yet Implemented:**
- Multi-step wizard container/navigation
- Aliases rendering (defined in YAML, not rendered)
- Sitelinks rendering (defined in YAML, not rendered)
- Dynamic statement addition ("Add another" button)
- Validation results display UI
- Draft persistence and resume functionality
- Review/summary step

---

### Phase 2 (Revised): Multi-Step Wizard Architecture

**Goal:** Build wizard container and navigation, refactor ProfileFormApp into step-specific views.

#### 2.1: Wizard Container & Navigation

**Implement `WizardContainer` (new Textual widget):**
- Header: Progress indicator, current step label, breadcrumb trail
- Body: Dynamic content area for step-specific views
- Footer: Navigation buttons (Back, Next/Skip, Cancel, Finish)
- Draft auto-save on step navigation
- Validation trigger before allowing step progression

**Navigation Logic:**
- Back: Return to previous step, load draft data
- Next: Validate current step (non-blocking), save draft, advance
- Skip: Explicitly skip remaining fields in current step
- Cancel: Confirm and exit, optionally save draft
- Finish: Available only on final review step

**Validation Philosophy:**
- No validation ever blocks progression
- Warnings and suggestions accumulate for review step
- Only true errors (malformed data, type mismatches) prevent final shipping
- Missing recommended statements generate suggestions, not blockers

**Step Management:**
- `WizardStep` base class for all step views
- Each step implements: `render()`, `collect_data()`, `validate()`, `is_required()`
- Step state: `pending` → `in_progress` → `completed` → `validated`

#### 2.2: Step-Specific Views

**Step 1: BasicIdentificationStep**
- Labels (per language from profile)
- Descriptions (per language from profile)
- Aliases (per language from profile, with "Add another alias" functionality)
- Uses Input widgets with language labels
- Validation: Warnings if required languages missing, but progression allowed

**Step 2: StatementsStep** (Unified - No Core/Additional Split)
- Renders all statements from profile
- Statements appear in profile-defined order (community-curated priority)
- **Every statement has "Skip this statement" option**
- For each statement:
  - Main value input (appropriate widget per datatype, or read-only badge if `behavior.value: fixed`)
  - Qualifiers (nested container, if `behavior.qualifiers: editable`)
  - References (nested container, behavior per `behavior.references`: auto-derived, editable, or hidden)
- Validation: All non-blocking, generates warnings/suggestions for review
- "Add another" for multi-count statements

**Step 3: SitelinksStep**
- Renders sitelinks section from profile YAML
- Per-language sitelink inputs (enwiki, eswiki, etc.)
- Article title input with validation
- Always skippable

**Step 4: ReviewStep**
- Summary view of all collected data
- Grouped by section: Labels, Descriptions, Aliases, Statements, Sitelinks
- **What's missing**: List of community-expected statements that were skipped
- Run full ProfileValidator, display results
- Show "Errors" (malformed data), "Warnings" (conformance issues), "Suggestions" (missing statements)
- Action buttons:
  - Edit [section]: Navigate back to that step
  - Export: Save as JSON file
  - Ship to Wikidata: Upload (blocked only by true errors, not warnings/suggestions)
  - Save Draft: Persistent save for later resume

**Shipping Logic**:
- Only true errors (type mismatches, malformed data) block shipping
- Warnings and suggestions shown prominently but don't block
- Confirmation dialog: "You have 3 warnings and 5 missing recommendations. Ship anyway?"

#### 2.3: Draft State Management

**Implement `DraftManager`:**
- Save draft state to JSON file after each step
- Draft includes: profile identifier, step position, collected data, validation state
- Load draft on wizard launch (--resume-draft flag)
- Auto-save on navigation, manual save on cancel/exit
- Draft location: `.drafts/` directory (configurable)

**Draft Schema:**
```json
{
  "profile": "TribalGovernmentUS",
  "qid": null,  // or existing QID for edits
  "current_step": 2,
  "created_at": "2026-02-28T10:30:00Z",
  "updated_at": "2026-02-28T10:45:00Z",
  "data": {
    "labels": {"en": "Chickasaw Nation", ...},
    "descriptions": {...},
    "aliases": {...},
    "statements": [...],
    "sitelinks": {...}
  },
  "validation_state": {
    "step_1": {"ok": true, "issues": []},
    "step_2": {"ok": false, "issues": [...]}
  }
}
```

#### 2.4: Validation Display

**Implement `ValidationSummaryPanel` (Textual widget):**
- Compact header: "✓ 3 sections validated, ⚠ 2 need improvements"
- Expandable sections grouped by profile section
- Each issue shows:
  - Severity icon (⚠ for improvements needed, ℹ for suggestions)
  - Property label and statement context
  - Descriptive message with guidance
  - Link to jump to that field/step

**Per-Step Validation:**
- Real-time validation on field blur
- Field-level warning display (yellow border, inline message)
- Step-level validation on Next click (non-blocking, accumulates warnings)
- All modes allow progression—validation is advisory, not blocking

#### 2.5: Dynamic Statement Addition

**"Add Another" Functionality:**
- For statements with `max_count: null` or `max_count > 1`
- Button at end of statement block: "Add another [property label]"
- Dynamically adds new statement input group
- Each instance tracked in draft state
- "Remove" button for each added instance

---

### Phase 3: YAML Structure Enhancements

**Goal:** Extend ProfileDefinition YAML to support wizard-specific metadata.

#### 3.1: Add `wizard_steps` Metadata

**New top-level section in profile YAML:**
```yaml
wizard_steps:
  enabled: true  # If false, fall back to single-form view
  steps:
    - id: basic_id
      label: "Basic Identification"
      sections:
        - labels
        - descriptions
        - aliases
      required: true
      
    - id: core_statements
      label: "Core Information"
      statement_filter:
        required: true  # Only include required statements
      required: true
      
    - id: additional_statements
      label: "Additional Details"
      statement_filter:
        required: false  # Only optional statements
      required: false
      
    - id: sitelinks
      label: "Wiki Links"
      sections:
        - sitelinks
      required: false
      
    - id: review
      label: "Review & Submit"
      type: review
      required: true
```

#### 3.2: Backward Compatibility

- If `wizard_steps` not present, default to 5-step structure:
  1. Plan of Action
  2. Basic Identification (labels, descriptions, aliases)
  3. Statements (all statements, recommended first)
  4. Cross-platform links (sitelinks)
  5. Review & Validate
  
- Single-form fallback: `wizard_steps.enabled: false` uses existing ProfileFormApp

#### 3.3: Statement Grouping

**Optional enhancements for future:**
- Add `wizard_group` metadata to statement definitions
- Allow custom step organization beyond required/optional split
- Support conditional steps based on statement values

---

### Phase 4: Integration & Testing

#### 4.1: CLI Integration

**Update `gkc profile form` command:**
- Detect wizard_steps in profile, use WizardFormGenerator vs. single-form
- Add `--resume-draft` flag for draft path
- Add `--export-path` flag for JSON export  
- Add `--autosave-interval` for background draft saves

#### 4.2: End-to-End Workflow Tests

**Test scenarios:**
- New item creation through complete wizard
- Editing existing item (pre-populate with fetched data)
- Navigation: forward, backward, skip
- Draft save/resume at each step
- Validation display at each step and in review
- Export to JSON from review step
- Cancel wizard with draft save

#### 4.3: Real-World Use Case: Tribal Government

**Test with TribalGovernmentUS.yaml:**
- Complete wizard for creating new tribal government entity
- Include:
  - Labels/descriptions in English
  - Required statements: instance of, country, headquarters location (coordinates)
  - Optional statements: official website, flag image (commonsMedia stub), seal image
  - Qualifiers: point in time, language of work (monolingualtext)
  - References: reference URL, retrieved date
- Validate and export to JSON
- Manually inspect output for Wikidata compliance

#### 4.4: Performance Testing

- Large choice lists (>500 items) in TypeAheadSelect
- Complex profiles (>30 statements)
- Wizard responsiveness with deep nesting (qualifiers, references)
- Draft save/load times

---

## Open Questions

### Wizard Design

1. **Step granularity:**
   - Should sitelinks be separate step (Step 4) or combined with statements?
   - **Decision**: Separate—sitelinks are cross-platform metadata, distinct from Wikidata statements
   
2. **Progress saving frequency:**
   - Auto-save on every field blur, or only on step navigation?
   - **Decision**: Step navigation only (simpler, less I/O)
   
3. **Validation timing:**
   - Validate on blur, on Next, or only at Review?
   - **Decision**: On blur (per-field warnings), accumulate for Review. Never block progression.

4. **Minimal entity shipping:**
   - Can a curator ship with only labels + instance_of?
   - **Decision**: Yes—follow Wikipedia/Wikidata incremental contribution philosophy

5. **Sub-profile workflow:**
   - When user needs to create a linked item (e.g., "office held by head of government"), should we launch nested wizard?
   - **Decision from Architect Q8**: Yes—nested wizard with draft preservation, automatic return of value, breadcrumb model

### YAML Structure

6. **wizard_steps granularity:**
   - Should steps be configurable per profile, or use a standard 5-step structure?
   - **Decision**: Start with standard 5-step, add `wizard_steps` customization in Phase 3

7. **Statement grouping metadata:**
   - Do we need `wizard_group` or `section` tags on statements for custom organization?
   - **Decision**: Defer to future phase, use recommended (`required: true`) vs. other organization for now

### UX Details

8. **Skippable steps:**
   - Should users be able to skip recommended statements and complete them later in review?
   - **Decision**: Yes—all statements are skippable. `required: true` marks recommendations, not blockers

9. **Aliases and sitelinks:**
   - Should aliases be in Step 2 (basic ID) or separate step?
   - **Decision**: Keep in Step 2 for simplicity. Sitelinks separate in Step 4 (cross-platform metadata)

10. **Review step edit navigation:**
    - When user clicks "Edit Labels" from review, should they edit inline or navigate back to Step 2?
    - **Decision**: Navigate back to step—maintains wizard flow and validation

### Validation

11. **Shipping with warnings:**
    - Should curators be able to ship entities with warnings and missing recommendations?
    - **Decision**: Yes—only true errors (malformed data) block shipping. Warnings/suggestions are advisory.

12. **Minimal viable entity:**
    - What's the absolute minimum data required to ship?
    - **Decision**: Labels (at least one language) + valid instance_of. Everything else is enhancement.

13. **Improvements summary visibility:**
    - Should summary panel be visible in all steps or only review?
    - **Architect guidance from Q9**: Yes, compact section summary always visible

## Decisions (Log)
- 2026-02-27: SPARQL hydration infrastructure completed (GKCForms.md)
- 2026-02-27: Forms load choice lists from pre-hydrated caches
- 2026-02-27: Focus on Textual UI and expanded datatypes
- 2026-02-27: Phase 1 complete - all Wikidata datatypes supported
- 2026-02-27: Phase 2 partial - TypeAheadSelect and widget infrastructure built
- **2026-02-28: Design pivot to multi-step wizard approach**
  - Single-form ProfileFormApp too cumbersome for complex profiles
  - Wizard steps align with Entity Profile structure
  - Draft state management required for step navigation
  - Review step consolidates validation and export/ship actions
- **2026-02-28: Philosophical shift - all statements are optional**
  - `required: true` marks recommendations, not blockers
  - No validation blocks progression—warnings/suggestions accumulate for review
  - Only true errors (malformed data) prevent final shipping
  - Aligns with Wikipedia/Wikidata incremental contribution philosophy
  - Single StatementsStep (not Core/Additional split)
  - Minimal viable entity: labels + instance_of
- **2026-02-28: Replaced `form_policy` enum with `behavior` object**
  - Profile authors needed clearer way to express universal processing rules
  - `behavior` applies across ALL GKC operations (wizards, bulk imports, validation)
  - Three independent controls: `value` (editable|fixed|hidden), `qualifiers` (editable|hidden), `references` (editable|auto_derive|hidden)
  - Pattern 1: Fixed value with editable references (`instance_of` - same classification, different sources)
  - Pattern 2: Editable value with auto-derived references (`official_website` - URL becomes its own reference)
  - Eliminates confusion between UI presentation hints and data transformation rules
  - Works in bulk CSV imports: auto_derive creates references programmatically
- 2026-02-28: Validation messaging uses "improvements needed" and "suggestions" (not error/warning)
- 2026-02-28: TypeAheadSelect configured per architect guidance (Q6, Q7):
  - 1-character trigger
  - Label-only search (prefix match, alphabetical sort)
  - 10-item render cap with "keep typing" guidance
  - Strict selection (no free-text QID entry for now, configurable in YAML later)

## Risks/Assumptions

**Risks:**
- Textual may not support complex nested wizard navigation (sub-profiles within wizard steps)
  - Mitigation: Start with simple nesting, escalate if limitations found
- Draft state management may grow complex with deep statement structures
  - Mitigation: Use normalized data model, comprehensive testing
- Step-to-step validation may still allow invalid data to accumulate
  - Mitigation: Final validation in review step is authoritative

**Assumptions:**
- 5-step wizard structure is appropriate for most profiles
- Draft auto-save on step navigation is sufficient (no need for continuous background saves)
- Terminal UI is acceptable for MVP (web UI can follow later)
- YAML `wizard_steps` metadata can be added without breaking existing profiles

## Progress Notes

### Phase 1: Datatype Expansion ✅ COMPLETE
- 2026-02-27: Extended wikidata_normalizer to handle monolingualtext, globecoordinate, commonsMedia, external-id
- 2026-02-27: Updated StatementValue model to support dict values for complex datatypes
- 2026-02-27: Added quantity with units support, time with precision/calendar
- 2026-02-27: Implemented coordinate validation constraints (lat/long ranges, precision)
- 2026-02-27: Expanded TribalGovernmentUS.yaml with 4 new fields using new datatypes
- 2026-02-27: Created comprehensive test suite (17 tests, all passing)
- 2026-02-27: All 171 tests pass with no regressions

### Phase 2: Textual Form Generation (PARTIAL - REFACTOR NEEDED)
- 2026-02-27: Installed Textual framework dependency
- 2026-02-27: Created TypeAheadSelect widget with filtering (fully functional)
- 2026-02-27: Implemented WidgetFactory for all datatypes
- 2026-02-27: Built ProfileFormApp (single-form approach - needs wizard refactor)
- 2026-02-27: Created TextualFormGenerator orchestration class
- **2026-02-28: Discovery - single form too cumbersome, pivoting to wizard**

### Phase 2 (Revised): Multi-Step Wizard - IN PROGRESS
- 2026-02-28: Planning document revised to reflect wizard approach
- (Implementation to begin)

## Tests/Checks Run
- All tests passing: 171 passed, 2 skipped (as of Phase 1 completion)
- New datatype test coverage: 17 tests for monolingualtext, globecoordinate, commonsMedia, external-id, quantity with units, time with precision
- No mypy regressions in gkc/profiles/ module
- Coverage increased in profiles modules (validators, normalizer, generators)

## Completion Summary

(To be filled in upon wizard implementation completion)

### What changed:
- <summary>

### Issues encountered:
- <notes>

### Remaining questions:
- <notes>

### Suggested commit message:
```
<message>
```

---

## Engineering Notes for Implementation

### Reusable Components (Build On These)
- **TypeAheadSelect widget**: Fully functional, use as-is in wizard steps
- **WidgetFactory**: Maps datatypes to widgets, reuse across all steps
- **ProfileValidator**: Integrates with wizard for per-step and final validation
- **LookupCache/LookupFetcher**: Pre-hydrated choice lists already working
- **Wikidata normalizer**: Handles all datatypes, use for draft→Wikidata JSON export

### Refactoring Strategy
1. **Extract from ProfileFormApp (current single-form)**:
   - Field rendering logic → `_render_labels()`, `_render_statements()`, etc.
   - Validation integration → Adapt for per-step validation
   - Data collection → Centralize in DraftManager
   
2. **New implementations**:
   - `WizardContainer` - Top-level navigation and step orchestration
   - `WizardStep` base class - Abstract step interface
   - Step views: `BasicIdentificationStep`, `StatementsStep`, `SitelinksStep`, `ReviewStep`
   - `DraftManager` - State persistence and loading
   - `ValidationSummaryPanel` - Visual display of validation results (non-blocking)

### File Structure (Proposed)
```
gkc/profiles/forms/
  __init__.py
  textual_generator.py         # WizardFormGenerator (entry point)
  wizard/
    __init__.py
    container.py                # WizardContainer
    step_base.py                # WizardStep abstract class
    steps/
      __init__.py
      plan_of_action.py         # Step 1
      basic_identification.py   # Step 2
      statements.py             # Step 3 (unified, recommended first)
      sitelinks.py              # Step 4
      review.py                 # Step 5
    draft_manager.py            # Draft state persistence
    navigation.py               # Navigation logic (non-blocking)
  widgets/
    __init__.py
    typeahead_select.py         # Existing TypeAheadSelect
    validation_panel.py         # New ValidationSummaryPanel (advisory)
    widget_factory.py           # Existing WidgetFactory
```

### Type Safety Checkpoints
- Run `mypy gkc/profiles/ --strict` after each step view implementation
- All wizard components must have full type hints
- Draft schema should have TypedDict or Pydantic model
- Validation results typed with ValidationResult model

### Test Strategy
**Unit Tests:**
- Each step view: render, collect_data, validate
- DraftManager: save, load, auto-save logic
- NavigationController: step transitions, validation blocking
- ValidationSummaryPanel: issue grouping, display

**Integration Tests:**
- Complete wizard flow (new item creation)
- Draft save/resume across wizard restart
- Validation propagation from step to review
- Export from review step

**E2E Tests:**
- TribalGovernmentUS profile through wizard
- Sub-profile navigation (if implemented)
- Complex profiles with 30+ statements
- **Minimal entity creation**: labels + instance_of only, verify can ship
- **Incremental enhancement**: Create minimal, edit, add more statements

**Coverage Target:** 60% minimum on new wizard code

### Pre-Merge Checkpoints (Revised)
1. **After wizard container:** Navigation works (Back/Next/Skip, never blocked), progress indicator displays
2. **After each step view:** Renders correctly, data collection works, validation triggers (non-blocking)
3. **After draft manager:** Save/load works, auto-save on navigation
4. **After review step:** Full validation displays (advisory), export and ship actions implemented
5. **Before final commit:** All tests pass, minimal entity e2e test succeeds, tribal government e2e test succeeds, mypy clean

### Critical Escalation Points
- If Textual doesn't support nested wizard navigation for sub-profiles
- If draft state JSON exceeds reasonable size (>1MB for typical item)
- If non-blocking validation creates UX confusion (curators don't notice warnings/suggestions)
- If minimal entity philosophy leads to too many incomplete items in production
- If validation logic becomes fragmented across steps (centralization may be needed)

### Documentation Requirements
- User guide: "Creating Entities with the Wizard"
- API docs: WizardFormGenerator, WizardStep interface
- CLI docs: `gkc profile form` with wizard examples
- YAML schema docs: wizard_steps metadata
- Examples: Step-by-step screenshots (if possible in terminal UI)
