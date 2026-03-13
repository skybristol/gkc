# WizardV2: Wikibase-First Wizard Engineering Reset

**Target Agent:** Wizard Engineer  
**Phase:** Comprehensive reset for Wikibase-backed profiles  
**Status:** Planning (v2 reset)  

---

## Executive Summary

This document defines the **complete reset** of the GKC Wizard user interface to fully embrace the **Wikibase-first architecture** where form generation, validation guidance, and navigation flows are driven by Data Distillery Wikibase profile metadata (consumed via SpiritSafe JSON cache). This reset abandons previous YAML-based wizard approaches in favor of a dynamic, graph-traversing, specification-driven curation experience.

**Core Architectural Shift:**

**Current State:**
- Wizard forms generated from hand-authored YAML profiles
- Form fields, labels, and constraints hardcoded in profile YAML
- Limited cross-profile navigation (no P162 linkage support)
- Validation messages generic (not driven by ontology guidance properties)

**Target State:**
- **Forms generated from DD Wikibase profiles** (via SpiritSafe JSON cache)
- **P185-P190 guidance properties** drive field-level help text, examples, prompts
- **P162 linked profile navigation** enables "Create new" / "Select existing" affordances
- **Profile graph traversal** for multi-entity curation sessions (breadcrumb navigation)
- **P164 expected qualifiers** rendered as sub-form fields (expandable/collapsible)
- **Specification-driven validation** (fermenter integration) with actionable error messages

**Design Principles:**
- **Zero hardcoded forms:** All form structure derived from cached profiles
- **Guidance-first UX:** P185-P190 properties provide inline help, not separate docs
- **Graph-aware navigation:** Users can create linked entities without leaving context
- **Offline-capable:** Full functionality when DD Wikibase unavailable (cache fallback)
- **Fermenter-first execution:** Wizard never implements standalone coercion/validation logic; it calls fermenter and renders results

---

## Profile-Driven Form Generation

### Form Schema Derivation

**Source:** SpiritSafe JSON cache (`profiles/{EntityID}/profile.json`)

**Generation Flow:**
1. User requests curation session for profile (e.g., "Create new Tribal Government")
2. Wizard loads profile JSON from SpiritSafe cache
3. For each statement in `profile.statements[]`:
   - Extract field metadata: `id`, `label`, `value.type`, `max_count`, `guidance`
   - Extract guidance properties: P185-P190 for help text/examples/prompts
   - Determine widget type based on `value.type` (see Widget Mapping table below)
   - Check for P162 linked profiles (add "Create new" / "Select existing" affordances)
   - Check for P164 expected qualifiers (add sub-form fields)
4. Render form with fields in profile-specified order
5. Attach fermenter API calls to each field/session boundary (real-time or submit-time validation by mode)

### Widget Mapping (by Datatype)

| Datatype | Widget Type | Behavior | Example |
|----------|------------|----------|---------|
| `item` | Type-ahead search or linked profile selector | Auto-complete from Wikibase items; if P162 present, show "Create new" button | Search for country (Q43 value list) |
| `monolingualtext` | Text input + language dropdown | User enters text, selects language code | Label/description fields |
| `url` | URL input with validation indicator | Real-time URL format check, optional accessibility check | Official website field |
| `string` | Text input (single-line or multi-line) | Free text entry, optional length constraints | Name, description |
| `time` | Date picker with precision selector | ISO 8601 input, selects precision (year, month, day, hour, etc.) | Established date |
| `quantity` | Numeric input + optional unit selector | Number entry, unit dropdown if configured | Population count |
| `globecoordinate` | Map picker or lat/long inputs | Interactive map (future) or manual coordinate entry | Headquarters location |
| `commonsMedia` | File upload or Commons file selector | Browse local file (upload to Commons), or search existing Commons files | Flag image, logo |

**Fixed Value Fields (P183 + Q23 specification):**
- Display value as **read-only text** (grayed out)
- Show tooltip: "This value is fixed for this profile"
- Do not allow user editing

