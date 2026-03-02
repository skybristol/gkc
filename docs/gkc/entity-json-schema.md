# GKC Entity JSON Schema

**Purpose:** Define the canonical internal data format for entity curation within the GKC Wizard and broader Data Distillery ecosystem. This schema bridges [profile](./profiles.md) definitions (YAML) with curator input (form data) and eventual serialization (Wikidata JSON, Wikimedia Commons JSON, etc. distributed to Global Knowledge Commons partners).

---

## Overview

The **GKC Entity JSON** is a JSON object representing a single entity being curated through Data Distillery actions. When multiple related entities are created in sequence (e.g., primary tribal government + linked office entity), they exist as an array of GKC Entity JSON objects within a **Curation Packet**.

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

## Curation Packet Format

When multiple entities exist in a single curation session:

```json
{
  "packet_version": "1.0.0",
  "created_at": "2026-03-02T14:32:00Z",
  "entities": [
    { /* GKC Entity JSON for entity 1 */ },
    { /* GKC Entity JSON for entity 2 */ },
    { /* ... */ }
  ]
}
```

### Packet Metadata

| Field | Type | Description |
|-------|------|-------------|
| `packet_version` | string | Schema version (for migrations) |
| `created_at` | string (ISO 8601) | When packet was created |
| `entities` | array | Array of GKC Entity JSON objects |

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

- [Profile Schema](./profiles.md) — How profiles define entity structure
- Validation Requirements — Real-time validation/coercion specifications (see `.github/prompts/ValidationAgent.working.md`)
- Shipper Module — How GKC Entity JSON → Wikidata JSON conversion happens (future)
