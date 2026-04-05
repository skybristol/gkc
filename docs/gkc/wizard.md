# GKC Wizard Documentation

**Purpose:** Document how GKC Wizards consume Entity Profiles to generate interactive, multi-step curation workflows for creating and editing entities across Wikidata, Wikimedia Commons, and other Global Knowledge Commons platforms.

---


## Launching the Wizard

To start the interactive profile wizard, use the dedicated CLI command:

```bash
gkc wizard --profile Q4 --local-root /path/to/SpiritSafe
```

Replace `Q4` with the desired profile QID and adjust the path as needed. This launches the Streamlit-based wizard for guided entity curation.

---

## Overview

GKC Wizards are **profile-driven user interfaces** that transform declarative JSON Entity Profile definitions into guided, step-by-step data entry workflows. Every aspect of the wizard—field labels, validation rules, input widgets, help text, and workflow organization—derives directly from the profile with zero hardcoded entity logic.

**Key Characteristics:**

- **Fully declarative**: All UI behavior comes from profile metadata
- **Multi-entity capable**: Can curate primary entity + related entities in single session
- **Real-time validation**: Feedback on every field blur, guided by profile constraints
- **Graceful degradation**: Follows Wikidata/Wikipedia philosophy—incomplete entities can be saved; enhancement happens iteratively

---

## Wizard Architecture

### Profile → UI Generation Pipeline

```
┌──────────────────────────────────────────────────────────┐
│  SpiritSafe JSON Entity Profile (Q4 — tribal_government_us) │
│  - Entity metadata (labels, descriptions, aliases)       │
│  - Statements with datatypes, constraints, guidance      │
│  - Profile graph (links to related profile types)        │
│  - Value-list routes to SPARQL-hydrated cache files      │
└──────────────────┬──────────────────────────────────────-┘
                   │ Load & parse
                   ↓
┌──────────────────────────────────────────────────────────┐
│  GKC Spirit Safe Module                                  │
│  - Load JSON Entity Profile + related profiles           │
│  - Discover profile graph (linked profile types)         │
│  - Resolve value-list cache routes                       │
└──────────────────┬──────────────────────────────────────-┘
                   │ Provide profile + graph
                   ↓
┌──────────────────────────────────────────────────────────┐
│  Wizard Loader                                           │
│  - Create GKC Curation Packet with uncharged slots       │
│  - Entity slots keyed by profile name_identifier and ID  │
│  - Statement slots keyed by statement name_identifier    │
└──────────────────┬──────────────────────────────────────-┘
                   │ Pass packet + profile to renderer
                   ↓
┌──────────────────────────────────────────────────────────┐
│  Wizard Step Renderers                                   │
│  - Step 1: Plan          (from metadata.description)     │
│  - Step 2: Identification (labels/desc/aliases)          │
│  - Step 3: Statements    (statement definitions)         │
│  - Step 4: Sitelinks     (sitelinks config)              │
│  - Step 5: Review        (completeness check)            │
└──────────────────┬──────────────────────────────────────-┘
                   │ User interaction & data entry
                   ↓
┌──────────────────────────────────────────────────────────┐
│  Curation Packet (updated with user data)               │
│  - Saved to disk (draft) or shipped to Wikidata          │
└──────────────────────────────────────────────────────────┘
```

---

## Charged Packet Contract

When the wizard loads an existing Wikidata item via `--qid`, it calls `charge_packet_from_wikidata_items()` to populate the packet with live Wikidata data. The charged packet provides a stable contract that wizard rendering can rely on.

**What the wizard can consume from a charged packet:**

- `data.entities[*].statements` — statement slots with `data-value` populated from Wikidata; use these to pre-fill form fields.
- `data.entities[*].labels / descriptions / aliases` — filled from Wikidata entity labels; use for Step 2 pre-population.
- `conformance.entity_profile_map` — maps each loaded entity QID (and its profile `name_identifier` and URI) to the governing profile URI. Use to determine which profile governs each entity tab in multi-entity workflows.
- `conformance.statement_evaluations` — per-claim conformance records with `status: conformant` or `nonconformant`. Use to pre-highlight non-conformant statements in the review step without re-running validation inline.

**What the wizard should NOT derive from the charged packet:**