**Repeatable Fields (`max_count` > 1 or null):**
- Render "Add another [Field Label]" button
- Each instance gets own validation context
- Display count indicator: "2 of 5 added" (if max_count specified)

### Guidance Property Integration (P185-P190)

**Mapping to UI Elements:**

| Wikibase Property | JSON Field Path | UI Element | Example Usage |
|-------------------|----------------|------------|---------------|
| P185 (label guidance) | `labels.{lang}.guidance` | Tooltip on label field | "Use the official name as registered with BIA" |
| P186 (description example) | `descriptions.{lang}.guidance` | Placeholder text or tooltip | "Example: Federally recognized tribal government in Oklahoma" |
| P187 (alias guidance) | `aliases.{lang}.guidance` | Tooltip on alias field | "Include historical names or common abbreviations" |
| P188 (label field description) | `labels.{lang}.input_prompt` | Field label text | "Official Name" (instead of generic "Label") |
| P189 (description field description) | `descriptions.{lang}.input_prompt` | Field label text | "Brief Description" |
| P190 (alias field description) | `aliases.{lang}.input_prompt` | Field label text | "Alternative Names" |
| P171 (consequence message) | `statements[].guidance` | Help text below field or info icon | "If headquarters location is unknown, leave blank" |

**Implementation:**
- Extract `guidance` and `input_prompt` fields from profile JSON
- Render as:
  - **Field label:** Use `input_prompt` if available, fall back to `label`
  - **Tooltip:** Use `guidance` text (show on hover/click of info icon)
  - **Placeholder:** Use `guidance` for text inputs (if short, < 50 chars)

**Multi-Language Support:**
- Default language: `en` (English)
- If user's browser language is available in profile (e.g., `es`, `fr`), use that language's guidance
- Language switcher control (future enhancement): Allow user to toggle guidance language

---

## Cross-Profile Linkage Navigation (P162)

### P162 Linked Profile Architecture

**Requirement:** When profile statement has P162 qualifier, enable navigation to linked profile for entity creation/selection.

**Example (from Q4 TribalGovernmentUS → Q39 OfficeHeldByHeadOfState):**
- User creating Tribal Government entity
- Reaches "office held by head of government" field
- Profile JSON shows: `"linked_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q39"`
- Wizard presents two affordances:
  1. **"Create new office"** button → opens Q39 wizard modal/panel
  2. **"Select existing office"** type-ahead search → constrained to items conforming to Q39 profile

### Navigation Affordance UI Design

**Modal Approach (Recommended for V2):**

```
[Tribal Government Wizard]

Office held by head of government *
ℹ️ Select an existing office or create a new one

┌─────────────────────────────────────────────────────────────┐
│ [Search existing offices...]                       [Search] │
│                                                               │
│ No office selected.                                          │
│                                                               │
│ [+ Create New Office]                                        │
└─────────────────────────────────────────────────────────────┘

When user clicks [+ Create New Office]:

┌─────────────────────────────────────────────────────────────┐
│ Create New Office (Office Held by Head of Government)   [×] │
│─────────────────────────────────────────────────────────────│
│ Label (English) *                                            │
│ [____________________________________________]               │
│ ℹ️ Enter the official title of this office                  │
│                                                               │
│ Description (English)                                        │
│ [____________________________________________]               │
│                                                               │
│ Applies to jurisdiction *                                    │
│ [Search for Tribal Government...] [+ Create New]            │
│                                                               │
│ ... (rest of Q39 profile fields)                            │
│                                                               │
│ [Cancel]                               [Save & Return]       │
└─────────────────────────────────────────────────────────────┘
```

**Behavior:**
1. User clicks "Create New Office" button
2. Wizard loads Q39 profile JSON from cache
3. Modal overlay displays Q39 form (recursive form generation)
4. User fills Q39 form fields (may encounter nested P162 linkages → sub-modals)
5. User clicks "Save & Return"
6. Wizard validates Q39 entity via fermenter
7. If valid:
   - Create Q39 entity reference (item stub or full entity, depending on mode)
   - Populate parent form field with new item reference
   - Close modal, return to Q4 form
