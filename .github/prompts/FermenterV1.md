# FermenterV1: Validation & Coercion Engine

**Target Agent:** Validation Agent  
**Phase:** New module implementation  
**Status:** Planning (v1 fresh start)  

---

## Executive Summary

The **fermenter** module is a new component in the gkc package responsible for **primitive datatype validation and coercion** based on GKC Property Specifications defined in the Data Distillery Wikibase. This module bridges the gap between user-provided input (from wizard forms, CSV uploads, or API calls) and the strict Wikibase JSON format required for entity serialization.

**Core Responsibilities:**
1. Validate values against 8 primitive Wikibase datatypes
2. Coerce loosely-typed input to strict Wikibase JSON structure
3. Enforce GKC Property Specification directives (Q6 instances)
4. Resolve and validate against GKC Value Lists (Q7 instances)
5. Validate qualifier requirements and reference constraints
6. Return a shared result envelope consumable by wizard, CLI, and bulk pipelines

**Design Principles:**
- **Atomic validators:** One validator function per datatype, independently testable
- **Fail-fast policy:** Validation errors stop processing, coercion attempts are logged
- **Specification-driven:** All validation rules sourced from DD Wikibase ontology (no hardcoded constraints)
- **Offline-capable:** Value lists cached in SpiritSafe for fallback when SPARQL unavailable
- **API-first multi-modal:** One fermenter API powers wizard, batch, CLI, and automation; callers vary only in presentation and workflow handling

---

## API-First Execution Contract

Fermenter must expose a public interface that is interface-agnostic and reusable across all curation modes.

**Public Contract Requirements:**
- Accept normalized profile statement context (including policy references and value/reference specs)
- Accept caller execution mode metadata (e.g., interactive preview vs batch strict)
- Return a shared result envelope with machine-readable codes, severity, normalized values, user-facing messages, and provenance trace
- Avoid any wizard-only branching inside fermenter core

**Caller Responsibilities (outside fermenter):**
- Wizard renders inline hints/errors and interaction affordances
- CLI formats terminal output and exit behavior
- Bulk pipelines aggregate/report failures and drive retry or quarantine flows

---

## Primitive Datatype Validators

### Contract

Each datatype requires **internal helpers** and is exposed through a **shared public fermenter API**:
1. **Validator helper:** Returns `ValidationResult` (pass/fail + error messages)
2. **Coercer helper:** Attempts to transform input to Wikibase JSON structure, raises exception if impossible
3. **Public orchestrator:** Applies policy directives, runs validator/coercer pipeline, and emits the shared result envelope

### Datatype Inventory (from P194 in DD Wikibase)

| Datatype | YAML `value.type` | Wikibase JSON `datatype` | Example Input | Example Output |
|----------|-------------------|-------------------------|---------------|----------------|
| item | `item` | `wikibase-item` | `"Q12345"` or `"https://www.wikidata.org/entity/Q12345"` | `{"entity-type": "item", "id": "Q12345"}` |
| monolingual text | `monolingualtext` | `monolingualtext` | `{"text": "Hello", "language": "en"}` | `{"text": "Hello", "language": "en"}` |
| url | `url` | `url` | `"https://example.com"` | `"https://example.com"` |
| string | `string` | `string` | `"Free text"` | `"Free text"` |
| datetime | `time` | `time` | `"2024-03-15"` or `"2024-03-15T10:30:00Z"` | `{"+2024-03-15T00:00:00Z", "timezone": 0, "precision": 11, ...}` |
| quantity | `quantity` | `quantity` | `"42"` or `{"amount": "+42", "unit": "1"}` | `{"amount": "+42", "unit": "1", "upperBound": "+42", "lowerBound": "+42"}` |
| geographic coordinates | `globecoordinate` | `globe-coordinate` | `{"latitude": 38.8977, "longitude": -77.0365}` | `{"latitude": 38.8977, "longitude": -77.0365, "precision": 0.0001, "globe": "http://www.wikidata.org/entity/Q2"}` |
| commons media file | `commonsMedia` | `commonsMedia` | `"Example.jpg"` or `"File:Example.jpg"` | `"Example.jpg"` |

### Implementation Template

