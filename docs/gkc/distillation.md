# Distillation: Reconciliation & Entity Linking

## Overview

**Distillation** is where messy, local data gets linked to canonical reference entities. After clean records flow from [Fermentation](fermentation.md), Distillation matches source records against authoritative systems—Wikidata items, OpenStreetMap features, external authority files—and creates explicit logical links. It's the "reconciliation" or "entity resolution" stage.

Like whiskey distillation concentrating alcohol from grain mash, Distillation concentrates signal by resolving ambiguity and creating authoritative links.

| Aspect | Details |
|--------|---------|
| **Input** | Clean, normalized records from Fermentation |
| **What Happens** | Entity matching, disambiguation, external linking, confidence scoring |
| **Output** | Records with explicit links to canonical entities (Wikidata QIDs, OSM IDs, etc.) + confidence metadata |
| **Best For** | Creating reusable links, disambiguating ambiguous names, authority file integration |
| **Typical Duration** | Hours to days, depending on dataset size and matching complexity |

---

## The Problem Distillation Solves

Local source data doesn't know about canonical entities:

- **Ambiguity**: "Smith" could match thousands of Wikidata items; which one?
- **Variation**: "United States", "USA", "US", "America" all refer to the same entity
- **Authority gaps**: Source records lack persistent identifiers from authoritative systems
- **Transitive relationships**: A person worked for an organization; which Wikidata organizations match that name?
- **Confidence vs. certainty**: Some matches are obvious; others need human review or heuristics

**The cost of skipping Distillation**: Your data remains local and isolated. A downstream user has no way to know that your "Alice Johnson" row corresponds to Wikidata item Q12345678. You miss opportunities for linked data enrichment.

---

## Input Contract

Records entering Distillation should be:

1. **Clean and normalized** — From Fermentation; consistent types, vocabulary, encoding
2. **Schema-conformant** — All records have expected fields
3. **Identified** — Each has a source_id and provenance metadata

References should include:
- **Field specifications** — Which fields are candidates for matching? (Name, location, category, etc.)
- **Authority targets** — Which systems to match against? (Wikidata, OSM, custom authority files)
- **Match strategies** — Exact, substring, fuzzy, heuristic?

**Example input:**
```json
{
  "source_id": "researchers_csv:R001",
  "name": "Alice Johnson",
  "birth_year": 1987,
  "field_of_study": "Physics",
  "publication_count": 42,
  "_source": "researchers_csv",
  "_ingestion_timestamp": "2025-02-13T09:00:00Z"
}
```

---

## Core Transformations

### 1. Exact & Fuzzy String Matching

**Goal**: Match source text values against known entity names.

```python
# Exact match (fast but limited)
matches = authority_index["name"] == record["name"]

# Fuzzy matching (handles typos, abbreviations)
from difflib import SequenceMatcher
for candidate_name in authority_names:
    ratio = SequenceMatcher(None, record["name"], candidate_name).ratio()
    if ratio > 0.85:  # "Alice Johnson" vs. "Alice Jonson" matches
        candidates.append((candidate_name, ratio))

# Phonetic matching (handles name variations)
from fuzzy_match import fuzzy_match
if fuzzy_match(record["name"], candidate_name, method="metaphone"):
    candidates.append(candidate_name)
```

**Decision Point**:
- Exact only, or allow fuzzy? (Exact: fewer false matches; fuzzy: catches more)
- Fuzzy threshold? (0.8 = loose; 0.95 = very strict)
- Should you apply fuzzy matching only if exact fails?
- How to handle multiple close matches?

---

### 2. Multi-Field Disambiguation

**Goal**: Use multiple fields to disambiguate when names alone are ambiguous.

```python
# Example: multiple "Smith" candidates
candidates = [
    {"qid": "Q1234", "name": "John Smith", "birth_year": 1950, "field": "Chemistry"},
    {"qid": "Q5678", "name": "John Smith", "birth_year": 1978, "field": "Biology"},
    {"qid": "Q9012", "name": "John Smith", "birth_year": 1987, "field": "Physics"},
]

source_record = {
    "name": "John Smith",
    "birth_year": 1987,
    "field_of_study": "Physics"
}

# Score candidates by field similarity
scores = []
for candidate in candidates:
    score = 0
    score += 1 if candidate["name"] == source_record["name"] else 0  # Name match
    score += 0.5 if abs(candidate["birth_year"] - source_record["birth_year"]) < 2 else 0  # Close birth year
    score += 1 if candidate["field"] == source_record["field_of_study"] else 0  # Field match
    scores.append((candidate["qid"], score))

best_match = max(scores, key=lambda x: x[1])  # Q9012 with score 2.5
```

**Decision Point**:
- Which fields are useful for disambiguation? (Birth year, location, occupation, etc.)
- How to weight different field similarities?
- If no clear best match, flag for manual review or set confidence threshold?

---

### 3. Authority File & External Lookups

**Goal**: Query external authority files, thesauri, and reference databases.