8. If invalid:
   - Display validation errors in Q39 modal
   - User corrects errors, retries save

**Breadcrumb Navigation:**
- Display breadcrumb trail at top of modal: `Tribal Government > Office > (Tribal Government)` (shows circular linkage)
- Prevent infinite nesting: max 3 levels deep (configurable)
- If user attempts to exceed depth limit, show warning: "Maximum nesting depth reached. Please complete this entity and return to parent."

### Type-Ahead Search Constraints (P162)

**Requirement:** When selecting existing item for P162-linked field, constrain search to items conforming to linked profile.

**Implementation:**
1. User types in "Select existing office" search box
2. Wizard queries Wikibase (or local cache) for items matching search term
3. **Filter results:** Only show items where `P1 → Q39` (instance of Office Held by Head of Government)
4. Display results with excerpt: `[Q12345] Chief of Tribal Government (Applies to: Example Tribe)`
5. User selects item from results
6. Wizard pre-populates field with selected item reference

**Fallback Behavior (Offline Mode):**
- If Wikibase unavailable, search local cache only
- Cache may be incomplete (not all Q39 items cached)
- Display warning: "Offline mode: Search limited to cached items. Connect to network for full search."

### Reciprocal Linkage Handling (Bidirectional P162)

**Challenge:** Q4 links to Q39, and Q39 links back to Q4 via P162. How to prevent infinite UI loops?

**Solution:**
1. Track profile navigation stack: `[Q4, Q39, Q4]` (detects cycle)
2. When cycle detected:
   - **Option A (Recommended):** Show grayed-out "Create new" button with tooltip: "This would create a circular reference. Select existing item instead."
   - **Option B:** Allow cycle but display warning: "You are creating a reciprocal linkage. Ensure both entities reference each other correctly."
3. Limit depth to 3 levels (prevents deeply nested cycles)

**UX Example:**
```
[Tribal Government Wizard] → Field: "office held by head of government"
  ↓ User clicks "Create New Office"
  
[Office Wizard] → Field: "applies to jurisdiction"
  ↓ User clicks "Create New Tribal Government" ← CYCLE DETECTED
  
Display: "Cannot create new Tribal Government from this context (circular reference). 
         Please select the Tribal Government you started with, or create entities separately."
```

---

## Profile Graph Traversal & Dependency Management

### Profile Dependency Graph

**Source:** SpiritSafe cache `manifest.json` → `profile_graph.edges`

**Structure:**
```json
{
  "profile_graph": {
    "edges": [
      {
            "source_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
            "source_statement_entity": "https://datadistillery.wikibase.cloud/entity/Q40",
            "target_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q39",
        "linkage_type": "P162",
        "bidirectional": true
      }
    ]
  }
}
```

**Usage in Wizard:**
1. **Pre-loading linked profiles:** When user starts Q4 session, wizard pre-loads Q39 profile JSON (anticipates P162 navigation)
2. **Graph visualization (future):** Display profile dependency graph to user as navigation aid (nodes = profiles, edges = P162 linkages)
3. **Bulk entity creation:** When user creates multiple entities in one session, wizard tracks dependency order for correct submission sequence

### Curation Packet Assembly

**Goal:** Build multi-entity packets where linked entities are created/referenced together.

**Example Workflow:**
1. User creates Tribal Government (Q4)
2. User creates Office (Q39) via P162 linkage from Q4
3. Office creation requires Tribal Government reference (bidirectional P162)
4. Wizard detects cycle, prompts user:
   - "This office will reference the Tribal Government you are creating. Proceed?"
   - User confirms
5. Wizard assembles packet:
   - Entity 1: Tribal Government with placeholder reference to Entity 2
   - Entity 2: Office with reference back to Entity 1
6. Wizard submits packet to bottler/shipper for processing (creates both entities, resolves references)

