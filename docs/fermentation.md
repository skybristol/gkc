# Fermentation: Cleaning & Normalization

## Overview

**Fermentation** is where messy, heterogeneous data becomes clean and coherent. After raw data is parsed and structured in the [Mash Tun](mash_tun.md), records flow into fermentation for sanitization, type coercion, encoding fixes, and schema conformance. It's the "washing and preparation" stage—essential groundwork before any matching or linking can happen.

| Aspect | Details |
|--------|---------|
| **Input** | Parsed, structured records from the Mash Tun |
| **What Happens** | Whitespace handling, type coercion, encoding normalization, schema validation, missing value handling |
| **Output** | Clean records all conforming to expected schema; ready for reconciliation |
| **Best For** | Fixing typos, standardizing formats, catching bad data early |
| **Typical Duration** | Minutes to hours, depending on dataset size and messiness |

---

## The Problem Fermentation Solves

Raw data from diverse sources rarely arrives "ready":

- **Encoding issues**: UTF-8 mixing, BOM markers, mojibake
- **Whitespace problems**: Leading/trailing spaces, irregular tabs, CRLF vs. LF
- **Type inconsistency**: Numbers stored as strings, dates in 5 different formats, boolean true/false/TRUE/1/"yes"
- **Missing values**: NULL, "N/A", empty strings, "unknown", zeros all meaning "no data"
- **Schema deviations**: Extra columns, missing expected fields, nested data in flat columns
- **Systematic errors**: Misspellings in enumerated fields, off-by-one errors, abbreviations

**The cost of not cleaning early**: Every downstream stage (Distillation, Refinement, Proofing) becomes harder. Better to catch and fix problems here, once, than to debug them through three more stages.

---

## Input Contract

Before records enter fermentation, they should be:

1. **Structurally valid** — Parsed from a source format (CSV, JSON, etc.) into a standardized working record
2. **Presence complete** — All rows have all expected fields (even if values are null)
3. **Identified** — Each record has a unique, stable identifier from the source

**Example input record:**
```json
{
  "source_id": "row_4521",
  "name": " John Smith  ",
  "birth_date": "1987/3/15",
  "nationality": "usa",
  "has_published": "yes",
  "website": "",
  "gender": "M"
}
```

Notice the problems: leading spaces in name, date format, string booleans, abbreviations, empty string meaning null.

---

## Core Transformations

### 1. Encoding & Whitespace Normalization

**Goal**: Ensure consistent UTF-8, remove invisible noise, prepare for text matching.

```python
# Pseudo-code: what should happen
record["name"] = record["name"].strip()  # Remove leading/trailing whitespace
record["name"] = normalize_unicode(record["name"])  # Combine decomposed accents
record["raw_name"] = record["name"]  # Keep original for provenance
```

**Decision Point**: 
- Keep a `_raw` field for each cleaned field, storing the original? (Useful for debugging, adds storage)
- Which Unicode normalization form (NFC vs. NFD)? (Usually NFC for readability)
- Strip tabs/newlines from within field values, or preserve them?

---

### 2. Special Character Handling

**Goal**: Normalize or sanitize special characters, diacritics, and symbols consistently for matching and storage.

Text data often contains variation in how special characters are represented:
- **Diacritics**: Café vs. Cafe, Müller vs. Muller, São Paulo vs. Sao Paulo
- **Punctuation variants**: Smart quotes vs. straight quotes, en-dash vs. hyphen, ellipsis vs. three dots
- **Symbols**: ® vs. (R), © vs. (C), € vs. EUR
- **Combined characters**: e + combining acute accent vs. precomposed é

```python
# Example transformations
import unicodedata

# Option A: Remove diacritics entirely (aggressive)
def remove_accents(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'  # Mn = Mark, Nonspacing (accents)
    )
record["name"] = remove_accents(record["name"])  # "François" → "Francois"

# Option B: Keep diacritics but normalize form (conservative)
record["name"] = unicodedata.normalize('NFC', record["name"])

# Option C: Smart quotes to straight quotes
record["notes"] = record["notes"].replace('"', '"').replace('"', '"')
record["notes"] = record["notes"].replace(''', "'").replace(''', "'")

# Option D: Symbol standardization
symbol_map = {
    "®": "(R)",
    "©": "(C)",
    "€": "EUR",
    "…": "...",
    "–": "-",  # en-dash to hyphen
}
for symbol, replacement in symbol_map.items():
    record["description"] = record["description"].replace(symbol, replacement)
```

