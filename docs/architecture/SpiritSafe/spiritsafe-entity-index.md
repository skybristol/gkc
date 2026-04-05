# SpiritSafe Entity Index Architecture

## Overview

The SpiritSafe Entity Index (`cache/entity_index.json`) is a normalized, derived artifact that accelerates runtime lookups and enables efficient metadata discovery without traversing raw Wikibase JSON structures.

**Plain meaning:** The entity index is a pre-computed registry of all semantics and links encoded in the Data Distillery Wikibase, organized for fast lookups by entity, class membership, and link relationship type.

## Purpose

The entity index solves several runtime efficiency problems:

1. **Semantic Normalization** - Raw Wikibase JSON requires traversing nested claim structures. The index provides flat, direct access to extracted metadata (classes, links, guidance messages, cardinality) for each entity.

2. **Class Membership** - Queries like "what entities are value lists?" or "what statements apply to this profile?" require O(n) scans of raw cache without an index. The class-index partition enables O(1) class membership lookups.

3. **Link Metadata** - References between entities (statements to statements, statements to qualifiers, etc.) carry scoping information. The index materializes these relationships with scope metadata pre-extracted so consumers can apply lightweight membership tests rather than reparsing claims.

4. **Downstream Consumer Efficiency** - Validation engine and wizard form generation benefit from pre-normalized, searchable metadata structures. Consumers query the index instead of writing custom Wikibase JSON traversal code.

## Build Process

The entity index is built as part of the standard `spiritsafe manifest build` CLI command:

```bash
gkc --json spiritsafe manifest build --source local --local-root /path/to/SpiritSafe
```

This produces:
- `cache/manifest.json` - registry index
- `cache/entity_index.json` - normalized entity and class metadata (**new**)

Build implementation:
- Iterates all JSON files in `cache/entities/`
- Normalizes each entity's metadata (see [Index Entry Schema](#index-entry-schema) below)
- Builds class-index partition for O(1) class membership lookups
- Writes JSON to `entity_index.json`

## Index Entry Schema

Each entity in the index produces a normalized entry with the following structure:

```json
{
  "id": "Q4",
  "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
  "label": "Whiskey",
  "name_identifier": "whiskey",
  "classes": ["Q3", "Q7"],
  "value_type": "Q44_item",
  "io_map": [
    {
      "to": "https://www.wikidata.org/entity/P31",
      "value_transform": null
    }
  ],
  "max_count": null,
  "messages": {
    "en": {
      "prompt": "Whiskey type",
      "guidance": "Select the appropriate whiskey category",
      "consequences": "This sets the primary classification",
      "error": "Classification is required"
    }
  },
  "links": {
    "statements": [
      {
        "target": "https://datadistillery.wikibase.cloud/entity/Q19",
        "scope": {
          "profiles": ["Q4"],
          "statements": []
        }
      }
    ],
    "qualifiers": [
      {
        "target": "https://datadistillery.wikibase.cloud/entity/Q51",
        "scope": {
          "profiles": [],
          "statements": []
        }
      }
    ],
    "references": [],
    "values": [
      {
        "target": "https://datadistillery.wikibase.cloud/entity/Q52",
        "scope": null
      }
    ],
    "derives_default_value_from": [
      {
        "target": "https://datadistillery.wikibase.cloud/entity/Q29",
        "scope": {
          "profiles": ["Q4"],
          "statements": []
        }
      }
    ]
  }
}
```

### Key Fields

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | QUID of the entity (e.g., "Q4") |
| `entity` | string | Full IRI of the entity in the Data Distillery Wikibase |
| `label` | string | English label from entity metadata |
| `name_identifier` | string | Machine-readable identifier (from P214) |
| `classes` | array[string] | List of class QUIDs this entity belongs to (from P1 claims) |
| `value_type` | string | Primitive datatype hint (from P194, e.g., "Q44_item", "Q44_string") |
| `io_map` | array[object] | Directional routing definitions (to/from Wikidata, external systems) |
| `max_count` | integer\|null | Cardinality constraint; null = no limit |
| `messages` | object | Multilingual UI text (prompts, guidance, error messages) |
| `links` | object | Semantic relationships to other entities, organized by link type |