**Implementation Contract:**
- Wizard builds packet structure: `{"entities": [entity1_data, entity2_data], "references": [{"from": "entity1.field_id", "to": "entity2"}]}`
- Passes to `gkc.bottler` for Wikidata JSON shaping
- Bottler resolves placeholder references to actual QIDs after entity creation

---

## Expected Qualifiers (P164) Sub-Form Rendering

### P164 Architecture

**Requirement:** Statement may require specific qualifiers. Render these as expandable sub-form fields.

**Example (from Q4 TribalGovernmentUS → Q33 headquarters location):**
- Main field: "Headquarters location" (item type)
- P164 expected qualifiers: Q34 (street address), Q35 (postal code), Q36 (coordinate location)
- UI renders sub-form for these qualifiers when user populates main field

### UI Design

**Collapsed State (Before User Populates Main Field):**
```
Headquarters location
[___________________________________________] [Search]
ℹ️ Enter the coordinates or address of the tribal government's main office
```

**Expanded State (After User Selects Location):**
```
Headquarters location
[✓ Selected: Leupp, Arizona, United States]         [Change]

└─ Additional Details (Optional)
   ├─ Street address
   │  [1234 Main Street]
   │
   ├─ Postal code
   │  [86035]
   │
   └─ Coordinate location
      Latitude:  [35.2842]   Longitude: [-111.0254]
      [Pick on map]
```

**Implementation:**
1. User selects/enters main field value
2. Wizard checks `statement_spec.expected_qualifiers[]`
3. If qualifiers present:
   - Expand sub-form section (animated slide-down)
   - Render qualifier fields (same widget mapping logic as main statements)
   - Each qualifier field gets own fermenter validation
4. User fills qualifier fields (optional or required based on qualifier spec)
5. Wizard validates qualifiers before allowing statement save

**Validation:**
- If qualifier marked as required (via P159/P161 specification), display asterisk (*)
- If user skips required qualifier, show error: "Street address is required for headquarters location"

---

## Validation Integration with Fermenter

### Real-Time Field Validation

**Requirement:** Validate user input as they type/select, provide immediate feedback.

**Implementation:**
1. User enters value in field
2. On blur (or debounced keypress), wizard calls `fermenter.validate_{datatype}(value, context)`
3. Fermenter returns `ValidationResult` with `valid`, `errors`, `warnings`
4. Wizard displays result in UI:
   - **Valid:** Green checkmark icon, field border turns green
   - **Invalid:** Red X icon, field border turns red, error message displayed below field
   - **Warning:** Yellow triangle icon, warning message displayed (field still valid but user advised)

**Example:**
```
Official website *
[https://example.com] ✓
ℹ️ Enter the main website URL for this entity

Official website *
[htp://bad-url] ✗
⚠️ Invalid URL format: must start with http:// or https://
```

### Form-Level Validation (Before Submission)

**Requirement:** Validate entire entity before allowing submission.

**Implementation:**
1. User clicks "Save" or "Submit" button
2. Wizard calls `fermenter.validate_statement_comprehensive()` for each statement
3. Wizard aggregates results:
   - If all valid: proceed to submission
   - If any invalid: block submission, scroll to first error, highlight invalid fields
4. Display summary: "3 errors must be fixed before submission"

**Error Display:**
```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ Cannot submit: 3 errors found                            │
│─────────────────────────────────────────────────────────────│
│ • Instance of: Value must be Q574 (federally recognized     │
│   Indian tribe), got Q123                                    │
│                                                               │
│ • Official website: URL returned status 404                  │
│                                                               │
│ • Headquarters location: Missing required qualifier          │
│   "street address"                                           │
│                                                               │
│ [Scroll to first error]                           [Close]   │
└─────────────────────────────────────────────────────────────┘
```

### Specification-Driven Error Messages

**Requirement:** Display validation errors sourced from DD Wikibase (P191 validation directives).

**Current Limitation:** P191 directives are human-readable prose, not structured error messages.

**V2 Approach:**
- Use P191 text as **contextual help** (display in error tooltip)
- Generate specific error messages in fermenter (code-based)
- **Future enhancement:** Add P192 (localized error message template) to DD Wikibase for multilingual structured errors