- Do not re-infer which profile governs a linked entity. Always read from `conformance.entity_profile_map`.
- Do not interpret `nonconformant` records as hard blockers. They are informational notices for curator review; the wizard should surface them with guidance, not prevent saving.
- Richer conformance signals (`uncovered`, `missing_required`, coercion notices) will arrive via fermenter integration in a future step. When available they will appear alongside `statement_evaluations` under `conformance`.

---

## The 5-Step Wizard Structure

Every wizard follows a consistent 5-step progression designed to match curator mental models:

### Step 1: Plan of Action

**Purpose:** Orient curator to what they're about to create and what information they'll need

**Content derived from profile:**

- **Entity type**: `metadata.name` and profile top-level `name` field
- **Description**: `metadata.description` (long form) or `profile.description` (short form)
- **Required elements**: Count of required statements, required languages
- **Secondary entities**: Lists profiles discovered via profile graph (e.g., "You may also create: Office Held by Head of State")
- **Time estimate**: Auto-calculated from statement count and complexity
- **Preparation guidance**: Any profile-level `preparation_guidance` field (future enhancement)

**UI Elements:**

- Entity type badge/icon
- Summary statistics ("5 required statements, 8 optional statements")
- List of related entity types that may need creation
- "Start curation" button to proceed to Step 2

**Example Display:**

```
┌─────────────────────────────────────────────────────────┐
│ Create Tribal Government (US)                           │
├─────────────────────────────────────────────────────────┤
│ Federally recognized Native American tribes in the      │
│ United States. Comprehensive profile for documenting    │
│ tribal nomenclature, federal recognition, governmental   │
│ structure, and cross-platform links.                     │
│                                                          │
│ REQUIRED ELEMENTS                                        │
│ • Labels and descriptions in English                    │
│ • 3 required statements                                 │
│ • At least 1 sitelink                                   │
│                                                          │
│ YOU MAY ALSO CREATE                                      │
│ • Office Held by Head of State (optional)               │
│                                                          │
│ ESTIMATED TIME: 10-15 minutes                            │
│                                                          │
│            [Start Curation →]                            │
└─────────────────────────────────────────────────────────┘
```

---

### Step 2: Basic Identification (Labels, Descriptions, Aliases)

**Purpose:** Collect multilingual metadata that identifies the entity

**Content derived from profile:**

- **Languages supported**: Discovered by scanning `labels`, `descriptions`, `aliases` sections in profile
- **Required vs optional languages**: Inferred from `required: true` in profile (future: explicit `languages` section)
- **Input prompts**: `labels.input_prompt`, `descriptions.input_prompt` (or defaults)
- **Guidance text**: `labels.guidance`, `descriptions.guidance`

**UI Structure:**

- **Single-language profiles**: Simple form (Label, Description, Aliases)
- **Multi-language profiles**: Tabbed interface (one tab per language)

**Field-Specific Behavior:**

| Field | Cardinality | Validation | Profile Source |
|-------|-------------|------------|----------------|
| **Label** | 1 per language (max) | Required if language is required; max length ~250 chars | `labels.en.input_prompt`, `labels.en.guidance` |
| **Description** | 1 per language (max) | Required if language is required; must be distinctive | `descriptions.en.input_prompt`, `descriptions.en.guidance` |
| **Aliases** | 0-many per language | Optional; no duplicates within language | `aliases.en.input_prompt`, `aliases.en.guidance` |

**Validation:**

- Real-time: On field blur, check length constraints and required status
- Cross-field: Ensure description doesn't duplicate label
- Pre-advancement: Validate all required languages have non-empty label + description

**Example Display (Multi-Language):**

```
┌─────────────────────────────────────────────────────────┐
│ Basic Identification    [EN] [CHR] [NV]                 │
├─────────────────────────────────────────────────────────┤
│ ENGLISH (REQUIRED)                                       │
│                                                          │
│ Label *                                                  │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Cherokee Nation                                     │ │
│ └─────────────────────────────────────────────────────┘ │
│ ℹ️ Use the name the tribe uses to refer to itself      │
│                                                          │
│ Description *                                            │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Federally recognized Native American tribe in OK   │ │
│ └─────────────────────────────────────────────────────┘ │
│ ℹ️ Short, distinctive description (not just a repeat    │
│    of the label)                                         │
│                                                          │
│ Aliases (Alternative Names)                              │
│ • Cherokee ✕                                             │
│ • Cherokee Tribe ✕                                       │
│ [+ Add another alias]                                    │
│                                                          │
│         [← Back]              [Continue →]               │
└─────────────────────────────────────────────────────────┘
```