```python
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ValidationResult:
    """Result of a validation operation."""
    valid: bool
    value: Any
    errors: list[str]
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


# ============================================================================
# ITEM DATATYPE
# ============================================================================

def validate_item(value: Any, context: dict = None) -> ValidationResult:
    """
    Validate that value is a valid Wikibase item reference.
    
    Accepts:
    - QID string: "Q12345"
    - Full URI: "https://www.wikidata.org/entity/Q12345"
    - Wikibase JSON: {"entity-type": "item", "id": "Q12345"}
    
    Args:
        value: Input value to validate
        context: Optional context (e.g., allowed item list for constraint checking)
    
    Returns:
        ValidationResult with normalized Wikibase JSON structure if valid
    """
    errors = []
    
    # Type check
    if value is None:
        errors.append("Item value cannot be None")
        return ValidationResult(valid=False, value=None, errors=errors)
    
    # Normalize to QID
    try:
        qid = coerce_to_item_qid(value)
    except ValueError as e:
        errors.append(str(e))
        return ValidationResult(valid=False, value=value, errors=errors)
    
    # Optional constraint: check against allowed items list
    if context and "allowed_items" in context:
        if qid not in context["allowed_items"]:
            errors.append(f"Item {qid} not in allowed items list")
            return ValidationResult(valid=False, value=qid, errors=errors)
    
    # Success
    return ValidationResult(valid=True, value={"entity-type": "item", "id": qid}, errors=[])


def coerce_to_item_qid(value: Any) -> str:
    """
    Coerce value to QID string format.
    
    Raises:
        ValueError: If value cannot be coerced to valid QID
    """
    if isinstance(value, dict):
        # Already Wikibase JSON
        if value.get("entity-type") == "item" and "id" in value:
            return value["id"]
        else:
            raise ValueError(f"Invalid Wikibase item JSON: {value}")
    
    if isinstance(value, str):
        # Strip URI prefix if present
        if value.startswith("http"):
            value = value.split("/")[-1]
        
        # Validate QID format
        if not value.startswith("Q") or not value[1:].isdigit():
            raise ValueError(f"Invalid QID format: {value}")
        
        return value
    
    raise ValueError(f"Cannot coerce {type(value)} to item QID")


# ============================================================================
# MONOLINGUAL TEXT DATATYPE
# ============================================================================

def validate_monolingualtext(value: Any, context: dict = None) -> ValidationResult:
    """
    Validate monolingual text value.
    
    Accepts:
    - Dict with text/language: {"text": "Hello", "language": "en"}
    - Tuple: ("Hello", "en")
    
    Language codes validated against BCP 47 (basic check: 2-3 letter codes).
    """
    errors = []
    warnings = []
    
    try:
        text, language = coerce_to_monolingualtext(value)
    except ValueError as e:
        errors.append(str(e))
        return ValidationResult(valid=False, value=value, errors=errors)
    
    # Validate language code format (basic check)
    if len(language) < 2 or len(language) > 3:
        warnings.append(f"Unusual language code: {language} (expected 2-3 characters)")
    
    # Optional constraint: required language
    if context and "required_language" in context:
        if language != context["required_language"]:
            errors.append(f"Language must be {context['required_language']}, got {language}")
            return ValidationResult(valid=False, value=value, errors=errors, warnings=warnings)
    
    return ValidationResult(
        valid=True,
        value={"text": text, "language": language},
        errors=[],
        warnings=warnings
    )


def coerce_to_monolingualtext(value: Any) -> tuple[str, str]:
    """
    Coerce value to (text, language) tuple.
    
    Raises:
        ValueError: If value cannot be coerced
    """
    if isinstance(value, dict):
        if "text" in value and "language" in value:
            return value["text"], value["language"]
        else:
            raise ValueError(f"Monolingual text dict must have 'text' and 'language' keys: {value}")
    
    if isinstance(value, tuple) and len(value) == 2:
        return str(value[0]), str(value[1])
    
    raise ValueError(f"Cannot coerce {type(value)} to monolingual text")


# ============================================================================
# URL DATATYPE
# ============================================================================

def validate_url(value: Any, context: dict = None) -> ValidationResult:
    """
    Validate URL string.
    
    Accepts:
    - Valid HTTP/HTTPS URL strings
    
    Basic validation: must start with http:// or https://
    Advanced validation (optional): URL accessibility check
    """
    import re
    
    errors = []
    warnings = []
    
    if not isinstance(value, str):
        errors.append(f"URL must be string, got {type(value)}")
        return ValidationResult(valid=False, value=value, errors=errors)
    
    # Basic URL pattern check
    url_pattern = re.compile(r'^https?://[^\s]+$')
    if not url_pattern.match(value):
        errors.append(f"Invalid URL format: {value}")
        return ValidationResult(valid=False, value=value, errors=errors)
    
    # Optional: URL accessibility check (expensive, skip by default)
    if context and context.get("check_accessibility"):
        try:
            import requests
            response = requests.head(value, timeout=5, allow_redirects=True)
            if response.status_code >= 400:
                warnings.append(f"URL returned status {response.status_code}: {value}")
        except Exception as e:
            warnings.append(f"Could not verify URL accessibility: {e}")
    
    return ValidationResult(valid=True, value=value, errors=[], warnings=warnings)


def coerce_to_url(value: Any) -> str:
    """
    Coerce value to URL string.
    
    Raises:
        ValueError: If value cannot be coerced
    """
    if isinstance(value, str):
        return value
    
    raise ValueError(f"Cannot coerce {type(value)} to URL")


# ============================================================================
# Additional validators for remaining 5 datatypes follow same pattern:
# - validate_{datatype}(value, context) -> ValidationResult
# - coerce_to_{datatype}(value) -> normalized_output
# ============================================================================
```