**Decision Point**:
- Keep diacritics or strip them? (Depends on target system: Wikidata preserves them, some APIs drop them)
- Normalize smart quotes and punctuation, or preserve original?
- Should symbol standardization be aggressive (€ → EUR) or conservative (keep as-is)?
- Which fields need special character handling? (Names, descriptions, titles yes; codes, IDs typically no)
- For matching purposes (Distillation stage), should you create both diacritic and non-diacritic variants?

---

### 3. Language Detection

**Goal**: Identify the language of text fields and potentially validate or separate records by language.

Multi-language datasets require explicit language tracking:
- **Mixed content**: Record with French name, English description, German keywords
- **Unknown language**: Text that doesn't match expected language for that field
- **Script mismatch**: Field expected to be Latin script but contains Arabic or Chinese
- **Language tagging**: For Wikidata/Wikipedia, language tags (en, fr, de) must be explicit

```python
# Example: detect language of free-text fields
from langdetect import detect, detect_langs  # or textblob, polyglot, etc.

# Simple detection
detected_lang = detect(record["description"])  # Returns 'en', 'fr', 'de', etc.
record["description_lang"] = detected_lang
record["description_lang_confidence"] = detect_langs(record["description"])[0].prob

# Validation: make sure text is in expected language
expected_lang = "en"
if detected_lang != expected_lang:
    record[f"_fermentation_flags"].append(f"language_mismatch: expected {expected_lang}, detected {detected_lang}")

# Handle multilingual field with language variants
if isinstance(record["title"], dict):  # {"en": "...", "fr": "..."}
    for lang, text in record["title"].items():
        detected = detect(text)
        if detected != lang:
            record["_fermentation_flags"].append(f"title[{lang}] detected as {detected}")
else:
    # Single language title; detect and tag it
    lang = detect(record["title"])
    record["title_detected_lang"] = lang
```

**Decision Point**:
- Should language detection be mandatory or optional? (Flag unknown languages vs. error out)
- Confidence threshold: what's "confident enough"? (0.5? 0.8? 0.95?)
- If language doesn't match expectation: error, warning, or just flag?
- For multilingual text (e.g., author names in two scripts), how to handle? (Tag each part separately, or flag as ambiguous?)
- Which text fields need language detection? (Names: rarely; descriptions: often; keywords: depends)
- Store detected language in separate `_lang` field per source field, or in a unified language metadata block?

---

### 4. Type Coercion

**Goal**: Convert values to expected types (int, date, boolean, enum) or flag failures.

```python
# Example transformations
record["birth_date"] = parse_date(record["birth_date"], formats=["%Y/%m/%d", "%m-%d-%Y"])
record["has_published"] = coerce_boolean(record["has_published"])  # "yes" → True
record["record_count"] = int(record["record_count"])  # "42" → 42
```

**Decision Point**:
- Strict or lenient parsing? (Strict: fail the record; Lenient: flag as `_coercion_error`)
- For dates, should you infer regional formats (e.g., DD/MM/YYYY for UK)? How to handle ambiguous dates like "01/02/2020"?
- For booleans, what counts as true/false/unknown?

---

### 5. Enum/Vocabulary Standardization

**Goal**: Map variant spellings and abbreviations to canonical values.

```python
# Example: standardize country codes
country_map = {
    "usa": "US",
    "united states": "US",
    "USA": "US",
    "U.S.": "US",
    "gb": "GB",
    "uk": "GB",
    "united kingdom": "GB",
}
record["nationality"] = country_map.get(record["nationality"].lower(), record["nationality"])
```

**Decision Point**:
- When a value doesn't match your vocabulary, do you: reject it? flag it? keep as-is for manual review?
- Should you maintain a registry of "seen but unmapped" values?
- When should the mapping list be curated vs. auto-generated from data?

---

### 6. Missing Value Handling

**Goal**: Standardize how you represent "no data" and make strategic decisions about what to keep/drop.

