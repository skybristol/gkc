# Refinement: Deduplication & Enrichment

## Overview

**Refinement** is where reconciled data gets polished and consolidated. After Distillation links records to canonical entities, Refinement handles the messy follow-up: identifying duplicates, consolidating variants, enriching with cross-references, and validating against shape constraints. It's the "curation" step—ensuring data is coherent and complete before quality assessment.

| Aspect | Details |
|--------|---------|
| **Input** | Linked records from Distillation with confidence scores |
| **What Happens** | Duplicate detection & collapsing, enrichment, shape validation, relationship mapping |
| **Output** | Deduplicated, enriched records conforming to target schemas (ShEx, etc.) |
| **Best For** | Handling multiple source records of the same entity, adding relationships, validating structure |
| **Typical Duration** | Hours, depending on dataset size and enrichment strategy |

---

## The Problem Refinement Solves

Linked data is still messy:

- **Duplicates**: Same entity matched by Distillation from multiple sources (or multiple times within a source)
- **Variant values**: Different attribute values for the same entity across records ("New York" vs. "New York City")
- **Missing relationships**: Canonical entities may need sitelinks, relationships to other entities, or semantic typing
- **Schema deviations**: Records don't conform to target shape (Wikidata properties, OSM tags, etc.)
- **Incomplete enrichment**: Data lacks context that would be added by cross-referencing related entities

**The cost of skipping Refinement**: Duplicate records flow downstream; batch loads have conflicts; Wikidata quality claims fail validation.

---

## Input Contract

Records entering Refinement should be:

1. **Linked** — Have _wikidata_qid or equivalent from Distillation
2. **Confidence-scored** — Have _match_confidence
3. **Schema-conformant** — From Fermentation; all fields have expected types

Targets should include:
- **Dedup rules** — How to identify duplicates and which to keep
- **Enrichment catalogs** — Which cross-references are relevant
- **Target schemas** — ShEx, Wikidata entity schemas, etc.

---

## Core Transformations

### 1. Duplicate Detection & Collapsing

**Goal**: Find multiple records referring to the same entity; consolidate them.

```python
# Strategy A: Group by matched canonical ID
from collections import defaultdict
by_wikidata_id = defaultdict(list)
for record in records:
    if record.get("_wikidata_qid"):
        by_wikidata_id[record["_wikidata_qid"]].append(record)

# For each group of duplicates, keep best and merge
deduplicated = []
for qid, group in by_wikidata_id.items():
    if len(group) == 1:
        deduplicated.append(group[0])
    else:
        # Multiple records for same entity: merge
        merged = merge_records(group, strategy="high_confidence_first")
        merged["_duplicate_count"] = len(group)
        merged["_duplicate_record_ids"] = [r["source_id"] for r in group]
        deduplicated.append(merged)

# Strategy B: Fuzzy matching for near-duplicates
for rec1 in records:
    for rec2 in records:
        if rec1["source_id"] < rec2["source_id"]:  # Avoid double-checking
            score = calculate_duplicate_score(rec1, rec2)
            if score > 0.9:  # High similarity
                # Mark as duplicate pair
                rec2["_duplicate_of"] = rec1["source_id"]
```

**Decision Point**:
- Is an exact matched QID enough to declare duplicates, or require additional confirmation?
- For near-duplicates (high similarity but no shared QID), what's the threshold?
- When duplicates exist, keep which one? (Highest confidence? Most recent? Most complete?)
- Merge values or choose one? (For conflict: "Smith" vs. "SMITH")

---

### 2. Record Merging Strategy

**Goal**: Consolidate duplicate records coherently, tracking provenance.

```python
def merge_records(group, strategy="highest_confidence"):
    """
    Merge multiple records of same entity.
    
    Strategies:
    - highest_confidence: Keep values from highest-confidence record
    - most_complete: Prefer records with fewer nulls
    - reconcile: Intelligently merge non-conflicting values
    - first_wins: Keep first record, use others for gaps
    """
    
    if strategy == "reconcile":
        merged = {}
        for field in all_fields:
            field_values = [r.get(field) for r in group if r.get(field) is not None]
            
            if not field_values:
                merged[field] = None
            elif len(set(field_values)) == 1:
                # All same value
                merged[field] = field_values[0]
            else:
                # Conflicting values: flag for manual review
                merged[field] = field_values[0]  # Use first, but flag
                merged["_conflicts"].append({
                    "field": field,
                    "values": field_values,
                    "sources": [r["source_id"] for r in group]
                })
        return merged
```

**Decision Point**:
- Reconcile conflicting values or flag for review?
- Should merged records track all contributing sources?
- For numeric fields (publication count), sum or take max?
- For dates (birth date), allow flexibility or require exact match?

---

### 3. Deduplication Flagging & Tracking

**Goal**: Document what was deduplicated for downstream transparency.