### Remaining Datatype Implementations (Validation Agent TODO)

**String:** Simplest validator (accept any string, optional length constraints from context)

**DateTime:** Most complex validator
- Accept ISO 8601 formats: `YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SSZ`, partial dates `YYYY-MM`, `YYYY`
- Convert to Wikibase time format: `{"+2024-03-15T00:00:00Z", "timezone": 0, "precision": 11, "calendarmodel": "http://www.wikidata.org/entity/Q1985727"}`
- Precision mapping: year (9), month (10), day (11), hour (12), minute (13), second (14)

**Quantity:** 
- Accept numeric strings, floats, ints, or dict with `amount`/`unit`
- Default unit: `"1"` (unitless)
- Convert to Wikibase quantity: `{"amount": "+42", "unit": "1", "upperBound": "+42", "lowerBound": "+42"}`
- Optional bounds validation from context

**Geographic Coordinates:**
- Accept dict with `latitude`/`longitude` (required) + optional `precision`/`globe`
- Validate latitude range: -90 to +90
- Validate longitude range: -180 to +180
- Default globe: `"http://www.wikidata.org/entity/Q2"` (Earth)
- Default precision: `0.0001` (street-level)

**Commons Media:**
- Accept filename with or without `File:` prefix
- Strip prefix, validate filename characters (no `/`, `\`, special chars)
- Optional: verify file exists on Wikimedia Commons via API (expensive, skip by default)

---

## GKC Property Specification Enforcement

### Specification Taxonomy (from DD Wikibase)

**Q6 (GKC Property Specification):** Parent class for all validation/policy specifications

**Known Specification Items:**

| QID | Label | Directive (P191) | Type | Fermenter Implementation |
|-----|-------|------------------|------|--------------------------|
| **Q23** | require fixed value | "apply a supplied fixed value without any need for deliberate input action" | Policy | `apply_fixed_value()` |
| **Q24** | allow nonconforming statements | "allow other statements for an entity beyond what is strictly specified" | Policy | `relax_validation()` (profile-level, not fermenter) |
| **Q26** | value applied as reference | "apply the statement value as reference URL type of reference" | Transform | `route_value_to_reference()` |
| **Q31** | reference must be at least one of URL or stated in | "require a reference that is at least one of qualifier values" | Constraint | `validate_reference_constraint()` |
| **Q28** | Federal Register Notices Listing Tribes | "use the value list as values for stated in references" | Value List (Q7) | `validate_value_from_list()` |
| **Q43** | List of World Countries | "use the value list as values for country statements" | Value List (Q7) | `validate_value_from_list()` |

### Specification Processor Contract

```python
from typing import Any, Optional
from dataclasses import dataclass

@dataclass
class SpecificationContext:
    """Context for applying a property specification."""
    spec_item_qid: str
    spec_directive: str
    target_statement: str  # Which statement this spec applies to
    value_lists: dict[str, list[str]] = None  # Cached value lists (QID -> [items])
    
    def __post_init__(self):
        if self.value_lists is None:
            self.value_lists = {}


# ============================================================================
# SPECIFICATION PROCESSORS
# ============================================================================

def apply_fixed_value(spec: SpecificationContext, value: Any, fixed_value: str) -> ValidationResult:
    """
    Q23 handler: Enforce fixed value.
    
    Args:
        spec: Specification context
        value: User-provided value (should be None or match fixed_value)
        fixed_value: The fixed value URI/QID from P183 qualifier
    
    Returns:
        ValidationResult with fixed_value enforced
    
    Behavior:
    - If user provides value that matches fixed_value: accept
    - If user provides None: inject fixed_value
    - If user provides different value: reject with error
    """
    if value is None:
        # Inject fixed value
        return ValidationResult(
            valid=True,
            value=fixed_value,
            errors=[],
            warnings=["Fixed value applied automatically"]
        )
    
    # Normalize both values for comparison
    normalized_input = coerce_to_item_qid(value)
    normalized_fixed = coerce_to_item_qid(fixed_value)
    
    if normalized_input != normalized_fixed:
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"Value must be {normalized_fixed}, got {normalized_input}"]
        )
    
    return ValidationResult(valid=True, value=normalized_fixed, errors=[])


