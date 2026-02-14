# Mapping Format Migration Guide

## Overview

The mapping configuration format has been refactored to provide a more consistent and maintainable structure. This guide explains the changes and how to migrate existing mappings.

## Key Changes

### 1. Eliminated Separate "Defaults" Section

**Before:**
```json
{
  "mappings": {
    "claims": [...]
  },
  "defaults": {
    "claims": {
      "P31": "Q7840353",
      "P30": "Q49"
    }
  }
}
```

**After:**
All claims are now in the unified `claims` array. Fixed-value claims use `"value"` instead of `"source_field"`:

```json
{
  "mappings": {
    "claims": [
      {
        "property": "P31",
        "value": "Q7840353",
        "datatype": "wikibase-item",
        "comment": "Instance of: federally recognized tribe"
      },
      {
        "property": "P30",
        "value": "Q49",
        "datatype": "wikibase-item",
        "comment": "Continent: North America"
      }
    ]
  }
}
```

## Reference and Qualifier Libraries

**New Feature:** Define reusable reference and qualifier patterns in two ways:

### Option 1: Explicit Library (Recommended for widely-used patterns)

Define reusable patterns upfront in dedicated library sections:

**Structure:**
```json
{
  "reference_library": {
    "stated_in_federal_register": {
      "P248": {
        "value": "Q127419548",
        "datatype": "wikibase-item",
        "comment": "Stated in: Federal Register"
      },
      "P813": {
        "value": "current_date",
        "datatype": "time",
        "comment": "Retrieved date"
      }
    }
  },
  "qualifier_library": {
    "point_in_time": {
      "property": "P585",
      "source_field": "date_field",
      "datatype": "time"
    }
  }
}
```

### Option 2: Inline Named (Best for patterns used within one mapping)

Define patterns inline on first use with a `"name"` attribute, then reference by name:

**Structure:**
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
            "P887": {
              "value": "Q131921702",
              "datatype": "wikibase-item"
            }
          }
        ]
      },
      {
        "property": "P17",
        "value": "Q30",
        "references": ["inferred_from_hq"]  // Reuse by name
      }
    ]
  }
}
```

### Using Both Patterns Together

You can mix both approaches in the same mapping:

```json
{
  "reference_library": {
    "federal_register": { /* explicit definition */ }
  },
  "mappings": {
    "claims": [
      {
        "property": "P31",
        "value": "Q7840353",
        "references": ["federal_register"]  // From explicit library
      },
      {
        "property": "P30",
        "value": "Q49",
        "references": [
          {
            "name": "inferred_from_hq",  // Define inline
            "P887": {"value": "Q131921702", "datatype": "wikibase-item"}
          }
        ]
      },
      {
        "property": "P17",
        "value": "Q30",
        "references": ["inferred_from_hq"]  // Reuse inline named
      }
    ]
  }
}
```

### Choosing Your Approach

**Use Explicit Library when:**
- Pattern will be used across multiple mappings
- You want all reusable elements visible upfront
- Pattern is organization-standard (e.g., "stated in Federal Register")
- You prefer top-down documentation style

**Use Inline Named when:**
- Pattern is specific to this mapping only
- You discover the pattern while building claims
- You want co-location (definition near usage)
- You prefer bottom-up, organic development style

**Use Both when:**
- You have some standard patterns AND some mapping-specific patterns
- You want flexibility in your workflow

## Consistent Structure (v2.0)

**Important:** As of version 2.0, the format uses a **consistent structure** for all elements:

- Claims: `"property": "P31"`
- References: `"property": "P248"` (not property-as-key)
- Qualifiers: `"property": "P585"` (not property-as-key)

Library entries are now arrays of property objects:

```json
"reference_library": {
  "my_reference": [
    {"property": "P248", "value": "Q123", "datatype": "wikibase-item"},
    {"property": "P813", "value": "current_date", "datatype": "time"}
  ]
}
```

References use name-only objects (not strings):

```json
"references": [{"name": "my_reference"}]
```

**Usage in Claims:**

Instead of inline references:
```json
{
  "property": "P31",
  "value": "Q7840353",
  "references": [
    {
      "property": "P248",
      "value": "Q127419548",
      "datatype": "wikibase-item"
    },
    {
      "property": "P813",
      "value": "current_date",
      "datatype": "time"
    }
  ]
}
```

Use library references:
```json
{
  "property": "P31",
  "value": "Q7840353",
  "references": [{"name": "stated_in_federal_register"}]
}
```

## Migration Steps

### Step 1: Create Reference Library

1. Identify common reference patterns in your `defaults.claims` and claim-level `references`
2. Extract them into the `reference_library` section
3. Give each pattern a descriptive name

Example:
```json
"reference_library": {
  "stated_in_federal_register": [
    {
      "property": "P248",
      "value": "Q127419548",
      "datatype": "wikibase-item"
    },
    {
      "property": "P813",
      "value": "current_date",
      "datatype": "time"
    }
  ],
  "stated_in_with_url": [
    {
      "property": "P248",
      "value_from": "source_qid",
      "datatype": "wikibase-item"
    },
    {
      "property": "P854",
      "value_from": "source_url",
      "datatype": "url"
    }
  ]
}
```

### Step 2: Move Defaults to Claims

Convert default claims to regular claims with `"value"` instead of `"source_field"`:

**Before:**
```json
"defaults": {
  "claims": {
    "P31": "Q7840353"
  }
}
```

**After:**
```json
"mappings": {
  "claims": [
    {
      "property": "P31",
      "comment": "Instance of: federally recognized tribe",
      "value": "Q7840353",
      "datatype": "wikibase-item",
      "references": [{"name": "stated_in_federal_register"}]
    }
  ]
}
```

### Step 3: Update Reference Usage

Replace inline reference definitions with library references:

**Before:**
```json
{
  "property": "P1705",
  "source_field": "native_name",
  "references": [
    {
      "property": "P248",
      "value_from": "source_qid",
      "datatype": "wikibase-item"
    },
    {
      "property": "P813",
      "value": "current_date",
      "datatype": "time"
    }
  ]
}
```

**After:**
```json
{
  "property": "P1705",
  "source_field": "native_name",
  "references": [{"name": "stated_in_federal_register"}]
}
```

### Step 4: Remove Defaults Section

Delete the entire `"defaults"` section from your mapping file.

## Benefits of the New Structure

1. **Consistency**: All claims are handled the same way, whether fixed or data-driven
2. **Reusability**: Define common reference patterns once, use everywhere
3. **Maintainability**: Update a reference pattern in one place, affects all uses
4. **Clarity**: Easier to read `"references": ["stated_in_federal_register"]` than inline JSON
5. **Flexibility**: Can still use inline references when needed for unique cases

## Backward Compatibility

The refactored code does NOT support the old format. You must migrate existing mapping files to use:
- Unified `claims` array (no separate `defaults`)
- Optional `reference_library` and `qualifier_library` sections

## Complete Example

See [examples/mappings/tribe_mapping_example.json](https://github.com/skybristol/gkc/blob/main/examples/mappings/tribe_mapping_example.json) for a complete working example using the new structure.

## Questions?

If you encounter issues during migration, check:
1. All fixed-value claims use `"value"` not `"source_field"`
2. All data-driven claims use `"source_field"` not `"value"`
3. Reference library entries are defined before being used
4. Library reference names match exactly (case-sensitive)