**Example:**
- P191 directive for Q23: "apply a supplied fixed value without any need for deliberate input action"
- Fermenter error message: "Value must be Q574 (federally recognized Indian tribe)"
- Tooltip hover on error: "This field requires a fixed value as specified by the profile. [Learn more about fixed values]"

---

## Value List Integration (Q28/Q43)

### Type-Ahead Search with Value Lists

**Requirement:** When statement has value list constraint (Q28/Q43 via P163), populate type-ahead search from that list.

**Implementation:**
1. Wizard detects `statement_spec.value_specs` includes Q28 or Q43
2. Wizard loads value list JSON from SpiritSafe cache (`cache/value_lists/{ListQID}.json`)
3. Wizard renders type-ahead search widget:
   - User types in search box
   - Wizard filters value list items by label (prefix match, fuzzy match)
   - Display top 10 matches in dropdown
4. User selects item from dropdown
5. Wizard populates field with selected QID

**Example (Q43 List of World Countries):**
```
Country *
[United_______________________] 
  ↓ Dropdown appears
  • United States (Q30)
  • United Kingdom (Q145)
  • United Arab Emirates (Q878)
  [Show all results...]
```

**Offline Fallback:**
- If value list cache missing or stale, display warning: "Value list unavailable. Enter QID manually or refresh cache."
- Allow user to enter QID directly (validate format only, skip list constraint)

### Value List Refresh UI

**Requirement:** Allow user to trigger value list regeneration (SPARQL query execution).

**Implementation:**
- Add settings menu option: "Refresh value lists"
- When clicked:
  1. Wizard calls `gkc.spirit_safe.refresh_value_lists()` (CLI function wrapped for UI)
  2. Display progress: "Refreshing value lists... (Q28: 574 items, Q43: 195 countries)"
  3. On completion: "Value lists updated. Restart wizard to use fresh data."
- Future enhancement: Auto-refresh on app launch if cache older than TTL (30 days)

---

## Multi-Language Support (Future Enhancement)

### Language Switching

**Requirement:** Allow user to switch wizard interface language (not just entity language).

**V2 Scope:** English only (hardcoded)

**Future Implementation:**
1. Load profile guidance in multiple languages from JSON cache (`labels.{lang}.guidance`)
2. Display language switcher control in wizard header: `[EN ▼] → [ES] [FR] [DE]`
3. When user switches language:
   - Re-render all field labels, tooltips, guidance from selected language
   - Fall back to English if selected language not available for specific field
4. Store language preference in browser localStorage (persist across sessions)

**Challenges:**
- Not all profiles will have complete translations (P185-P190 may only exist in English)
- Error messages from fermenter are English-only (localization requires P192 or similar)

---

## Accessibility & Usability

### Keyboard Navigation

**Requirement:** All wizard interactions must be keyboard-accessible (WCAG 2.1 AA compliant).

**Implementation:**
- Tab order follows logical field sequence (top to bottom, left to right)
- Enter key submits form (or advances to next field if multi-step)
- Escape key closes modals
- Arrow keys navigate type-ahead dropdown results
- Screen reader support: ARIA labels on all fields, error messages announced

### Responsive Design

**Requirement:** Wizard functional on mobile, tablet, desktop.

**V2 Scope:** Desktop-first (mobile optimization deferred)

**Future:**
- Collapsible sections for long forms on mobile
- Touch-friendly controls (larger tap targets)
- Horizontal swipe for breadcrumb navigation

### Progress Indicators

**Requirement:** For long forms, show progress through wizard.

**Implementation:**
- Display progress bar or step indicator: "Step 3 of 7"
- Highlight completed sections (green checkmark)
- Allow user to jump to incomplete sections (if non-sequential form allowed)

---

## GitHub Issue Triage Mapping (2026-03-09)

### Kept Open and Mapped to WizardV2 Execution