def route_value_to_reference(spec: SpecificationContext, value: str) -> dict:
    """
    Q26 handler: Convert statement value to reference URL.
    
    Args:
        spec: Specification context
        value: Statement value (URL string)
    
    Returns:
        Wikibase reference structure
    
    Example:
        Input: "https://example.com/source"
        Output: {
            "snaks": {
                "P854": [{"snaktype": "value", "property": "P854", "datavalue": {"type": "string", "value": "https://example.com/source"}}]
            }
        }
    """
    # Validate URL first
    url_validation = validate_url(value)
    if not url_validation.valid:
        raise ValueError(f"Cannot route invalid URL to reference: {url_validation.errors}")
    
    # Construct reference structure (P854 = reference URL in Wikidata)
    # TODO: Make property configurable from ontology
    return {
        "snaks": {
            "P854": [{
                "snaktype": "value",
                "property": "P854",
                "datavalue": {
                    "type": "string",
                    "value": value
                }
            }]
        }
    }


def validate_reference_constraint(
    spec: SpecificationContext,
    references: list[dict]
) -> ValidationResult:
    """
    Q31 handler: Require at least one of URL or stated-in references.
    
    Args:
        spec: Specification context
        references: List of Wikibase reference structures
    
    Returns:
        ValidationResult indicating whether constraint is satisfied
    """
    if not references:
        return ValidationResult(
            valid=False,
            value=None,
            errors=["At least one reference (URL or stated in) is required"]
        )
    
    # Check for P854 (reference URL) or P248 (stated in) in any reference
    # TODO: Make property IDs configurable from ontology
    has_url_or_stated_in = False
    for ref in references:
        snaks = ref.get("snaks", {})
        if "P854" in snaks or "P248" in snaks:
            has_url_or_stated_in = True
            break
    
    if not has_url_or_stated_in:
        return ValidationResult(
            valid=False,
            value=references,
            errors=["Reference must include at least one of: URL (P854) or stated in (P248)"]
        )
    
    return ValidationResult(valid=True, value=references, errors=[])


# ============================================================================
# VALUE LIST VALIDATION
# ============================================================================

def validate_value_from_list(
    spec: SpecificationContext,
    value: Any,
    match_policy: str = "strict"
) -> ValidationResult:
    """
    Q28/Q43 handler: Validate value against GKC Value List.
    
    Args:
        spec: Specification context with value_lists cached
        value: User-provided value (QID, label, or URI)
        match_policy: "strict" (exact match), "fuzzy" (label matching), "best_effort" (coerce)
    
    Returns:
        ValidationResult with normalized value if found in list
    """
    # Get value list for this specification
    value_list = spec.value_lists.get(spec.spec_item_qid)
    if not value_list:
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"Value list {spec.spec_item_qid} not loaded"],
            warnings=["Cannot validate without value list"]
        )
    
    # Normalize input to QID
    try:
        input_qid = coerce_to_item_qid(value)
    except ValueError:
        # Value is not a QID, try label matching if fuzzy policy
        if match_policy in ["fuzzy", "best_effort"]:
            matched_qid = _fuzzy_match_label(value, value_list)
            if matched_qid:
                return ValidationResult(
                    valid=True,
                    value=matched_qid,
                    errors=[],
                    warnings=[f"Matched label '{value}' to {matched_qid}"]
                )
        
        return ValidationResult(
            valid=False,
            value=value,
            errors=[f"Value '{value}' is not a valid QID and no fuzzy match found"]
        )
    
    # Check if QID exists in value list
    if input_qid in value_list:
        return ValidationResult(valid=True, value=input_qid, errors=[])
    
    return ValidationResult(
        valid=False,
        value=input_qid,
        errors=[f"Item {input_qid} not in allowed value list for {spec.spec_item_qid}"]
    )


