# Reference and Qualifier Patterns

## Overview

The mapping format uses a **consistent structure** for claims, references, and qualifiers. All use `"property"` as a field (not property-as-key), making the format intuitive and easy to learn.

You can define reusable references and qualifiers in **two ways**:
1. **Explicit Library** - Define upfront in dedicated sections
2. **Inline Named** - Define on first use with a `"name"` attribute

## Consistent Structure

All three elements use the same structure:

```json
{
  "property": "P31",
  "value": "Q7840353",
  "datatype": "wikibase-item"
}
```

This consistency makes the mapping format easier to understand and reduces cognitive load.

## Pattern 1: Explicit Library (Top-Down)

Define reusable patterns upfront in dedicated library sections.

**Best for:**
- Patterns used across multiple mappings
- Organization-wide standards
- When you want all reusable elements visible at the top
- Documentation-first workflow

**Example:**

```json
{
  "reference_library": {
    "federal_register": [
      {
        "property": "P248",
        "value": "Q127419548",
        "datatype": "wikibase-item"
      }
    ]
  },
  "mappings": {
    "claims": [
      {
        "property": "P31",
        "value": "Q7840353",
        "references": [{"name": "federal_register"}]
      }
    ]
  }
}
```

## Pattern 2: Inline Named (Bottom-Up)

Define patterns inline on first use with a `"name"` attribute, then reference by name elsewhere.

**Best for:**
- Patterns specific to one mapping
- Organic, discover-as-you-go workflow
- Co-location (definition near usage)
- When you realize reuse potential while building

**Example:**

```json
{
  "mappings": {
    "claims": [
      {
        "property": "P30",
        "value": "Q49",
        "references": [
          {
            "name": "inferred_from_hq",
            "property": "P887",
            "value": "Q131921702",
            "datatype": "wikibase-item"
          }
        ]
      },
      {
        "property": "P17",
        "value": "Q30",
        "references": [{"name": "inferred_from_hq"}]
      }
    ]
  }
}
```

## Using Both Patterns

Mix explicit library and inline named in the same mapping:

```json
{
  "reference_library": {
    "federal_register": [
      {
        "property": "P248",
        "value": "Q127419548",
        "datatype": "wikibase-item"
      }
    ]
  },
  "mappings": {
    "claims": [
      {
        "property": "P31",
        "references": [{"name": "federal_register"}]
      },
      {
        "property": "P30",
        "references": [
          {
            "name": "local_inference",
            "property": "P887",
            "value": "Q131921702",
            "datatype": "wikibase-item"
          }
        ]
      },
      {
        "property": "P17",
        "references": [{"name": "local_inference"}]
      }
    ]
  }
}
```

## How It Works

1. **Initialization:** Distillate scans all claims and extracts inline named references/qualifiers
2. **Merging:** Inline named patterns are merged into the library
3. **Precedence:** Explicit library entries take precedence if names collide
4. **Resolution:** During transformation, all string references resolve from the combined library

**Performance:** O(n) - very efficient, no performance penalty

## Reference Types

### Name-Only Object (Library Lookup)
```json
"references": [{"name": "library_name"}]
```

### Inline Named (Define + Reuse)
```json
"references": [
  {
    "name": "my_pattern",
    "property": "P248",
    "value": "Q12345",
    "datatype": "wikibase-item"
  }
]
```

### Inline Unnamed (One-Off)
```json
"references": [
  {
    "property": "P248",
    "value": "Q12345",
    "datatype": "wikibase-item"
  }
]
```

### Multi-Property Reference (Option A)
All properties in the array form **one reference block**:
```json
"references": [
  {"property": "P248", "value": "Q12345", "datatype": "wikibase-item"},
  {"property": "P813", "value": "current_date", "datatype": "time"}
]
```

## When to Use What

| Scenario | Pattern |
|----------|---------|
| Organization-wide source (Federal Register) | Explicit Library |
| Mapping-specific inference rule | Inline Named |
| Unique, one-time reference | Inline Unnamed |
| Mix of standard + specific patterns | Both |

## Examples

- **Explicit Library:** See [tribe_mapping_example.json](https://github.com/skybristol/gkc/blob/main/examples/mappings/tribe_mapping_example.json)
- **Inline Named:** See [inline_named_pattern_example.py](https://github.com/skybristol/gkc/blob/main/examples/inline_named_pattern_example.py)
- **Both Patterns:** See [fed_tribe_from_missing_ak_tribes.json](https://github.com/skybristol/gkc/blob/main/examples/mappings/fed_tribe_from_missing_ak_tribes.json)

## Migration

If you have existing inline references without names, you can:
1. Keep them as-is (inline unnamed) for one-off uses
2. Add `"name"` attribute if you want to reuse them
3. Move to explicit library if they're organization-wide

No breaking changes - all existing patterns still work!