- **Wizard core integration and packet UX:** #108, #117, #118
- **Cross-entity wizard behavior extensions:** #96, #98, #100
- **Deferred but still relevant UX feature:** #91

### Closed as OBE (Handled by Architecture Reset)

- #90 Auto-Creation Pattern for Fixed-Value Statements (absorbed into fixed-value behavior in V2 design)
- #94 Form Policy Clarity and Extensibility (absorbed into fermenter execution metadata and shared policy dispatch behavior)
- #95 Missing Consequence Warnings and Implications (absorbed into guidance/consequence display model)

### Sequencing Guidance

- Start with #108 + #117 as baseline execution for dynamic forms and multi-entity packet workflows.
- Follow with #118 for persistence/recovery once baseline flow is stable.
- Treat #96/#98/#100 as second-wave extensions after core wizard and fermenter integration are reliable.

---

## Testing Strategy

### Unit Tests (Component-Level)

**Coverage Requirements:**
- Widget rendering: Test each widget type (item, monolingualtext, url, etc.) with valid/invalid input
- Guidance property display: Test tooltip, placeholder, field label generation from P185-P190
- P162 navigation: Test "Create new" modal opening, breadcrumb display, depth limit enforcement
- P164 qualifier rendering: Test sub-form expansion/collapse, validation

**Example Test:**
```python
def test_item_widget_with_p162_linkage():
    profile = load_profile_json("TribalGovernmentUS")
    statement_spec = profile["statements"][5]  # office_held_by_head_of_government
    
    widget = render_widget(statement_spec)
    
    assert widget.type == "item_selector"
    assert widget.has_create_new_button is True
   assert widget.linked_profile_entity == "https://datadistillery.wikibase.cloud/entity/Q39"
    assert widget.search_constraint == "P1 → Q39"
```

### Integration Tests (Full Form Rendering)

**Coverage Requirements:**
- Full profile rendering: Load Q4 profile, render all fields, verify order/labels/widgets
- P162 navigation workflow: Simulate "Create new" click, verify modal opens with Q39 form
- Form submission: Fill all required fields, submit, verify fermenter validation called
- Error handling: Simulate validation errors, verify error messages displayed

**Example Test:**
```python
def test_create_tribal_government_with_linked_office():
    wizard = Wizard(profile="TribalGovernmentUS")
    
    # Fill basic fields
    wizard.set_field("label", "Example Tribe")
    wizard.set_field("instance_of", "Q574")  # federally recognized Indian tribe
    
    # Navigate to linked profile
    office_wizard = wizard.create_linked_entity("office_held_by_head_of_government")
    office_wizard.set_field("label", "Chief")
    office_wizard.set_field("applies_to_jurisdiction", wizard.entity_reference)
    office_wizard.save()  # Returns to parent wizard
    
    # Submit parent form
    result = wizard.submit()
    
    assert result.valid is True
    assert len(result.entities) == 2  # Tribal Government + Office
```

### End-to-End Tests (User Workflow Simulation)

**Coverage Requirements:**
- Complete entity creation workflow: Open wizard, fill all fields, submit, verify entity created in Wikibase
- Multi-entity workflow: Create Tribal Government → Create linked Office → Submit packet
- Offline mode: Disable network, verify wizard functions with cache fallback
- Error recovery: Trigger validation error, correct error, resubmit successfully

**Test Fixture Strategy:**
- Use SpiritSafe JSON fixtures for profile data (`tests/fixtures/profiles/`)
- Mock Wikibase API responses (avoid live API calls in tests)
- Mock fermenter validation results (avoid dependency on fermenter module in wizard tests)

---

## Open Questions & Decisions Needed

1. **Modal vs. Tabbed Navigation for P162:**
   - Current proposal: Modal overlay
   - Alternative: Open linked profile in new browser tab (preserves context in parent tab)
   - Decision needed: Which UX pattern preferred?

2. **Depth Limit for P162 Nesting:**
   - Current proposal: 3 levels max
   - Question: Is 3 sufficient for real-world use cases? (e.g., Tribal Government → Office → Person → Address)
   - Decision needed: Increase to 5, or keep at 3 with user override option?