def _fuzzy_match_label(label: str, value_list: list[dict]) -> Optional[str]:
    """
    Fuzzy match label against value list items.
    
    Args:
        label: Input label string
        value_list: List of dicts with 'qid' and 'label' keys
    
    Returns:
        Matched QID or None
    
    Strategy:
    1. Exact case-insensitive match
    2. Prefix match (label starts with input)
    3. Levenshtein distance < 3 (future enhancement)
    """
    label_lower = label.lower()
    
    # Exact match
    for item in value_list:
        if item.get("label", "").lower() == label_lower:
            return item["qid"]
    
    # Prefix match
    for item in value_list:
        if item.get("label", "").lower().startswith(label_lower):
            return item["qid"]
    
    # No match found
    return None
```

---

## Value List Resolution & Caching

### Architecture

**Source:** DD Wikibase items of type Q7 (GKC Value List)

**Storage:** SpiritSafe cache (`cache/value_lists/{ListQID}.json`)

**SPARQL Location:** MediaWiki Discussion (Talk) page for each value list item (Q28, Q43, etc.)

**Extraction Workflow:**
1. Query DD Wikibase for all Q7 instances
2. Fetch Discussion page content for each item (MediaWiki API)
3. Extract SPARQL query text from Discussion page (parse wiki markup)
4. Execute SPARQL against configured endpoint (Wikidata Query Service, etc.)
5. Materialize results as JSON: `[{"qid": "Q123", "label": "Example"}, ...]`
6. Write to `SpiritSafe/cache/value_lists/{ListQID}.json`

**Runtime Loading:**
1. `fermenter` module reads value list JSON from SpiritSafe cache
2. If cache missing or stale, optionally regenerate via SPARQL (configuration flag)
3. Pass value list to `validate_value_from_list()` via `SpecificationContext.value_lists`

### Value List JSON Schema

```json
{
  "list_qid": "Q28",
  "list_label": "Federal Register Notices Listing Tribes",
  "applies_to_property": "Q30",
  "generated_at": "2026-03-09T12:00:00Z",
  "sparql_query": "SELECT ?item ?itemLabel WHERE { ... }",
  "truncated": false,
  "item_count": 574,
  "items": [
    {"qid": "Q12345", "label": "Example Tribal Nation"},
    {"qid": "Q67890", "label": "Another Tribe"}
  ]
}
```

**Truncation Policy:**
- Default: Materialize up to 10,000 items per list in SpiritSafe cache
- If SPARQL returns more, set `"truncated": true` and store first 10,000
- Runtime can regenerate full list on-demand if needed

---

## Qualifier Validation

### P164 Expected Qualifiers

**Requirement:** Statement may require specific qualifiers to be present.

**Example (from Q4 TribalGovernmentUS):**
- P157 statement targeting Q33 (headquarters location)
- P164 qualifier: Q34 (street address), Q35 (postal code), Q36 (coordinate location)
- Semantics: "headquarters location statement must include qualifiers for street address, postal code, and coordinates"

**Validation Contract:**

```python
def validate_expected_qualifiers(
    statement: dict,
    expected_qualifier_qids: list[str],
    qualifier_policy: str = "require_all"
) -> ValidationResult:
    """
    Validate that statement includes expected qualifiers.
    
    Args:
        statement: Wikibase statement structure with 'qualifiers' key
        expected_qualifier_qids: List of required qualifier statement QIDs
        qualifier_policy: "require_all" (all must be present), "require_any" (at least one)
    
    Returns:
        ValidationResult indicating whether qualifiers are satisfied
    """
    qualifiers = statement.get("qualifiers", {})
    qualifier_properties = set(qualifiers.keys())
    
    # Map expected QIDs to property IDs (requires statement-definition lookup)
    # TODO: Inject this mapping from profile or manifest
    expected_properties = set()
    for qid in expected_qualifier_qids:
        prop_id = _resolve_statement_qid_to_property(qid)
        if prop_id:
            expected_properties.add(prop_id)
    
    if qualifier_policy == "require_all":
        missing = expected_properties - qualifier_properties
        if missing:
            return ValidationResult(
                valid=False,
                value=statement,
                errors=[f"Missing required qualifiers: {', '.join(missing)}"]
            )
    
    elif qualifier_policy == "require_any":
        if not qualifier_properties.intersection(expected_properties):
            return ValidationResult(
                valid=False,
                value=statement,
                errors=[f"At least one of these qualifiers required: {', '.join(expected_properties)}"]
            )
    
    return ValidationResult(valid=True, value=statement, errors=[])


