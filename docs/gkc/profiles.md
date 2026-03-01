# GKC Entity Profiles: Construction and Reference

**Plain Meaning:** A comprehensive guide to building, structuring, and validating YAML profiles that define how **GKC Entities** are captured, validated, and transformed in the Global Knowledge Commons.

## Overview

Entity profiles are declarative, machine-readable definitions of entity structures that bridge raw user input and refined, cross-platform entity models. They encode:

- **What statements** make up an entity (properties and their datatypes)
- **How statements relate** to Wikidata properties and external systems
- **What constraints** apply to each statement's values
- **How to validate** incoming data against those constraints
- **How to reference** sources and maintain provenance

Profiles are YAML files that live in the SpiritSafe profile registry (`profiles/<ProfileID>/profile.yaml`) and are managed in version control in the dedicated SpiritSafe repository. They serve as both human-readable documentation and executable specifications that drive **two distinct workflows**:

1. **GKC Wizards** — Interactive, multi-step data entry interfaces where curators create and edit entities with guided input, validation, and choice lists
2. **Validation & Coercion** — Programmatic validation of existing data (from Wikidata, spreadsheets, APIs) using dynamically-generated Pydantic models

This document focuses primarily on how to build profiles that drive successful wizard experiences while maintaining the validation rigor needed for bulk data processing.

---

## Implementation Status

The following profile capabilities are implemented and stable in current GKC architecture:

- YAML profile loading into typed profile models.
- Statement, qualifier, reference, and datatype validation structures.
- SPARQL allowed-items extraction and hydration workflows with fallback behavior.
- Profile path and query reference resolution aligned to SpiritSafe registrant layout.

For architecture-level implementation details, see:

- [Architecture Overview](../architecture/index.md)
- [Profile Loading Architecture](../architecture/profile-loading.md)
- [SpiritSafe Infrastructure](../architecture/spiritsafe-infrastructure.md)
- [Validation Architecture](../architecture/validation-architecture.md)

## Theoretical Design Notes

Some sections in this document describe wizard behavior and curator flow targets that are directionally committed but not fully implemented end-to-end in a single production UI stack.

Treat those sections as architecture guidance for future Wizard Engineer and Validation Agent implementation work, not as guaranteed current runtime behavior.

---

## Profiles and GKC Wizards

**GKC Wizards** are the primary curator-facing interface for working with entity profiles. A wizard is a multi-step, guided workflow that transforms a YAML profile into an interactive data-entry experience. Every field, validation rule, prompt, and choice list comes directly from the profile—wizards have no hardcoded forms or entity-specific logic.

### The 5-Step Wizard Structure

Every wizard follows a consistent 5-step progression designed with a curator mental model in mind:

#### **Step 1: Plan of Action**
A summary screen that explains:

- What type of entity will be created (drawn from profile `name` and `description`)
- What the wizard will ask for (metadata, required statements, optional statements, cross-platform links)
- **Secondary entities** that may need to be created or linked (e.g., government positions, related organizations)
- How long the process will take and what sources/references the curator should have ready

This step sets expectations and helps curators gather the right information before starting data entry.

#### **Step 2: Basic Identification**
Primary entity metadata:

- **Labels** (one per language, required languages determined by profile)
- **Descriptions** (one per language, must be distinctive and disambiguating)
- **Aliases** (multiple per language, includes alternative names, historical names)

Each field shows `input_prompt` and `guidance` from the profile. Required languages are validated before progression.

#### **Step 3: Statements**
All statements about the entity:

- Profile's community-curated statement ordering determines presentation sequence
- **Any statement can be skipped** with explicit "Skip this statement" option
- Each statement includes:
  - Value input (widget determined by datatype)
  - **Qualifiers** (nested under statement)
  - **References** (behavior.references determines whether shown, auto-derived, or hidden)
  - "Add another" button for multi-count statements (`max_count > 1` or `max_count: null`)

Validation occurs per-field (on blur) and per-statement (when complete). **No validation blocks progression**—curators can advance even with incomplete data. Missing statements generate suggestions in the review step.

**Philosophy**: Following Wikidata/Wikipedia principles, curators can create minimal entities quickly and enhance them later. The wizard guides toward completeness but never forces it.

#### **Step 4: Cross-Platform Links**
Sitelinks and external platform connections:

- **Wikipedia articles** (per language, with conflict detection)
- **Wikimedia Commons** categories or files
- **OpenStreetMap** relations (for geographic entities)
- **Other wiki projects** as defined in profile `sitelinks` section

Each sitelink validates format and checks for uniqueness conflicts (one sitelink per language+project across all Wikidata).

#### **Step 5: Review & Validate**
Comprehensive summary and validation:

- **All collected data** grouped by section (metadata, statements, sitelinks)
- **What's missing**: Community-expected statements that were skipped (helps curators understand completeness)
- **Secondary entities identified** during statement entry (if any need creation, wizard offers to branch)
- **Full validation results**: errors (data type/format issues), warnings (conformance issues), suggestions (statements worth considering)
- **Quality score** and conformance indicators
- **Actions**:
  - Edit any section (returns to that step)
  - Export to JSON (save locally without shipping)
  - Ship to Wikidata (write via API, create Commons connections, update OSM if applicable)

**Curators can ship even with warnings and suggestions**—only true errors (malformed data) block shipping. Skipped statements appear as suggestions: "Consider adding: official website, member count" with quick-add options.

### How Profile Elements Map to Wizard Steps

| Profile Element | Wizard Step | Wizard Behavior |
|-----------------|-------------|------------------|
| `name`, `description` | Step 1 (Plan) | Displayed as "You will create..." summary |
| `labels`, `descriptions`, `aliases` | Step 2 (Identification) | Per-language inputs, required languages enforced |
| `statements` | Step 3 (Statements) | All statements presented in profile order, all skippable |
| `qualifiers` | Step 3 (nested) | Nested under parent statement |
| `references` | Step 3 (nested) | Behavior determined by `behavior.references` (auto-derived, editable, or hidden) |
| `sitelinks` | Step 4 (Links) | Per-project inputs, conflict validation |
| All data + validation | Step 5 (Review) | Summary view with validation report and community completeness suggestions |

### Profiles Used Without Wizards

Profiles also support **non-interactive workflows** where no wizard is involved:

