# Property Constraints Analysis (P2302)

**Date:** February 15, 2026  
**Status:** Implementation Complete - Analysis Ready  
**Location:** `/temp/working.ipynb`

## What Was Implemented

Enhanced the GKC codebase to fetch and analyze Wikidata property constraints (P2302 statements) during the property metadata gathering process.

### Code Changes

1. **PropertyProfile** (`gkc/recipe.py`)
   - Added `constraints` parameter to store P2302 statements
   - Added `get_constraints()` method to retrieve constraint data

2. **EntityCatalog** (`gkc/recipe.py`)
   - Enhanced `_fetch_batch()` to call `_fetch_property_constraints()` after fetching property metadata
   - Added `_fetch_property_constraints()` method to fetch P2302 claims for each property
   - Parses constraint claims using `_parse_constraint_claim()` helper function

3. **Constraint Parsing** (`gkc/recipe.py`)
   - `_parse_constraint_claim()` - Extracts constraint type, values, exceptions, and notes from Wikibase API responses
   - Handles qualifiers: P2308 (value), P2303 (exception), P1004 (note)

## Analysis Results: E502 Schema (Federally Recognized Tribe)

### Properties with Constraints
- **Total properties:** 32
- **Properties with constraints:** 30 (94%)
- **Total constraint records:** ~70

### Constraint Type Distribution

| ID | Name | Count | Examples |
|---|---|---|---|
| Q21502404 | Item requirement | 15 | P18, P41, P158, P242, P856 |
| Q21510865 | Allowed qualified relations | 13 | P6, P35, P1313, P1906, P248 |
| Q21503250 | Range constraint | 12 | P30, P17, P281, P407, P580 |
| Q21502838 | Allowed qualifiers | 9 | P17, P18, P625, P856 |
| Q21503247 | None of | 4 | P11693, P159, P1792 |
| Q52060874 | Timing constraint | 4 | P625, P30, P910, P1906 |
| Q52558054 | Format constraint | 4 | P31, P361, P527 |
| Q21510851 | Allowed entity types | 3 | P17, P407, P571 |
| Q21502410 | Forbidden qualifiers | 3 | P242, P856, P910 |
| Q19474404 | Inverse property constraint | 2 | P1792, P585 |
| Q21510864 | Must have source | 2 | P17, P31 |

### Sample Constraints

**P11693 (OpenStreetMap node ID)**
- Range constraint: Q27096213, Q838948, Q43229, Q123349687, Q670985
- None of: 20+ forbidden combinations

**P1313 (office held by head of government)**
- Range constraint: 6 allowed types (Q56061, Q15617994, Q3895768, etc.)
- Allowed qualified relations: Q4164871, Q21451536, Q114962596

**P158 (seal image)**
- Item requirement with exception: Q1991782

## Key Observations

1. **High constraint coverage** - 94% of properties in E502 have constraints
2. **Most common constraint types:**
   - Item/range constraints (require specific entity types)
   - Allowed qualifiers (restrict which qualifiers can be used)
   - Qualified relations (control which properties can be qualified by others)

3. **Constraint patterns:**
   - Media properties (P18, P41, P158, P242) use "Item requirement" constraint
   - Location properties (P17, P30, P625) use range + qualifier constraints
   - Reference properties use source requirements

## Usage in Code

```python
from gkc.recipe import RecipeBuilder

builder = RecipeBuilder(eid="E502")
builder.load_specification()
builder.fetch_entity_metadata()

# Access constraints for a property
for prop_id, prop_profile in builder.property_dictionary.items():
    constraints = prop_profile.get_constraints()
    if constraints:
        for constraint in constraints:
            print(f"{prop_id}: {constraint['constraint_type']}")
            if 'value' in constraint:
                print(f"  Values: {constraint['value']}")
```

## Outstanding Questions for Integration

1. **Which constraint types should be preserved in Barrel Recipes?**
   - All? Subset? Only the most impactful?

2. **How to represent constraints in the recipe JSON structure?**
   - Include in claim mappings?
   - Separate constraints section?
   - Link to source property constraints?

3. **Constraint validation in SpiritSafeValidator?**
   - Should we validate against constraint types discovered here?
   - How would that integrate with ShEx validation?

4. **Recipe generation strategy?**
   - Use constraints to auto-generate qualifiers/restrictions?
   - Use as documentation/metadata?
   - Use to provide warnings about potential issues?

## Files Modified

- `gkc/recipe.py` - PropertyProfile, EntityCatalog, constraint parsing functions
- `temp/working.ipynb` - Analysis and visualization cells

## Next Steps

1. Review constraint data in `/temp/working.ipynb`
2. Discuss which constraint types to include in Barrel Recipes
3. Design integration approach for constraint handling
4. Update documentation with constraint patterns discovered