def _resolve_statement_qid_to_property(qid: str) -> Optional[str]:
    """
    Resolve statement-definition QID to Wikidata property ID.
    
    Args:
        qid: Statement-definition item QID (e.g., Q34)
    
    Returns:
        Property ID (e.g., "P6375") or None if not found
    
    Implementation: Look up in cached manifest or profile data.
    """
    # Placeholder: real implementation would query manifest or profile cache
    # For now, return None (requires integration with profiles module)
    return None
```

---

## Error Handling & Logging

### Validation Result Aggregation

**Challenge:** Single statement may have multiple validation failures (value invalid, qualifier missing, reference constraint violated)

**Strategy:** Accumulate errors/warnings across all validators, return single `ValidationResult`

```python
def validate_statement_comprehensive(
    statement_spec: dict,
    statement_data: dict,
    context: dict
) -> ValidationResult:
    """
    Comprehensive statement validation with error aggregation.
    
    Args:
        statement_spec: Profile statement specification (from JSON cache)
        statement_data: User-provided statement data
        context: Validation context (value lists, specifications, etc.)
    
    Returns:
        Aggregated ValidationResult
    """
    all_errors = []
    all_warnings = []
    
    # Validate value datatype
    value_result = validate_value_by_type(
        statement_data.get("value"),
        statement_spec["value"]["type"],
        context
    )
    all_errors.extend(value_result.errors)
    all_warnings.extend(value_result.warnings)
    
    # Validate expected qualifiers (P164)
    if statement_spec.get("expected_qualifiers"):
        qualifier_result = validate_expected_qualifiers(
            statement_data,
            statement_spec["expected_qualifiers"]
        )
        all_errors.extend(qualifier_result.errors)
        all_warnings.extend(qualifier_result.warnings)
    
    # Validate reference constraints (P159)
    if statement_spec.get("reference_specs"):
        for spec_qid in statement_spec["reference_specs"]:
            ref_result = validate_reference_specification(
                spec_qid,
                statement_data.get("references", []),
                context
            )
            all_errors.extend(ref_result.errors)
            all_warnings.extend(ref_result.warnings)
    
    # Apply value specifications (P161)
    if statement_spec.get("value_specs"):
        for spec_qid in statement_spec["value_specs"]:
            spec_result = apply_value_specification(
                spec_qid,
                statement_data.get("value"),
                statement_spec,
                context
            )
            all_errors.extend(spec_result.errors)
            all_warnings.extend(spec_result.warnings)
    
    return ValidationResult(
        valid=len(all_errors) == 0,
        value=statement_data,
        errors=all_errors,
        warnings=all_warnings
    )