```python
# Mark merged records
merged_record["_deduplicated"] = True
merged_record["_duplicate_count"] = len(original_group)
merged_record["_duplicate_sources"] = list(set(r["_source"] for r in original_group))
merged_record["_duplicate_record_ids"] = [r["source_id"] for r in original_group]

# Track merging decisions made
merged_record["_refinement_merges"] = [
    {
        "field": "name",
        "original_values": ["John Smith", "John SMITH"],
        "merged_value": "John Smith",
        "decision": "case_normalize"
    }
]
```

**Decision Point**:
- How detailed to track merging decisions?
- Should Barrel store full merge logs for audit trail?

---

### 4. Enrichment & Cross-Reference Addition

**Goal**: Link merged records to related entities and add derived properties.

```python
# Add relationship fields
enriched = enrich_from_wikidata(merged_record)  # Fetch biography, website, etc.
enriched["_wikidata_data_fetched"] = True

# Add sitelinks (Wikipedia, Commons, etc.)
enriched["_sitelinks"] = fetch_sitelinks(record["_wikidata_qid"])
# Example: {"en": "Alice_Johnson", "fr": "Alice_Johnson_(physicienne)"}

# Add related entities
enriched["employer_qid"] = extract_employer_from_wikidata(record["_wikidata_qid"])
enriched["location_qid"] = extract_birthplace_from_wikidata(record["_wikidata_qid"])

# Add confidence and quality hints
enriched["_wikidata_completeness"] = 0.75  # Percentage of common properties filled
enriched["_sitelink_count"] = len(enriched["_sitelinks"])
```

**Decision Point**:
- Which enrichments are essential vs. optional?
- Fetch full Wikidata item or just key properties?
- Should enrichment errors cause record failure, or just flag?
- Cache enriched data or re-fetch on demand?

---

### 5. Shape Validation (ShEx, Schema Conformance)

**Goal**: Validate records against target schema requirements.

```python
# Validate against ShEx
from pyshex import evaluate_cli

shex_schema = """
EXTRA p:P31
<PersonShape> {
  p:P31 [wd:Q5] ;
  rdfs:label xsd:string ? ;
  p:P580 xsd:gYear ? ;
  p:P569 xsd:gYear ? ;
  p:P19 IRI ? ;
  p:P27 IRI ? ;
  p:P106 IRI ? ;  # occupation
}
"""

result = evaluate_cli(record, shex_schema, focus="Q12345678")
if result.conforms:
    record["_shape_valid"] = True
else:
    record["_shape_valid"] = False
    record["_shape_errors"] = result.errors
    record["_refinement_flags"].append("shape_validation_failed")

# Or validate against simpler property checklist
required_properties = ["name", "birth_year", "nationality"]
missing = [p for p in required_properties if not record.get(p)]
if missing:
    record["_refinement_flags"].append(f"missing_required_properties: {missing}")
```

**Decision Point**:
- Strict shape validation (fail record) or permissive (flag and continue)?
- Which shapes are mandatory vs. optional?
- Should validation be at Wikidata/OSM schema or custom schema level?

---

## Output Contract

Records exiting Refinement should:

1. **Be deduplicated** — No duplicate records for same entity
2. **Be enriched** — Include relevant cross-references and relationships
3. **Be shape-validated** — Conform to target schemas (ShEx, etc.)
4. **Have flags** — Any conflicts, missing properties, or validation failures noted
5. **Be traceable** — Merging and enrichment decisions tracked for audit

**Example output record:**
```json
{
  "source_id": ["researchers_csv:R001", "researchers_api:external_A1"],
  "name": "Alice Johnson",
  "birth_year": 1987,
  "field_of_study": "Physics",
  "publication_count": 50,
  "_wikidata_qid": "Q12345678",
  "_match_confidence": 0.98,
  "_deduplicated": true,
  "_duplicate_count": 2,
  "_duplicate_sources": ["researchers_csv", "researchers_api"],
  "_sitelinks": {
    "en": "Alice_Johnson",
    "fr": "Alice_Johnson_(physicienne)"
  },
  "_employer_qid": "Q567890",
  "_wikidata_completeness": 0.8,
  "_shape_valid": true,
  "_refinement_flags": []
}
```

---

## Angel's Share (Schema Deviations)

Refinement often uncovers fields or relationships that fall outside the current target schema. Preserve them as **Angel's Share** data with deviation notes so they can be evaluated for future schema expansion or different publication targets.

---

## Configuration & Decisions

Before running Refinement, define:

### 1. Deduplication Strategy
- How to identify duplicates? (By QID? Fuzzy matching? Both?)
- When duplicates exist, which to keep?
- How to merge conflicting values?

