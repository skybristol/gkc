# Mash Tun: Data Ingestion & Parsing

## Overview

**Mash Tun** is the entry point to the Data Distillery. Raw data from diverse sources—CSV files, JSON APIs, spreadsheets, RDF dumps, databases—arrives in many formats. The Mash Tun parses these heterogeneous sources into a standardized internal working format: structured records with identified fields ready for cleaning.

It's the "grain mill" of the pipeline—breaking down whole grains (raw data) into consistent meal that flows to subsequent stages.

| Aspect | Details |
|--------|---------|
| **Input** | Raw files in any format (CSV, JSON, XML, RDF, databases, APIs) |
| **What Happens** | Format parsing, structural validation, field identification, basic enrichment |
| **Output** | Standardized records with identified fields; ready for fermentation |
| **Best For** | Onboarding diverse data sources, handling format variations, initial extraction |
| **Typical Duration** | Minutes to hours, depending on source complexity and volume |

---

## The Problem Mash Tun Solves

Raw data sources are inherently messy and diverse:

- **Format heterogeneity**: CSV, JSON, XML, RDF, databases, API responses all need parsing
- **Schema variation**: Different sources may have different column names, nesting, structure
- **Field identification**: Which columns/fields matter? Are they named consistently?
- **Incomplete records**: Some sources have rows with missing columns
- **Encoding chaos**: Different files use different encodings (UTF-8, Latin-1, etc.)
- **Metadata gaps**: No clear source provenance, record ID scheme, or collection timestamp

**The cost of not parsing well**: Downstream stages make assumptions about record structure. If Mash Tun is sloppy, every stage downstream has to compensate. Better to invest here once.

---

## Input Contract

Before records enter the Mash Tun, you need:

1. **Accessible data source** — File path, API endpoint, database connection, or stream
2. **Format specification** — CSV dialect, JSON schema, XML structure, or API docs
3. **Source identification** — Name or ID for audit trail (which source is this from?)

**Example input sources:**
```
- file: data/researchers.csv (CSV with header row)
- API: https://api.example.com/publications (JSON array endpoint)
- database: researchers_db.sqlite3 (SQL query results)
- RDF: https://example.org/data.ttl (Turtle RDF dump)
```

---

## Core Transformations

### 1. Format-Specific Parsing

**Goal**: Read the raw format into standardized Python objects (dicts, lists, etc.).

```python
# CSV: parse dialect (delimiter, quoting, encoding), read headers
import csv
with open('data.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=',')
    records = list(reader)

# JSON: validate structure, extract array or iterate stream
import json
with open('data.json') as f:
    records = json.load(f)  # Expect list of objects
    # or: records = [json.loads(line) for line in f]  # JSONL format

# XML: parse and extract elements
import xml.etree.ElementTree as ET
tree = ET.parse('data.xml')
root = tree.getroot()
records = [dict((child.tag, child.text) for child in elem) for elem in root.findall('record')]

# RDF: parse and query for triples
from rdflib import Graph
g = Graph()
g.parse('data.ttl', format='turtle')
records = [dict(row) for row in g.query('SELECT * WHERE {...}')]
```

**Decision Point**:
- How to handle parsing errors (strict: fail fast; lenient: skip bad records)?
- For CSV files: auto-detect dialect, or require explicit specification?
- For JSON: expect single array or line-delimited objects?
- For APIs: paginate? Stream? Cache response?
- Character encoding: auto-detect or require specification?

---

### 2. Field Identification & Normalization

**Goal**: Identify which fields matter and normalize field names for consistency.

```python
# Example: multiple sources with variant field names
source_1 = {"name": "...", "birth_date": "...", "country_code": "..."}
source_2 = {"Name": "...", "DOB": "...", "Country": "..."}
source_3 = {"full_name": "...", "birth_year": "...", "nationality": "..."}

# Define a mapping to canonical field names
field_mappings_source_1 = {}  # Already canonical
field_mappings_source_2 = {
    "Name": "name",
    "DOB": "birth_date",
    "Country": "country_code"
}
field_mappings_source_3 = {
    "full_name": "name",
    "birth_year": "birth_date",  # Note: different granularity, handled later
    "nationality": "country_code"
}

# Normalize all records
for record in all_records:
    mapping = get_mapping_for_source(record['_source_id'])
    record = {mapping.get(k, k): v for k, v in record.items()}
```

**Decision Point**:
- Have a canonical schema before parsing, or infer from first source?
- How to handle field name variations (nicknames, abbreviations, language differences)?
- Should you keep original field names for audit trail?
- For hierarchical data (nested objects), flatten or preserve structure?

---

### 3. Record Identification

**Goal**: Ensure each record has a unique, stable identifier from the source.