- **Bulk validation**: Validate thousands of Wikidata items against a profile, generating conformance reports
- **Data coercion**: Normalize and transform data from external sources (spreadsheets, APIs) into Wikidata-conformant structures
- **Programmatic entity creation**: Generate entities from code without user interaction (e.g., automated bots)
- **Quality analysis**: Scan existing Wikidata content to identify gaps or constraint violations

In these workflows, profiles are loaded into dynamically-generated Pydantic models that provide validation and type coercion. The `validation_policy` and `behavior` settings still apply—for example, `behavior.references: auto_derive` will generate references automatically even in bulk operations.

**Key distinction**: Wizard-driven workflows are **curator-centric** (interactive, guided, with prompts and choice lists). Validation-driven workflows are **programmatic** (batch processing, no UI, focused on conformance checking).

---

## Profile Anatomy

A SpiritSafe YAML profile has this essential structure:

```yaml
name: Entity Type Name
description: >
  Multi-line description of what this profile represents
  and what kinds of entities it covers.

# Optional: Reusable reference patterns (via YAML anchors)
standard_reference: &standard_reference
  min_count: 1
  # ... reference structure

statements:
  - id: statement_identifier
    label: Human-readable label
    wikidata_property: P123  # Wikidata property ID
    type: statement           # Always "statement" for now
    max_count: 1              # null = unlimited
    validation_policy: allow_existing_nonconforming
    
    behavior:  # Optional: control processing across all GKC operations
      value: editable       # or fixed, hidden
      qualifiers: editable  # or hidden
      references: editable  # or auto_derive, hidden

    value:
      type: string  # Datatype
      constraints:  # Statement-level constraints
        - type: format
          pattern: '[A-Z0-9]+'

    qualifiers:  # (optional) properties that modify the main statement
      - id: qualifier_id
        label: Qualifier label
        wikidata_property: P456
        required: false
        value:
          type: item

    references:  # (optional) sources and citations
      required: true
      min_count: 1
      allowed:
        - id: source_id
          wikidata_property: P248
          type: item
          label: Stated in
```

### Top-level Keys

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| `name` | string | YES | Profile name displayed to users and in logs |
| `description` | string | YES | Multi-line explanation of profile scope |
| `statements` | array | YES | List of statement definitions |
| *Anchors* | any | NO | YAML anchors for reusable patterns (e.g., `&standard_reference`) |

