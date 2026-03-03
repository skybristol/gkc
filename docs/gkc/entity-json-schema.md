# GKC Entity JSON Schema

**Purpose:** Define the canonical internal data format for entity curation within the GKC Wizard and broader Data Distillery ecosystem. This schema bridges [profile](./profiles.md) definitions (YAML) with curator input (form data, bulk data, API data) and eventual serialization (Wikidata JSON, Wikimedia Commons JSON, etc. distributed to Global Knowledge Commons partners).

---

## Overview

The **GKC Entity JSON** is a JSON object representing a single entity being curated through Data Distillery actions. When multiple related entities are created in sequence (e.g., primary tribal government + linked office entity), they exist as an array of GKC Entity JSON objects within a **GKC Curation Packet**.

### Key Principles

1. **Profile-driven structure**: Shape and validation rules derive from profile YAML
2. **Multilingual support**: All text fields use Wikidata's language-keyed model
3. **Normalization-ready**: Data stored in clean, coerced form (no raw user input pollution)
4. **Completeness trackable**: Can calculate progress as `completed_fields / required_fields`
5. **Round-trip capable**: Can load from disk, edit in wizard, save back to disk
6. **Transitive references**: Links to other entities in same packet use packet IDs (resolved to QIDs during shipping)

---

## Schema Definition

### Entity Metadata

```json
{
  "packet_id": "ent-001-primary",
  "profile_name": "TribalGovernmentUS",
  "username": "skybristol",
  "status": "in_progress",
  "created_at": "2026-03-02T14:32:00Z",
  "creation_path": "primary",
  
  "labels": { },
  "descriptions": { },
  "aliases": { },
  "statements": { },
  "sitelinks": { }
}
```

#### Entity Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `packet_id` | string | ✅ | Unique identifier within curation packet (e.g., "ent-001-primary", "ent-002-office") |
| `profile_name` | string | ✅ | Profile used for curation (e.g., "TribalGovernmentUS") |
| `username` | string | ✅ | Curator username from `WIKIVERSE_USERNAME` env var (needed for later authentication) |
| `status` | string | ✅ | Current entity lifecycle: `in_progress`, `ready_to_resolve_refs`, `waiting_for_qid` (post-creation) |
| `created_at` | string (ISO 8601) | ✅ | Timestamp entity was first created in packet |
| `creation_path` | string | ✅ | Breadcrumb showing where entity was created: `primary` (root) or `primary.field_id` (from sub-wizard) |

---

## Multilingual Text Fields

Following Wikidata's model, text fields use language-keyed dictionaries:

```json
{
  "labels": {
    "en": "Cherokee Nation",
    "chr": "ᎳᎫᎿ ᎠᏰᎲ"
  },
  "descriptions": {
    "en": "Federally recognized Native American tribe",
    "chr": ""
  },
  "aliases": {
    "en": ["Cherokee", "Cherokee Tribe"],
    "chr": []
  }
}
```

