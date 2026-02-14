# Blending: Multi-Source Merging & Conflict Resolution

## Overview

**Blending** is the stage where multiple refined datasets are merged into a unified whole. After each source has been proofed, Blending resolves conflicts, combines complementary information, and builds a single coherent knowledge graph. It's the stage where different "casks" (datasets) become one finished batch.

| Aspect | Details |
|--------|---------|
| **Input** | Proofed records from one or more datasets |
| **What Happens** | Merge across datasets, resolve conflicts, reconcile provenance, build unified graph |
| **Output** | One merged dataset with consolidated entities and provenance metadata |
| **Best For** | Multi-source integration, conflict resolution, graph construction |
| **Typical Duration** | Hours to days, depending on dataset size and merge complexity |

---

## The Problem Blending Solves

Multiple datasets rarely agree perfectly:

- **Conflicting values**: Different sources disagree on the same property
- **Duplicate entities**: The same entity appears in multiple datasets under different IDs
- **Uneven completeness**: One dataset has rich biographies, another has coordinates
- **Provenance complexity**: You need to preserve which data came from which source
- **Schema mismatch**: Slightly different schemas across datasets

**The cost of skipping Blending**: You end up with multiple partial datasets instead of one coherent knowledge graph.

---

## Input Contract

Records entering Blending should:

1. **Be proofed** — Each record has quality scores and pass/review/fail status
2. **Include provenance** — Source IDs and datasets clearly identified
3. **Have canonical identifiers** — QIDs, OSM IDs, or other stable IDs for linking
4. **Follow a shared schema** — Or have mapping rules to a canonical schema

---

## Core Transformations

### 1. Dataset Alignment

**Goal**: Align schemas and identifiers between datasets.

```python
# Example: dataset A uses "birth_year", dataset B uses "date_of_birth"
alignment_map = {
    "birth_year": "birth_year",
    "date_of_birth": "birth_year"
}

aligned_record = {alignment_map.get(k, k): v for k, v in record.items()}
```

**Decision Point**:
- Should alignment happen earlier (Mash/Ferment) or here?
- How to handle fields present in one dataset but not another?

---

### 2. Entity Matching Across Datasets

**Goal**: Identify the same entity appearing in multiple datasets.

```python
# Match by canonical ID if available
if record_a.get("_wikidata_qid") == record_b.get("_wikidata_qid"):
    merge_candidates.append((record_a, record_b))

# If no canonical IDs, use fuzzy matching
if similarity(record_a["name"], record_b["name"]) > 0.9:
    merge_candidates.append((record_a, record_b))
```

**Decision Point**:
- Should you only blend records with shared canonical IDs, or allow fuzzy matches?
- How to handle near-duplicates that might not be the same entity?

---

### 3. Conflict Resolution Strategy

**Goal**: Decide which value to keep when sources disagree.

```python
# Example conflict: birth_year differs
values = [record_a["birth_year"], record_b["birth_year"]]

# Strategy A: Trust higher-confidence source
winner = record_a if record_a["_final_quality_score"] > record_b["_final_quality_score"] else record_b

# Strategy B: Prefer authoritative source
if record_a["_source"] in authoritative_sources:
    winner = record_a
elif record_b["_source"] in authoritative_sources:
    winner = record_b

# Strategy C: Keep both with provenance
merged_record["birth_year"] = {
    "value": winner["birth_year"],
    "alternates": values,
    "sources": [record_a["_source"], record_b["_source"]]
}
```

**Decision Point**:
- Trust a single authoritative source, or combine values?
- How to handle conflicts that can't be resolved automatically?
- Should you flag unresolved conflicts for manual review?

---

### 4. Provenance Merging

**Goal**: Preserve source history and explain where each value came from.

```python
merged_record["_provenance"] = {
    "sources": [record_a["_source"], record_b["_source"]],
    "source_ids": [record_a["source_id"], record_b["source_id"]],
    "merge_strategy": "authoritative_preference",
    "conflicts": ["birth_year"]
}
```

**Decision Point**:
- How detailed should provenance be? (field-level vs. record-level)
- Should provenance include confidence scores and decision logic?

---

### 5. Unified Graph Construction

**Goal**: Build a connected graph of entities and relationships.

```python
# Example: build edges between entities
for record in merged_records:
    graph.add_node(record["_wikidata_qid"], data=record)
    if record.get("employer_qid"):
        graph.add_edge(record["_wikidata_qid"], record["employer_qid"], relation="employer")
    if record.get("location_qid"):
        graph.add_edge(record["_wikidata_qid"], record["location_qid"], relation="location")
```