### Statement Keys

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| `id` | string | YES | Unique identifier (snake_case) |
| `label` | string | YES | Human-readable display name |
| `input_prompt` | string | NO | Curator-facing prompt shown in wizard |
| `guidance` | string | NO | Extended help text for curators |
| `wikidata_property` | string | YES | Wikidata property ID (e.g., "P31") |
| `type` | string | YES | Always "statement" (for now) |
| `max_count` | int or null | NO | Max statements allowed (null = unlimited); determines "Add another" button visibility |
| `validation_policy` | enum | NO | How to handle existing data (see [Validation Policy](#validation-policy)) |
| `behavior` | object | NO | Universal processing rules for value, qualifiers, and references across all GKC operations (see [Statement Behavior](#statement-behavior)) |
| `entity_profile` | string | NO | Filename reference to another GKC Entity Profile for secondary entities (see [Secondary Entities](#secondary-entities-and-profile-references)); enables wizard chaining |
| `value` | object | YES | Value definition (datatype + constraints) |
| `qualifiers` | array | NO | Qualifier definitions (nested in wizard step 3) |
| `references` | object | NO | Reference definition (includes derivation rules) |

---

## Validation Policy

The `validation_policy` enum controls how strict validation is when working with existing Wikidata data, affecting both interactive wizard workflows and programmatic validation workflows.

**`validation_policy`** determines how strict validation is when working with existing Wikidata data.

#### `allow_existing_nonconforming` (Default, Recommended)

**What it means:**
- New data must conform to all profile constraints
- Existing data in Wikidata that doesn't conform is allowed to remain
- Validation warnings are issued for non-conforming existing data, but they don't block operations

**When to use:**
- Almost always—this is the recommended default
- When working with mature Wikidata items that may have legacy data
- When profile constraints are stricter than historical Wikidata practices
- When you want to improve data quality incrementally without breaking existing items

**Wizard behavior:**
- When editing existing items, pre-populated fields may show non-conforming data with warning indicators
- Curators can choose to fix warnings or leave them as-is
- New statements added during the wizard session should conform (warnings shown if not)
- Review step shows warnings for existing non-conforming data but **always allows shipping**
- Philosophy: Get the data in, refine it later

**Example:**
```yaml
statements:
  - id: instance_of
    wikidata_property: P31
    required: true
    validation_policy: allow_existing_nonconforming  # Existing items may have multiple P31 values
    max_count: 1  # But new items should only have one
```

#### `strict`

**What it means:**
- All data must conform to profile constraints, whether new or existing
- Non-conforming existing data triggers validation errors that block operations
- No tolerance for deviations from the profile

**When to use:**
- When working with newly-created entity types with no legacy data
- When profile constraints match established Wikidata community norms exactly
- When conformance is critical (e.g., regulatory compliance, legal requirements)
- When you control all existing data and can guarantee conformance

**Wizard behavior:**
- When editing existing items, non-conforming data triggers errors
- Curators see errors and are **strongly encouraged** to fix them before shipping
- Review step shows prominent error indicators but **still allows shipping** (with confirmation)
- Philosophy: Even in strict mode, contribution is more important than perfection

**Example:**
```yaml
statements:
  - id: headquarters_location
    wikidata_property: P159
    required: false
    validation_policy: strict  # When present, must have exactly the qualifiers we define
    max_count: 1
```

---

## Statement Behavior

The `behavior` object defines **universal processing rules** for how a statement is handled across all GKC operations—interactive wizards, bulk data imports, validation workflows, and programmatic entity creation. These are profile-level data transformation rules, not just UI presentation hints.

Each statement has three components that can be controlled independently:
1. **Value** (the main statement content)
2. **Qualifiers** (contextual modifiers on the statement)
3. **References** (source citations)

### Behavior Keys

```yaml
behavior:
  value: editable | fixed | hidden
  qualifiers: editable | hidden
  references: editable | auto_derive | hidden
```

#### `behavior.value`

Controls how the statement value is processed.

**`editable` (default):**
- User/process can set any valid value conforming to datatype constraints
- In wizards: full input widget shown based on datatype
- In bulk operations: value read from input data (CSV, JSON, etc.)

**`fixed`:**
- Value must match `value.fixed` - locked across all operations
- In wizards: shown as read-only badge with label (e.g., "federally recognized Native American tribe in the United States")
- In bulk operations: value auto-populated from profile, not expected in input data
- In validation: flags error if existing value doesn't match `value.fixed`

**`hidden`:**
- Statement not shown in forms or expected in bulk data
- Reserved for future use (computed values, deprecated fields)

**Example:**
```yaml
statements:
  - id: instance_of
    label: Instance of
    wikidata_property: P31
    
    behavior:
      value: fixed           # Value locked to Q7840353 in all contexts
      references: editable    # References manually provided
    
    value:
      type: item
      fixed: Q7840353
      label: federally recognized Native American tribe in the United States
```

#### `behavior.qualifiers`

Controls how qualifiers are processed.

**`editable` (default):**
- User/process can add qualifiers as defined in `qualifiers` array
- In wizards: qualifier inputs shown nested under statement
- In bulk operations: qualifiers read from input data

**`hidden`:**
- Qualifiers not shown in forms or expected in bulk data
- Use when qualifiers exist in schema but shouldn't be collected for this entity type

**Example:**
```yaml
statements:
  - id: official_website
    wikidata_property: P856
    
    behavior:
      qualifiers: editable  # Show language_of_work qualifier
    
    qualifiers:
      - id: language_of_work
        wikidata_property: P407
        value:
          type: item
          fixed: Q1860  # English
```

#### `behavior.references`

Controls how references are processed and where their values come from.

**`editable` (default):**
- User/process manually provides all reference details
- In wizards: full reference entry controls shown (type selector + value inputs)
- In bulk operations: references read from input data
- All `allowed` reference types available for selection

**`auto_derive`:**
- References automatically generated using `value_source` rules
- In wizards: reference section hidden or shows "auto-generated" indicator
- In bulk operations: references created automatically from statement value
- Common pattern: official website URL becomes reference URL

**`hidden`:**
- No references shown, collected, or required
- Use sparingly—most Wikidata statements should have references

**Example - Auto-derived references:**
```yaml
statements:
  - id: official_website
    wikidata_property: P856
    
    behavior:
      value: editable
      references: auto_derive  # Generate P854 from P856 automatically
    
    value:
      type: url
    
    references:
      min_count: 1
      target:
        id: reference_url
        wikidata_property: P854
        type: url
        value_source: statement_value  # Derivation rule: P854 = P856
```

**Example - Manual references with choice:**
```yaml
statements:
  - id: member_count
    wikidata_property: P2124
    
    behavior:
      references: editable  # Curator chooses reference type
    
    value:
      type: quantity
    
    references:
      min_count: 1
      allowed:
        - id: stated_in
          wikidata_property: P248
          type: item
        - id: reference_url
          wikidata_property: P854
          type: url
```

### How Behavior Works Across Contexts

**Interactive Wizard:**
- `behavior.value: fixed` → renders as read-only badge
- `behavior.references: auto_derive` → hides reference input, shows "auto-generated" note
- `behavior.references: editable` → shows reference type selector and value inputs

**Bulk CSV Import:**
```csv
qid,official_website
Q123,https://cherokeenation.com
Q456,https://navajo-nsn.gov
```

Profile processor reads `behavior.references: auto_derive` and automatically:
- Creates P856 statement with URL from CSV
- Creates P854 reference with same URL (no reference column needed in CSV)

**Validation Workflow:**
```python
validator.check_entity(qid="Q789", profile="TribalGovernmentUS")
```

Validator reads `behavior`:
- Checks `behavior.value: fixed` on instance_of → validates P31 = Q7840353
- Checks `behavior.references: auto_derive` on official_website → if P856 exists without P854 or P854 ≠ P856, flags non-conforming
- Applies rules consistently regardless of how entity was created

### Default Behavior

If `behavior` is omitted, defaults are:

```yaml
behavior:
  value: editable         # Unless value.fixed is set, then value: fixed
  qualifiers: editable    # If qualifiers array defined
  references: editable    # Unless target.value_source set, then auto_derive
```

Profile authors can omit `behavior` for standard statements and only specify it when special handling is needed.

---

## Datatypes Reference

SpiritSafe supports 9 core Wikidata datatypes. Each has specific use cases, constraint options, and validation behaviors.

### 1. Item (`item`)

**Wikidata type:** `wikibase-entityid`  
**Use cases:** entity references, enums with bounded choice lists  
**Form widget:** Autocomplete or select dropdown

```yaml
value:
  type: item
  fixed: Q5  # (optional) Lock to specific item
  label: human
  constraints:
    - type: allowed_items
      source: sparql
      query: SELECT ?item ?itemLabel WHERE { ... }
```

**Key constraint types:**
- `allowed_items` - SPARQL query for choice list
- `fixed` - item value must be exactly this QID

**Validation:** Checks that value is a valid QID and (if specified) exists in choice list.

---

### 2. String (`string`)

**Wikidata type:** `string`  
**Use cases:** Names, identifiers, free text  
**Form widget:** Text input

```yaml
value:
  type: string
  constraints:
    - type: format
      pattern: '^[A-Z0-9\-]+$'
    - type: length
      min_length: 1
      max_length: 255
```

**Key constraint types:**
- `format` - regex pattern for validation
- `length` - min/max string length

**Validation:** Matches against regex pattern and length bounds.

---

### 3. URL (`url`)

**Wikidata type:** `string` (with datatype="url")  
**Use cases:** Website links, reference URLs, external system links  
**Form widget:** URL input (with validation)

```yaml
value:
  type: url
  constraints:
    - type: url_scheme
      allowed_schemes: ['http', 'https']
    - type: url_validation
      validate: true  # Check URL returns valid HTTP response
```

**Key constraint types:**
- `url_scheme` - Allowed protocols (http, https, ftp, etc.)
- `url_validation` - HTTP HEAD validation

**Validation:** Parses as valid URL and optionally checks HTTP response.

---

### 4. Quantity (`quantity`)

**Wikidata type:** `quantity`  
**Use cases:** Counts, measurements, amounts  
**Form widget:** Number input + unit selector

```yaml
value:
  type: quantity
  constraints:
    - type: integer_only
      description: Must be whole number (no decimals)
    - type: range
      min_value: 0
      max_value: 10000
    - type: unit
      default_unit: Q199  # Number (dimensionless)
      allowed_units:
        - Q199  # Number
        - Q11588322  # Second
```

**Key constraint types:**
- `integer_only` - No decimal places
- `range` - Min/max numeric bounds
- `unit` - Unit system specification

**Validation:** Checks numeric type and value bounds. Converts to Wikidata quantity format with unit and precision.

---

### 5. Time (`time`)

**Wikidata type:** `time`  
**Use cases:** Dates, years, temporal ranges  
**Form widget:** Date picker / text input with fuzzy parsing

```yaml
value:
  type: time
  constraints:
    - type: precision
      allowed_precisions: [9, 10, 11]  # year, month, day
      auto_derive: true  # Infer precision from input format
    - type: calendar_model
      default: Q1985727  # Gregorian calendar
      allowed_calendars:
        - Q1985727  # Gregorian
        - Q12138    # Julian (historical)
    - type: format
      patterns:
        - 'YYYY'           # Year only
        - 'YYYY-MM'        # Year-month
        - 'YYYY-MM-DD'     # Full date
```

**Key constraint types:**
- `precision` - Allowed precision levels (year/month/day/hour/etc.)
- `calendar_model` - Calendar system (Gregorian vs. Julian)
- `auto_derive` - Automatically determine precision from input

**Validation:** Parses various date formats, derives precision, normalizes to Wikidata time format `+YYYY-MM-DDTHH:MM:SSZ`.

---

### 6. Monolingualtext (`monolingualtext`)

**Wikidata type:** `monolingualtext`  
**Use cases:** Text in specific languages (names, descriptions, addresses)  
**Form widget:** Text input + language selector

```yaml
value:
  type: monolingualtext
  constraints:
    - type: language_required
      description: Must specify language code
    - type: valid_language_code
      description: Must be valid Wikimedia language code
```

**Key constraint types:**
- `language_required` - Language code is mandatory
- `valid_language_code` - Must match Wikimedia language code list

**Storage:** Internally stored as `{text: string, language: string}` tuple.

**Validation:** Validates language code against Wikimedia language list. Normalizes text and language code.

---

### 7. Globecoordinate (`globecoordinate`)

**Wikidata type:** `globecoordinate`  
**Use cases:** Geographic coordinates, locations, buildings  
**Form widget:** Map picker or lat/long input boxes

```yaml
value:
  type: globecoordinate
  constraints:
    - type: valid_coordinates
      description: Latitude -90 to 90, longitude -180 to 180
    - type: precision
      min_precision: 0.0001   # ~11m (building-level)
      max_precision: 0.01     # ~1km (city-level)
    - type: globe
      default: Q2  # Earth
      allowed_globes:
        - Q2  # Earth
```

**Key constraint types:**
- `valid_coordinates` - Latitude/longitude bounds
- `precision` - Coordinate precision bounds (in degrees)
- `globe` - Which celestial body (Earth, Mars, etc.)

**Storage:** Internally stored as `{latitude: float, longitude: float, precision: float, globe: string}`.

**Validation:** Checks coordinate bounds and precision range. Converts to Wikidata globe coordinate format.

---

### 8. External-id (`external-id`)

**Wikidata type:** `external-id` (string with special handling)  
**Use cases:** IDs from external systems (OSM, DOI, ISBN, etc.)  
**Form widget:** Text input (with validation against external system)

```yaml
value:
  type: external-id
  constraints:
    - type: format
      description: Pattern for valid ID format
      pattern: '^\d+$'  # Numeric only
    - type: formatter_url
      description: Wikidata property formatter URL
      url_pattern: 'http://www.openstreetmap.org/relation/$1'
      validate: true
      validation_method: http_head  # Check URL validity
    - type: external_system
      system: OpenStreetMap
      url_base: 'http://www.openstreetmap.org/relation/'
```

**Key constraint types:**
- `format` - Regex pattern for ID format
- `formatter_url` - Wikidata P1630 (formatter URL) pattern
- `external_system` - External system metadata

**Validation:** Matches regex pattern. Optionally validates formatted URL with HTTP HEAD request.

**Note:** External IDs are considered *declarative* statements from data curators and typically don't require references.

---

### 9. Commons Media (`commonsMedia`)

**Wikidata type:** `commonsMedia` (string filename with special handling)  
**Use cases:** Media files on Wikimedia Commons (images, audio, video)  
**Form widget:** File selector / file upload stub

```yaml
value:
  type: commonsMedia
  constraints:
    - type: file_exists
      description: File must exist on Wikimedia Commons
      validate: true
      validation_method: commons_api
    - type: file_type
      description: Allowed file formats
      allowed_types:
        - 'image/svg+xml'
        - 'image/png'
        - 'image/jpeg'
    - type: wikidata_constraint
      description: Commons file must have specific properties
      required_property: P6216  # License
```

**Key constraint types:**
- `file_exists` - Check file exists on Commons
- `file_type` - MIME type restrictions
- `wikidata_constraint` - Required properties on Commons file

**Storage:** Stored as filename string (e.g., "Flag.svg").

**Validation:** Checks file exists on Commons via API. Validates file format and licensing metadata.

---

## Constraints Reference

Constraints are the validation rules applied to statement values. They enforce business logic, external system compliance, and data quality.

### Universal Constraint Properties

All constraints share these properties:

```yaml
- type: constraint_type_name     # Identifier (required)
  description: Human-readable    # Description (required)
  # + type-specific properties
```

### Common Constraint Patterns

#### Format Constraints (Regex Validation)

```yaml
- type: format
  pattern: '^[A-Z0-9]{3,10}$'  # Alphanumeric, 3-10 chars
  message: 'Must be 3-10 alphanumeric characters'
```

#### Range Constraints (Numeric Bounds)

```yaml
- type: range
  min_value: 0
  max_value: 100
  message: 'Must be between 0 and 100'
```

#### Choice List Constraints (SPARQL-backed)

```yaml
- type: allowed_items
  source: sparql
  query: |
    SELECT ?item ?itemLabel
    WHERE {
      ?item wdt:P31 wd:Q5 .
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
    }
  refresh: daily  # or manual, weekly, on_release
  fallback_items:
    - id: Q123
      label: Fallback option
```

#### URL Validation

```yaml
- type: formatter_url
  url_pattern: 'http://example.com/item/$1'
  validate: true
  validation_method: http_head
  timeout: 10  # seconds
```

---

## References: Sourcing and Provenance

References document the origin and authority of statements. Wikidata supports multiple reference patterns:

### Reference Structure

```yaml
references:
  required: true              # Are references mandatory?
  min_count: 1                # Minimum number of references
  validation_policy: allow_existing_nonconforming
  form_policy: target_only    # or show_all

  # Option 1: Single target (exactly one reference type allowed)
  target:
    id: reference_id
    wikidata_property: P248   # Stated in
    type: item
    label: Stated in

  # Option 2: Multiple allowed types
  allowed:
    - id: stated_in
      wikidata_property: P248
      type: item
      label: Stated in
    - id: reference_url
      wikidata_property: P854
      type: url
      label: Reference URL
```

### Reusable Reference Patterns with YAML Anchors

Instead of repeating reference structures, define them once and reuse:

```yaml
# Define at top of profile
standard_reference: &standard_reference
  min_count: 1
  validation_policy: allow_existing_nonconforming
  allowed:
    - id: stated_in
      wikidata_property: P248
      type: item
      label: Stated in
    - id: reference_url
      wikidata_property: P854
      type: url
      label: Reference URL

# Use anywhere in statements with editable references behavior
statements:
  - id: member_count
    wikidata_property: P2124
    behavior:
      references: editable  # Curator chooses reference type
    value:
      type: quantity
    references: *standard_reference
```

This pattern dramatically reduces duplication and makes profile maintenance easier.

---

## Qualifiers: Statement Modifiers

Qualifiers are properties that modify or provide context for a main statement. They appear alongside the statement value in Wikidata's data model.

### Qualifier Structure

```yaml
qualifiers:
  - id: qualifier_id
    label: Human-readable label
    wikidata_property: P123
    required: false        # Is qualifier mandatory?
    max_count: 1           # null = unlimited

    value:
      type: string         # Qualifier's datatype
      constraints: []
```

### Common Qualifier Examples

**Point in time** (P585) - When a statement is true:
```yaml
- id: point_in_time
  label: Point in time
  wikidata_property: P585
  required: true
  max_count: 1
  value:
    type: time
```

**Language of work or name** (P407) - Language for text:
```yaml
- id: language_of_work
  label: Language of work or name
  wikidata_property: P407
  required: false
  max_count: 1
  value:
    type: item
    allowed_items:
      source: sparql
      query: SELECT ?item ?itemLabel WHERE { ... }
```

**Criterion used** (P1013) - How location was determined:
```yaml
- id: criterion_used
  label: Criterion used
  wikidata_property: P1013
  required: false
  value:
    type: item
```

---

## Entity Metadata: Labels, Descriptions, Aliases, and Sitelinks

In addition to statements (claims), Wikidata items have **entity-level metadata** that provides context and discoverability:

- **Labels:** The primary name in each language (only one per language)
- **Descriptions:** Short, distinctive descriptions (only one per language)
- **Aliases:** Alternative names, historical names, abbreviations (multiple per language)
- **Sitelinks:** Links to Wikipedia, Wikimedia Commons, and other wiki projects

SpiritSafe profiles can optionally declare curator guidance for these metadata elements to ensure consistency and quality across language versions.

### Metadata in Wizard Workflows

Entity metadata maps to **Wizard Step 2 (Basic Identification)** for labels/descriptions/aliases and **Step 4 (Cross-Platform Links)** for sitelinks. The wizard renders these sections based on what's defined in the profile.

### Labels

Labels are the primary identifiers for items in human-readable form. Each language gets exactly one label.

```yaml
labels:
  en:
    label: Label
    description: The primary name by which this entity is known.
    required: true
    guidance: |
      Use the name that the tribe uses in referring to itself as the primary label.
      Check official sources and tribal government websites before setting.
  
  es:
    label: Label (Spanish)
    description: The entity name in Spanish.
    required: false
    guidance: |
      Use official Spanish names where available, preferring tribal self-designations.
```

**Design notes:**
- **One per language:** Wikidata enforces this strictly—a label is immutable within a language
- **Statement ordering:** Place commonly expected languages first in the profile to set curator expectations
- **Guidance:** Include curator instructions on naming conventions and authority sources

### Descriptions

Descriptions disambiguate items when there are multiple with the same or similar labels. They should be concise and contextual.

```yaml
descriptions:
  en:
    label: Description
    description: A short, distinctive description to disambiguate this entity.
    guidance: |
      Format: "federally recognized Native American tribe based in [region/state]"
      Example: "federally recognized Native American tribe based in Oklahoma"
      Keep under 250 characters. Use present tense when possible.
  
  fr:
    label: Description (French)
    description: La description en français.
    required: false
    guidance: |
      Translate the English description or write a naturally-phrased French equivalent.
```

**Design notes:**
- **Disambiguation:** Should help distinguish this item from others with same/similar label
- **Consistency:** Use consistent language and phrasing across language versions
- **Conciseness:** Aim for 50–150 characters; under 250 is a strict limit

### Aliases

Aliases capture alternative names: historical names, abbreviations, informal names, names in other languages, transliterations, etc.

```yaml
aliases:
  en:
    label: Aliases
    description: Alternative names by which this entity is known or has been referred to.
    required: false
    guidance: |
      Include official alternative names, historical names, acronyms, and colloquial variants.
      For tribes: include the U.S. Government official name if different from self-designation.
      Example aliases:
        - "Northern Band of Paiute Indians"
        - "Northern Paiute"
        - "Kucedika"
    examples:
      - "Northern Band"
      - "Historic name from federal recognition document"
      - "Colloquial short form"
```

**Design notes:**
- **No uniqueness constraint:** Many items can have the same alias
- **Multiple per language:** Aliases are not limited (unlike labels/descriptions)
- **Type-specific guidance:** Tribes → government names; places → historical names; organizations → acronyms
- **Bidirectional matching:** Aliases improve discoverability in search

### Sitelinks

Sitelinks are references to articles in Wikimedia projects (Wikipedia, Wikimedia Commons, etc.) in different languages. They establish the "interlinking" between language versions.

```yaml
sitelinks:
  required: false
  validation_policy: allow_existing_nonconforming
  guidance: |
    Sitelinks connect this Wikidata item to Wikipedia articles and other Wikimedia projects.
    IMPORTANT: Each language+project combination can only exist on ONE Wikidata item.
    Check for conflicts before adding any sitelink. The Wikidata API will reject duplicates.
  
  languages:
    en:
      project: wikipedia
      description: English Wikipedia article
      required: false
      guidance: |
        Article title should match the item label or follow Wikipedia naming conventions.
        If an article exists, add it here to improve discoverability.
      
    es:
      project: wikipedia
      description: Spanish Wikipedia article
      required: false
      guidance: |
        Add if this entity has significant coverage in Spanish Wikipedia.
    
    commons:
      project: commons
      description: Wikimedia Commons entity (for media files)
      required: false
      guidance: |
        Use only for entities that deserve a category or page on Commons (cultural institutions, 
        notable historical figures, geographic features with associated media collections).
```

**Design notes:**
- **Uniqueness constraint:** Wikidata enforces one sitelink per language+project combination across ALL items
- **Validation policy:** Use `allow_existing_nonconforming` to prevent blocking item creation when conflicts exist
- **Project scope:** Limit to projects with active communities (Wikipedia, Commons, etc.)
- **Conflict detection:** Curators should verify no conflicting item already links to target article before adding
- **Wizard rendering:** Sitelinks appear in Step 4 (Cross-Platform Links) with conflict validation

---

## Secondary Entities and Profile References

Many entity types naturally reference **secondary entities**—related entities of different types that need their own profiles. For example:

- A **Federally Recognized Tribe** profile might link to:
  - "Office held by head of state" (a position/role entity)
  - "Headquarters location" (a geographic entity)
  
- A **University** profile might link to:
  - "Founded by" (person or organization entities)
  - "Academic department" entities
  - "Campus" (geographic entities)

When a statement references another entity that should be managed by its own profile, use the **`entity_profile`** key at the statement level to link to that profile.

### Profile Reference Syntax

The `entity_profile` field contains a **filename reference** (without extension) to another profile registered in the SpiritSafe:

```yaml
statements:
  - id: office_held_by_head_of_state
    label: Office held by head of state
    wikidata_property: P1906
    type: statement
    entity_profile: OfficeHeldByHeadOfState  # Filename reference (no .yaml extension)
    
    value:
      type: item
    
    references: *standard_reference
```

**Key design points:**
- `entity_profile` is specified at the **statement level**, not the value level
- Value is always `type: item` (Wikidata entity reference)
- Filename reference uses PascalCase without file extension
- SpiritSafe CI enforces uniqueness of profile filenames across the repository

### How Profile References Work in Wizards

**During Wizard Step 1 (Plan of Action):**
- Wizard scans all statements for `entity_profile` keys
- Lists secondary entity types that may need creation: "You may also create or link to: Office Held by Head of State"
- Provides context: "If the entity doesn't exist in Wikidata, the wizard can help you create it"

**During Wizard Step 3 (Statements):**
- When curator encounters a statement with `entity_profile`, the wizard **always** shows:
  - **Option 1:** Select existing item (QID) from Wikidata (standard item selection widget)
  - **Option 2:** "Create new [entity type]" button (always visible when `entity_profile` is present)
- If curator chooses "Create new":
  - Sub-wizard launches using the linked profile (full 5-step workflow with summaries)
  - Curator completes the secondary entity creation
  - Sub-wizard final summary offers: "Create another [entity type]" or "Return to [primary entity] wizard"
  - Returns to main wizard with new entity's temporary ID populated
  - Secondary entity is flagged for creation alongside primary entity

**During Wizard Step 5 (Review):**
- Section shows "Secondary entities to be created" with:
  - List of new entities created during workflow
  - Summary of each (label, type, key statements)
  - Option to edit or remove before shipping
- When shipped, all entities are created in dependency order (secondary entities first, then primary)

**Note on sub-wizard design:** Sub-wizards follow the same 5-step structure as primary wizards, including Plan of Action and Review screens. Post-MVP, sub-wizards may themselves spawn tertiary entity creation (nested wizard chains).

### When to Use Profile References

**Use `entity_profile` when:**
- The referenced entity is complex enough to warrant its own profile
- Curators may need to create these entities during workflow (not just link to existing)
- The entity type has specific validation rules or statement patterns
- You want wizard support for creating related entities inline with full workflow support

**Don't use `entity_profile` when:**
- The entity is generic and well-established in Wikidata (e.g., "country" or "language")
- The entity is unlikely to be created by curators (only linked to existing items)
- A simple choice list is sufficient (`allowed_items` with SPARQL query)
- The relationship is to a person or other entity managed through different workflows

### Example: Tribal Government with Position Entities

```yaml
# TribalGovernmentUS.yaml
statements:
  - id: head_of_government
    label: Head of government
    wikidata_property: P6
    value:
      type: item
      # No entity_profile - this links to a person, managed by a different workflow
    references: *standard_reference
  
  - id: office_held_by_head_of_state
    label: Office held by head of state
    wikidata_property: P1906
    entity_profile: OfficeHeldByHeadOfState  # Links to secondary entity profile
    guidance: >
      This is the office itself (e.g., "Principal Chief of the Cherokee Nation"),
      not the person holding the office.
    value:
      type: item
    references: *standard_reference
```

In this pattern:
- `head_of_government` (P6) links to a person (QID) - no special handling needed
- `office_held_by_head_of_state` (P1906) links to an office entity that may need creation - wizard **always** shows "Create new" button

---

## Best Practices

### 1. Design Profiles for Curator Mental Models

Profiles should align with how curators think about entities, not how developers think about code. The wizard steps (Plan → Identification → Statements → Links → Review) mirror curator workflows—design profiles to support that flow.

**Wizard-aware design:**
- Order statements to reflect community expectations—most important statements first in the YAML
- All statements are technically optional; communities aim to eventually fill all agreed-upon statements
- Use clear `input_prompt` text that guides curators at data-entry time
- Provide `guidance` for fields that need context (authority sources, formatting conventions, implications of not providing)
- Group semantically related statements together in the YAML (they'll appear together in Step 3)
- Use `entity_profile` for secondary entities that curators may need to create inline
- **Philosophy**: Support incremental contribution—minimal viable entities (labels + instance_of) can be enhanced later

### 2. Keep Profiles Focused and Cohesive

A profile should represent a single, well-defined entity type. Don't try to combine multiple unrelated entity types into one profile.

**Good:**
```yaml
name: Federally Recognized Tribe
description: Native American tribes in the United States...
```

**Bad:**
```yaml
name: Native American Entities
description: Tribes, nations, organizations, and cultural groups...
```

### 2. Use Reusable Patterns

Define common patterns once at the top and reuse them via YAML anchors.

```yaml
# Define standard_reference, standard_source_qualifier, etc.
standard_reference: &standard_reference
  # ...

# Then use in every statement that needs it
statements:
  - id: ...; references: *standard_reference
```

### 3. Document Constraints Clearly

Each constraint should have a clear `description` that explains both *what* it does and *why*:

```yaml
constraints:
  - type: format
    pattern: '^\d+$'
    description: 'OSM relation IDs are numeric only'  # Good
  - type: format
    pattern: '^\d+$'  # Bad - no explanation
```

### 4. Choose Validation Policy and Behavior Intentionally

**For validation_policy:**
- Use `allow_existing_nonconforming` (default) unless you have a specific reason not to
- Use `strict` only when conformance is critical and you control all existing data

**For behavior:**
- Use `behavior.references: auto_derive` when references are predictable and can be derived from statement value (reduces curator work, applies universally)
- Use `behavior.references: editable` when curators need flexibility in choosing reference types
- Use `behavior.value: fixed` when all entities of this type share the same value (e.g., instance_of classification)

```yaml
# Example: locked value with editable references
behavior:
  value: fixed
  references: editable

value:
  fixed: Q7840353
  label: federally recognized Native American tribe

# Example: editable value with auto-derived references
behavior:
  references: auto_derive

value:
  type: url

references:
  target:
    value_source: statement_value  # URL becomes its own reference
```

### 5. Leverage SPARQL for Choice Lists

Instead of hardcoding choices, query Wikidata dynamically:

```yaml
allowed_items:
  source: sparql
  query: |
    PREFIX wd: <http://www.wikidata.org/entity/>
    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    
    SELECT ?item ?itemLabel
    WHERE {
      ?item wdt:P31 wd:Q6581097 .  # Administrative territory
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
    }
```

### 6. Use Explicit Prefixes in SPARQL Queries

Since profiles may be used with alternate SPARQL endpoints (Qlever, Virtuoso), use explicit prefixes:

```yaml
query: |
  PREFIX wd: <http://www.wikidata.org/entity/>
  PREFIX wdt: <http://www.wikidata.org/prop/direct/>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
  
  SELECT ?item ?itemLabel
  WHERE {
    ?item wdt:P31 wd:Q6581097 ;
          rdfs:label ?itemLabel .
    FILTER(LANG(?itemLabel) = "en")
  }
```

Avoid `SERVICE wikibase:label` which only works on WDQS.

### 7. Set Reasonable Refresh Policies for Choice Lists

```yaml
refresh: manual      # Check manually when updated
refresh: daily       # Check once per day
refresh: weekly      # Check once per week
refresh: on_release  # Check on new Wikidata releases
```

Use `manual` during development, `daily` or `weekly` for production.

### 8. Make References Required Where Domain-Appropriate

External IDs typically don't need references (they're declarations). But facts that can be disputed should have references:

```yaml
# No references needed - it's an identifier
- id: osm_relation_id
  # ...
  # No references block

# References required - it's a factual claim
- id: headquarters_location
  # ...
  references: *standard_reference
```

### 9. Test Profiles With Wizard Workflows

The best way to validate a profile is to walk through the wizard it generates:

1. Launch wizard with profile: `gkc profile form --profile YourProfile --new`
2. Walk through all 5 steps as a curator would
3. Check:
   - Are `input_prompt` messages clear and helpful?
   - Does statement ordering reflect community priorities?
   - Can you create a minimal viable entity by skipping most statements?
   - Are choice lists populated and relevant?
   - Does `behavior.references: auto_derive` work correctly and reduce curator burden?
   - Does `behavior.value: fixed` display appropriately as read-only?
   - Do secondary entities (`entity_profile`) appear at the right time with "Create new" option?
   - Is `guidance` text helpful for understanding implications of skipping statements?
4. Test the incremental workflow:
   - Create minimal entity (labels + instance_of only)
   - "Ship" it to see if review step allows minimal data
   - Return and enhance with more statements
5. Iterate based on curator experience, not code convenience

---

## Complete Example: Federally Recognized Tribe Profile

Here's the complete tribal government profile used throughout this phase:

```yaml
name: Federally Recognized Tribe
description: >
  Canonical form for representing a federally recognized Native American tribe
  in the United States, based loosely on EntitySchema E502.

# Entity labels (multilingual)
labels:
  en:
    label: Label
    description: The primary name by which this tribe is commonly known in English.
    required: true
    guidance: >
      Use the name that the tribe uses in referring to itself as the primary label where possible.
      Check official tribal government websites and Wikidata items for existing tribes.
      Prefer the tribe's self-designation over external government names.

# Entity descriptions (multilingual)
descriptions:
  en:
    label: Description
    description: A short, distinctive description to disambiguate this tribe from others.
    required: true
    guidance: >
      Format: "federally recognized Native American tribe based in [region/state]"
      Example: "federally recognized Native American tribe based in Oklahoma"
      Keep concise (under 250 characters) and informative.

# Entity aliases (multilingual alternative names)
aliases:
  en:
    label: Aliases
    description: Alternative names by which this tribe is known or has been referred to.
    required: false
    guidance: >
      Include an alias for the official name of the tribe as referred to by the U.S. Government
      (e.g., from the Bureau of Indian Affairs list).
      Include historical names and names in other languages when available.
    examples:
      - "Anishinaabek"
      - "Northern Band"
      - "Official tribal name from federal recognition document"

# Entity sitelinks (Wikipedia and other wiki language versions)
sitelinks:
  required: false
  validation_policy: allow_existing_nonconforming
  guidance: >
    Sitelinks connect this item to Wikipedia articles and other Wikimedia projects in different languages.
    Each language/project combination can only appear on ONE Wikidata item - check for conflicts
    before adding sitelinks. Validation at profile level can check format, but uniqueness
    constraint will only be caught when writing to Wikidata.
  languages:
    en:
      project: wikipedia
      description: English Wikipedia article
      required: false
      guidance: >
        Article title should match the tribe name or established Wikipedia conventions.
    fr:
      project: wikipedia
      description: French Wikipedia article
      required: false
      guidance: >
        Include if a French Wikipedia article exists for this tribe.

# Reusable reference patterns
standard_reference: &standard_reference
  min_count: 1
  validation_policy: allow_existing_nonconforming
  allowed:
    - id: stated_in
      wikidata_property: P248
      type: item
      label: Stated in
      description: Reference to source document or database
    - id: reference_url
      wikidata_property: P854
      type: url
      label: Reference URL
      description: Direct URL to source

statements:

  - id: instance_of
    label: Instance of
    wikidata_property: P31
    type: statement
    max_count: null
    validation_policy: allow_existing_nonconforming
    
    behavior:
      value: fixed        # Value locked to Q7840353
      references: editable  # References manually provided

    value:
      type: item
      fixed: Q7840353
      label: federally recognized Native American tribe in the United States

    references: *standard_reference

  - id: native_name
    label: Native name
    wikidata_property: P1705
    type: statement
    required: false
    max_count: null

    value:
      type: monolingualtext
      constraints:
        - type: language_required
        - type: valid_language_code

    qualifiers:
      - id: language_of_work
        label: Language of work or name
        wikidata_property: P407
        required: false
        value:
          type: item
          allowed_items:
            source: sparql
            query: |
              PREFIX wd: <http://www.wikidata.org/entity/>
              PREFIX wdt: <http://www.wikidata.org/prop/direct/>
              PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
              
              SELECT ?item ?itemLabel ?languageCode
              WHERE {
                ?item wdt:P31/wdt:P279* wd:Q34770 ;
                      wdt:P424 ?languageCode ;
                      rdfs:label ?itemLabel .
                FILTER(LANG(?itemLabel) = "en")
              }
            refresh: weekly

    references: *standard_reference

  - id: headquarters_location
    label: Headquarters location
    wikidata_property: P159
    type: statement
    required: false
    max_count: 1

    value:
      type: item

    qualifiers:
      - id: street_address
        label: Street address
        wikidata_property: P6375
        required: false
        value:
          type: monolingualtext
          constraints:
            - type: language_required

      - id: postal_code
        label: Postal code
        wikidata_property: P281
        required: false
        value:
          type: string

      - id: coordinate_location
        label: Coordinate location
        wikidata_property: P625
        required: false
        value:
          type: globecoordinate
          constraints:
            - type: precision
              min_precision: 0.0001
              max_precision: 0.01

    references: *standard_reference

  - id: inception
    label: Inception
    wikidata_property: P571
    type: statement
    required: false
    max_count: 1

    value:
      type: time
      constraints:
        - type: precision
          allowed_precisions: [9, 10, 11]
          auto_derive: true
        - type: calendar_model
          default: Q1985727
        - type: format
          patterns: ['YYYY', 'YYYY-MM', 'YYYY-MM-DD']

    references: *standard_reference

  - id: osm_relation_id
    label: OpenStreetMap relation ID
    wikidata_property: P402
    type: statement
    required: false
    max_count: 1

    value:
      type: external-id
      constraints:
        - type: format
          pattern: '^\d+$'
        - type: formatter_url
          url_pattern: 'http://www.openstreetmap.org/relation/$1'
          validate: true
          validation_method: http_head

  - id: flag_image
    label: Flag image
    wikidata_property: P41
    type: statement
    required: false
    max_count: 1

    value:
      type: commonsMedia
      constraints:
        - type: file_exists
          validate: true
          validation_method: commons_api
        - type: file_type
          allowed_types: ['image/svg+xml', 'image/png', 'image/jpeg']

    references: *standard_reference
```

---

## Step-by-Step: Building Your Own Profile

1. **Define the entity type** - What kind of thing are you profiling?
   ```yaml
   name: My Entity Type
   description: >
     Clear description of scope, examples, and use cases.
   ```

2. **Identify key properties** - Which Wikidata properties are essential?
   - Look at existing Wikidata items of this type
   - Check EntitySchemas for precedent
   - Consult domain-specific schemas

3. **Start with required statements** - What must always be present?
   ```yaml
   statements:
     - id: statement_id
       label: Statement Label
       wikidata_property: P123
       type: statement
       required: true
   ```

4. **Add datatype definitions** - What type of value does each statement hold?
   ```yaml
   value:
     type: string  # or item, url, quantity, time, etc.
   ```

5. **Define constraints** - What rules validate the data?
   ```yaml
   constraints:
     - type: format
       pattern: '^[A-Z]+$'
   ```

6. **Add references where needed** - Which statements need sources?
   ```yaml
   references:
     required: true
     allowed:
       - id: stated_in
         wikidata_property: P248
         type: item
   ```

7. **Test with real data** - Load a profile and validate against actual items
8. **Iterate based on feedback** - Refine constraints and statement definitions
9. **Document edge cases** - Add comments explaining non-obvious choices

---

## Future Enhancements

As profiles are used in practice, expect iterative refinements:

- **Wizard step customization** - Profile-level `wizard_steps` metadata to customize step organization beyond the default 5-step structure
- **Conditional statements** - Statements that appear only if certain conditions are met (e.g., "headquarters location" only for organizations with `instance_of: organization`)
- **Qualifier constraints** - Validate qualifiers without loading full statement
- **Cross-statement validation** - Rules connecting multiple statements  
- **Profile composition** - Merging or extending existing profiles
- **Multi-language support** - Localized statement labels and prompts
- **Version management** - Profile versioning and migration guides
- **Wizard branching logic** - More sophisticated secondary entity workflows with dependency tracking

---

## See Also

- [Architecture Overview](../architecture/index.md) - Profile role in GKC pipeline
- [API Reference](api/index.md) - Profile loading and validation utilities
- [Validation Utilities](api/index.md) - Constraint enforcement
- [SpiritSafe Repository](https://github.com/skybristol/SpiritSafe) - Canonical profile registrants and query assets