### Link Types

The `links` object organizes relationships by semantic role:

- **`statements`** - Entities declared as allowed statements for this entity (from P157)
- **`qualifiers`** - Entities declared as allowed qualifiers (from P158)
- **`references`** - Entities declared as allowed references (from P211)
- **`values`** - Entities declared as allowed values (from P161)
- **`derives_default_value_from`** - Entities from which this entity derives default values (from P213)

Each link entry is an object:

```json
{
  "target": "https://datadistillery.wikibase.cloud/entity/Q19",
  "scope": {
    "profiles": ["Q4"],
    "statements": ["official_website"]
  }
}
```

**`target`**: IRI of the linked entity.

**`scope`** (optional): Scoping constraints extracted from P205 (applies to profile) and P163 (applies to statement) qualifiers:
- `profiles`: If non-empty, link applies only within these profiles
- `statements`: If non-empty, link applies only within these statement contexts

When `scope` is `null`, the link is globally applicable with no profile or statement constraints.

### Class Index Format

The top-level `class_index` object provides O(1) membership lookups:

```json
{
  "class_index": {
    "Q3": ["Q4", "Q29", "Q39"],
    "Q5": ["Q19", "Q28"],
    "Q7": ["Q4", "Q39"],
    "Q44": ["Q43", "Q51", "Q54"]
  }
}
```

For each class QUID, members are an array of entity QUIDs belonging to that class. This enables fast queries like:
- "Is Q4 a profile?" → check `class_index.Q3.contains(Q4)`
- "What are all the value lists?" → iterate `class_index.Q7`

### Top-Level Structure

The complete entity_index.json:

```json
{
  "generated_at": "2026-03-21T10:15:30.123456Z",
  "source": "cache/entities",
  "entity_count": 47,
  "class_count": 8,
  "entities": {
    "Q1": { ... },
    "Q3": { ... },
    "Q4": { ... }
  },
  "class_index": {
    "Q3": ["Q4", "Q29"],
    "Q5": ["Q19", "Q28"]
  }
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `generated_at` | string | ISO 8601 timestamp of index generation |
| `source` | string | Path to the entities directory this index was built from |
| `entity_count` | integer | Number of entities in the index |
| `class_count` | integer | Number of distinct classes |
| `entities` | object | Entity QUID → normalized entry mapping |
| `class_index` | object | Class QUID → member QUIDs mapping |

## Semantic Mapping Reference

The entity index extraction normalizes the following Data Distillery Wikibase properties and classes:

### Properties Extracted as Index Fields

| Property | Index Field | Meaning |
|----------|------------|---------|
| P1 | `classes` | Entity's class memberships |
| P5 | `io_map` | Directional routing to Wikidata/external systems |
| P157 | `links.statements` | Linked statement definitions |
| P158 | `links.qualifiers` | Linked qualifier definitions |
| P161 | `links.values` | Linked value definitions |
| P182 | `max_count` | Cardinality constraint |
| P194 | `value_type` | Primitive datatype hint |
| P205 | scope.profiles | Profile applicability qualifier |
| P211 | `links.references` | Linked reference definitions |
| P212 | (reference item identity) | Fixed-value marker via Q52 target class |
| P213 | `links.derives_default_value_from` | Default-value inheritance markers |
| P214 | `name_identifier` | Machine-readable identifier |
| P168/P169/P170/P171 | `messages.{error\|guidance\|consequences\|prompt}` | UI text by language |

### Class Hierarchy Recognized

| Class | Meaning |
|-------|---------|
| Q3 | Profile entity class — appears in index as entity AND class_index entry |
| Q5 | Statement class — appears in index with link relationships |
| Q7 | Value list class — appears in index; enables value-list hierarchy |
| Q44 | Datatype templates — extracted for `value_type` mapping |
| Q50+ | Vendor/reference items — appear in index as referenceable entities |

## Runtime Consumption Patterns

### For Validation Engine

```python
from gkc.spirit_safe import load_spiritsafe_entity_index

index = load_spiritsafe_entity_index('/path/to/SpiritSafe')