### 2. Enrichment Profile
- Which fields to enrich? (Sitelinks? Related entities? Completeness scores?)
- Fetch from external systems or use cached data?
- Fail on enrichment errors or flag and continue?

### 3. Validation Schemas
- Which shapes to validate against? (ShEx? Wikidata type? Custom?)
- Strict or lenient validation?
- Which missing properties cause failure vs. warning?

---

## A Worked Example

**Scenario**: Two sources had records for the same physicist; Distillation matched both to Q12345678.

**Before Refinement (two duplicate records):**
```json
[
  {
    "source_id": "researchers_csv:R001",
    "name": "Alice Johnson",
    "birth_year": 1987,
    "publication_count": 42,
    "_wikidata_qid": "Q12345678",
    "_match_confidence": 0.98
  },
  {
    "source_id": "researchers_api:external_A1",
    "name": "Alice Johnson",
    "birth_year": 1987,
    "publication_count": 50,
    "_wikidata_qid": "Q12345678",
    "_match_confidence": 0.95
  }
]
```

**Refinement config:**
```python
config = {
    "dedup_strategy": "reconcile",
    "merge_strategy": "highest_confidence",
    "enrich": ["sitelinks", "related_entities", "completeness"],
    "validate_schema": "wikidata_person"
}
```

**After Refinement (one merged record):**
```json
{
  "source_id": ["researchers_csv:R001", "researchers_api:external_A1"],
  "name": "Alice Johnson",
  "birth_year": 1987,
  "publication_count": 50,
  "_wikidata_qid": "Q12345678",
  "_match_confidence": 0.98,
  "_deduplicated": true,
  "_duplicate_count": 2,
  "_duplicate_sources": ["researchers_csv", "researchers_api"],
  "_duplicate_record_ids": ["researchers_csv:R001", "researchers_api:external_A1"],
  "_sitelinks": {
    "en": "Alice_Johnson",
    "de": "Alice_Johnson_(Physikerin)"
  },
  "_wikidata_completeness": 0.82,
  "_shape_valid": true,
  "_refinement_merges": [
    {
      "field": "publication_count",
      "original_values": [42, 50],
      "merged_value": 50,
      "decision": "max_from_sources"
    }
  ],
  "_refinement_flags": []
}
```

---

## Supporting Systems

### Schema Registry
Refinement uses:
- Deduplication rules and decision trees
- Enrichment source catalogs
- Target shape schemas (ShEx, Wikidata types, OSM, etc.)

### Spirit Safe (Validation)
Validates:
- Shape conformance
- Required property presence
- Relationship integrity

### Barrel (Provenance)
Stores:
- Merge decisions and conflict logs
- Enrichment source data (for reproducibility)
- Shape validation results

---

## Relationship to Other Stages

**Before**: [Distillation](distillation.md) links records to canonical entities

**After**: [Proofing](proofing.md) scores quality and fitness; [Blending](blending.md) merges multiple refined datasets

---

## Common Patterns

### Pattern 1: "I have lots of duplicates from multiple sources"
Use reconcile strategy: merge all values intelligently, flag conflicts, let downstream stages decide.

### Pattern 2: "I need to preserve all contributing sources"
Track source provenance in deduplicated records. Use Barrel to store full merge logs. Enables traceability.

### Pattern 3: "I want to enrich with Wikidata data"
Fetch sitelinks, related entities, and property completeness scores during Refinement. Cache in Barrel. Needed before export to Wikidata (avoids importing redundant data).

---

## Reference

- **Configuration File Format**: (Link to refinement config schema)
- **API Reference**: (Link to Refiner class)
- **Deduplication Algorithms**: (Blocking, clustering, merging strategies)
- **Enrichment Sources**: (Wikidata, OSM, custom catalogs)
- **ShEx Validation**: (Shape expression tutorials and schemas)
- **Related**: [Distillation](distillation.md) | [Proofing](proofing.md) | [Spirit Safe](spirit_safe.md)

---

## GitHub Issues & Development

Work on the Refinement stage is tracked under the [`refine` label](https://github.com/skybristol/gkc/issues?q=label%3Arefine). Issues represent deduplication strategies, enrichment integrations, and shape validation improvements.

**Other Workflow Stages:**
- [`mash`](https://github.com/skybristol/gkc/issues?q=label%3Amash) — Data Ingestion
- [`ferment`](https://github.com/skybristol/gkc/issues?q=label%3Aferment) — Cleaning & Normalization
- [`distill`](https://github.com/skybristol/gkc/issues?q=label%3Adistill) — Reconciliation & Linking
- [`proof`](https://github.com/skybristol/gkc/issues?q=label%3Aproof) — Quality Assurance
- [`blend`](https://github.com/skybristol/gkc/issues?q=label%3Ablend) — Multi-Source Merging
- [`bottle`](https://github.com/skybristol/gkc/issues?q=label%3Abottle) — Format & Export