3. **Offline Mode UX:**
   - Question: Should wizard block submission in offline mode, or allow with warning?
   - Current proposal: Allow submission, queue for later upload when connection restored
   - Decision needed: Coordinate with shipper module for offline queue implementation

4. **Value List Truncation Display:**
   - If value list truncated (e.g., 10k items cached, 50k total), how to communicate this to user?
   - Options: (a) Warning banner "Search may be incomplete", (b) "Load more results" button (triggers SPARQL query)
   - Decision needed: UX pattern for large value lists

5. **Multi-Entity Submission Order:**
   - When packet contains multiple entities with reciprocal references (Q4 ↔ Q39), which entity created first?
   - Options: (a) Shipper handles ordering automatically, (b) Wizard explicitly orders entities in packet
   - Decision needed: Coordinate with shipper module on packet structure expectations

6. **Qualifier Requirement Enforcement:**
   - If P164 expected qualifiers are "expected" but not strictly required, should wizard warn or block submission?
   - Current proposal: Warn (yellow triangle), allow submission
   - Decision needed: Configurable fermenter execution mode per profile, or global default?

---

## Implementation Roadmap

### Phase 1: Core Form Generation (Weeks 1-2)

**Goal:** Render forms from SpiritSafe JSON cache with basic field widgets

**Tasks:**
1. Implement profile JSON loader (reads from SpiritSafe cache)
2. Implement widget factory (maps `value.type` to widget component)
3. Implement field rendering (labels, tooltips from P188-P190 guidance)
4. Implement basic validation (call fermenter validators on field blur)
5. Unit tests for widget rendering and guidance display

**Deliverables:**
- Wizard can render Q4 (TribalGovernmentUS) form with all fields
- Field labels use P188-P190 input prompts
- Tooltips display P171 guidance
- Basic item/string/url widgets functional

### Phase 2: P162 Linked Profile Navigation (Weeks 3-4)

**Goal:** Enable "Create new" / "Select existing" affordances for P162-linked fields

**Tasks:**
1. Implement P162 detection logic (read `linked_profile_entity` from statement spec)
2. Implement "Create new" modal (recursive form generation)
3. Implement breadcrumb navigation (track profile stack)
4. Implement depth limit enforcement (max 3 levels)
5. Implement type-ahead search with profile constraint (filter by P1 → linked profile QID)
6. Integration tests for P162 workflows

**Deliverables:**
- User can create Office (Q39) from Tribal Government (Q4) wizard
- Modal displays Q39 form, returns item reference to Q4 form on save
- Breadcrumb trail shows navigation history
- Cycle detection prevents infinite nesting

### Phase 3: P164 Qualifier Sub-Forms (Week 5)

**Goal:** Render expected qualifiers as expandable sub-form fields

**Tasks:**
1. Implement P164 detection logic (read `expected_qualifiers[]` from statement spec)
2. Implement sub-form expansion/collapse (animated slide-down)
3. Implement qualifier field rendering (same widget logic as main statements)
4. Implement sub-form validation (call fermenter validators for qualifiers)
5. Unit tests for qualifier rendering and validation

**Deliverables:**
- Headquarters location field expands to show street address, postal code, coordinates sub-fields
- Qualifier validation errors displayed inline
- User can save statement with qualifiers

### Phase 4: Value List Integration (Week 6)

**Goal:** Populate type-ahead searches from Q28/Q43 value lists

**Tasks:**
1. Implement value list loader (read from `cache/value_lists/*.json`)
2. Implement type-ahead search with value list filtering (prefix match, fuzzy match)
3. Implement offline fallback (warn if value list unavailable)
4. Implement value list refresh UI (trigger SPARQL regeneration)
5. Integration tests for value list workflows

**Deliverables:**
- Country field populates from Q43 value list
- Stated-in reference field populates from Q28 value list
- User can refresh value lists from settings menu

### Phase 5: Form-Level Validation & Submission (Week 7)

