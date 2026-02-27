# SpiritSafe YAML Profiles: Construction and Reference

**Plain Meaning:** A comprehensive guide to building, structuring, and validating YAML profiles that define how entities are captured, validated, and transformed in the Global Knowledge Commons.

## Overview

SpiritSafe YAML profiles are declarative, machine-readable definitions of entity structures that bridge raw user input and refined, cross-platform entity models. They encode:

- **What fields** make up an entity (properties and their datatypes)
- **How fields relate** to Wikidata properties and external systems
- **What constraints** apply to each field's values
- **How to validate** incoming data against those constraints
- **How to reference** sources and maintain provenance

Profiles are YAML files that live in the `.SpiritSafe/profiles/` directory and are managed alongside code in version control. They serve as both human-readable documentation and executable specifications that drive form generation, validation, and data transformation.

## Profile Anatomy

A SpiritSafe YAML profile has this essential structure:

```yaml
name: Entity Type Name
description: >
  Multi-line description of what this profile represents
  and what kinds of entities it covers.

# Optional: Reusable reference patterns (via YAML anchors)
standard_reference: &standard_reference
  required: true
  min_count: 1
  # ... reference structure

fields:
  - id: field_identifier
    label: Human-readable label
    wikidata_property: P123  # Wikidata property ID
    type: statement           # Always "statement" for now
    required: true            # Is this field mandatory?
    max_count: 1              # null = unlimited
    validation_policy: allow_existing_nonconforming
    form_policy: target_only

    value:
      type: string  # Datatype
      constraints:  # Field-level constraints
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
| `fields` | array | YES | List of field definitions |
| *Anchors* | any | NO | YAML anchors for reusable patterns (e.g., `&standard_reference`) |

### Field Keys

| Key | Type | Required | Purpose |
|-----|------|----------|---------|
| `id` | string | YES | Unique identifier (snake_case) |
| `label` | string | YES | Human-readable display name |
| `wikidata_property` | string | YES | Wikidata property ID (e.g., "P31") |
| `type` | string | YES | Always "statement" (for now) |
| `required` | boolean | NO | Whether field is mandatory (default: false) |
| `max_count` | int or null | NO | Max statements allowed (null = unlimited) |
| `validation_policy` | enum | NO | How to handle existing data (allow_existing_nonconforming \| strict) |
| `form_policy` | enum | NO | How forms display field (target_only \| show_all) |
| `value` | object | YES | Value definition (datatype + constraints) |
| `qualifiers` | array | NO | Qualifier definitions |
| `references` | object | NO | Reference definition |

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

Constraints are the validation rules applied to field values. They enforce business logic, external system compliance, and data quality.

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
  required: true
  min_count: 1
  validation_policy: allow_existing_nonconforming
  form_policy: target_only
  allowed:
    - id: stated_in
      wikidata_property: P248
      type: item
      label: Stated in
    - id: reference_url
      wikidata_property: P854
      type: url
      label: Reference URL

# Use anywhere in fields
fields:
  - id: field_name
    # ... field definition ...
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
- **Required fields:** Mark commonly expected languages as `required: true` to prompt curators
- **Guidance:** Include curator instructions on naming conventions and authority sources

### Descriptions

Descriptions disambiguate items when there are multiple with the same or similar labels. They should be concise and contextual.

```yaml
descriptions:
  en:
    label: Description
    description: A short, distinctive description to disambiguate this entity.
    required: true
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

---

## Best Practices

### 1. Keep Profiles Focused and Cohesive

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

# Then use in every field that needs it
fields:
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

### 4. Use Precise Validation Policies

- `allow_existing_nonconforming`: Data already in Wikidata can deviate, but new data must conform
- `strict`: All data must conform strictly

```yaml
validation_policy: allow_existing_nonconforming  # Reasonable default
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
  required: true
  min_count: 1
  validation_policy: allow_existing_nonconforming
  form_policy: target_only
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

fields:

  - id: instance_of
    label: Instance of
    wikidata_property: P31
    type: statement
    required: true
    max_count: null
    validation_policy: allow_existing_nonconforming
    form_policy: target_only

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

3. **Start with required fields** - What must always be present?
   ```yaml
   fields:
     - id: field_id
       label: Field Label
       wikidata_property: P123
       type: statement
       required: true
   ```

4. **Add datatype definitions** - What type of value does each field hold?
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
8. **Iterate based on feedback** - Refine constraints and field definitions
9. **Document edge cases** - Add comments explaining non-obvious choices

---

## Future Enhancements

As profiles are used in practice, expect iterative refinements:

- **Qualifier constraints** - Validate qualifiers without loading full statement
- **Cross-field validation** - Rules connecting multiple fields  
- **Conditional fields** - Fields that appear only if certain conditions are met
- **Profile composition** - Merging or extending existing profiles
- **Multi-language support** - Localized field labels and descriptions
- **Version management** - Profile versioning and migration guides

---

## See Also

- [Architecture Overview](architecture.md) - Profile role in GKC pipeline
- [API Reference](api/index.md) - Profile loading and validation utilities
- [Validation Utilities](api/index.md) - Constraint enforcement
- [GitHub Repository](https://github.com/skybristol/gkc) - Full profile examples in `.SpiritSafe/profiles/`