### Multilingual Field Definitions

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labels` | `dict[lang_code, string]` | `{}` | Primary names in each language (max 1 per language) |
| `descriptions` | `dict[lang_code, string]` | `{}` | Short definitions in each language (empty string if not provided) |
| `aliases` | `dict[lang_code, list[string]]` | `{}` | Alternative names per language (empty array if none provided) |

**Language Codes**: Any Wikimedia-supported language code (e.g., `en`, `chr`, `nv`, `es`)

**Completeness Rules**:
- Progress tracking includes: `2 (base) + num_languages_in_profile * 2`
- Required languages (from profile): must have non-empty label + description
- Optional languages: any provided are counted toward completion

---

## Statements

### Structure

```json
{
  "statements": {
    "instance_of": [
      {
        "value": "Q7840353",
        "qualifiers": {
          "point_in_time": [
            {
              "value": "2020-01-15"
            }
          ]
        },
        "references": [
          {
            "stated_in": "Q4168174",
            "reference_url": "https://example.com/source"
          }
        ]
      }
    ],
    "member_count": [
      {
        "value": {
          "amount": 150000,
          "unit": null
        },
        "qualifiers": {},
        "references": [
          {
            "stated_in": "Q123456"
          }
        ]
      }
    ]
  }
}
```

### Statement Object

```json
{
  "value": <datatype-specific>,
  "qualifiers": {
    "<property_id>": [
      {
        "value": <datatype-specific>,
        "qualifiers": {}  // Qualifiers can nest; typically empty
      }
    ]
  },
  "references": [
    {
      "<property_id>": <datatype-specific>,
      "<property_id>": <datatype-specific>
    }
  ],
  "validation_issues": [
    {
      "severity": "warning",
      "message": "...",
      "suggestion": "..."
    }
  ]
}
```

### Datatype-Specific Values

#### Item (wikibase-item)
```json
"value": "Q7840353"  // QID as string; validation ensures Q-prefixed format
```

#### String (string)
```json
"value": "Some text content"
```

#### Time (time)
Stored in normalized format with precision:
```json
"value": {
  "value": "+2020-01-15T00:00:00Z",  // ISO 8601 with precision
  "precision": 11  // Wikidata precision level: 9=year, 10=month, 11=day
}
```

#### Quantity (quantity)
```json
"value": {
  "amount": 150000,
  "unit": null  // null if unitless; else Q-string if unit exists
}
```

#### Monolingual Text (monolingualtext)
```json
"value": {
  "language": "en",
  "text": "Cherokee Nation"
}
```

#### URL (url)
```json
"value": "https://example.com/source"
```

#### External ID (external-id)
```json
"value": "12345"  // As string; no Q-prefix
```

#### Commons Media (commonsMedia)
```json
"value": "File:Example.jpg"
```

#### Globe Coordinate (globe-coordinate)
```json
"value": {
  "latitude": 35.5,
  "longitude": -95.3
}
```

---

## Sitelinks

```json
{
  "sitelinks": {
    "enwiki": "Cherokee_Nation",
    "chrwiki": "ᎳᎫᎿ_ᎠᏰᎲ"
  }
}
```

Follows Wikidata's sitelink model: `<language_project>: <article_title>`

---

## Completeness Calculation

### Formula

```
required_fields_total = 2 + num_statements + (2 * num_profile_languages)
completed_fields = count(non_empty_labels_in_required_languages) 
                 + count(non_empty_descriptions_in_required_languages)
                 + count(statements_with_at_least_one_value)

progress_pct = completed_fields / required_fields_total * 100
progress_text = f"{completed_fields} of {required_fields_total} required elements"
```

### Example

Profile: `TribalGovernmentUS` with:
- 2 required languages (en, chr)
- 8 statements

```
required_fields_total = 2 + 8 + (2 * 2) = 14

// After curator fills:
// - en label ✅
// - en description ✅
// - chr label ❌
// - chr description ❌
// - instance_of statement ✅
// - member_count statement ✅
// - (remaining 6 statements unfilled)