**Goal:** Validate entire entity before submission, display aggregated errors

**Tasks:**
1. Implement form-level validation (call `fermenter.validate_statement_comprehensive()` for all statements)
2. Implement error aggregation (collect all errors/warnings)
3. Implement error display UI (modal or inline with scroll-to-error)
4. Implement submission workflow (pass validated entity to bottler/shipper)
5. End-to-end tests for full entity creation

**Deliverables:**
- User cannot submit form with validation errors
- Error summary modal displays all errors with scroll-to-error button
- Successful submission creates entity in Wikibase (dry-run mode or live)

### Phase 6: Multi-Entity Packet Assembly (Week 8)

**Goal:** Create linked entities together in single submission

**Tasks:**
1. Implement packet structure (multiple entities with reciprocal references)
2. Implement reference resolution (placeholder references → actual QIDs after creation)
3. Coordinate with shipper module on packet handling
4. Integration tests for multi-entity workflows

**Deliverables:**
- User can create Tribal Government + Office in single wizard session
- Packet submitted to shipper with both entities and reciprocal references
- Entities created successfully with correct linkages

---

## Success Criteria

**Must Have (Blocking):**
- [ ] Forms generated dynamically from SpiritSafe JSON cache (no hardcoded forms)
- [ ] P185-P190 guidance properties displayed in field labels, tooltips, placeholders
- [ ] P162 "Create new" modal functional (can create linked entities)
- [ ] P164 expected qualifiers rendered as sub-form fields
- [ ] Fermenter validation integrated (real-time field validation)
- [ ] Form-level validation blocks submission if errors present
- [ ] Value list type-ahead search functional for Q28/Q43

**Should Have (High Priority):**
- [ ] Breadcrumb navigation for P162 nesting (up to 3 levels)
- [ ] Cycle detection prevents infinite P162 loops
- [ ] Error messages actionable (specific, not generic)
- [ ] Offline mode functional (cache fallback, queue submission)
- [ ] Multi-entity packet assembly (create linked entities together)
- [ ] Test coverage: 80% for widget rendering, 60% for integration workflows

**Nice to Have (Future Enhancement):**
- [ ] Multi-language support (switch wizard language)
- [ ] Graph visualization (display profile dependency graph)
- [ ] Mobile responsive design (tablet/phone optimization)
- [ ] Accessibility compliance (WCAG 2.1 AA)
- [ ] Auto-save drafts (persist form state in browser localStorage)
- [ ] Bulk entity creation (CSV upload → wizard pre-population)

---

## Handoff to Profile Architect

**After Wizard V2 Implementation:**

1. **Feedback on Guidance Properties (P185-P190):**
   - Which guidance properties are most useful in UI? (P185? P171?)
   - Are there missing guidance properties needed? (e.g., P192 for localized error messages)
   - Document UX findings for future profile design

2. **Profile Graph Usability:**
   - Are P162 linkages discoverable enough? (user understands when/why to create linked entities)
   - Should manifest include graph visualization metadata (node positions, edge weights)?

3. **Value List Optimization:**
   - Which value lists exceed 10k items? (need pagination/streaming)
   - Should value lists include item descriptions (not just labels) for disambiguation?

---

## Handoff to Validation Agent

**After Wizard V2 Implementation:**

1. **Fermenter Integration Testing:**
   - Verify fermenter validators return expected `ValidationResult` structure
   - Document edge cases where wizard bypasses fermenter (e.g., fixed values, offline mode)

2. **Performance Profiling:**
   - Profile form rendering speed (target: < 500ms for Q4 profile)
   - Profile validation speed (target: < 100ms per field, < 2s for full form)
   - Optimize bottlenecks (value list loading, recursive P162 checks)

3. **Error Message Clarity:**
   - User test error messages (are they actionable? understandable?)
   - Propose improvements to fermenter error generation (more specific, less technical)

---

**Document Version:** 1.1  
**Last Updated:** 2026-03-09  
**Next Review:** After Phase 1 completion (core form generation functional)
