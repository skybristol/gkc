# Profile Architect Working Notes

**Purpose**: Capture issues, improvements, and enhancement requests for the SpiritSafe profile schema and metadata structure discovered during GKC Wizard development.

**Status**: Active collection (handoff pending)

---

## High-Priority Items

### 1. README Reevaluation

**Current State**: Profile directories contain README.md files that are too dense to be useful in wizard context.

**Problem**: 
- READMEs are written as comprehensive documentation rather than user-facing guidance
- They're not structured for programmatic consumption by the wizard
- No clear separation between developer documentation and curator guidance

**Needed**: 
- Reevaluate what READMEs should contain and how they should be structured
- Consider whether wizard-specific guidance belongs in metadata.yaml instead
- Determine if READMEs should be:
  - Human-readable documentation for profile developers
  - Structured guidance for wizard interfaces
  - Both (with clear separation)
  - Something else entirely

**Use Case**: Wizard needs brief, actionable guidance to show users. Current READMEs would overwhelm the interface.

---

### 2. Sub-Wizard Configuration

**Current State**: Profiles can reference other profiles via `entity_profile` field in statements (e.g., `office_held_by_head_of_state` references `OfficeHeldByHeadOfState` profile).

**Problem**:
- No explicit metadata about how to present sub-entity creation
- Wizard needs to know:
  - When to offer "Create new" vs "Select existing" for entity_profile statements
  - How to organize multi-entity workflows (primary + linked entities)
  - Whether linked entities should be created inline or in separate steps
  - What form_policy values mean and how they affect UI rendering

**Needed**:
- Formalize sub-wizard invocation patterns in profile schema
- Add metadata fields that describe:
  - Workflow organization (inline, separate step, external)
  - Creation vs selection policy
  - Validation dependencies between primary and linked entities
  - Display hints for nested entity forms

**Use Case**: When creating a Tribal Government with an office_held_by_head_of_state, wizard needs to know whether to:
1. Show inline mini-form for the office
2. Launch separate wizard for office creation
3. Only allow selection from existing items
4. Present these as separate steps vs nested sections

**Current Workaround**: `form_policy: target_only` exists but semantics unclear to wizard engineer.

---

### 3. Auto-Creation Pattern for Fixed-Value Statements

**Current State**: The `instance_of` statement in TribalGovernmentUS profile uses `behavior.value: fixed` to lock the value to Q7840353, but the intended workflow is unclear.