completed_fields = 4  // (en labels + en desc + 2 statements)
progress = "4 of 14 required elements" (29%)
```

---

## Validation Rules

### Schema Compliance

- All metadata fields present (null allowed for `status` in some contexts)
- Labels/descriptions/aliases structured as language-keyed dicts
- Statements keyed by property ID with array values
- All values conform to datatype rules (validated by the Validation Agent)

### Completeness Validation

- Required languages: must have non-empty label + description
- Required statements: at minimum one value per required statement
- Cross-entity references: must reference valid `packet_id` in same packet (or omitted if not yet resolved)

### Transitive Reference Resolution (Post-Shipping)

When shipping to Wikidata:
1. Create secondary entities first (depth-first traversal)
2. Collect returned QIDs
3. Hydrate cross-entity references in primary entity with resolved QIDs
4. Create primary entity with hydrated references

---

## Multi-Entity Curation Packets

When multiple related entities are curated together (e.g., tribal government + executive office), they exist as a **Curation Packet** containing multiple GKC Entity JSON objects.

### Packet Structure

```json
{
  "packet_version": "1.0.0",
  "created_at": "2026-03-02T14:32:00Z",
  "entities": [
    {
      "packet_id": "ent-001-primary",
      "profile_name": "TribalGovernmentUS",
      "creation_path": "primary",
      "statements": {
        "office_held_by_head_of_state": [
          {
            "value": "ent-002-office",  // References packet_id of related entity
            "qualifiers": {},
            "references": [...]
          }
        ]
      }
    },
    {
      "packet_id": "ent-002-office",
      "profile_name": "OfficeHeldByHeadOfState",
      "creation_path": "primary.office_held_by_head_of_state",
      "statements": { ... }
    }
  ]
}
```

### Packet Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `packet_version` | string | Schema version (for migrations); current: "1.0.0" |
| `created_at` | string (ISO 8601) | When packet was created |
| `entities` | array | Array of GKC Entity JSON objects |

### Cross-Entity References via `packet_id`

Entities within a packet reference each other using **packet-local identifiers** rather than Wikidata QIDs:

- **During curation**: Statement values use `packet_id` strings (e.g., `"ent-002-office"`)
- **After shipping**: Shipper resolves `packet_id` → QID and replaces values before creating Wikidata items

**Example workflow:**

1. User creates tribal government entity (`ent-001-primary`)
2. User creates office entity via sub-wizard (`ent-002-office`)
3. Tribal government's `office_held_by_head_of_state` statement has value `"ent-002-office"`
4. Shipper creates office first → receives QID `Q999888`
5. Shipper replaces `"ent-002-office"` with `"Q999888"` in tribal government before shipping
6. Tribal government created with correct P1906 reference

### Creation Path Breadcrumbs

The `creation_path` field tracks entity provenance:

| Creation Path | Meaning |
|---------------|---------|
| `primary` | Root entity; loaded directly by wizard or bulk operation |
| `primary.office_held_by_head_of_state` | Created via statement on primary entity |
| `primary.headquarters.location` | Nested entity (location of headquarters of primary) |

**Uses:**

- **Dependency ordering**: Ship entities depth-first (leaves before roots)
- **Audit trails**: Understand how curator created complex entity graphs
- **Rollback logic**: If primary creation fails, skip dependent entities

### Packet Lifecycle States

Tracked via `status` field on individual entities:

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `in_progress` | Curator actively editing | Continue curation |
| `ready_to_resolve_refs` | All data entered; awaiting cross-entity QID resolution | Ship to Wikidata |
| `waiting_for_qid` | Shipped to Wikidata; awaiting item creation response | Poll API or mark complete |

---

## Profile Graph Integration

Curation packets reflect the **profile graph** — the network of profiles connected via `entity_profile` statements.

### Profile Graph Discovery

When wizard loads `TribalGovernmentUS` profile, it:

1. Scans statements for `entity_profile` type
2. Finds `office_held_by_head_of_state` statement with `profile_name: OfficeHeldByHeadOfState`
3. Recursively loads `OfficeHeldByHeadOfState` profile
4. Creates packet with placeholders for both entities

### Loading Strategy

**Current implementation:** Depth = 1 (direct children only)

- Primary profile → directly linked profiles
- Does **not** recursively load links-of-links

**Future:** Configurable depth or lazy loading:

```yaml
# In metadata.yaml
profile_graph:
  edges:
    - target_profile: OfficeHeldByHeadOfState
      loading_strategy: eager  # vs "lazy" (load on-demand)
      max_depth: 2  # How many hops to traverse
```

### Multi-Entity Packet Example

**Scenario:** User creates Cherokee Nation (tribal government) with its Principal Chief office

**Profile linkage:**

```
TribalGovernmentUS (primary)
  └─ office_held_by_head_of_state: OfficeHeldByHeadOfState (related)
