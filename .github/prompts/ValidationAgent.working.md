# Validation Agent Working Document

## Mission
Implement robust validation and data coercion functions that integrate directly into the GKC Wizard's data entry flow, enabling clean data collection and comprehensive statement validation before submission to Wikidata.

## Current State
The wizard emits data to a `draft_data` structure as users enter values. Existing validation infrastructure (`ProfileValidator`, `WikidataNormalizer`, Pydantic models) exists but is not integrated into the real-time data entry process.

**Post-Phase-1 Evolution**: Curation packets now bundle multiple related entities (primary + linked profiles) in a single workflow. Validation must account for:
- Individual entity validation (same as before)
- Cross-profile validation (constraints spanning multiple entities)
- Cardinality enforcement (profile_graph constraints on linked entities)

### Architectural Decision: GKC Entity JSON vs Wikidata JSON

**Deferred**: Wikidata JSON output generation until validation/coercion is solid.

**Rationale**:
1. YAML profile → JSON transformation (✓ done)
2. Wizard collects user input → **GKC Entity JSON** (✓ done, internal format)
3. GKC Entity JSON → Wikidata JSON (deferred)

The wizard's internal JSON structure ("GKC Entity JSON") needs to capture clean, normalized data with full precision information. Once this format is formalized and properly validated, transformation to Wikidata JSON will be trivial.

**Key Example**: Date coercion shows why this matters:
- User enters: "2021"
- GKC Entity JSON stores: `{"value": "2021", "precision": "year"}` (clean, normalized)
- Wikidata JSON generation: Trivial conversion to ISO8601 with precision level

**Next Steps**:
1. Formalize GKC Entity JSON schema in architecture documentation
2. Ensure validation/coercion functions normalize to this format
3. Build Wikidata JSON serialization once GKC Entity JSON is stable

## Requirements Discovered from Wizard MVP

### 1. Real-Time Validation/Coercion During Data Entry

**Problem:** User enters raw values (e.g., "2024-03-02", "March 2, 2026", "3/2/2026") in date qualifiers and quantity units. These need to be normalized immediately.

**Solution:** Coercion-focused validators that:
- Take user input and config
- Return: `(coerced_value, issues: list[Issue])`
- Allow the wizard to store clean data immediately
- Enable inline feedback to the user

**Trigger points in wizard:**
- After user exits a field (onBlur-style, though Streamlit reruns on interaction)
- On explicit validation button click
- Before moving to next step

### 2. Datatype-Specific Coercion Functions

These should be callable by the wizard layer and usable elsewhere:

#### 2.1 Date Coercion (`time` datatype)
Accepts multiple formats and normalizes to profile format (YYYY, YYYY-MM, YYYY-MM-DD):
- "March 2, 2026" → "2026-03-02"
- "2026/03/02" → "2026-03-02"
- "03-02-2026" → detect ambiguity, warn or ask for clarification
- Partial dates: "March 2026" → "2026-03"
- ISO formats: already valid

**Input:** `(user_input: str, constraints: dict)` → `(normalized: str | None, issues: list[Issue])`

#### 2.2 Quantity Coercion
- Normalize units to standard form (m → meter properties)
- Apply unit defaults based on profile (`unit_behavior`)
- Validate numeric value (integer-only constraints, range checks)

**Input:** `(amount: str, unit_input: str, profile_config: QuantityConfig)` → `(amount: float, unit: str, issues: list[Issue])`

#### 2.3 Item (QID) Coercion
- Normalize format: "q123" → "Q123", "wikidata:Q123" → "Q123"
- Optional: Verify QID exists on Wikidata (may require async call)
- Check against `allowed_items` lists if configured

#### 2.4 Monolingualtext Coercion
- Validate language code is valid Wikimedia code
- Auto-detect common language codes from input hints
- Normalize full language names to codes

