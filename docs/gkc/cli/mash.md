# Mash Commands

Plain meaning: Load source data as ingredients for further actions.

## Overview

The mash module in GKC handles the input of various data and information content and structure that will be processed through data distillery workflows. The mash CLI provides an interface to load Wikidata entities - items (QID), properties (PID), and EntitySchemas (EID).

The name "mash" comes from the distillery metaphor—like grain that's been milled and steeped to extract fermentable sugars, mashed entities extract the essential structure and content from source data, readying the ingredients for further processing.

**Current implementations:**
- Wikidata items (QID)
- Wikidata properties (PID)
- Wikidata EntitySchemas (EID)

**Future implementations:** CSV files, JSON APIs, dataframes

---

## Load Wikidata Items by QID

```bash
gkc mash qid <QID> [options]
```

Load one or more Wikidata items by QID and output them in various formats.

### Arguments

- `qid`: Positional argument for a single item ID (e.g., `Q42`)
- `--qid <QID>`: Repeatable flag for multiple items (e.g., `--qid Q42 --qid Q5`)
- `--qid-list <file>`: Path to file containing item IDs (one per line)

### Output Options

- `-o, --output <file>`: Write output to file instead of stdout
- `--raw`: Output raw JSON to stdout (default behavior when no transform specified)
- `--transform <type>`: Transform the output  
  - `shell`: Strip all identifiers for new item creation
  - `qsv1`: Convert to QuickStatements V1 format
  - `gkc_entity_profile`: Convert to GKC Entity Profile (not yet implemented)

### Filtering Options

- `--include-properties <P1,P2,...>`: Comma-separated list of properties to include
- `--exclude-properties <P1,P2,...>`: Comma-separated list of properties to exclude
- `--exclude-qualifiers`: Omit all qualifiers from output
- `--exclude-references`: Omit all references from output
- `--no-entity-labels`: Skip fetching entity labels for QuickStatements comments (faster)

### Examples

#### Load a single item (raw JSON)

```bash
gkc mash qid Q42
```

Output: Raw Wikidata JSON for item Q42

#### Load multiple items

```bash
# Using repeatable --qid flags
gkc mash qid --qid Q42 --qid Q5 --qid Q30

# Using a file list
echo "Q42
Q5
Q30" > items.txt
gkc mash qid --qid-list items.txt
```

#### Transform to shell for new item creation

```bash
gkc mash qid Q42 --transform shell -o new_item_template.json
```

Strips all identifiers (id, pageid, ns, title, statement IDs, hashes) to create a clean template for submitting as a new item.

#### Transform to QuickStatements

```bash
# For editing existing item
gkc mash qid Q42 --transform qsv1

# Extract specific properties only
gkc mash qid Q42 --transform qsv1 --include-properties P31,P21,P569
```

#### Filter properties and save

```bash
gkc mash qid Q42 \
  --exclude-properties P18,P373 \
  --exclude-qualifiers \
  --exclude-references \
  -o filtered_item.json
```

---

## Load Wikidata Properties by PID

```bash
gkc mash pid <PID> [options]
```

Load one or more Wikidata properties by PID and output them in various formats.

### Arguments

- `pid`: Positional argument for a single property ID (e.g., `P31`)
- `--pid <PID>`: Repeatable flag for multiple properties (e.g., `--pid P31 --pid P279`)
- `--pid-list <file>`: Path to file containing property IDs (one per line)

### Output Options

- `-o, --output <file>`: Write output to file instead of stdout
- `--raw`: Output raw JSON to stdout (default behavior)
- `--transform <type>`: Transform the output
  - `shell`: Strip all identifiers for new property creation
  - `gkc_entity_profile`: Convert to GKC Entity Profile (not yet implemented)

### Examples

#### Load a single property

```bash
gkc mash pid P31
```

Output: Raw Wikidata JSON for property P31 including labels, descriptions, datatype, formatter URL

#### Load multiple properties

```bash
# Using repeatable --pid flags
gkc mash pid --pid P31 --pid P279 --pid P21

# Using a file list
echo "P31
P279
P21" > properties.txt
gkc mash pid --pid-list properties.txt
```

#### Transform to shell for new property creation

```bash
gkc mash pid P31 --transform shell -o new_property_template.json
```

---

## Load Wikidata EntitySchemas by EID

```bash
gkc mash eid <EID> [options]
```

Load a Wikidata EntitySchema by EID and output it in various formats.

### Arguments