# Fast lookup: what statements apply to profile Q4?
profile_statements = index['entities']['Q4']['links']['statements']
applicable_qids = [link['target'] for link in profile_statements 
                   if 'Q4' in (link.get('scope', {}) or {}).get('profiles', [])]

# Class membership: is entity a profile?
is_profile = 'Q3' in index['entities'][qid]['classes']

# Value list discovery: get all value lists from class index
value_lists = index['class_index'].get('Q7', [])
```

### For Form Generation

The index provides pre-organized metadata for form generation:

- Use entity `labels` for display text
- Use entity `messages` for prompts and guidance
- Use `links.values` to populate value pickers
- Use `links.statements` to determine allowed statement types for a profile
- Use scope metadata to filter link relationships by profile/statement context

### For Profile Loading/Validation

The entity index replaces repeated Wikibase JSON traversal with indexed lookups:

- Lookup statement metadata: `entities[statement_qid]`
- Verify cardinality: `entities[qid]['max_count']`
- Check class membership: `'Q5' in entities[qid]['classes']`
- Find allowed qualifiers: `entities[statement_qid]['links']['qualifiers']`

## Lifecycle and Updates

The entity index **regenerates** on each `spiritsafe manifest build` CLI run. It is a **deterministic derived artifact** — same input cache produces identical output (up to timestamp).

The index is **committed to version control** alongside `manifest.json` so that:
1. SpiritSafe remains offline-capable
2. CI/CD workflows can validate index correctness
3. Downstream consumers have predictable artifact availability

When Wikibase is updated:
1. `gkc spiritsafe manifest build` refreshes `cache/entities/` and regenerates index
2. Commit includes both manifest and entity_index updates
3. All consumers pull new version (if using SpiritSafe via GitHub)

## Future Extensions

The index is designed to support future enhancements:

- **Qualified relationship metadata** — links could carry additional metadata (e.g., `inverse_of`, `transitive`) for graph traversal
- **Profile-specific views** — derived index sections optimized for specific profiles (e.g., "only links applicable to Q4")
- **Statement-context indexes** — specialized partitions for reference-finding by statement parent
- **Analytics** — entity/link statistics for registry diagnostics and wizard UX optimization

These remain theoretical design notes and do not require index format changes.

## Examples

### Example 1: Find all statements in a profile

Given profile Q4, retrieve all linked statements with their labels:

```python
import json
from pathlib import Path

def get_profile_statements(index, profile_qid):
    profile = index['entities'][profile_qid]
    statements = []
    for link in profile['links']['statements']:
        stmt_qid = link['target'].split('/')[-1]
        stmt = index['entities'][stmt_qid]
        statements.append({
            'qid': stmt_qid,
            'label': stmt['label'],
            'scope': link.get('scope')
        })
    return statements
```

### Example 2: Build value picker for statement

Given a statement, get all allowed values with labels and class info:

```python
def get_statement_values(index, statement_qid):
    statement = index['entities'][statement_qid]
    values = []
    for link in statement['links']['values']:
        value_qid = link['target'].split('/')[-1]
        value = index['entities'][value_qid]
        values.append({
            'qid': value_qid,
            'label': value['label'],
            'classes': value['classes'],
            'scope': link.get('scope')
        })
    return values
```

### Example 3: Validate required fields

Check if an entity provides all expected guidance fields:

```python
def check_completeness(index, qid, language='en'):
    entity = index['entities'][qid]
    messages = entity.get('messages', {}).get(language, {})
    required_keys = {'prompt', 'guidance', 'error'}
    missing = required_keys - set(messages.keys())
    return {
        'complete': len(missing) == 0,
        'missing_fields': list(missing)
    }
```

## Notes for Contribution

- The entity index should **never be hand-edited**. All changes flow through Wikibase → cache refresh → index rebuild.
- If the index structure needs to change, coordinate through the normal architecture review path.
- Index test fixtures should be regenerated whenever Wikibase semantics changes (via `gkc spiritsafe manifest build` on test SpiritSafe repo).
- For offline development, a test fixture entity_index.json should exist in `tests/fixtures/` with representative Q3/Q5/Q7/Q44 entities.