```

### Logging Strategy

**Requirement:** All validation failures must be traceable to source data for debugging

**Implementation:**
- Use Python `logging` module (not print statements)
- Log level mapping:
  - `ERROR`: Hard validation failures (data rejected)
  - `WARNING`: Soft validation issues (data accepted with warning)
  - `INFO`: Successful coercions (data transformed)
  - `DEBUG`: Detailed validator execution (for development)

**Log Format:**
```
[ERROR] fermenter.validate_item: Item Q99999 not in allowed items list (statement: instance_of, entity: TribalGovernmentUS_001)
[WARNING] fermenter.validate_url: URL returned status 404 (statement: official_website, entity: TribalGovernmentUS_001)
[INFO] fermenter.coerce_to_item_qid: Converted URI to QID: https://www.wikidata.org/entity/Q12345 -> Q12345
```

---

## Integration with gkc.profiles Module

### Coordination with ProfileValidator

**Current State:** `gkc.profiles.validation.ProfileValidator` validates entity structure against profile schema

**New Requirement:** `fermenter` handles **value-level validation** (datatype, constraints), `ProfileValidator` handles **structure-level validation** (required statements, cardinality, profile conformance)

**Division of Responsibility:**

| Validation Type | Module | Example |
|----------------|--------|---------|
| Required statement present | `ProfileValidator` | "Entity must have 'instance of' statement" |
| Statement cardinality | `ProfileValidator` | "Entity can have max 1 'headquarters location' statement" |
| Value datatype | `fermenter` | "Value must be valid item QID" |
| Value constraint | `fermenter` | "Item must be from allowed list" |
| Qualifier presence | `fermenter` | "Statement must have 'street address' qualifier" |
| Reference constraint | `fermenter` | "Reference must include URL or stated-in" |

**Call Sequence:**
1. `ProfileValidator.validate_entity(entity, profile)`:
   - Check required statements present
   - Check statement cardinality (max_count)
   - For each statement, call `fermenter.validate_statement_comprehensive()`
   - Aggregate results
   - Return overall validation result

2. `fermenter.validate_statement_comprehensive(statement_data, statement_spec, context)`:
   - Validate value datatype
   - Validate value constraints (value lists, fixed values)
   - Validate qualifiers
   - Validate references
   - Return statement-level validation result

**Handoff:** Validation Agent to implement this integration after fermenter module core is complete.

---

## Testing Strategy

### Unit Tests (Atomic Validators)

**Coverage Requirements:**
- Each `validate_{datatype}()` function: 3-5 test cases
  - Valid input (pass)
  - Invalid type (fail)
  - Edge case (e.g., empty string, None, boundary values)
- Each `coerce_to_{datatype}()` function: 3-5 test cases
  - Successful coercion (various input types)
  - Coercion failure (raises ValueError)
  - Edge case handling

**Example Test:**
```python
def test_validate_item_with_qid_string():
    result = validate_item("Q12345")
    assert result.valid is True
    assert result.value == {"entity-type": "item", "id": "Q12345"}
    assert len(result.errors) == 0

def test_validate_item_with_invalid_format():
    result = validate_item("invalid_qid")
    assert result.valid is False
    assert "Invalid QID format" in result.errors[0]

def test_coerce_to_item_qid_from_uri():
    qid = coerce_to_item_qid("https://www.wikidata.org/entity/Q12345")
    assert qid == "Q12345"

def test_coerce_to_item_qid_from_dict():
    qid = coerce_to_item_qid({"entity-type": "item", "id": "Q67890"})
    assert qid == "Q67890"
```

### Integration Tests (Specification Processors)

**Coverage Requirements:**
- Each specification processor (Q23, Q26, Q28, Q31, Q43): 2-3 test cases
  - Successful application (pass)
  - Constraint violation (fail)
  - Edge case (e.g., missing value list, malformed reference)

**Example Test:**
```python
def test_apply_fixed_value_with_none_input():
    spec = SpecificationContext(
        spec_item_qid="Q23",
        spec_directive="apply fixed value",
        target_statement="instance_of"
    )
    result = apply_fixed_value(spec, value=None, fixed_value="Q55555")
    assert result.valid is True
    assert result.value == "Q55555"
    assert "Fixed value applied automatically" in result.warnings[0]

def test_validate_value_from_list_with_valid_qid():
    spec = SpecificationContext(
        spec_item_qid="Q43",
        spec_directive="use value list",
        target_statement="country",
        value_lists={"Q43": ["Q30", "Q145", "Q183"]}  # USA, UK, Germany
    )
    result = validate_value_from_list(spec, "Q30")
    assert result.valid is True
    assert result.value == "Q30"