**Decision Point**:
- Should graph be built directly in memory or exported as RDF/graph DB?
- Should relationships from different sources be weighted differently?

---

## Output Contract

Records exiting Blending should:

1. **Be merged across datasets** — Single unified record for each entity
2. **Have resolved conflicts** — With provenance for decisions
3. **Be graph-ready** — Relationships clearly expressed
4. **Preserve source lineage** — Provenance metadata remains intact

**Example output record:**
```json
{
  "_wikidata_qid": "Q12345678",
  "name": "Alice Johnson",
  "birth_year": 1987,
  "publication_count": 50,
  "_final_quality_score": 0.92,
  "_provenance": {
    "sources": ["researchers_csv", "researchers_api"],
    "source_ids": ["R001", "external_A1"],
    "merge_strategy": "authoritative_preference",
    "conflicts": []
  }
}
```

---

## Angel's Share (Schema Deviations)

When blending sources, you may encounter fields that don't align with the unified schema or that conflict in ways you don't want to resolve yet. Keep those values as **Angel's Share** data with provenance notes so they remain available for future schema adjustments or alternate outputs.

---

## Configuration & Decisions

Before running Blending, define:

### 1. Source Priority Rules
- Which datasets are authoritative for certain fields?
- Do some sources always override others?

### 2. Merge Strategy
- Match by canonical IDs only, or allow fuzzy matching?
- How to handle conflicts (prefer one, keep both, flag)?

### 3. Provenance Granularity
- Record-level vs. field-level provenance
- Whether to store alternates and conflict history

---

## A Worked Example

**Scenario**: Two datasets both contain Carl Sagan with different birth year values.

**Dataset A:**
```json
{"name": "Carl Sagan", "birth_year": 1934, "_source": "dataset_a", "_final_quality_score": 0.9}
```

**Dataset B:**
```json
{"name": "Carl Sagan", "birth_year": 1933, "_source": "dataset_b", "_final_quality_score": 0.7}
```

**Blend config:**
```python
config = {
    "authoritative_sources": ["dataset_a"],
    "merge_strategy": "authoritative_preference",
    "conflict_policy": "keep_alternates"
}
```

**Output:**
```json
{
  "name": "Carl Sagan",
  "birth_year": 1934,
  "_provenance": {
    "sources": ["dataset_a", "dataset_b"],
    "conflicts": ["birth_year"],
    "alternates": {"birth_year": [1933]}
  }
}
```

---

## Supporting Systems

### Barrel (Provenance)
Stores:
- Merge decisions and conflict history
- Source priority rules

### Spirit Safe (Validation)
Validates:
- Consistency after merge
- No duplicate entities remain

---

## Relationship to Other Stages

**Before**: [Proofing](proofing.md) ensures data quality per dataset

**After**: [Bottling](bottling.md) exports merged data to target formats

---

## Common Patterns

### Pattern 1: "I trust one dataset above all others"
Use authoritative source rules: if dataset A has value, override others. Track conflicts for audit.

### Pattern 2: "I need to preserve conflicting values"
Keep alternates for conflicting fields, store provenance. Useful for cases where conflict can't be resolved automatically.

### Pattern 3: "I only want to merge records with identical IDs"
Restrict merging to shared canonical IDs (QID/OSM) for maximum safety.

---

## Reference

- **Configuration File Format**: (Link to blending config schema)
- **API Reference**: (Link to Blender class)
- **Conflict Resolution Rules**: (Detailed policy docs)
- **Related**: [Proofing](proofing.md) | [Bottling](bottling.md)

---

## GitHub Issues & Development

Work on the Blending stage is tracked under the [`blend` label](https://github.com/skybristol/gkc/issues?q=label%3Ablend). Issues represent merge strategy improvements, conflict resolution policies, and multi-source integration work.

**Other Workflow Stages:**
- [`mash`](https://github.com/skybristol/gkc/issues?q=label%3Amash) — Data Ingestion
- [`ferment`](https://github.com/skybristol/gkc/issues?q=label%3Aferment) — Cleaning & Normalization
- [`distill`](https://github.com/skybristol/gkc/issues?q=label%3Adistill) — Reconciliation & Linking
- [`refine`](https://github.com/skybristol/gkc/issues?q=label%3Arefine) — Deduplication & Enrichment
- [`proof`](https://github.com/skybristol/gkc/issues?q=label%3Aproof) — Quality Assurance
- [`bottle`](https://github.com/skybristol/gkc/issues?q=label%3Abottle) — Format & Export