**Intended Behavior** (as clarified by user):
- If statement doesn't exist on entity: automatically create it with fixed value
- If statement exists: keep existing value (don't overwrite)
- User task: Only collect references, not the value itself
- Wizard should focus user attention on adding source references, not value entry

**Current Profile Syntax**:
```yaml
statements:
  - id: instance_of
    behavior:
      value: fixed           # Value locked to Q7840353
      references: editable   # References manually provided from SPARQL list
    
    value:
      type: item
      fixed: Q7840353
      label: federally recognized Native American tribe in the United States
    
    references:
      min_count: 1
      input_prompt: Add the Federal Register source for this classification statement
```

**Problem**: 
- Not clear from schema that this should auto-create if missing
- Not clear that wizard should skip value input UI entirely
- Not clear distinction between "fixed value, skip UI" vs "fixed value, show read-only"

**Needed Clarification**:
1. **Auto-creation flag**: Add explicit `auto_create: true` to indicate wizard should create this statement automatically?
2. **UI behavior flag**: Distinguish between:
   - `fixed + auto_create` → Skip value UI, focus on references
   - `fixed + no auto_create` → Show read-only value display
3. **Workflow hints**: Add field like `user_workflow: references_only` to clarify what user should do

**Proposed Enhanced Syntax**:
```yaml
statements:
  - id: instance_of
    behavior:
      value: fixed
      auto_create: true          # NEW: Create automatically if missing
      ui_mode: references_only   # NEW: Only show reference collection UI
    
    value:
      type: item
      fixed: Q7840353
      label: federally recognized Native American tribe in the United States
    
    references:
      min_count: 1
      input_prompt: Add the Federal Register source for this classification statement
```

**Alternative Approach**: Use a simpler top-level flag:
```yaml
statements:
  - id: instance_of
    workflow: auto_create_with_references  # Explicit workflow pattern
    value:
      type: item
      fixed: Q7840353
```

**Use Cases for This Pattern**:
- Classification statements where value is predetermined by profile
- Statements where curator's task is verification/sourcing, not value selection
- Profile-enforced consistency (all items in this profile MUST have this value)
- Focus curator attention on highest-value tasks (adding sources rather than selecting obvious values)

**Wizard Implementation Impact**:
- Need clear semantics to determine when to show value input UI
- Need clear semantics for when to auto-create vs require user action
- Pattern likely applies to other statements beyond instance_of

---

### 4. Sitelinks: URL-Based Entry with Semantic Relationships

**Current State**: Sitelinks section uses language dropdown → project dropdown → title input pattern. Profile defines allowed languages for each project.

**Proposed Change**: URL-based entry where users paste Wikipedia/sister project URLs and system parses them.

**Key Requirements**:

1. **User Experience**: 
   - Single text input per sitelink (paste URL)
   - System parses URL to extract: language code, project type, article title
   - Validates URL actually exists via `requests.head()`
   - More intuitive than language/project dropdowns
   - Easier to extend to arbitrary Wikimedia projects

2. **Bidirectional Transformation** (critical for loading existing items, post-MVP):
   - Must translate existing Wikidata sitelinks → editable URL format
   - Must transform user-entered URLs → Wikidata sitelink format
   - Round-trip integrity required

3. **Two-Part Structure Needed**:
   - **Part 1**: The URL itself
   - **Part 2**: Relationship/significance indicator
   
4. **Semantic Gap in Wikidata Model**:
   - **Problem**: Wikidata sitelinks have no semantic relationship indicator
   - Is Wikipedia article directly about this entity and ONLY this entity?
   - Or does article mention/discuss entity among other topics?
   - Same issue affects External IDs (assumed "same as" but rarely true semantically)
   
5. **Relationship Type Vocabulary**:
   - Need short, well-defined vocabulary of relation types
   - Examples (TBD by Profile Architect):
     - `primary`: Article/resource is primarily and exclusively about this entity
     - `shared`: Article/resource discusses this entity among others
     - `contextual`: Entity mentioned in context of broader topic
     - `same_as`: External identifier represents same entity (rare true case)
   - Helps determine how to handle links in different contexts
   - May inform future data quality / trust scoring

6. **Initial Scope**:
   - Start with vocabulary sufficient for Wikidata sitelinks
   - Only implement what we have placement for in Wikidata model
   - Design extensibility for future semantic enrichment

7. **Profile Schema Implications**:
   ```yaml
   sitelinks:
     input_mode: url_based  # vs language_selection
     
     relationship_types:
       - id: primary
         label: Primary article
         description: This article is exclusively about this entity
         
       - id: shared
         label: Shared article
         description: This article discusses multiple related entities
     
     validation:
       check_url_exists: true
       allowed_domains:
         - "*.wikipedia.org"
         - "*.wikimedia.org"
         - "*.wikidata.org"
       
     # Legacy structure still needed for serialization:
     languages:
       en:
         projects: [wikipedia, wikivoyage]
       chr:
         projects: [wikipedia]
   ```

8. **MVP Plan**:
   - Document this architectural direction for Profile Architect
   - Make minimal setup changes to current `SitelinksStep` structure
   - Keep existing functionality aligned with current profile schema
   - Full URL-based implementation post-MVP after profile schema updated

**Use Case**: User curating Tribal Government pastes:
```
https://en.wikipedia.org/wiki/Cherokee_Nation
```
System:
- Validates URL exists
- Parses: language=en, project=wikipedia, title="Cherokee_Nation"
- Asks: "What type of relationship?" → user selects "Primary article"
- Stores both URL and relationship metadata
- On save: serializes to Wikidata sitelink format
- On load: reconstructs URL from Wikidata sitelink for editing

**Benefits**:
- Dramatically better UX (paste vs multiple dropdowns)
- Captures semantic relationship (missing from current Wikidata model)
- Extensible to arbitrary sister projects
- Lays groundwork for external ID semantic modeling
- Enables future data quality analysis

---

## Profile Schema Improvements

### 5. Language Configuration Clarity

**Current State**: Languages are implicitly defined by presence in labels/descriptions/aliases sections.

**Problem**:
- Wizard must scan all three sections to determine supported languages
- No way to declare "this profile supports languages X, Y, Z but only requires X"
- Unclear whether absence of a language in one section is intentional or oversight

**Needed**: Explicit language declaration at profile level:
```yaml
languages:
  supported:
    - en
    - chr  # Cherokee
    - nv   # Navajo
  required:
    - en
  default: en
  guidance: >
    Provide labels and descriptions in English. Additional languages are optional
    but strongly encouraged for Cherokee and Navajo when applicable.
```

**Use Case**: Wizard can:
- Show tab UI only when multiple languages supported
- Validate required vs optional languages
- Guide users on language expectations

---

### 6. Profile/Metadata Description Redundancy

**Current State**: Both `profile.yaml` and `metadata.yaml` contain `name` and `description` fields.

**Observation**:
- profile.yaml: `name` and `description` (shorter, 1-2 sentences)
- metadata.yaml: `name` and `description` (longer, multiple paragraphs)

**Question for Profile Architect**:
- Is this intentional design (short vs long description)?
- Should profile.yaml contain minimal info and defer to metadata.yaml?
- How should wizard prioritize which description to show?

**Current Wizard Behavior**: Uses `metadata.description` if available, falls back to `profile.description`.

---

## Spirit Safe Module Enhancements

### 7. Profile Loading with Metadata

**Current State**: Wizard must make two separate calls:
```python
profile = load_profile(profile_name)
metadata = load_profile_metadata(profile_name)
```

**Suggestion**: Consider a unified loader:
```python
profile_package = gkc.load_profile_package(profile_name)
# Returns: ProfilePackage(profile=..., metadata=..., readme=...)
```

**Benefits**:
- Single source of truth for "everything about a profile"
- Ensures metadata and profile stay in sync
- Simplifies wizard code
- Could include parsed README if that becomes structured

---

### 8. README Access API

**Current State**: No programmatic way to access profile README files.

**If READMEs become structured/useful**: Add to spirit_safe module:
```python
readme_content = gkc.get_profile_readme(profile_name)
# or
readme_sections = gkc.get_profile_readme(profile_name, parsed=True)
```

---

## Wizard-Specific Observations

### 9. Guidance Field Structure

**Current State**: `guidance` fields are freeform text strings.

**Working Well**: Displaying guidance in help icons or captions.

**Potential Enhancement**: Consider structured guidance:
```yaml
guidance:
  text: >
    Use the name that the tribe uses in referring to itself as the primary label.
  examples:
    - "Cherokee Nation"
    - "Navajo Nation"
    - "Muscogee (Creek) Nation"
  warnings:
    - "Avoid historical or outdated names"
    - "Check official tribal government website for current usage"
  references:
    - url: https://example.com/tribal-naming-guidelines
      title: Tribal Naming Best Practices
```

**Use Case**: Wizard could render examples, warnings, and reference links in collapsible sections.

---

### 10. Form Policy Semantics

**Current State**: `form_policy: target_only` appears on `office_held_by_head_of_state` statement.

**Question**: What does this mean for wizard rendering?
- Only show QID input (no sub-wizard)?
- Show lookup/search interface?
- Disable creation of new entities inline?

**Needed**: Documentation of all `form_policy` values and their wizard implications.

**Current Understanding**: Unknown to wizard engineer; needs clarification.

---

### 11. Allowed Items Display

**Current State**: SPARQL-driven `allowed_items` return long lists (e.g., Federal Register issues).

**Wizard Need**: Know whether to:
- Show as dropdown (if list is short, e.g., < 20 items)
- Show as searchable select (if list is medium, e.g., 20-200 items)
- Show as lookup/autocomplete (if list is large, e.g., > 200 items)

**Suggestion**: Add cardinality hints to allowed_items configuration:
```yaml
allowed_items:
  source: sparql
  query_ref: queries/bia_federal_register_issues.sparql
  expected_count: large  # small, medium, large
  ui_hint: searchable_select  # dropdown, searchable_select, autocomplete
```

---

### 12. Quantity Datatype: Unit Pre-population

**Current State**: Quantity datatype properties (e.g., `member_count`) render as two inputs: amount + unit (QID).

**Problem**: No way to signal in profile whether units should be:
- Omitted entirely (no unit field shown)
- Optional (unit field shown but can be left blank)
- Required with specific allowed values
- Pre-populated with a default unit

**Use Cases**:
1. **No units** (e.g., `member_count`): Count of people has no units, just a number
   - Current behavior: Shows unit QID input field that should be left blank
   - Desired: Hide unit field entirely or mark as "not applicable"

2. **Optional units** (e.g., distance measurement): Could be meters, kilometers, miles
   - Show unit field, allow user to select from list or leave blank

3. **Required specific unit** (e.g., monetary amount): Must have currency
   - Show unit field, require selection from allowed units list

4. **Default unit** (e.g., temperature in scientific context): Assume Kelvin unless specified
   - Pre-populate unit field, allow user to change if needed

**Current Profile Syntax** (member_count example):
```yaml
- id: member_count
  value:
    type: quantity
    constraints:
      - type: integer_only
```

**Proposed Enhancement**:
```yaml
- id: member_count
  value:
    type: quantity
    unit_behavior: none  # or "optional", "required", "default"
    constraints:
      - type: integer_only

# Alternative for cases with units:
- id: height
  value:
    type: quantity
    unit_behavior: required
    allowed_units:
      - Q11573  # metre
      - Q3710  # foot
    default_unit: Q11573  # metre
```

**Wizard Impact**:
- `unit_behavior: none` → Don't show unit input field
- `unit_behavior: optional` → Show unit field, can be blank
- `unit_behavior: required` → Show unit field, validate not empty
- `default_unit: Q...` → Pre-populate unit field with specified QID

**Current Workaround**: Wizard shows unit field for all quantities; users must know to leave it blank for unitless quantities.

---

## Questions for Profile Architect

1. **README Purpose**: What should profile READMEs contain? Should wizard guidance live there or in metadata.yaml?

2. **Sub-Wizard Invocation**: How should profiles declare workflow organization for entity_profile statements?

3. **Auto-Creation Pattern**: How should profiles express "auto-create this statement with fixed value, only collect references"? Should this use `auto_create: true` + `ui_mode: references_only`, or a simpler `workflow: auto_create_with_references` pattern? What other workflow patterns will need similar expression?

4. **Sitelinks Relationship Vocabulary**: What relationship types should be defined for URL-based sitelinks? How should they map to Wikidata serialization? Are there placement options in Wikidata for semantic relationship metadata?

5. **Sitelinks URL Validation**: What domains should be allowed? Should validation include checking for URL existence? How should failed validation be handled (block save vs warning)?

6. **Sitelinks Bidirectional Transform**: What transformation logic is needed for existing Wikidata sitelinks → editable URLs? Should this be part of profile schema or wizard logic?

7. **Language Declaration**: Should languages be explicitly declared at profile level vs inferred from sections?

8. **Description Hierarchy**: Is the profile.description vs metadata.description split intentional? Which should wizard prioritize?

9. **Form Policy**: What are all valid `form_policy` values and what do they mean for UI rendering?

10. **Quantity Units**: How should profiles signal unit behavior for quantity datatypes? Should this use `unit_behavior: none|optional|required|default` with optional `allowed_units` and `default_unit` fields? How should unitless quantities (like member_count) be distinguished from quantities that require units?

---

### 13. Missing Statement Consequences

**Current State**: Profiles define a complete set of statements expected to be contributed. MVP philosophy acknowledges that curators will miss some statements (at least temporarily) as they work through the wizard.

**Problem**: 
- No way to communicate **why** a missing statement matters
- Review stage has no context for curators about downstream impact
- Validation shows "required field missing" but not useful consequences

**Design Decision**:
- Profile can express consequences of missing statements explicitly
- Review stage displays these consequences to help curators prioritize
- Examples of consequences:
  - "Member count is essential for tribal government profiling"
  - "Lead official office determines primary leadership structure"
  - "Sitelinks provide critical linkage to Wikipedia knowledge base"
  - "Federal recognition evidence supports data quality validation"

**Proposed Schema**:
```yaml
statements:
  - id: member_count
    label: Member Count
    description: Number of enrolled tribal members
    
    # NEW: Explain impact of being missing
    missing_consequence: >
      Member count is one of the most important metrics for tribal government profile.
      Without it, the profile is significantly incomplete and appears unverified across
      the Global Knowledge Commons.
    missing_severity: high  # high, medium, low
    
    # ... rest of statement definition

  - id: head_office_location
    label: Office Location
    
    missing_consequence: >
      Office location helps verify current operational status and supports geographic
      data quality checks.
    missing_severity: medium
```

**Wizard Impact**:
- StatementsStep: No change (continue allowing missing optional statements)
- ReviewStep: Display consequences for any statements not provided
- Could add visual indicator (⚠️) for high-severity missing statements
- Helps curators make informed decision: "Is this good enough to save draft?"

**Use Cases**:
1. **In-progress work**: Curator saves draft after collecting some statements, sees consequences for missing ones
2. **Data quality**: Community can see which profile elements were prioritized vs skipped
3. **Future enhancement**: Could feed into quality scoring algorithms

**Not "Required" Validation**: 
- Missing statements with consequences shown as guidance, not errors
- Allows flexible curation workflow (collect what you can find)
- Respects curator judgment about what's worth the effort to research

---

## Implementation Notes for Profile Architect

- Wizard Engineer is blocked on sub-wizard implementation (Phase 4: Statements) until `entity_profile` semantics are clarified
- Any schema changes should be coordinated with Validation Agent to ensure validation logic stays aligned
- Consider backward compatibility if changing existing fields

---

**Last Updated**: 2026-03-02 (during WizardMVP development)
**Next Review**: After Profile Architect addresses items and provides guidance