```python
# Option A: Source already has an ID
record['source_id'] = record['id']
record['source'] = 'researchers_db'

# Option B: Generate ID from combination of fields
import hashlib
key = f"{record['name']}_{record['birth_date']}"
record['source_id'] = hashlib.md5(key.encode()).hexdigest()[:12]

# Option C: Auto-increment or UUID
import uuid
record['source_id'] = str(uuid.uuid4())
record['_id_generated'] = True  # Track that we generated it

# All records should track source provenance
record['_source'] = 'researchers_db'
record['_batch_id'] = batch_timestamp
record['_ingestion_timestamp'] = datetime.now().isoformat()
```

**Decision Point**:
- Is there a natural primary key in the source? Use it or generate?
- Should you track how the ID was determined (found vs. generated)?
- Include ingestion timestamp and batch ID for reproducibility?

---

### 4. Structural Validation

**Goal**: Confirm records have required fields; catch schema mismatches early.

```python
expected_fields = ["name", "birth_date", "country_code"]
optional_fields = ["biography", "website"]

for i, record in enumerate(records):
    # Check for required fields
    missing = [f for f in expected_fields if f not in record]
    if missing:
        record['_mash_tun_issues'] = f"Missing required fields: {missing}"
        # Decide: skip record, flag for review, or error out?
    
    # Check for unexpected fields
    expected_set = set(expected_fields + optional_fields + ['source_id', '_source'])
    unexpected = set(record.keys()) - expected_set
    if unexpected:
        record['_mash_tun_warnings'] = f"Unexpected fields: {unexpected}"
```

**Decision Point**:
- Strict validation (reject any deviation) or permissive (warn and keep)?
- What counts as "required" vs. "optional"?
- Should unexpected fields cause an error or just a warning?
- Track issues in a `_issues` field or separate error log?

---

### 5. Data Enrichment

**Goal**: Add metadata, context, or derived fields useful for downstream processing.

```python
# Add enrichment
record['_ingestion_source_url'] = 'https://example.org/researchers.csv'
record['_batch_timestamp'] = '2025-02-13T14:30:00Z'
record['_data_version'] = '1.0'

# Derive field counts, detect data types
record['_field_count'] = len(record)
record['_null_count'] = sum(1 for v in record.values() if v is None or v == '')

# Add confidence or quality hints (used by later stages)
record['_record_completeness'] = (
    record['_field_count'] - record['_null_count']
) / record['_field_count']
```

**Decision Point**:
- Which enrichment fields are essential vs. nice-to-have?
- Should you compute data quality hints here, or defer to Proofing stage?
- How much metadata to attach? (Helps traceability but adds storage)

---

## Output Contract

Records exiting the Mash Tun should:

1. **Be structurally consistent** — All records have the same fields (even if some are null)
2. **Have identified fields** — Field names are canonical and documented
3. **Have provenance** — Source, batch ID, ingestion timestamp recorded
4. **Have unique IDs** — Each record has a stable source_id
5. **Be flagged** — Structural issues or anomalies recorded (not rejected, but noted)

**Example output record:**
```json
{
  "source_id": "researchers_db_4521",
  "name": "Alice Johnson",
  "birth_date": "1987-03-15",
  "country_code": "US",
  "biography": "Physicist and author",
  "website": "https://example.org/alice",
  "_source": "researchers_db",
  "_source_version": "1.0",
  "_batch_id": "batch_20250213_morning",
  "_ingestion_timestamp": "2025-02-13T09:30:00Z",
  "_field_count": 6,
  "_null_count": 0,
  "_record_completeness": 1.0,
  "_mash_tun_issues": null
}
```

---

## Angel's Share (Schema Deviations)

Raw sources often contain fields that don't fit your current schema. Rather than dropping them, keep those fields in an **Angel's Share** sidecar (for example, `_angel_share`) with notes about how they deviate. This preserves alternative ingredients for future schema expansion or different downstream endpoints.

---

## Configuration & Decisions

Most Mash Tun work is *configuration*. Before ingesting a new source, you define:

### 1. Source Specification
- Format type (CSV, JSON, RDF, database, API)?
- Connection details (file path, API endpoint, query)?
- Character encoding (UTF-8, Latin-1, auto-detect)?
- Source name and version for tracking

### 2. Field Mapping
- Canonical field names (your schema)
- Mapping from source field names to canonical names
- Which fields are required vs. optional?
- Any field transformations (flatten nested, join columns)?

### 3. Record Identification
- Is there a natural primary key? Use it or generate?
- How to handle duplicate IDs?
- Track source and batch metadata?

### 4. Validation Strategy
- Strict (fail on schema mismatch) or permissive (flag and continue)?
- Which structural issues cause rejection vs. warning?
- How to handle records with missing required fields?

---

## A Worked Example

**Scenario**: You're ingesting researcher data from two sources—a CSV database export and a JSON API—and need to merge them into a common working format.

**Source 1: CSV file (researchers.csv)**
```csv
researcher_id,Full Name,Birth Year,Field,num_pubs
R001,Alice Johnson,1987,Physics,42
R002,Bob Smith,1978,Computer Science,
R003,Carol Garcia,1992,Art History,5
```

