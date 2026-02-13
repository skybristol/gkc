# Bottling: Format & Export

## Overview

**Bottling** is the final stage: transforming refined, proofed, and blended data into concrete outputs for downstream systems. Bottling doesn't create new knowledge—it packages knowledge in the right formats for Wikidata, Wikipedia, Wikimedia Commons, OpenStreetMap, and other targets.

| Aspect | Details |
|--------|---------|
| **Input** | Blended, proofed dataset with canonical identifiers |
| **What Happens** | Formatting, serialization, packaging, validation, export staging |
| **Output** | Wikidata JSON, infobox templates, Commons metadata, OSM tags, reports |
| **Best For** | Preparing data for contribution or publication |
| **Typical Duration** | Minutes to hours, depending on output volume |

---

## The Problem Bottling Solves

Even perfect data isn't useful until it's packaged correctly:

- **Different targets require different formats** (Wikidata JSON vs. OSM tags)
- **Data must be validated per system** (Wikidata constraints, OSM tag conventions)
- **Batch sizes and rate limits** must be respected
- **Export needs provenance** (citations, references, sources)
- **Human review artifacts** may be needed (reports, previews)

**The cost of skipping Bottling**: Data isn't deployable, and manual packaging is error-prone.

---

## Input Contract

Records entering Bottling should:

1. **Be proofed and blended** — Only records that passed or were approved
2. **Have canonical identifiers** — QIDs, OSM IDs, etc.
3. **Include provenance** — References and source metadata
4. **Be validated** — No known schema errors or conflicts

---

## Core Transformations

### 1. Target-Specific Serialization

**Goal**: Convert unified records into the format expected by each target system.

```python
# Wikidata JSON format
wikidata_payload = {
    "id": record["_wikidata_qid"],
    "claims": {
        "P31": ["Q5"],  # instance of human
        "P569": [{"value": record["birth_year"], "type": "time"}],
        "P27": [{"value": record["nationality_qid"], "type": "wikibase-item"}]
    }
}

# Wikipedia infobox template
infobox = f"""
{{Infobox scientist
 | name = {record['name']}
 | birth_date = {record['birth_year']}
 | nationality = {record.get('nationality_label', '')}
 | fields = {record.get('field_of_study', '')}
}}
"""

# OSM tag set
osm_tags = {
    "name": record["name"],
    "amenity": "research_institute",
    "wikidata": record["_wikidata_qid"]
}
```

**Decision Point**:
- Which outputs are required for this run?
- How strict should target validation be before export?
- Should you generate preview artifacts for review?

---

### 2. Reference & Citation Packaging

**Goal**: Ensure claims are supported by citations and provenance metadata.

```python
# Wikidata references
wikidata_payload["references"] = [
    {
        "P854": record["source_url"],
        "P813": record["_ingestion_timestamp"],  # retrieved
        "P248": record.get("source_qid")  # stated in
    }
]

# OSM changeset tags
osm_changeset = {
    "comment": "Added institution data from official registry",
    "source": record["source_name"],
    "created_by": "gkc-bottler"
}
```

**Decision Point**:
- How to map provenance to references per target?
- Required citation formats per system?

---

### 3. Validation & Constraints

**Goal**: Ensure export conforms to target system constraints.

```python
# Example: Wikidata constraint check
if "P569" in wikidata_payload["claims"]:
    if not is_valid_time(wikidata_payload["claims"]["P569"]):
        record["_bottling_flags"].append("invalid_birth_date")

# Example: OSM tag validation
if "amenity" in osm_tags:
    if osm_tags["amenity"] not in osm_allowed_amenities:
        record["_bottling_flags"].append("invalid_osm_tag")
```

**Decision Point**:
- Fail export on validation error, or flag and continue?
- Keep validation rules close to target system or simplified?

---

### 4. Export Packaging & Batching

**Goal**: Prepare export files or API batches.

```python
# Batch Wikidata edits
batch = []
for record in records:
    if record["_proofing_status"] == "pass":
        batch.append(serialize_wikidata(record))
    if len(batch) == 500:  # Batch size limit
        write_batch(batch, filename=f"wikidata_batch_{i}.json")
        batch = []

# Write CSV export
write_csv(records, "bottled_output.csv")

# Generate report for review
write_report(records, "bottling_report.md")
```