```python
# Strategy: standardize to None, but keep track of why
for field in record:
    if record[field] in ["", "N/A", "NA", "null", "NULL", None]:
        record[f"{field}_was_missing"] = True
        record[field] = None
```

**Decision Point**:
- Should you drop records with critical missing values, or flag them for manual review?
- For optional fields, keep as None or delete the key?
- Track *why* a value was missing (data never collected vs. filtered out vs. encoding error)?

---

### 7. Schema Validation

**Goal**: Confirm all records conform to expected structure; flag/reject deviations.

```python
expected_schema = {
    "source_id": {"type": "string", "required": True},
    "name": {"type": "string", "required": True},
    "birth_date": {"type": "date", "required": False},
    "nationality": {"type": "enum", "values": ["US", "GB", "FR", ...], "required": False},
}
```

**Decision Point**:
- Strict schema (reject any deviation) or permissive (warn but allow)?
- Extra fields: keep, ignore, or error?
- How to handle records with missing *required* fields?

---

## Output Contract

Records exiting fermentation should:

1. **Be type-consistent** — All dates are date objects, all booleans are actual booleans, etc.
2. **Pass schema validation** — All fields match expected types and restrictions
3. **Be clean** — No leading/trailing whitespace, consistent encoding, standardized vocabulary
4. **Be auditable** — Original values retained in `_raw` or `_original` fields where possible
5. **Be flagged** — Records with warnings (suspicious values, coercion errors, schema mismatches) marked for review

**Example output record (corresponding to input above):**
```json
{
  "source_id": "row_4521",
  "name": "John Smith",
  "name_raw": " John Smith  ",
  "birth_date": "1987-03-15",
  "birth_date_raw": "1987/3/15",
  "nationality": "US",
  "nationality_raw": "usa",
  "has_published": true,
  "has_published_raw": "yes",
  "website": null,
  "website_was_missing": true,
  "gender": "M",
  "_fermentation_flags": ["suspicious_value_gender_M_check_abbreviation"]
}
```

---

## Angel's Share (Schema Deviations)

Not everything fits the current schema, and that's expected. In Fermentation, any values or fields that don't conform should be preserved as an **Angel's Share** alongside the cleaned record (for example, in an `_angel_share` structure with deviation notes). This keeps "extra ingredients" available for future schema expansion or alternate endpoints in the Global Knowledge Commons.

---

## Configuration & Decisions

Most fermentation work is *configuration*, not code. Before running fermentation on a dataset, you define:

### 1. Schema Definition
- Which fields are required vs. optional?
- What type is each field? (string, int, date, enum, etc.)
- For enums, what are valid values?
- Any length limits or patterns (regex validation)?

### 2. Transformation Rules
- How to parse dates? (Regional format assumptions?)
- String mappings for enums (country → code, abbreviation → full name)
- Whitespace handling (trim? normalize unicode form?)
- Missing value representations

### 3. Error Handling Strategy
- Strict (fail on any error) vs. lenient (flag and continue)?
- Which errors cause record rejection vs. just warnings?
- How to handle records with missing required fields?

### 4. Provenance Options
- Keep `_raw` fields for all transformed values? (Storage cost vs. auditability)
- Log every transformation or only errors?
- Track data lineage (which source, which batch)?

---

## A Worked Example

**Scenario**: You have a CSV of researchers with publication counts, and you want to clean it before matching to Wikidata authors.

**Raw CSV:**
```
id,Full Name,Birth Year,field_of_study,num_publications,gender
1," Dr. Alice Johnson ",1985,physics,42,F
2,bob smith,1978,"  computer science  ",,M
3,Carol Lee García,1992,art history,5,unknown
```

**Schema you define:**
```python
schema = {
    "id": {"type": "string", "required": True},
    "fullname": {"type": "string", "required": True},
    "birth_year": {"type": "int", "min": 1800, "max": 2010, "required": False},
    "field_of_study": {"type": "enum", "values": ["Physics", "Computer Science", "Art History"], "required": True},
    "num_publications": {"type": "int", "required": False},
    "gender": {"type": "enum", "values": ["M", "F", "Other", "Unknown"], "required": False},
}
```