- `eid`: The EntitySchema ID (e.g., `E502`)

### Output Options

- `-o, --output <file>`: Write output to file instead of stdout
- `--raw`: Output raw JSON to stdout (default behavior)
- `--transform <type>`: Transform the output
  - `shell`: Strip all identifiers for new EntitySchema creation
  - `gkc_entity_profile`: Convert to GKC Entity Profile

### Examples

#### Load an EntitySchema

```bash
gkc mash eid E502
```

Output: Raw EntitySchema JSON including labels, descriptions, and ShEx schema text

#### Transform to GKC Entity Profile

```bash
gkc mash eid E502 --transform gkc_entity_profile -o tribe_profile.json
```

Converts the EntitySchema's ShEx specification into a GKC Entity Profile that can be used for data validation and transformation.

#### Transform to shell for reuse

```bash
gkc mash eid E502 --transform shell -o new_schema_template.json
```

---

## Batch Processing Patterns

### Load multiple items from a file

```bash
# Create a file with QIDs
cat > items.txt <<EOF_MARKER
Q42
Q5
Q30
# Comments are ignored
Q515
EOF_MARKER

# Process all items
gkc mash qid --qid-list items.txt -o batch_items.json
```

### Transform multiple items to QuickStatements

```bash
# Load multiple items and convert to QS for batch editing
gkc mash qid --qid Q42 --qid Q5 --transform qsv1 -o batch_statements.qs
```

### Property metadata extraction

```bash
# Extract metadata for a set of properties
cat > props.txt <<EOF_MARKER
P31
P279
P21
P569
P570
EOF_MARKER

gkc mash pid --pid-list props.txt -o property_metadata.json
```

---

## Output Formats

### Raw JSON (default)
The raw Wikidata entity JSON as returned by the API. This format preserves all structure and identifiers, suitable for:
- Round-trip processing
- Integration with other tools
- Detailed inspection

### Shell (--transform shell)
Strips all system identifiers and metadata:
- Removes: `id`, `pageid`, `lastrevid`, `modified`, `ns`, `title`
- Removes: statement IDs (GUIDs)
- Removes: all hashes from snaks, qualifiers, and references

Use this when creating templates for new entity creation on Wikidata or Wikibase instances.

### QuickStatements V1 (--transform qsv1, items only)
Converts item data to QuickStatements V1 format for bulk operations:
- Format: `QID|property|value`
- Includes property labels as comments for readability
- Use on [QuickStatements](https://quickstatements.toolforge.org/) for batch editing

### GKC Entity Profile (--transform gkc_entity_profile, EntitySchemas only)
Converts EntitySchemas to GKC Entity Profiles:
- Extracts properties and constraints from ShEx
- Creates portable profiles for validation and transformation
- Currently only implemented for EntitySchemas

---

## Common Workflows

### Creating Similar Items

1. Find anexemplar item on Wikidata (e.g., Q42)
2. Load with shell transform: `gkc mash qid Q42 --transform shell -o template.json`
3. Edit the template JSON to modify labels/values
4. Submit to Wikidata using the wbeditentity API or QuickStatements

### Property Documentation

```bash
# Extract metadata for all properties in a domain
gkc mash pid --pid-list biological_properties.txt -o bio_props.json
```

### EntitySchema Development

```bash
# Load existing schema as starting point
gkc mash eid E502 --transform shell -o new_schema.json

# Or convert to profile for analysis
gkc mash eid E502 --transform gkc_entity_profile -o tribe_profile.json
```

---

## Migration from Previous CLI

The mash CLI has been refactored for consistency. Key changes:

**Old:**
```bash
gkc mash qid Q42 --output qsv1 --new
gkc mash qid Q42 --output json
```

**New:**
```bash
gkc mash qid Q42 --transform qsv1
gkc mash qid Q42  # raw JSON is default
gkc mash qid Q42 --transform shell  # for new items
```

Changes:
- `--output` now means output file path, not format
- `--transform` specifies the transformation type
- `--new` flag removed (use `--transform shell` or `--transform qsv1` with for_new_item)
- `--save-profile` replaced with `-o, --output`
- Added support for batch loading with `--qid-list`, `--pid-list`
- Added `mash pid` command for properties
- Simplified `mash eid` command

---

## Related Documentation

- [Mash API](../api/mash.md) - Python API for programmatic use
- [QuickStatements Documentation](https://www.wikidata.org/wiki/Help:QuickStatements) - External tool for batch operations
