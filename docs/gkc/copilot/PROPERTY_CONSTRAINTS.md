# Constraint Processing Design Decision

## Date
February 16, 2026

## Context

During development of the Wikidata Barrel Recipe Builder, we implemented functionality to fetch and process Wikidata property constraints (P2302 statements) with the intention of using them to validate data transformations.

### What are Wikidata Property Constraints?

Wikidata property constraints are statements on property items that define validation rules for how the property should be used. These include:

- **Format constraints (Q21502404)**: Regex patterns that values must match
- **Type constraints**: What types of items can be used as values
- **Range constraints (Q21503250)**: Min/max values for numeric properties
- **Allowed/Forbidden qualifiers**: What qualifiers can/cannot be used with the property
- **Allowed entity types**: What types of entities can be used

Example: Property P856 (official website) has format constraints with regex patterns like `(https?|ftps?)://\S+` to ensure values are valid URLs.

## Problem

After implementing constraint fetching and examining real-world constraints from EntitySchema E502, we discovered that Wikidata property constraints are too varied and complex for our intended use case.

### Why constraints won't work for validation/transformation

Wikidata property constraints are designed for a different purpose than data transformation:

1. **Bot Notifications**: They're primarily used by Wikidata bots to notify contributors when they violate constraints
2. **Human Contributors**: They guide manual editors on best practices for using properties
3. **Infrastructure Dependent**: Many constraints (like type constraints, qualifier constraints) only make sense within Wikidata's infrastructure

### What We Expected vs. Reality

**Expected**: Reasonable validation rules we could apply during data transformation from our canonical Still Schema to Wikidata format.

**Reality**: Complex, context-heavy rules designed for quality control *within* Wikidata, not for external transformation workflows.

Example issue: A format constraint on P856 might have multiple regex patterns for different edge cases, exceptions for specific items, and notes intended for human contributors - all of which add complexity without providing clear validation value for our transformation pipeline.

## Decision

**Constraint processing is now OPTIONAL and DISABLED by default.**

### Implementation

Added `process_constraints` parameter to both `RecipeBuilder` and `EntityCatalog`:

```python
# Default: constraints are NOT fetched (simpler, faster SPARQL queries)
builder = RecipeBuilder(eid="E502")

# Explicit opt-in: constraints ARE fetched
builder = RecipeBuilder(eid="E502", process_constraints=True)
```

When `process_constraints=False` (default):
- SPARQL query is simplified to fetch only essential metadata (labels, descriptions, datatypes, formatter URLs)
- No constraint statements (P2302) are fetched from Wikidata
- Property ledger entries have empty constraint lists
- Query execution is faster and results are smaller

When `process_constraints=True`:
- Full SPARQL query fetches all constraint types from `USEFUL_CONSTRAINT_TYPES`
- Constraint ledger processing is available via `PropertyLedgerEntry.get_constraint_ledger()`
- Format constraints (Q21502404) with regex patterns are processed into `ConstraintLedgerEntry` objects

## Rationale

### Why Keep the Functionality?

While constraints don't serve our *current* use case (data transformation), they may be valuable in the *future* for:

1. **Contributor Notifications**: If we build tooling to notify contributors about data quality issues (similar to Wikidata bots)
2. **Quality Dashboards**: Showing constraint violations in administrative interfaces
3. **Documentation**: Including constraint information in generated documentation about properties

### Why Disable by Default?

1. **Performance**: Fetching constraints significantly increases SPARQL query complexity and result size
2. **Irrelevance**: Most barrel recipe use cases don't need constraint validation
3. **Clarity**: Makes it explicit when constraint processing is needed vs. when it's just overhead

### Query Complexity Comparison

**Without constraints (default)**:
```sparql
SELECT DISTINCT ?entityId ?label ?description ?datatype ?formatterUrl
WHERE {
    VALUES ?entityId { wd:P31 wd:P856 ... }
    OPTIONAL { ?entityId wikibase:propertyType ?datatype . }
    OPTIONAL { ?entityId schema:description ?description. FILTER(LANG(?description) = "en") }
    OPTIONAL { ?entityId wdt:P1630 ?formatterUrl . }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

**With constraints (opt-in)**:
```sparql
SELECT DISTINCT ?entityId ?label ?description ?datatype ?formatterUrl
               ?constraintType ?constraintTypeLabel
               ?constraintScope ?constraintException ?constraintNote 
               ?constraintRegex ?constraintRegexAlt
WHERE {
    VALUES ?entityId { wd:P31 wd:P856 ... }
    OPTIONAL { ?entityId wikibase:propertyType ?datatype . }
    OPTIONAL { ?entityId schema:description ?description. FILTER(LANG(?description) = "en") }
    OPTIONAL { ?entityId wdt:P1630 ?formatterUrl . }
    OPTIONAL {
        ?entityId p:P2302 ?constraintStatement.
        ?constraintStatement ps:P2302 ?constraintType.
        FILTER(?constraintType = wd:Q21502404 || ?constraintType = wd:Q52558054 || ...)
        OPTIONAL { ?constraintStatement pq:P2308 ?constraintScope . }
        OPTIONAL { ?constraintStatement pq:P2303 ?constraintException . }
        OPTIONAL { ?constraintStatement pq:P1004 ?constraintNote . }
        OPTIONAL { ?constraintStatement pq:P1793 ?constraintRegex . }
        OPTIONAL { ?constraintStatement pq:P2306 ?constraintRegexAlt . }
    }
    SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

## Consequences

### Positive

- Default behavior is simpler and faster
- Clear separation of concerns: recipe transformation vs. quality control
- Future-proof: keeps the door open for contributor notification features
- Opt-in model: users who need constraints can still access them

### Negative

- Additional parameter adds slight API complexity
- Constraint processing code remains in codebase even though rarely used
- Documentation must explain when to enable constraints

### Migration Impact

Since this is a new feature and constraints were never used in production barrel recipes, there is NO breaking change. Existing code continues to work as-is, and new code gets simpler defaults.

## Lessons Learned

1. **Design for your use case**: Don't import features just because the source data has them
2. **Validate assumptions early**: Testing with real-world data (E502) revealed the mismatch
3. **Make complexity opt-in**: Default to simple; let users enable complexity when needed
4. **Keep future options open**: Even if a feature doesn't fit now, preserve the capability for later

## Related Documentation

- [Property Constraints on Wikidata](https://www.wikidata.org/wiki/Help:Property_constraints_portal)
- **ConstraintLedgerEntry class** - Processing architecture for constraints (see `gkc/recipe.py`)
- **PropertyLedgerEntry.get_constraint_ledger()** - Constraint processing method (see `gkc/recipe.py`)
- **USEFUL_CONSTRAINT_TYPES** - Filtered constraint types (see `gkc/recipe.py`)

## Future Considerations

If we implement contributor notifications or quality dashboards:

1. Expand constraint processing beyond format constraints (Q21502404)
2. Add UI/reporting for constraint violations
3. Consider caching constraint data separately from recipe transformation data
4. Evaluate whether to build constraint checking into the bottling process or keep it separate

## Status

**IMPLEMENTED** - `process_constraints` parameter added to `RecipeBuilder` and `EntityCatalog`, defaulting to `False`.

## Contributors

- Sky Bristol (@skybristol)
- GitHub Copilot (implementation assistant)