---

### Step 3: Statements

**Purpose:** Collect all property-value assertions about the entity

**Content derived from profile:**

- **Statement list**: `profile.statements[]` array (rendered in order)
- **For each statement**:
  - Label: `statement.label`
  - Input prompt: `statement.input_prompt` or `statement.value.input_prompt`
  - Guidance: `statement.guidance`
  - Datatype: `statement.value.type` → determines widget
  - Constraints: `statement.constraints[]` → validation rules
  - Allowed items: `statement.value.allowed_items` → choice lists
  - Qualifiers: `statement.qualifiers[]` → nested inputs
  - References: `statement.references` → source collection

**Statement Rendering Order:**

Wizard renders statements in the exact order specified in the JSON Entity Profile artifact. Profile designers should order statements logically (e.g., classification statements first, then descriptive, then relationships).

**Widget Selection by Datatype:**

| Datatype | Widget | Behavior |
|----------|--------|----------|
| `item` | QID text input OR autocomplete | If `allowed_items` present, show searchable dropdown; else free QID entry |
| `entity_profile` | QID input + "Create new" button | Always shows both "Select existing" and "Create new [profile]" options |
| `string` | Text input | Single-line for short strings; multi-line if `max_length > 200` |
| `url` | URL input | Validates URL format; shows protocol dropdown (http/https) |
| `time` | Date picker | Precision auto-detected from input format (YYYY vs YYYY-MM vs YYYY-MM-DD) |
| `quantity` | Number input + unit selector | Unit field shown if `unit_behavior != "none"` |
| `monolingualtext` | Text input + language dropdown | Language choices from `allowed_items` SPARQL or fallback list |
| `commonsMedia` | File upload widget | Uploads to Wikimedia Commons (requires auth) |
| `globe-coordinate` | Map picker | Click map to set lat/lon; or manual entry |

**Skip Functionality:**

Every statement can be skipped via explicit "Skip this statement" button. Philosophy: curators can save incomplete entities and enhance later.

**Multi-Value Statements:**

If `statement.max_count > 1` or `max_count: null`, show "Add another [statement label]" button after each value.

**Qualifiers:**

Rendered as nested form under statement value. Each qualifier follows same widget selection rules as statements.

**References:**

Behavior determined by `statement.references.behavior`:

- `editable`: Show reference collection UI (itemlist from SPARQL or manual entry)
- `auto_derive`: System generates references automatically (e.g., from statement value URL)
- `fixed`: References pre-populated from profile; user cannot edit

**Example Display:**

```
┌─────────────────────────────────────────────────────────┐
│ Statements (3 of 8 completed)                           │
├─────────────────────────────────────────────────────────┤
│ Instance of (classification) *                           │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Q7840353 - federally recognized Native American... │ │
│ └─────────────────────────────────────────────────────┘ │
│ ℹ️ Fixed value: This entity is always classified as a   │
│    federally recognized tribe.                           │
│                                                          │
│ REFERENCES (required: 1+)                                │
│ • Federal Register notice: Vol. 87, No. 18 ✕            │
│ [+ Add reference]                                        │
│ ─────────────────────────────────────────────────────── │
│                                                          │
│ Office held by head of state                             │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Q999888 - Principal Chief of the Cherokee Nation   │ │
│ └─────────────────────────────────────────────────────┘ │
│ [Select existing QID]  [Create new office →]            │
│ ℹ️ The executive leadership position (not the person).  │
│                                                          │
│              [Skip this statement]                       │
│ ─────────────────────────────────────────────────────── │
│                                                          │
│         [← Back]              [Continue →]               │
└─────────────────────────────────────────────────────────┘
```

---

### Step 4: Cross-Platform Links (Sitelinks)

**Purpose:** Link entity to Wikipedia articles and other sister projects

**Content derived from profile:**