**Decision Point**:
- Batch size limits per target?
- Should failed records be exported to a separate review file?
- Should bottling output be dry-run or write-ready?

---

## Output Contract

Records exiting Bottling should:

1. **Be serialized** — In the required format(s)
2. **Include references** — Provenance and citations attached
3. **Be validated** — Target system constraints satisfied
4. **Be packaged** — Batched and ready for upload or manual review

---

## Angel's Share (Schema Deviations)

If some fields or values don't fit the export target, do not throw them away. Preserve them as **Angel's Share** data with deviation notes and provenance so they can be considered for future targets or schema expansions.

---

## Configuration & Decisions

Before running Bottling, define:

### 1. Target Outputs
- Wikidata, Wikipedia, Commons, OSM, or custom target
- Output formats required

### 2. Citation Rules
- How to map source metadata into citations
- Required references per target

### 3. Validation Policy
- Strict vs. lenient validation
- Which validation errors stop export vs. just flag

### 4. Export Strategy
- Batch size limits
- Dry-run vs. write-ready output
- Review report format

---

## A Worked Example

**Scenario**: Export a dataset to Wikidata and generate a Wikipedia infobox.

**Input record:**
```json
{
  "name": "Alice Johnson",
  "birth_year": 1987,
  "nationality_qid": "Q30",
  "_wikidata_qid": "Q12345678",
  "source_url": "https://example.org/researchers.csv",
  "_proofing_status": "pass"
}
```

**Bottling config:**
```python
config = {
    "targets": ["wikidata", "wikipedia"],
    "batch_size": 500,
    "include_references": True
}
```

**Output (Wikidata JSON):**
```json
{
  "id": "Q12345678",
  "claims": {
    "P31": ["Q5"],
    "P569": [{"value": "1987-01-01", "type": "time"}],
    "P27": [{"value": "Q30", "type": "wikibase-item"}]
  },
  "references": [
    {"P854": "https://example.org/researchers.csv", "P813": "2025-02-13"}
  ]
}
```

**Output (Infobox template):**
```text
{{Infobox scientist
 | name = Alice Johnson
 | birth_date = 1987
 | nationality = American
}}
```

---

## Supporting Systems

### Cooperage (Schema Registry)
Provides:
- Property mappings for each target
- Output format definitions

### Spirit Safe (Validation)
Provides:
- Final constraint checks
- Target-specific validation rules

### Barrel (Provenance)
Stores:
- Export batches
- Reports and audit logs

---

## Relationship to Other Stages

**Before**: [Blending](blending.md) merges datasets into a unified whole

**After**: Data is ready for upload or manual contribution to target systems

---

## Common Patterns

### Pattern 1: "I need a dry-run first"
Generate export files and reports without uploading. Use diff or review to confirm before pushing to target systems.

### Pattern 2: "I need multiple outputs"
Configure Bottling to output in multiple formats at once (Wikidata JSON + Wikipedia infobox + OSM tags).

### Pattern 3: "I want to export only high-confidence records"
Filter by `_proofing_status == "pass"` or a minimum quality threshold.

---

## Reference

- **Configuration File Format**: (Link to bottling config schema)
- **API Reference**: (Link to Bottler class)
- **Target Output Specs**: (Links to Wikidata JSON, OSM, Commons, Wikipedia formats)
- **Related**: [Blending](blending.md) | [Proofing](proofing.md) | [Wikidata Maintainer](wd_item_maintainer.md)

---

## GitHub Issues & Development

Work on the Bottling stage is tracked under the [`bottle` label](https://github.com/skybristol/gkc/issues?q=label%3Abottle). Issues represent exporter support, output validation rules, and target-specific packaging.

**Other Workflow Stages:**
- [`mash`](https://github.com/skybristol/gkc/issues?q=label%3Amash) — Data Ingestion
- [`ferment`](https://github.com/skybristol/gkc/issues?q=label%3Aferment) — Cleaning & Normalization
- [`distill`](https://github.com/skybristol/gkc/issues?q=label%3Adistill) — Reconciliation & Linking
- [`refine`](https://github.com/skybristol/gkc/issues?q=label%3Arefine) — Deduplication & Enrichment
- [`proof`](https://github.com/skybristol/gkc/issues?q=label%3Aproof) — Quality Assurance
- [`blend`](https://github.com/skybristol/gkc/issues?q=label%3Ablend) — Multi-Source Merging
