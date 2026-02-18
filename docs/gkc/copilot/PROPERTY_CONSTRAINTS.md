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

**Constraint processing has been removed from the active codebase.**

### Implementation

Entity metadata now focuses on labels, descriptions, and aliases by default,
with optional property-only details (datatype, formatter URL) controlled by
`fetch_property_details`:

```python
# Default: metadata only (labels, descriptions, aliases)
catalog = EntityCatalog()

# Optional: include property datatype + formatter URL
catalog = EntityCatalog(fetch_property_details=True)
```

## Rationale

### Why Remove the Functionality?

While constraints might be valuable in the *future* for:

1. **Contributor Notifications**: If we build tooling to notify contributors about data quality issues (similar to Wikidata bots)
2. **Quality Dashboards**: Showing constraint violations in administrative interfaces
3. **Documentation**: Including constraint information in generated documentation about properties

### Why Disable by Default?

1. **Performance**: Fetching constraints significantly increases SPARQL query complexity and result size
2. **Irrelevance**: Most barrel recipe use cases don't need constraint validation
3. **Clarity**: Keeping the API focused on essential metadata keeps usage simple

### Query Complexity Comparison

**Current query pattern (default)**:
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX schema: <http://schema.org/>

SELECT DISTINCT ?entityId ?label ?labelLang ?alias ?aliasLang ?desc ?descLang
WHERE {
    VALUES ?entityId { wd:P31 wd:P856 ... }
    OPTIONAL { ?entityId rdfs:label ?label . BIND(LANG(?label) AS ?labelLang) }
    OPTIONAL { ?entityId skos:altLabel ?alias . BIND(LANG(?alias) AS ?aliasLang) }
    OPTIONAL { ?entityId schema:description ?desc . BIND(LANG(?desc) AS ?descLang) }
}
```

## Consequences

### Positive

- Default behavior is simpler and faster
- Clear separation of concerns: recipe transformation vs. quality control
- Future-proof: keeps the door open for contributor notification features
- Opt-in model: users who need constraints can still access them

### Negative

- Constraint data is no longer directly available via the recipe builder

### Migration Impact

Constraint-related APIs were removed. Any callers using `process_constraints` or
constraint-specific methods must migrate to the new metadata-only approach.

## Lessons Learned

1. **Design for your use case**: Don't import features just because the source data has them
2. **Validate assumptions early**: Testing with real-world data (E502) revealed the mismatch
3. **Make complexity opt-in**: Default to simple; let users enable complexity when needed
4. **Keep future options open**: Even if a feature doesn't fit now, preserve the capability for later

## Related Documentation

- [Property Constraints on Wikidata](https://www.wikidata.org/wiki/Help:Property_constraints_portal)

## Future Considerations

If we implement contributor notifications or quality dashboards:

1. Expand constraint processing beyond format constraints (Q21502404)
2. Add UI/reporting for constraint violations
3. Consider caching constraint data separately from recipe transformation data
4. Evaluate whether to build constraint checking into the bottling process or keep it separate

## Status

**REMOVED** - Constraint processing was removed in favor of simplified metadata fetching.

## Contributors

- Sky Bristol (@skybristol)
- GitHub Copilot (implementation assistant)