**Transformations you configure:**
```python
# Whitespace & case
"fullname" → trim, remove extra spaces within, title case
"field_of_study" → trim, title case

# Type coercion
"birth_year" → parse as int, validate range 1800–2010
"num_publications" → parse as int, handle empty as None

# Enum mapping
"field_of_study": {
    "physics" → "Physics",
    "computer science" → "Computer Science",
    "comp sci" → "Computer Science",
}
"gender": {
    "unknown" → "Unknown",
    other values → as-is
}

# Missing value handling
Empty "num_publications" → set to None, flag as "_num_publications_was_missing"
```

**After fermentation:**
```json
[
  {
    "id": "1",
    "fullname": "Dr. Alice Johnson",
    "fullname_raw": " Dr. Alice Johnson ",
    "birth_year": 1985,
    "field_of_study": "Physics",
    "field_of_study_raw": "physics",
    "num_publications": 42,
    "gender": "F",
    "_fermentation_flags": []
  },
  {
    "id": "2",
    "fullname": "Bob Smith",
    "fullname_raw": "bob smith",
    "birth_year": 1978,
    "field_of_study": "Computer Science",
    "field_of_study_raw": "  computer science  ",
    "num_publications": null,
    "num_publications_was_missing": true,
    "gender": "M",
    "_fermentation_flags": []
  },
  {
    "id": "3",
    "fullname": "Carol Lee García",
    "birth_year": 1992,
    "field_of_study": "Art History",
    "num_publications": 5,
    "gender": "Unknown",
    "gender_raw": "unknown",
    "_fermentation_flags": ["unknown_gender_mapped_to_Unknown"]
  }
]
```

---

## Supporting Systems

### Schema Registry
Fermentation relies on a Schema Registry that defines:
- Canonical field names and types
- Valid enum values and mappings
- Required vs. optional fields
- Validation rules (min/max, length, regex patterns)

### Barrel (Caching & Provenance)
Store:
- Original CSV/JSON for audit trail
- Configuration used for this fermentation run
- Error logs and flagged records
- Snapshot for potential rollback

---

## Relationship to Other Stages

**Before**: [Mash Tun](mash_tun.md) parses raw formats into structured records.

**After**: [Distillation](distillation.md) takes clean records and matches them to canonical entities (Wikidata, OSM).

**Skip fermentation if**: Your data is already clean, properly typed, and schema-validated. (Rare!)

---

## Common Patterns

### Pattern 1: "I have messy data from multiple sources"
Define a *unified* schema that's the superset of all sources. During fermentation, records get normalized to that schema. Some sources may have more fields than others—that's fine; missing fields become None.

### Pattern 2: "I want to catch weird values for manual review"
Use lenient error handling: transform what you can, flag suspicious values in `_fermentation_flags`. Export flagged records separately for review before proceeding to Distillation.

### Pattern 3: "I need to audit every transformation"
Keep `_raw` fields for all transformed values (double storage but full auditability). Log which transformation steps changed each field. Use Barrel to store full logs.

---

## Reference

- **Configuration File Format**: (Link to fermentation config schema once defined)
- **API Reference**: (Link to Fermenter class once documented)
- **Troubleshooting**: (Link to common issues once compiled)
- **Related**: Schema Building | [Distillation](distillation.md) | Spirit Safe (validation reference)

---

## GitHub Issues & Development

Work on the Fermentation stage is tracked under the [`ferment` label](https://github.com/skybristol/gkc/issues?q=label%3Aferment). Issues tagged with this label represent implementation efforts, feature requests, and improvements for this stage of the Data Distillery workflow.

**Other Workflow Stages:**
- [`mash`](https://github.com/skybristol/gkc/issues?q=label%3Amash) — Data Ingestion
- [`distill`](https://github.com/skybristol/gkc/issues?q=label%3Adistill) — Reconciliation & Linking
- [`refine`](https://github.com/skybristol/gkc/issues?q=label%3Arefine) — Deduplication & Enrichment
- [`proof`](https://github.com/skybristol/gkc/issues?q=label%3Aproof) — Quality Assurance
- [`blend`](https://github.com/skybristol/gkc/issues?q=label%3Ablend) — Multi-Source Merging
- [`bottle`](https://github.com/skybristol/gkc/issues?q=label%3Abottle) — Format & Export
