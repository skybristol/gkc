"""
Example showing inline named references and qualifiers.

This demonstrates the "define on first use" pattern where you
add a "name" attribute to a reference or qualifier, then reuse
it by referencing that name as a string.
"""

example_mapping = {
    "version": "1.0",
    "metadata": {
        "name": "Inline Named Pattern Example",
        "description": "Shows define-on-first-use pattern"
    },
    # Optional explicit library for widely-used patterns
    "reference_library": {
        "federal_register": [
            {
                "property": "P248",
                "value": "Q127419548",
                "datatype": "wikibase-item",
                "comment": "Federal Register"
            }
        ]
    },
    "qualifier_library": {},
    "mappings": {
        "labels": [
            {"source_field": "name", "language": "en"}
        ],
        "descriptions": [],
        "aliases": [],
        "claims": [
            # Use explicit library reference
            {
                "property": "P31",
                "comment": "Instance of",
                "value": "Q7840353",
                "datatype": "wikibase-item",
                "references": [{"name": "federal_register"}]
            },
            
            # Define inline named reference on FIRST use
            {
                "property": "P30",
                "comment": "Continent: North America",
                "value": "Q49",
                "datatype": "wikibase-item",
                "references": [
                    {
                        "name": "inferred_from_hq_location",
                        "property": "P887",
                        "value": "Q131921702",
                        "datatype": "wikibase-item",
                        "comment": "based on heuristic"
                    }
                ]
            },
            
            # REUSE the inline named reference
            {
                "property": "P17",
                "comment": "Country: United States",
                "value": "Q30",
                "datatype": "wikibase-item",
                "references": [{"name": "inferred_from_hq_location"}]
            },
            
            # Can also use inline unnamed references for one-off cases
            {
                "property": "P571",
                "comment": "Inception date",
                "source_field": "established_date",
                "datatype": "time",
                "references": [
                    {
                        "property": "P248",
                        "value_from": "source_qid",
                        "datatype": "wikibase-item"
                    }
                ]
            },
            
            # Example with inline named QUALIFIER
            {
                "property": "P2124",
                "comment": "Member count",
                "source_field": "member_count",
                "datatype": "quantity",
                "qualifiers": [
                    {
                        "name": "point_in_time_qualifier",
                        "property": "P585",
                        "source_field": "count_date",
                        "datatype": "time"
                    }
                ],
                "references": [{"name": "federal_register"}]
            },
            
            # Could reuse the qualifier on another claim
            {
                "property": "P1082",
                "comment": "Population",
                "source_field": "population",
                "datatype": "quantity",
                "qualifiers": [{"name": "point_in_time_qualifier"}],
                "references": [{"name": "federal_register"}]
            }
        ]
    }
}

# Key Points:
# 1. Consistent structure: claims, references, qualifiers all use "property" field
# 2. Add "name" attribute to define a reusable reference/qualifier
# 3. Reference by name-only object: [{"name": "..."}]
# 4. Mix with explicit library entries as needed
# 5. Explicit library takes precedence if names collide
# 6. Processing is O(n) - very efficient
# 7. All properties in references array form ONE reference block (Option A)

if __name__ == "__main__":
    import json
    print(json.dumps(example_mapping, indent=2))