- **Supported languages**: `profile.sitelinks.languages[]`
- **Supported projects**: Per language (e.g., `en: [wikipedia, wikivoyage]`)
- **Input mode**: Language+project+title dropdowns (current) or URL-based (future)
- **Validation**: Uniqueness constraints (one sitelink per language+project across all Wikidata)

**Current UI Pattern:**

1. Select language (dropdown)
2. Select project (dropdown: wikipedia, wikivoyage, etc.)
3. Enter article title (text input)
4. Validate: Check if sitelink already exists in Wikidata for another item (conflict detection)

**Future Enhancement: URL-Based Entry:**

```
Enter Wikipedia or Wikimedia URL:
┌─────────────────────────────────────────────────────┐
│ https://en.wikipedia.org/wiki/Cherokee_Nation      │
└─────────────────────────────────────────────────────┘
✓ URL validated • Article exists • No conflicts

Relationship type:
◉ Primary article (exclusively about this entity)
○ Shared article (discusses multiple entities)
○ Contextual mention (entity appears in broader topic)
```

**Sitelink List Display:**

```
┌─────────────────────────────────────────────────────────┐
│ Cross-Platform Links                                    │
├─────────────────────────────────────────────────────────┤
│ WIKIPEDIA ARTICLES                                       │
│ • English: Cherokee_Nation ✕                            │
│ • Cherokee: ᎳᎫᎿ_ᎠᏰᎲ ✕                                  │
│                                                          │
│ [+ Add sitelink]                                         │
│                                                          │
│         [← Back]              [Continue →]               │
└─────────────────────────────────────────────────────────┘
```

---

### Step 5: Review & Validate

**Purpose:** Show curator a complete summary of what will be created/edited; identify gaps

**Content displayed:**

- **Entity overview**: Labels, descriptions (all languages)
- **Completeness score**: "7 of 10 required elements complete (70%)"
- **Statements summary**: Grouped by completed vs skipped
- **Secondary entities**: If multi-entity packet, show related entities to be created
- **Validation warnings**: Missing required fields, constraint violations

**Completeness Calculation:**

```
required_fields = 2 (base for label+desc) 
                + num_required_statements 
                + (2 * num_required_languages)

completed_fields = count(non_empty required labels) 
                 + count(non_empty required descriptions)
                 + count(statements with at least one value)

progress_pct = (completed_fields / required_fields) * 100
```

**Action Options:**

- **Save Draft**: Serialize packet to disk for later editing (allows incomplete entities)
- **Ship to Wikidata**: Validate completeness; if warnings present, show confirmation dialog
- **Edit [Section]**: Jump back to specific step to fix issues

**Example Display:**

```
┌─────────────────────────────────────────────────────────┐
│ Review: Cherokee Nation                                 │
├─────────────────────────────────────────────────────────┤
│ COMPLETENESS: 8 of 10 required elements (80%)           │
│ ████████████████░░░░ Ready to ship                      │
│                                                          │
│ IDENTIFICATION ✓                                         │
│ • English label: Cherokee Nation                        │
│ • English description: Federally recognized tribe...    │
│ • 2 aliases                                              │
│                                                          │
│ STATEMENTS                                               │
│ ✓ Instance of: Q7840353                                 │
│ ✓ Office held by head of state: Q999888                 │
│ ✓ Member count: 380,000 (2023)                          │
│ ⚠️ Headquarters location: MISSING                        │
│ ⚠️ Official website: MISSING                             │
│                                                          │
│ CROSS-PLATFORM LINKS ✓                                   │
│ • enwiki: Cherokee_Nation                               │
│                                                          │
│ RELATED ENTITIES TO BE CREATED                           │
│ • Office: Principal Chief of the Cherokee Nation        │
│                                                          │
│ ⚠️ WARNINGS                                              │
│ • Headquarters location is highly recommended           │
│ • Official website helps verify tribal government       │
│                                                          │
│ [← Back] [Save Draft] [Ship to Wikidata →]              │
└─────────────────────────────────────────────────────────┘
```

---

## Multi-Entity Curation Sessions

When a profile references other profiles via `entity_profile` statements, wizard creates a **multi-entity curation packet** and allows curator to work on multiple entities in one session.

### Profile Graph Loading

**Example:** User launches wizard with `TribalGovernmentUS` profile