#### 2.5 URL Coercion
- Validate URL format
- Normalize scheme (add https:// if missing)
- Check for common issues (spaces, special chars)

### 3. Issue Reporting Structure

Each validator should return issues with severity and context:

```python
class ValidationIssue:
    severity: Literal["error", "warning", "info"]  # error=block, warning=record, info=advisory
    message: str  # User-friendly message
    field_id: str  # Which field (e.g., "member_count_point_in_time")
    suggestion: str | None  # How to fix it
    auto_fixed: bool  # Whether coercion auto-fixed this
```

### 4. Integration Points in Wizard

#### 4.1 After Value Widget Entry
```python
# In _render_value_input or widget handlers:
new_value = WidgetFactory.render_widget(...)
if new_value is not None:
    coerced_value, issues = coerce_value(new_value, statement_def.value)
    if issues:
        show_issues_inline(issues)  # warnings as st.warning(), errors block save
    value_data["value"] = coerced_value
    value_data["validation_issues"] = issues
```

#### 4.2 After Qualifier Entry
```python
# Similar flow in _render_qualifiers:
new_qual_value = WidgetFactory.render_widget(...)
if new_qual_value is not None:
    coerced, issues = coerce_value(new_qual_value, qualifier_def.value)
    show_issues_inline(issues)
    value_data["qualifiers"][qual_id] = coerced
```

#### 4.3 After Reference Entry
```python
# In _render_references:
new_ref_value = WidgetFactory.render_widget(...)
if new_ref_value is not None:
    coerced, issues = coerce_value(new_ref_value, ref_target)
    show_issues_inline(issues)
    existing_ref["value"] = coerced
```

### 5. Comprehensive Validation at Review Stage

After all steps collect data, run full ProfileValidator:
- Validates complete statements (not just individual values)
- Checks required fields, min/max counts for qualifiers/references
- Validates interdependencies between statement components
- Returns comprehensive issues for review before submission

### 6. Error Handling & User Guidance

**Block Entry (Error severity):**
- Invalid date format that can't be coerced
- Non-QID input in item field
- Invalid language code for monolingualtext

**Warn (Warning severity):**
- Ambiguous date (could be MM-DD or DD-MM)
- Field marked as required but empty
- Quantity without unit when unit is required

**Info (Info severity):**
- Common alternative formats ("might you mean X?")
- Deprecated terms
- Suggestions for related items

## 7. Packet-Level Validation (Cross-Profile Constraints)

**Context**: Curation packets now contain multiple entities (primary + related profiles connected via profile_graph). Validation must ensure consistency across entities and enforce inter-entity constraints.

### 7.1 Cardinality Validation

Profile graphs declare cardinality constraints (min/max) for linked entity relationships. Validator must enforce:

```python
class CardinalityConstraint:
    min: int  # Minimum linked entities required
    max: int  # Maximum linked entities allowed
    via_statement: str  # Statement that creates the link
    target_profile: str  # Name of linked profile
```

**Examples**:
- TribalGovernmentUS → OfficeHeldByHeadOfState: min=0, max=1 (at most one head of state office)
- TribalGovernmentUS → HeadOfficial: min=0, max=N (potentially many officials, but profile may constrain this)

**Validation Logic**:
```python
def validate_cardinality(packet: CurationPacket, profile_graph: ProfileGraph):
    """
    For each linked entity type in packet:
    - Count how many entities of that type are present
    - Check min ≤ count ≤ max
    - Return issues if outside bounds
    """
```

### 7.2 Bidirectional Relationship Consistency

When packet contains multiple related entities:
- If primary entity has statement linking to related_entity, ensure related_entity is in packet
- If related_entity is in packet, ensure it has reciprocal reference back to primary (if bidirectional)
- Return warning if relationships are incomplete (incomplete packet)

### 7.3 Entity-to-Entity Constraints

Some profile pairs may have temporal or semantic constraints:

**Example**: Office inception date ≤ Tribal government founding date
- Validation must access both entities and compare values
- Return error if constraint violated

**Future Approach**: Could define constraints in profile metadata or profile_graph edges
- For MVP: Handle case-by-case in validation logic
- Document patterns as they emerge

### 7.4 Integration Points

**When**:
- At review stage (before final submission) - comprehensive packet-level validation
- Optional: After loading linked entities (early feedback to curator)

**Input**: Full `CurationPacket` object containing all entities + ProfileGraph structure
**Output**: Comprehensive issue list scoped by entity + cross-entity issues

```python
packet_issues = {
    "primary_entity": [issue1, issue2, ...],
    "related_entity_1": [issue3, ...],
    "cross_entity": [issue4, issue5, ...]  # NEW: Spans multiple entities
}
```

---

## Known Constraints & Context

- Wizard uses Streamlit (reruns on every interaction)
- Data stored in `st.session_state.draft_data` as nested dict
- Coercion must be fast (no external API calls on keystroke, but optional for explicit validation)
- Must integrate with WidgetFactory (may need to pass validation context through)
- QID verification against Wikidata could be async but is optional for MVP

## Profile Schema Dependencies

Some coercion rules depend on profile schema being finalized:
- `unit_behavior` field for quantities (none/optional/required/default)
- `auto_create` pattern for fixed-value statements
- Constraint definitions (integer-only, valid language code, etc.)

See ProfileArchitect.working.md for related schema work.

## Profile Schema Dependencies

Some coercion and validation rules depend on profile schema being finalized:
- `unit_behavior` field for quantities (none/optional/required/default)
- `auto_create` pattern for fixed-value statements (fixed value, focus on references only)
- Constraint definitions (integer-only, valid language code, min/max dateTime, cardinality min/max)
- **NEW (Phase 1-3)**: `profile_graph` edges with cardinality (min/max for linked entities)
- **NEW (Phase 1-3)**: Statement-level `linkage` metadata defining cross-profile relationships
- **NEW (Phase 1-3)**: `missing_consequence` field for guidance on optional statements

See ProfileArchitect.working.md for related schema work and Phase 2-3 Pydantic model evolution.

## Testing Strategy

1. **Unit tests** for each coercion function (test various input formats)
2. **Integration tests** with wizard step rendering (test inline validation)
3. **Comprehensive validation tests** with complete statement data (single entity)
4. **Packet-level validation tests** with multiple related entities and cardinality constraints
5. **User scenarios** (entering date in multiple formats, adding quantities with/without units, multi-entity packets)

## Alignment with Phase 2-3 Development

**Phase 2 Dependencies**: 
- Extended `EntityProfile` model will provide statement linkage metadata
- New `ProfileGraph` model will provide cardinality constraints and traversal info
- Validator can consume these to enforce packet-level rules

**Phase 3 Dependencies**:
- `load_profile_package()` will return packet structure
- Validator will receive packets from wizard after all entities are collected
- `validate_packet_structure()` (in spirit_safe module) will ensure graph consistency
- `ProfileValidator` will handle content validation (values, qualifiers, references within/across entities)

---

## Next Steps (Coordinated with Phase 2-3)

1. Implement core coercion functions for each datatype
2. Create a coercion registry/dispatcher
3. Integrate with wizard layer (Update WidgetFactory or create validation hooks)
4. **NEW (Phase 2-3 era)**: Implement packet-level validation functions (cardinality, bidirectional consistency, cross-entity constraints)
5. Build comprehensive tests for single-entity and multi-entity (packet) validation
6. Test with real user data from MVP collection
7. Refine based on curator feedback

## Questions Remaining for Profile Architect

- Should coercion rules be defined in profile schema, or hardcoded per datatype?
- For date ambiguity (12-01), should we prompt user or pick a default interpretation?
- Should failed coercion block data entry (error) or just record issues (warning)?
- What cross-profile constraints should be expressed in profile metadata vs handled as special cases?
- How should entity-to-entity temporal constraints be declared (e.g., office inception ≤ government founding)?

## Coordination with Phase 2-3 Development

**Work in parallel**:
- Profile Architect continues refining schema (Phase 1 wrap-up)
- Validation Agent implements core coercion functions (can work independently)
- gkc package extends EntityProfile and builds ProfileGraph models (Phase 2)
- gkc package builds spirit_safe module with packet loading (Phase 3)
- Validation Agent integrates with ProfileGraph/packet structures (after Phase 2-3 complete)

**Integration point**: Once Phase 3 spirit_safe module is complete with `load_profile_package()`, Validation Agent incorporates packet-level validation into the workflow.