```

**Resulting packet:**

```json
{
  "packet_version": "1.0.0",
  "created_at": "2026-03-03T10:00:00Z",
  "entities": [
    {
      "packet_id": "ent-001-primary",
      "profile_name": "TribalGovernmentUS",
      "creation_path": "primary",
      "labels": { "en": "Cherokee Nation" },
      "statements": {
        "office_held_by_head_of_state": [
          { "value": "ent-002-office" }
        ]
      }
    },
    {
      "packet_id": "ent-002-office",
      "profile_name": "OfficeHeldByHeadOfState",
      "creation_path": "primary.office_held_by_head_of_state",
      "labels": { "en": "Principal Chief of the Cherokee Nation" },
      "statements": {
        "applies_to_jurisdiction": [
          { "value": "ent-001-primary" }  // Bidirectional reference
        ]
      }
    }
  ]
}
```

**Note:** Bidirectional references are allowed and encouraged for semantic clarity.

---

## Bulk Operations

Curation packets support bulk data operations where multiple existing entities are loaded, modified, and re-shipped together.

### Bulk vs Single-Entity Packets

| Aspect | Single-Entity | Bulk Operation |
|--------|---------------|----------------|
| **Packet size** | 1-3 entities (primary + related) | 10-1000+ entities |
| **Entity source** | New entities from scratch | Existing Wikidata items |
| **Modification scope** | All statements editable | Subset of statements (filtered) |
| **Workflow** | Wizard step-by-step | Automated or semi-automated |

### Statement Filtration

Bulk operations often target **specific statements** rather than full entities.

**Example:** "Update member_count and office leadership for all federally recognized tribes"

**Packet structure:**

```json
{
  "packet_version": "1.0.0",
  "operation_mode": "bulk",  // Indicates bulk operation
  "enabled_statements": [     // Whitelist of editable statements
    "member_count",
    "office_held_by_head_of_state"
  ],
  "entities": [
    {
      "packet_id": "bulk-001-Q5093",  // QID embedded for existing items
      "profile_name": "TribalGovernmentUS",
      "wikidata_qid": "Q5093",  // Original QID
      "statements": {
        "member_count": [
          { "value": { "amount": 450000, "unit": null } }
        ]
        // Other statements NOT loaded or editable
      }
    },
    // ... 99 more tribal governments
  ]
}
```

**Dot notation** for nested statements:

```json
"enabled_statements": [
  "office_held_by_head_of_state.inception",  // Only edit inception date of office
  "office_held_by_head_of_state.references"  // Only add references, not change office
]
```

### Validation in Bulk Operations

- **Schema validation**: Same as single-entity (all fields must conform)
- **Completeness validation**: **Relaxed** (can ship partial entities with only modified statements)
- **Cross-entity validation**: Can span multiple entities in packet (e.g., "all member counts must be > 0")

**Future:** Bulk operation templates that define:

- Which profiles to query
- Which statements are modifiable
- Validation rules specific to bulk context

---

## Round-Trip Transformation

Packets support **bidirectional transformation** between GKC Entity JSON and platform-specific formats (Wikidata JSON, Wikimedia Commons JSON, etc.).

### Wikidata JSON → GKC Entity JSON

**Use case:** Load existing Wikidata item into wizard for editing

**Transformation steps:**

1. Fetch Wikidata JSON via `wbgetentities` API
2. Load profile for entity type (determined by P31 instance-of value)
3. Transform Wikidata claims → GKC statements:
   - Property IDs (P31) → statement IDs (instance_of)
   - Wikidata datatypes → GKC value types
   - Qualifiers and references preserved
4. Generate `packet_id` and `creation_path` metadata
5. Set `status: in_progress` for editing session

**Example:**

```json
// Wikidata JSON (abbreviated)
{
  "entities": {
    "Q5093": {
      "labels": { "en": { "value": "Cherokee Nation" } },
      "claims": {
        "P31": [
          {
            "mainsnak": { "datavalue": { "value": { "id": "Q7840353" } } },
            "references": [...]
          }
        ]
      }
    }
  }
}

// GKC Entity JSON (transformed)
{
  "packet_id": "ent-001-primary",
  "profile_name": "TribalGovernmentUS",
  "wikidata_qid": "Q5093",  // Preserve original QID
  "labels": { "en": "Cherokee Nation" },
  "statements": {
    "instance_of": [
      { "value": "Q7840353", "references": [...] }
    ]
  }
}
```

### GKC Entity JSON → Wikidata JSON

**Use case:** Ship curation packet to Wikidata

**Transformation steps:**

1. Resolve `packet_id` references → QIDs (create secondary entities first)
2. Transform GKC statements → Wikidata claims:
   - Statement IDs (instance_of) → Property IDs (P31)
   - GKC value types → Wikidata datatypes
   - Validate all values conform to Wikidata constraints
3. Generate Wikidata JSON structure
4. Call `wbeditentity` API with bot credentials

**Depth-first shipping:**

```
ent-002-office (no dependencies) → Ship first → Q999888
ent-001-primary (depends on office) → Replace "ent-002-office" with "Q999888" → Ship second → Q999889
```

### Sitelinks: Wikidata Format ↔ URL Format

**Current state:** Sitelinks stored in Wikidata format (`enwiki: "Article_Title"`)

**Future enhancement:** URL-based curation format

```json
// GKC Entity JSON (curation format) - FUTURE
{
  "sitelinks": [
    {
      "url": "https://en.wikipedia.org/wiki/Cherokee_Nation",
      "relationship": "primary",  // Article is exclusively about this entity
      "verified": true  // URL existence validated
    }
  ]
}