**Source 2: JSON API (https://api.example.org/researchers)**
```json
[
  {
    "id": "external_A1",
    "researcher_name": "Alice Johnson",
    "birth_year": 1987,
    "specialization": "Physics",
    "publications": 50
  }
]
```

**Schema you define:**
```python
canonical_schema = {
    "source_id": "string",
    "name": "string",
    "birth_year": "int",
    "field_of_study": "string",
    "publication_count": "int"
}
```

**Field mappings:**
```python
csv_mapping = {
    "researcher_id": "source_id",
    "Full Name": "name",
    "Birth Year": "birth_year",
    "Field": "field_of_study",
    "num_pubs": "publication_count"
}

api_mapping = {
    "id": "source_id",
    "researcher_name": "name",
    "specialization": "field_of_study",
    "publications": "publication_count"
}
```

**After Mash Tun parsing:**
```json
[
  {
    "source_id": "researchers_csv:R001",
    "name": "Alice Johnson",
    "birth_year": "1987",
    "field_of_study": "Physics",
    "publication_count": null,
    "_source": "researchers_csv",
    "_batch_id": "batch_20250213",
    "_ingestion_timestamp": "2025-02-13T09:00:00Z",
    "_mash_tun_issues": null
  },
  {
    "source_id": "researchers_csv:R002",
    "name": "Bob Smith",
    "birth_year": "1978",
    "field_of_study": "Computer Science",
    "publication_count": null,
    "_source": "researchers_csv",
    "_batch_id": "batch_20250213",
    "_ingestion_timestamp": "2025-02-13T09:00:00Z",
    "_mash_tun_issues": null
  },
  {
    "source_id": "researchers_api:external_A1",
    "name": "Alice Johnson",
    "birth_year": 1987,
    "field_of_study": "Physics",
    "publication_count": 50,
    "_source": "researchers_api",
    "_batch_id": "batch_20250213",
    "_ingestion_timestamp": "2025-02-13T09:15:00Z",
    "_mash_tun_issues": null
  }
]
```

Notice: Same person (Alice) appears twice with different IDs and publication counts. Fermentation will normalize types, Distillation will later link these as the same entity.

---

## Supporting Systems

### Schema Registry
Mash Tun relies on:
- Canonical field names and types
- Source-to-canonical field mappings
- Field cardinality (required vs. optional)

### Barrel (Caching & Provenance)
Store:
- Original raw files/API responses for audit trail
- Mash Tun configuration used for this ingestion
- Error logs and flagged records
- Snapshot for potential rollback

---

## Relationship to Other Stages

**Before**: Raw data sources (CSV, API, databases, RDF)

**After**: [Fermentation](fermentation.md) takes parsed records and cleans, normalizes, and validates them.

**Skip Mash Tun if**: Your data is already in standardized, clean format with consistent field names and IDs. (Rare! Usually comes from a previous pipeline stage.)

---

## Common Patterns

### Pattern 1: "I have multiple sources with different schemas"
Define a canonical schema that's the superset of all sources. Create field mappings for each source. This way, Fermentation sees a unified schema but knows which source each record came from.

### Pattern 2: "I want to audit what was dropped or flagged"
Use permissive validation in Mash Tun (flag but don't reject). Export flagged records separately. Fermentation can then decide to skip them or try to fix them.

### Pattern 3: "My API has pagination or streaming"
Handle pagination in Mash Tun config. Cache full results in Barrel for reproducibility. Track batch ID and count so you know how many records you ingested.

---

## Reference

- **Configuration File Format**: (Link to mash tun config schema once defined)
- **API Reference**: (Link to MashTun class once documented)
- **Format Parsers**: (Link to format-specific parsing docs)
- **Troubleshooting**: (Link to common issues once compiled)
- **Related**: Schema Building | [Fermentation](fermentation.md) | Barrel (provenance & caching)

---

## GitHub Issues & Development

Work on the Mash Tun stage is tracked under the [`mash` label](https://github.com/skybristol/gkc/issues?q=label%3Amash). Issues tagged with this label represent implementation efforts, format support additions, and improvements for the data ingestion stage.

**Other Workflow Stages:**
- [`ferment`](https://github.com/skybristol/gkc/issues?q=label%3Aferment) — Cleaning & Normalization
- [`distill`](https://github.com/skybristol/gkc/issues?q=label%3Adistill) — Reconciliation & Linking
- [`refine`](https://github.com/skybristol/gkc/issues?q=label%3Arefine) — Deduplication & Enrichment
- [`proof`](https://github.com/skybristol/gkc/issues?q=label%3Aproof) — Quality Assurance
- [`blend`](https://github.com/skybristol/gkc/issues?q=label%3Ablend) — Multi-Source Merging
- [`bottle`](https://github.com/skybristol/gkc/issues?q=label%3Abottle) — Format & Export
