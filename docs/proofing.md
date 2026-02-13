# Proofing: Quality Assurance & Confidence Scoring

## Overview

**Proofing** is the quality gate of the pipeline. After records are reconciled and refined, Proofing evaluates each record against clear quality metrics: completeness, consistency, confidence, and fitness for downstream use. It's where the pipeline decides which data is strong enough to bottle and which should be held back or flagged.

| Aspect | Details |
|--------|---------|
| **Input** | Refined, deduplicated records from Refinement |
| **What Happens** | Quality scoring, consistency checks, confidence thresholds, audit flagging |
| **Output** | Records with quality scores and pass/fail status; records flagged for review |
| **Best For** | Ensuring data meets minimum quality standards before export |
| **Typical Duration** | Minutes to hours, depending on scoring model complexity |

---

## The Problem Proofing Solves

Even refined data can have quality issues:

- **Incomplete records**: Missing key properties (birth date, coordinates, type)
- **Inconsistent values**: Conflicting metadata (birth year vs. death year)
- **Low confidence matches**: Distillation links are uncertain
- **Shape deviations**: Records fail schema requirements
- **Outliers**: Unusual or suspicious values (e.g., birth year 1700 for a modern scientist)

**The cost of skipping Proofing**: Low-quality data enters Wikidata/OSM, damaging trust and causing reverts or validation failures.

---

## Input Contract

Records entering Proofing should:

1. **Be refined and deduplicated** — From Refinement
2. **Contain match confidence** — Distillation scores are present
3. **Include enrichment data** — Sitelinks, related entities, or completeness metrics
4. **Have validation results** — Shape validation results from Refinement

---

## Core Transformations

### 1. Completeness Scoring

**Goal**: Measure how much of the expected schema is filled.

```python
required_fields = ["name", "birth_year", "nationality", "occupation"]
optional_fields = ["gender", "website", "image"]

filled_required = sum(1 for f in required_fields if record.get(f))
filled_optional = sum(1 for f in optional_fields if record.get(f))

completeness_score = (filled_required / len(required_fields)) * 0.8 + \
                     (filled_optional / len(optional_fields)) * 0.2
record["_completeness_score"] = round(completeness_score, 2)
```

**Decision Point**:
- Should optional fields affect score? How much weight?
- Different completeness thresholds for different entity types?

---

### 2. Consistency Checks

**Goal**: Ensure values don't contradict each other or external rules.

```python
# Example consistency checks
issues = []

# Birth year must be before death year
if record.get("birth_year") and record.get("death_year"):
    if record["birth_year"] >= record["death_year"]:
        issues.append("birth_year_after_death_year")

# Coordinates must be within valid range
if record.get("latitude") and record.get("longitude"):
    if not (-90 <= record["latitude"] <= 90 and -180 <= record["longitude"] <= 180):
        issues.append("invalid_coordinates")

# Occupation must be valid enum
if record.get("occupation") and record["occupation"] not in valid_occupations:
    issues.append("invalid_occupation_value")

record["_consistency_issues"] = issues
```

**Decision Point**:
- What rules are strict vs. warning-only?
- Should consistency checks be customizable per dataset?

---

### 3. Confidence Thresholding

**Goal**: Combine match confidence and quality scores to decide pass/fail.

```python
match_confidence = record.get("_match_confidence", 0)
quality_score = record.get("_completeness_score", 0)

# Weighted final score
final_score = (match_confidence * 0.6) + (quality_score * 0.4)
record["_final_quality_score"] = round(final_score, 2)

if final_score >= 0.85:
    record["_proofing_status"] = "pass"
elif final_score >= 0.65:
    record["_proofing_status"] = "review"
else:
    record["_proofing_status"] = "fail"
```

**Decision Point**:
- What thresholds define pass/review/fail?
- Should match confidence outweigh completeness or vice versa?
- Should schema validation failures automatically override pass?

---

### 4. Outlier & Anomaly Detection

**Goal**: Flag unusual or suspicious records for review.

```python
# Example: birth year outliers
if record.get("birth_year") and record["birth_year"] < 1800:
    record["_proofing_flags"].append("birth_year_outlier")

# Example: unusually high publication count
if record.get("publication_count") and record["publication_count"] > 10000:
    record["_proofing_flags"].append("publication_count_outlier")
```

**Decision Point**:
- Which fields should have outlier thresholds?
- Manual thresholds or statistical (z-score, IQR)?

---

### 5. Audit Flags & Review Queue

**Goal**: Collect flagged records for manual review.

```python
if record["_proofing_status"] in ["review", "fail"]:
    record["_requires_manual_review"] = True
    review_queue.append(record)

# Export review queue for manual inspection
export_review_queue(review_queue, format="csv")
```