```python
# Wikidata SPARQL query
wikidata_query = """
SELECT ?item ?itemLabel WHERE {
  ?item wdt:P31 wd:Q5 . # Is a human
  ?item rdfs:label "%s"@en .
  BIND(LANG(?itemLabel) as ?lang)
  FILTER(?lang = "en")
}
LIMIT 5
""" % record["name"]

# OSM overpass query for locations
osm_query = f"""
[bbox:{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}];
(node["name"="{record['location']}"];);
out center;
"""

# Local authority file lookup
authority_record = authority_index.lookup_by_name(record["name"])
```

**Decision Point**:
- Which external authorities are relevant? (Wikidata, VIAF, Library of Congress, etc.)
- Cache results or query fresh each time?
- Timeout strategy for slow authority queries?
- Handle API rate limits?

---

### 4. Confidence Scoring & Thresholds

**Goal**: Assign confidence scores to matches; flag uncertain results.

```python
confidence_framework = {
    "exact_name_match": {"weight": 0.4, "score": 1.0 if exact else 0.0},
    "fuzzy_name_similarity": {"weight": 0.2, "score": fuzzy_ratio},
    "birth_year_match": {"weight": 0.15, "score": 1.0 if abs(year_diff) < 1 else max(0, 1 - year_diff/10)},
    "location_match": {"weight": 0.15, "score": 1.0 if location_exact else 0.5},
    "occupational_fit": {"weight": 0.1, "score": 1.0 if occupation_matches else 0.0},
}

total_score = sum(v["weight"] * v["score"] for v in confidence_framework.values())

# Apply thresholds
if total_score >= 0.95:
    match_status = "high_confidence"
elif total_score >= 0.7:
    match_status = "medium_confidence"
    record["_distillation_flags"].append(f"manual_review_suggested: score={total_score}")
else:
    match_status = "low_confidence"
    record["_distillation_flags"].append(f"no_match_found")

record["_match_confidence"] = total_score
record["_match_status"] = match_status
```

**Decision Point**:
- What confidence framework makes sense for your domain?
- High threshold (fewer false positives) or low (fewer missed matches)?
- Track scoring breakdowns for debugging?
- Allow partial matches (location but not name)?

---

### 5. Relationship & Transitive Linking

**Goal**: Link not just the primary entity but related entities too.

```python
# Primary match: person to Wikidata item
record["_wikidata_qid"] = matched_qid

# Secondary matches: employer, location, etc.
employer_name = record["employer"]
employer_candidates = wikidata_search(employer_name, instance_of="Q43229")  # Organization
record["_employer_wikidata_qid"] = best_match(employer_candidates)

# OSM location link
location_name = record["location"]
osm_location = osm_search(location_name)
record["_osm_id"] = osm_location["id"]

# Track all matched entities for downstream use
record["_matched_entities"] = {
    "primary": {"system": "wikidata", "id": matched_qid, "type": "person"},
    "employer": {"system": "wikidata", "id": employer_qid, "type": "organization"},
    "location": {"system": "osm", "id": osm_id, "type": "place"}
}
```

**Decision Point**:
- Link only primary entity or also relationships?
- Transitive matching depth (just direct links or multi-hop)?
- What to do if a secondary link fails but primary succeeds?

---

## Output Contract

Records exiting Distillation should:

1. **Have primary links** — Matched to canonical entity (Wikidata QID, OSM ID, etc.)
2. **Have confidence scores** — Quantified match quality
3. **Have secondary links** — Related entities (employer, location, etc.) if relevant
4. **Be flagged** — Low-confidence or ambiguous matches flagged for review
5. **Keep original data** — All source fields retained; nothing overwritten

**Example output record:**
```json
{
  "source_id": "researchers_csv:R001",
  "name": "Alice Johnson",
  "birth_year": 1987,
  "field_of_study": "Physics",
  "publication_count": 42,
  "_source": "researchers_csv",
  "_wikidata_qid": "Q12345678",
  "_match_confidence": 0.98,
  "_match_status": "high_confidence",
  "_matched_entities": {
    "primary": {"system": "wikidata", "id": "Q12345678", "type": "person"},
    "employer": {"system": "wikidata", "id": "Q567890", "type": "organization"}
  },
  "_distillation_flags": []
}
```

---

## Angel's Share (Schema Deviations)

During Distillation, some records or fields won't cleanly map to authoritative entities. Keep those as **Angel's Share** data instead of discarding them. Store unmapped values with deviation notes (for example, in `_angel_share`) so they can inform future schema expansions or alternative endpoints.

---

## Configuration & Decisions

Distillation is highly configurable. Before running it, define:

### 1. Matching Strategy
- Which fields to match on? (Name, dates, locations?)
- Exact, fuzzy, phonetic, or all three?
- Fuzzy thresholds?

### 2. Authority Targets
- Which systems to match against? (Wikidata, OSM, VIAF, etc.)
- Which queries or filters per authority? (e.g., "humans only" for Wikidata)
- Caching strategy?