1. Wizard loads `TribalGovernmentUS` profile
2. Discovers `office_held_by_head_of_state` statement with `entity_profile: OfficeHeldByHeadOfState`
3. Loads `OfficeHeldByHeadOfState` profile
4. Creates packet with two entity slots:
  - Primary slot: profile `tribal_government_us`, id `https://datadistillery.wikibase.cloud/entity/Q4`
  - Related slot: profile `office_held_by_head_of_state`, id `https://datadistillery.wikibase.cloud/entity/Q39`

### UI Presentation Strategy

**Sidebar Entity Navigator:**

```
┌──────────────┬──────────────────────────────────────────┐
│ ENTITIES     │                                          │
│              │  Step 2: Basic Identification            │
│ ◉ Tribal Gov │                                          │
│   (primary)  │  ENGLISH (REQUIRED)                      │
│              │                                          │
│ ○ Office     │  Label *                                 │
│   (related)  │  ┌────────────────────────────────────┐  │
│              │  │ Cherokee Nation                    │  │
│              │  └────────────────────────────────────┘  │
│              │                                          │
│ ────────────  │  ...                                     │
│              │                                          │
│ 80% complete │         [← Back]     [Continue →]        │
└──────────────┴──────────────────────────────────────────┘
```

Users can click side entities to switch between them at any time. Each entity maintains separate progress through the 5 steps.

**Alternative: Tab-Based Navigation:**

```
┌─────────────────────────────────────────────────────────┐
│ [Tribal Government ✓] [Office 40%]                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Currently editing: Office Held by Head of State        │
│  Step 3: Statements                                     │
│  ...                                                     │
└─────────────────────────────────────────────────────────┘
```

### Creating Related Entities

**Workflow when curator clicks "Create new office":**

1. Wizard creates a new related-entity slot in the packet for the linked profile
2. Sets `creation_path: primary.office_held_by_head_of_state`
3. Switches active entity in UI to office
4. Runs through 5 steps for office (Plan → Identify → Statements → Links → Review)
5. On office completion:
   - Returns focus to primary entity
  - Populates `office_held_by_head_of_state` statement value with the related entity URI/QID reference
   - Shows office as "Related entity (completed)" in sidebar/tabs

**Cardinality Enforcement:**

If statement has `max_count: 1` and office is already created, "Create new office" button is disabled.

If `max_count: null`, curator can create multiple offices; wizard adds additional related entity slots keyed by profile + canonical id.

### Review Stage for Multi-Entity Packets

Review step shows **all entities** in packet with expandable sections:

```
┌─────────────────────────────────────────────────────────┐
│ Review: Multi-Entity Packet                             │
├─────────────────────────────────────────────────────────┤
│ PRIMARY ENTITY: Cherokee Nation                         │
│ Profile: TribalGovernmentUS                              │
│ Completeness: 80%                                        │
│                                                          │
│ [▼ Show details]                                         │
│                                                          │
│ RELATED ENTITIES (1)                                     │
│                                                          │
│ [▶ Office: Principal Chief of the Cherokee Nation]      │
│    Profile: OfficeHeldByHeadOfState                     │
│    Completeness: 60%                                     │
│    [Edit] [Remove]                                       │
│                                                          │
│ SHIPPING ORDER                                           │
│ 1. Office (no dependencies)                              │
│ 2. Tribal Government (references office)                 │
│                                                          │
│ [← Back] [Save Draft] [Ship to Wikidata →]              │
└─────────────────────────────────────────────────────────┘
```

---

## Profile-Driven UI Generation

### Guidance Text Rendering

Profile `guidance` fields appear as:

- **Inline help icons** (ℹ️) with tooltip on hover
- **Expandable help sections** for longer guidance
- **Contextual captions** below input fields

**Example from profile artifact:**

```json
{
  "name_identifier": "native_name",
  "messages": {
    "guidance": {
      "mul": "Use the tribe's preferred self-designation in their native language(s). Consult tribal language preservation resources or official communications."
    }
  }
}
```

**Rendered in wizard:**

```
Native Name
┌─────────────────────────────────────────────────────┐
│ ᎳᎫᎿ ᎠᏰᎲ                                            │
└─────────────────────────────────────────────────────┘
ℹ️ Use the tribe's preferred self-designation in their
   native language(s). [Learn more ▼]
```

### Input Prompt Customization