**Decision Point**:
- Where should review queue be stored? (Barrel, separate file, database)
- Should review queue include full record or only flagged fields?

---

## Output Contract

Records exiting Proofing should:

1. **Have quality scores** — Completeness, consistency, final score
2. **Be classified** — Pass, review, or fail
3. **Be flagged** — Outliers and inconsistencies tracked
4. **Be audit-ready** — Review queue available for manual intervention

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
  "_completeness_score": 0.86,
  "_final_quality_score": 0.92,
  "_proofing_status": "pass",
  "_consistency_issues": [],
  "_proofing_flags": []
}
```

---

## Angel's Share (Schema Deviations)

Proofing should not discard information that fails current constraints. Keep those deviations as **Angel's Share** data with clear notes about what failed and why, so they can be revisited later or routed to a different endpoint.

---

## Configuration & Decisions

Before running Proofing, define:

### 1. Scoring Model
- Weights for completeness vs. match confidence
- Thresholds for pass/review/fail
- Different scoring for different entity types

### 2. Consistency Rules
- Field-level rules (birth before death, lat/lon ranges, etc.)
- Custom rules per dataset
- Strict vs. warning-only rules

### 3. Outlier Detection Strategy
- Manual thresholds vs. statistical detection
- Fields to monitor for anomalies

### 4. Review Workflow
- Should review queue be exported automatically?
- Manual review feedback loop back into Distillation/Refinement?

---

## A Worked Example

**Scenario**: A record has strong entity match but missing key fields.

**Input record:**
```json
{
  "name": "Alice Johnson",
  "birth_year": null,
  "field_of_study": "Physics",
  "publication_count": 50,
  "_wikidata_qid": "Q12345678",
  "_match_confidence": 0.98
}
```

**Proofing config:**
```python
config = {
    "required_fields": ["name", "birth_year", "field_of_study"],
    "confidence_weight": 0.6,
    "completeness_weight": 0.4,
    "pass_threshold": 0.85,
    "review_threshold": 0.65
}
```

**Output:**
```json
{
  "name": "Alice Johnson",
  "_completeness_score": 0.66,
  "_final_quality_score": 0.82,
  "_proofing_status": "review",
  "_proofing_flags": ["missing_required_field: birth_year"]
}
```

---

## Supporting Systems

### Spirit Safe (Validation)
Proofing builds on Spirit Safe checks:
- Shape validation results
- Integrity and consistency checks

### Barrel (Provenance)
Store:
- Proofing scores and audit logs
- Review queue snapshots

---

## Relationship to Other Stages

**Before**: [Refinement](refinement.md) cleans and enriches records

**After**: [Blending](blending.md) merges multiple proofed datasets; [Bottling](bottling.md) exports final data

---

## Common Patterns

### Pattern 1: "I need strict quality gates"
Set high pass threshold; mark most records as review/fail. Ensures only highest-quality data flows to output.

### Pattern 2: "I want a triage queue"
Use the review category to build a manual review list. Records failing should be revisited or corrected upstream.

### Pattern 3: "I need different thresholds for different targets"
For Wikidata, require high completeness and confidence. For internal analysis, allow lower thresholds. Configure Proofing per output.

---

## Reference

- **Configuration File Format**: (Link to proofing config schema)
- **API Reference**: (Link to Proofer class)
- **Quality Metrics**: (Definition of completeness, consistency, confidence)
- **Review Workflow**: (Manual review process and feedback loops)
- **Related**: [Refinement](refinement.md) | [Blending](blending.md) | [Spirit Safe](spirit_safe.md)

---

## GitHub Issues & Development

Work on the Proofing stage is tracked under the [`proof` label](https://github.com/skybristol/gkc/issues?q=label%3Aproof). Issues represent scoring strategies, threshold definitions, and review workflow improvements.

**Other Workflow Stages:**
- [`mash`](https://github.com/skybristol/gkc/issues?q=label%3Amash) — Data Ingestion
- [`ferment`](https://github.com/skybristol/gkc/issues?q=label%3Aferment) — Cleaning & Normalization
- [`distill`](https://github.com/skybristol/gkc/issues?q=label%3Adistill) — Reconciliation & Linking
- [`refine`](https://github.com/skybristol/gkc/issues?q=label%3Arefine) — Deduplication & Enrichment
- [`blend`](https://github.com/skybristol/gkc/issues?q=label%3Ablend) — Multi-Source Merging
- [`bottle`](https://github.com/skybristol/gkc/issues?q=label%3Abottle) — Format & Export