### 3. Confidence Framework
- Which signals to weigh? (Name, dates, relationships, etc.)
- Weights for each signal?
- Confidence thresholds for high/medium/low?

### 4. Escalation Strategy
- Below a threshold, flag for manual review?
- Allow multiple plausible matches, or require single best?
- Chain matches (if match A → B and B → C, consider C)?

---

## A Worked Example

**Scenario**: You have a list of authors and want to link them to Wikidata.

**Input record:**
```json
{
  "source_id": "authors:A123",
  "name": "Carl Sagan",
  "birth_year": 1934,
  "nationality": "USA",
  "field_of_study": "Astronomy"
}
```

**Distillation config:**
```python
config = {
    "match_fields": ["name", "birth_year"],
    "exact_threshold": 1.0,
    "fuzzy_threshold": 0.85,
    "confidence_framework": {
        "name_exact": {"weight": 0.5},
        "name_fuzzy": {"weight": 0.2},
        "birth_year": {"weight": 0.3}
    },
    "high_confidence_threshold": 0.85,
    "authority_targets": ["wikidata"]
}
```

**Distillation process:**

1. Exact name match: Search Wikidata for "Carl Sagan" → Found Q127063
2. Verify birth year: Wikidata Q127063 born 1934 → ✓ Match!
3. Cross-check: Field is Astronomy → Wikidata says Astronomer → ✓ Fits!
4. Calculate confidence: name_exact (1.0) * 0.5 + birth_year (1.0) * 0.3 + fuzzy bonus (0.0) * 0.2 = 0.8 → High confidence

**Output:**
```json
{
  "source_id": "authors:A123",
  "name": "Carl Sagan",
  "birth_year": 1934,
  "nationality": "USA",
  "field_of_study": "Astronomy",
  "_wikidata_qid": "Q127063",
  "_match_confidence": 0.95,
  "_match_status": "high_confidence",
  "_matched_entities": {
    "primary": {"system": "wikidata", "id": "Q127063", "type": "person"}
  },
  "_distillation_flags": []
}
```

---

## Supporting Systems

### Schema Registry
Distillation uses:
- Entity type definitions (what makes a valid match for each type?)
- Authority file catalogues (which systems are available?)
- Match query templates for each authority

### Spirit Safe (Validation)
Quality gates applied post-Distillation:
- Confidence thresholds enforced
- Link integrity checks (do linked entities exist?)
- Relationship coherence (does employer type make sense for person?)

### Barrel (Provenance)
Store:
- Authority query results (for reproducibility)
- Candidate lists and scoring details (for debugging)
- Confidence calculations (for audit)

---

## Relationship to Other Stages

**Before**: [Fermentation](fermentation.md) provides clean, normalized records

**After**: [Refinement](refinement.md) takes linked records and deduplicates, enriches, and validates them

**Parallel**: Spirit Safe validates links during distillation

---

## Common Patterns

### Pattern 1: "I need exact matches only, no fuzzy"
Set fuzzy thresholds to 1.0 (disabled) and use exact matching only. Increases false negatives but eliminates false positives. Good for high-stakes data where accuracy > coverage.

### Pattern 2: "I have multiple plausible matches"
Instead of forcing a single best match, export all candidates with confidence scores attached. Let downstream users (or Refinement stage) decide.

### Pattern 3: "I want to learn from past matches"
Cache results of manual reviews. Build a "match history" to improve heuristics over time (e.g., "when field_of_study matches, confidence +0.1").

---

## Reference

- **Configuration File Format**: (Link to distillation config schema once defined)
- **API Reference**: (Link to Distiller class once documented)
- **Authority Integrations**: (Links to Wikidata, OSM, VIAF integrations)
- **Matching Strategies**: (Detailed matching algorithm docs)
- **Troubleshooting**: (Link to common issues once compiled)
- **Related**: Schema Building | [Fermentation](fermentation.md) | [Refinement](refinement.md) | Spirit Safe

---

## GitHub Issues & Development

Work on the Distillation stage is tracked under the [`distill` label](https://github.com/skybristol/gkc/issues?q=label%3Adistill). Issues tagged with this label represent implementation efforts, matching algorithm improvements, and authority system integrations.

**Other Workflow Stages:**
- [`mash`](https://github.com/skybristol/gkc/issues?q=label%3Amash) — Data Ingestion
- [`ferment`](https://github.com/skybristol/gkc/issues?q=label%3Aferment) — Cleaning & Normalization
- [`refine`](https://github.com/skybristol/gkc/issues?q=label%3Arefine) — Deduplication & Enrichment
- [`proof`](https://github.com/skybristol/gkc/issues?q=label%3Aproof) — Quality Assurance
- [`blend`](https://github.com/skybristol/gkc/issues?q=label%3Ablend) — Multi-Source Merging
- [`bottle`](https://github.com/skybristol/gkc/issues?q=label%3Abottle) — Format & Export