// Transformed to Wikidata format for shipping
{
  "sitelinks": {
    "enwiki": {
      "site": "enwiki",
      "title": "Cherokee_Nation"
    }
  }
}
```

**Bidirectional:** Existing Wikidata sitelinks reconstruct URL for editing; saved URLs parse to Wikidata format.

### Profile-Driven Transformation

**Key principle:** All transformation logic derives from profile metadata

- Profile declares Wikidata property mappings (`P31`, `P1906`, etc.)
- Profile declares datatype conversions (quantity → Wikidata quantity format)
- Profile declares sitelink rules (allowed languages, allowed projects)

**No hardcoded entity-specific logic** — transformer reads profile and applies rules dynamically.

---

## Complete Example

```json
{
  "packet_version": "1.0.0",
  "created_at": "2026-03-02T14:32:00Z",
  "entities": [
    {
      "packet_id": "ent-001-primary",
      "profile_name": "TribalGovernmentUS",
      "username": "skybristol",
      "status": "in_progress",
      "created_at": "2026-03-02T14:32:00Z",
      "creation_path": "primary",
      
      "labels": {
        "en": "Cherokee Nation",
        "chr": ""
      },
      "descriptions": {
        "en": "Federally recognized Native American tribe based in Oklahoma",
        "chr": ""
      },
      "aliases": {
        "en": ["Cherokee", "Cherokee Tribe"],
        "chr": []
      },
      
      "statements": {
        "instance_of": [
          {
            "value": "Q7840353",
            "qualifiers": {},
            "references": [
              {
                "stated_in": "Q4168174",
                "retrieved": "+2026-03-02T00:00:00Z"
              }
            ]
          }
        ],
        "member_count": [
          {
            "value": {
              "amount": 380000,
              "unit": null
            },
            "qualifiers": {
              "point_in_time": [
                {
                  "value": {
                    "value": "+2023-01-01T00:00:00Z",
                    "precision": 9
                  }
                }
              ]
            },
            "references": [
              {
                "stated_in": "Q123456"
              }
            ]
          }
        ]
      },
      
      "sitelinks": {
        "enwiki": "Cherokee_Nation",
        "chrwiki": "ᎳᎫᎿ_ᎠᏰᎲ"
      }
    }
  ]
}
```

---

## Wizard Integration Contract

### Input: Loading Existing Entity

When wizard loads a saved packet (draft or for editing):
1. Deserialize curation packet JSON
2. Validate schema compliance (all fields present, correct types)
3. Pass to step renderers as `draft_data`
4. Steps read/write per multilingual structure

### Output: Saving Curation Packet

After each step or on explicit save:
1. Serialize `draft_data` to curation packet format
2. Write to disk (transient or permanent)
3. On submission, validate completeness + pass to shipper

### Error Handling

- **Schema violations**: Block load; display which fields are malformed
- **Completeness warnings**: Display in Review step; allow save (non-blocking)
- **Cross-entity validation failures**: Mark in `validation_issues` array per entity

---

## Future Extensions

1. **Annotation trails**: Add `audit_log` per entity tracking changes
2. **Conflict resolution**: Support concurrent multi-curator editing with merge strategies
3. **Version history**: Store historical snapshots for rollback
4. **Automated filling**: Pre-populate from external sources (DBpedia, Wikidata, etc.)
5. **Quality scoring**: Calculate confidence/completeness beyond binary checklist

---

## Related Documentation

- [GKC Architecture Overview](../architecture/index.md) — Core architectural components and data flow
- [GKC Entity Profiles](./profiles.md) — Complete profile schema reference
- [GKC Wizard Documentation](./wizard.md) — Multi-entity curation workflows
- [Profile Graphs & Cross-References](./profiles.md#profile-graphs-cross-references) — How profiles link together
- [Validation Architecture](../architecture/validation-architecture.md) — Real-time validation/coercion engine