```

### End-to-End Tests (Full Statement Validation)

**Coverage Requirements:**
- Comprehensive statement validation: 5-10 test cases covering:
  - Valid statement (all constraints satisfied)
  - Invalid value datatype
  - Missing required qualifier
  - Reference constraint violation
  - Multiple simultaneous errors (aggregation)

**Test Fixture Strategy:**
- Use real profile JSON from SpiritSafe test fixtures (`tests/fixtures/profiles/`)
- Mock value lists for Q28/Q43 (avoid SPARQL dependency in tests)
- Mock specification context with cached directives

---

## Performance Considerations

### Optimization Targets

**Value List Lookups:**
- **Current:** Linear search through list (O(n))
- **Optimization:** Index value lists by QID (O(1) lookup)
  - Build index on first load: `{qid: item_data for item in value_list}`
  - Cache index in memory for session lifetime

**Recursive Qualifier Validation:**
- **Current:** Depth-first recursion (may be slow for deeply nested qualifiers)
- **Optimization:** Depth limit (default 2 levels, configurable)
  - Track recursion depth in validation context
  - Skip validation beyond limit with warning

**SPARQL Query Execution:**
- **Current:** Synchronous HTTP requests (blocking)
- **Optimization:** Async execution with timeout (future enhancement)
  - Use `asyncio` or `httpx` for async SPARQL queries
  - Timeout after 10 seconds, fall back to cache

### Caching Strategy

**In-Memory Cache:**
- Value lists loaded once per session, stored in `SpecificationContext.value_lists`
- Specification directives (P191 text) cached in manifest, not re-fetched

**Disk Cache:**
- SpiritSafe JSON cache used as fallback when SPARQL unavailable
- TTL: 30 days (configurable via environment variable)

**Cache Invalidation:**
- Manual: CLI command `poetry run gkc spirit-safe refresh-value-lists`
- Automatic: Future enhancement (webhook trigger from DD Wikibase on profile update)

---

## GitHub Issue Triage Mapping (2026-03-09)

### Closed as OBE (Superseded by V2 Reset)

- #120 Design and plan fermenter module (replaced by this FermenterV1 execution plan)

### Kept Open and Mapped to FermenterV1 Execution

- **Core validation/coercion contracts:** #102, #103, #104, #105, #106, #107
- **Entity and packet validation layers:** #109, #110, #111, #112, #113
- **Data Distillery semantic integration track:** #121, #122, #123, #124, #125, #126, #127
- **Compatibility and lifecycle policy:** #99
- **Follow-on specialized resolver work:** #97

### Execution Sequencing Notes

- Prioritize #102-#107 first (atomic contracts and datatype handlers), then #109-#113 (entity/packet validation), then #121-#126 (semantic online/offline integration and parity hardening).
- Keep #127 as the controlling umbrella and link implementation PRs to child issues for traceability.

---

## Open Questions & Decisions Needed

1. **Value List Truncation:**
   - Current proposal: 10,000 items max in SpiritSafe cache
   - Question: Is this sufficient for largest value lists (e.g., all countries, all languages)?
   - Decision needed: Increase limit, or implement pagination/streaming for large lists?

2. **SPARQL Endpoint Configuration:**
   - Question: Where is SPARQL endpoint URL configured? (gkc config file, environment variable, profile metadata?)
   - Decision needed: Document configuration strategy in runtime_config.py

3. **Qualifier Recursion Limit:**
   - Current proposal: 2 levels depth
   - Question: Are there real-world use cases requiring deeper nesting?
   - Decision needed: Make configurable, or hardcode to 2?

4. **Fuzzy Label Matching:**
   - Current implementation: Exact + prefix matching
   - Question: Add Levenshtein distance matching for typo tolerance?
   - Decision needed: Complexity vs. accuracy trade-off

5. **Commons Media File Verification:**
   - Current proposal: Optional API check (expensive, skip by default)
   - Question: Should wizard UI always verify file existence before submission, or only backend validation?
   - Decision needed: Coordinate with Wizard Engineer on UX requirements

---

## Next Actions (Immediate)

**Validation Agent:**
1. Implement 8 primitive datatype validators (`validate_item`, `validate_monolingualtext`, `validate_url`, `validate_string`, `validate_time`, `validate_quantity`, `validate_globecoordinate`, `validate_commonsMedia`)
2. Implement 8 primitive datatype coercers (`coerce_to_*` functions)
3. Implement 5 specification processors (`apply_fixed_value`, `route_value_to_reference`, `validate_reference_constraint`, `validate_value_from_list`, `validate_expected_qualifiers`)
4. Write unit tests for all validators/coercers (target: 80% coverage)
5. Integrate with `ProfileValidator` via `validate_statement_comprehensive()` orchestrator

**Profile Architect (support):**
1. Finalize value list JSON schema (review truncation policy)
2. Document SPARQL extraction workflow for `gkc.spirit_safe` module
3. Provide example value list JSON fixtures for testing

**Wizard Engineer (after fermenter core complete):**
1. Integrate fermenter validators into wizard form validation (client-side + server-side)
2. Display validation errors/warnings in form UI
3. Implement type-ahead search with value list constraints

---

**Document Version:** 1.1  
**Last Updated:** 2026-03-09  
**Next Review:** After fermenter core implementation (8 datatypes + 5 specifications functional)