Default input prompts:

- Labels: "Enter the primary name for this entity"
- Descriptions: "Enter a short, distinctive description"
- Statements: "Enter [statement label]"

Profile can override:

```json
{
  "identification": {
    "labels": {
      "mul": {
        "input_prompt": "Use the name the tribe uses in referring to itself"
      }
    }
  }
}
```

Rendered as placeholder text or caption.

### Allowed Items: Choice List Rendering

**Behavior by list size:**

| List Size | UI Widget |
|-----------|-----------|
| < 10 items | Dropdown (simple select) |
| 10-50 items | Searchable select with type-ahead |
| 50-200 items | Autocomplete with lazy loading |
| 200+ items | Autocomplete with server-side search |

**UI hint override:**

```json
{
  "value": {
    "allowed_items": {
      "source": "sparql",
      "query_ref": "queries/federal_register_issues.sparql",
      "ui_hint": "searchable_select"
    }
  }
}
```

**Fallback behavior:**

If SPARQL query fails or returns empty, wizard uses `fallback_items` from profile:

```json
{
  "value": {
    "allowed_items": {
      "source": "sparql",
      "query_ref": "queries/languages.sparql",
      "fallback_items": [
        {"id": "Q1860", "label": "English"},
        {"id": "Q1567", "label": "Cherokee"}
      ]
    }
  }
}
```

---

## Future: QID Loading & Entity Editing

Load existing Wikidata items into the wizard for editing.

### Workflow

1. User provides QID (e.g., `Q5093`) + profile name
2. Wizard fetches Wikidata JSON via `wbgetentities` API
3. Transforms Wikidata JSON → GKC Entity JSON (reverse serialization)
4. Populates curation packet with existing data
5. User edits via normal 5-step workflow
6. On ship, only **changed** statements are sent to Wikidata (diff-based updates)

### Related Entity Auto-Loading

If profile references other profiles, wizard:

1. Checks existing entity for related statements (e.g., P1906 office held by head of state)
2. Fetches referenced QID (e.g., Q999888)
3. Loads it into packet as related entity
4. Presents multi-entity editing session

**Example:**

User loads Q5093 (Cherokee Nation) with TribalGovernmentUS profile

→ Wizard finds P1906 = Q999888 (Principal Chief office)

→ Loads OfficeHeldByHeadOfState profile for Q999888

→ Packet contains both entities; user can edit either

### Depth-1 Loading Strategy

**Current design:** Load direct children only (one hop)

- Primary entity → Related entities (via entity_profile statements)
- Does **not** recursively load links-of-links

**Future:** Configurable depth in metadata:

```json
{
  "metadata": {
    "profile_graph": [
      {
        "target_profile": "https://datadistillery.wikibase.cloud/entity/Q39",
        "max_depth": 2
      }
    ]
  }
}
```

---

## Validation & Error Handling

### Real-Time Validation

- **On field blur**: Check datatype, constraints, required status
- **On statement completion**: Validate qualifiers, references, cardinality
- **Before step advancement**: Check all required fields in current step are complete

### Validation Severity Levels

| Severity | Behavior | Example |
|----------|----------|---------|
| **Error** | Blocks progression; must fix | Missing required label |
| **Warning** | Allows progression; shows in review | Missing recommended statement |
| **Info** | Non-blocking suggestion | "Consider adding aliases for discoverability" |

### Constraint Violation Messaging

Profile constraints generate user-friendly error messages:

**Profile constraint:**

```json
{
  "value": {
    "constraints": [
      {
        "type": "format",
        "pattern": "^Q\\d+$",
        "error_message": "Must be a valid QID (e.g., Q123456)"
      }
    ]
  }
}
```

**Rendered error:**

```
✗ Must be a valid QID (e.g., Q123456)
  You entered: "Cherokee Nation" (not a valid format)
```

---

## Related Documentation

- [GKC Architecture Overview](../architecture/index.md) — How wizards fit in GKC pipeline
- [GKC Entity Profiles](./profiles.md) — Profile schema and structure reference
- [GKC Entity JSON Schema](./entity-json-schema.md) — Curation packet format
- [Profile Graphs & Multi-Entity Linking](./profiles.md#profile-graphs-cross-references)

---

**Last Updated:** March 26, 2026
