# ShEx Commands

Plain meaning: Validate RDF data against ShEx schemas.

## Overview

The ShEx module in GKC validates RDF data against ShEx (Shape Expression) schemas. It's designed primarily for validating Wikidata entities against EntitySchemas but supports validation of local RDF files as well.

ShEx validation helps ensure data quality by checking that entities conform to expected patterns—required properties, value types, cardinality constraints, and more.

**Current implementations:**
- Wikidata entity validation (QID + EID)
- Local RDF file validation
- Mixed source validation (Wikidata entity + local schema, or local RDF + EntitySchema)

**Future implementations:** Batch validation, validation reports, schema coverage analysis

---

## Validate RDF Data

```bash
gkc shex validate [options]
```

Validate RDF data (from Wikidata or local file) against a ShEx schema (from Wikidata EntitySchema or local file).

### Source Options

**RDF Data Source** (choose one):
- `--qid <QID>`: Fetch RDF data for Wikidata item (e.g., `Q42`)
- `--rdf-file <path>`: Use local RDF file (Turtle format)

**Schema Source** (choose one):
- `--eid <EID>`: Fetch ShEx schema from Wikidata EntitySchema (e.g., `E502`)
- `--schema-file <path>`: Use local ShEx schema file

### Other Options

- `--user-agent <string>`: Custom user agent for Wikidata API requests (recommended for bots)

### Examples

#### Validate Wikidata entity against EntitySchema

```bash
gkc shex validate --qid Q14708404 --eid E502
```

**Example output:**
```json
{
  "command": "shex.validate",
  "ok": true,
  "message": "✓ Validation passed\nEntity: Q14708404\nSchema: E502",
  "details": {
    "entity": "Q14708404",
    "entity_uri": "http://www.wikidata.org/entity/Q14708404",
    "schema": "E502",
    "valid": true
  }
}
```

#### Validation failure

```bash
gkc shex validate --qid Q999999 --eid E502
```

**Example output:**
```json
{
  "command": "shex.validate",
  "ok": false,
  "message": "✗ Validation failed\nError: wdt:P31 value not in allowed set [wd:Q133346]\nEntity: Q999999\nSchema: E502",
  "details": {
    "entity": "Q999999",
    "entity_uri": "http://www.wikidata.org/entity/Q999999",
    "schema": "E502",
    "valid": false,
    "error_summary": "wdt:P31 value not in allowed set [wd:Q133346]"
  }
}
```

#### Validate local RDF file

```bash
gkc shex validate --rdf-file entity.ttl --eid E502
```

Validates a locally stored Turtle file against Wikidata EntitySchema E502.

#### Validate Wikidata entity with local schema

```bash
gkc shex validate --qid Q42 --schema-file custom_schema.shex
```

Fetches entity data from Wikidata but uses a custom local ShEx schema.

#### Validate local files (fully offline)

```bash
gkc shex validate --rdf-file entity.ttl --schema-file schema.shex
```

Both RDF data and ShEx schema are loaded from local files—no network requests.

#### Custom user agent (for bots)

```bash
gkc shex validate \
  --qid Q14708404 \
  --eid E502 \
  --user-agent "MyBot/1.0 (https://example.com; bot@example.com)"
```

Use a custom user agent string when fetching data from Wikidata APIs (recommended for automated tools).

---

## Output Format

The `gkc shex validate` command outputs JSON with the following structure:

```json
{
  "command": "shex.validate",
  "ok": true|false,
  "message": "Human-readable summary with status",
  "details": {
    "entity": "Q14708404",
    "entity_uri": "http://www.wikidata.org/entity/Q14708404",
    "schema": "E502",
    "valid": true|false,
    "error_summary": "Brief error description (only on failure)",
    "results": "Full validation results (available if needed)"
  }
}
```

**Fields:**
- `ok`: Command execution status (true if command succeeded, false on error)
- `valid`: Validation result (true if entity conforms to schema, false if not)
- `message`: Human-readable summary of the validation result with entity/schema info
- `error_summary`: Brief description of validation errors (present only when valid=false)
- `details`: Complete validation details including entity URI, schema reference, and error information

---

## Validation Workflow Examples

### Pre-upload quality check

Before uploading new data to Wikidata, validate it locally:

```bash
# 1. Export new entity as RDF
cat > new_tribe.ttl << 'EOF'
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> .

wd:QNEW wdt:P31 wd:Q133346 ;
        wdt:P17 wd:Q30 ;
        wdt:P571 "1979-01-01"^^xsd:date .
EOF

# 2. Validate against tribe schema
gkc shex validate --rdf-file new_tribe.ttl --eid E502

# 3. If validation passes, proceed with upload
```

### Batch validation of existing entities

```bash
# Create list of QIDs to validate
cat > tribes_to_check.txt << 'EOF'
Q14708404
Q3551781
Q1948829
Q4675719
EOF

# Validate each entity
while read qid; do
  echo "Checking $qid..."
  gkc shex validate --qid "$qid" --eid E502 --json >> validation_report.jsonl
done < tribes_to_check.txt

# Parse results
jq 'select(.valid == false) | .qid' validation_report.jsonl
```

### Testing schema changes

When developing new EntitySchemas, test them locally before publishing:

```bash
# 1. Create draft schema
cat > draft_schema.shex << 'EOF'
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>

<FederallyRecognizedTribe> {
  wdt:P31 [ wd:Q133346 ] ;
  wdt:P17 [ wd:Q30 ] ;
  wdt:P571 xsd:date ? ;
  wdt:P576 xsd:date ?
}
EOF

# 2. Test against known good entity
gkc shex validate --qid Q14708404 --schema-file draft_schema.shex

# 3. Test against known problematic entity
gkc shex validate --qid Q999999 --schema-file draft_schema.shex --verbose

# 4. If tests pass, publish schema to Wikidata as new EntitySchema
```

### Comparing entities to multiple schemas

```bash
# Check if entity conforms to multiple related schemas
schemas=("E502" "E503" "E504")

for eid in "${schemas[@]}"; do
  result=$(gkc shex validate --qid Q14708404 --eid "$eid" --json)
  valid=$(echo "$result" | jq -r '.valid')
  echo "$eid: $valid"
done
```

---

## Common EntitySchemas

| EID | Description | Use Case |
|-----|-------------|----------|
| [E502](https://www.wikidata.org/wiki/EntitySchema:E502) | Federally recognized tribe | US tribal nations |
| [E49](https://www.wikidata.org/wiki/EntitySchema:E49) | Human | Person/biographical items |
| [E10](https://www.wikidata.org/wiki/EntitySchema:E10) | Place | Geographic locations |
| [E42](https://www.wikidata.org/wiki/EntitySchema:E42) | Scholarly article | Scientific publications |

Browse all schemas: [Wikidata:EntitySchema](https://www.wikidata.org/wiki/Wikidata:EntitySchema)

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Validation passed (entity conforms to schema) |
| 1 | Validation failed (entity does not conform to schema) |
| 2 | Error during validation process (missing files, network error, etc.) |

Use exit codes in scripts:

```bash
if gkc shex validate --qid Q42 --eid E49 --json > /dev/null 2>&1; then
  echo "Q42 is a valid human entity"
else
  echo "Q42 has validation issues"
fi
```

---

## See Also

- [ShEx API Documentation](../api/shex.md) - Python library usage
- [Utilities Guide](../utilities.md) - ShEx validation concepts and patterns
- [Wikidata EntitySchemas](https://www.wikidata.org/wiki/Wikidata:EntitySchema) - Browse published schemas
- [ShEx Primer](http://shex.io/shex-primer/) - Learn ShEx syntax
- [ShEx Test Suite](http://shex.io/shex-test/) - Additional validation examples
