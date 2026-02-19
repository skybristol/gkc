# Mash Commands

Plain meaning: Load source data as ingredients for further actions.

## Overview

The mash module in GKC handles the input of various data and information content and structure that will be processed through data distillery workflows. The mash CLI provides an interface to the most common functionality that is useful at the command line.

The name "mash" comes from the distillery metaphor—like grain that's been milled and steeped to extract fermentable sugars, mashed items extract the essential structure and content from source data, readying the ingredients for further processing.

**Current implementations:** The mash module currently supports loading Wikidata items as templates. Future versions will add support for CSV files, JSON APIs, and other data sources.

## Load Wikidata Item by QID

```bash
gkc mash qid <QID>
```

Load a Wikidata item by its QID (e.g., Q42) and output it in the specified format.

**Arguments:**
- `qid`: The Wikidata item ID (e.g., Q42, Q1234567)

**Output Format Options:**
- `--output summary`: (default) Human-readable summary of the item
- `--output qsv1`: QuickStatements V1 format for bulk operations
- `--output json`: Raw Wikidata entity JSON

**Filtering Options:**
- `--exclude-properties <P1,P2,...>`: Comma-separated list of property IDs to exclude (e.g., P31,P21)
- `--exclude-qualifiers`: Omit all qualifiers from the output
- `--exclude-references`: Omit all references from the output

**Item Creation Mode:**
- `--update`: Retain identifiers for updates (default)
- `--new`: Use CREATE/LAST syntax for new items and strip identifiers from JSON

### Examples

#### Summary Output (Default)

View a human-readable summary of an item:

```bash
$ gkc mash qid Q42
Template loaded: Q42
qid: Q42
labels: en: Douglas Adams
descriptions: en: English science fiction writer
aliases: en: Douglas Noël Adams, Douglas Noel Adams
claims: 42
```

#### QuickStatements V1 Format

Export an item for bulk creation of similar items:

```bash
$ gkc mash qid Q42 --output qsv1
Q42|Len|"Douglas Adams"
Q42|Den|"English science fiction writer"
Q42|P31|Q5  /* instance of: human */
Q42|P21|Q6581097  /* sex or gender: male */
...
```

Use `--new` for creating new items with CREATE/LAST syntax:

```bash
$ gkc mash qid Q42 --output qsv1 --new
CREATE
LAST|Len|"Douglas Adams"
LAST|Den|"English science fiction writer"
LAST|P31|Q5  /* instance of: human */
```

#### JSON Format

Export raw Wikidata entity JSON for programmatic use:

```bash
$ gkc mash qid Q42 --output json
{
  "id": "Q42",
  "labels": {
    "en": {"language": "en", "value": "Douglas Adams"}
  },
  "descriptions": {
    "en": {"language": "en", "value": "English science fiction writer"}
  },
  "claims": {...}
}
```

Use `--new` to strip identifiers for new-item creation. This removes:
- Item-level: `id`, `pageid`, `lastrevid`, `modified`
- Statement-level: `id` (statement GUID)
- Snak-level: `hash` (in mainsnak, qualifiers, and references)

#### Filtering Properties

Exclude specific properties (e.g., exclude "instance of" and "sex or gender"):

```bash
$ gkc mash qid Q42 --output qsv1 --exclude-properties P31,P21
```

Exclude qualifiers and references if not needed:

```bash
$ gkc mash qid Q42 --output qsv1 --exclude-qualifiers --exclude-references
```

#### Machine-Readable Output

Combine with `--json` flag for structured command output:

```bash
$ gkc --json mash qid Q42 --output summary
{
  "command": "mash.qid",
  "ok": true,
  "message": "Template loaded: Q42",
  "details": {
    "qid": "Q42",
    "labels": "en: Douglas Adams",
    "descriptions": "en: English science fiction writer",
    ...
  }
}
```

## Output Format Details

### Summary Format

The summary format provides a high-level overview of the item including:
- QID
- Labels (by language)
- Descriptions (by language)
- Aliases (by language)
- Claim count

This format is useful for quickly understanding an item's structure.

### QuickStatements V1 Format

QuickStatements V1 (QSV1) is a tab-separated format used by the [QuickStatements tool](https://quickstatements.toolforge.org/) for batch operations on Wikidata. The output includes:

- Labels: `Q42|Len|"Douglas Adams"`
- Descriptions: `Q42|Den|"English science fiction writer"`
- Claims: `Q42|P31|Q5` (with property label comments for readability)
- Qualifiers and references (if not excluded)

**Edit mode** (default): Uses the item's QID (e.g., `Q42|P31|Q5`)
**New mode** (`--new`): Uses CREATE/LAST syntax for new items (e.g., `CREATE` followed by `LAST|P31|Q5`)

Property labels are automatically fetched and included as comments (`/* property: value */`) to make the output more readable.

### JSON Format

The JSON format provides the raw Wikidata entity JSON suitable for:
- Programmatic processing
- Integration with other tools
- Detailed inspection of item structure

The JSON includes all labels, descriptions, aliases, and claims with their qualifiers and references as provided by Wikidata. Use `--new` to strip identifiers when preparing JSON for new-item creation.

## Typical Workflows

### Creating Similar Items

1. Find an exemplar item on Wikidata (e.g., Q42)
2. Load it with mash: `gkc mash qid Q42 --output qsv1 --new`
3. Copy the output and modify labels/values as needed
4. Paste into [QuickStatements](https://quickstatements.toolforge.org/) to create new items

### Understanding Item Structure

```bash
# Get a quick overview
gkc mash qid Q42

# See full structure
gkc mash qid Q42 --output json

# Focus on specific properties
gkc mash qid Q42 --output qsv1 --exclude-qualifiers --exclude-references
```

### Extracting Templates for Documentation

```bash
# Export clean template without system properties
gkc mash qid Q42 --output qsv1 \
  --exclude-properties P31,P21 \
  --exclude-qualifiers \
  --exclude-references > template.qs
```

## Property Label Comments

When using QSV1 output, the command automatically fetches human-readable labels for properties and includes them as comments:

```
Q42|P31|Q5  /* instance of: human */
Q42|P21|Q6581097  /* sex or gender: male */
```

This makes the output more readable without requiring constant lookups of property IDs. The labels are fetched efficiently in batch from Wikidata and use the default language (English).

## Error Handling

If an item cannot be loaded, the command will fail with an error message:

```bash
$ gkc mash qid Q999999999999
Failed to load item Q999999999999: Item not found
```

Use `--verbose` to see additional diagnostic information:

```bash
$ gkc --verbose mash qid Q42
```

## Related Documentation

- [Mash Tun](../mash_tun.md) - Overview of the mash stage in the distillery pipeline
- [CLI Overview](index.md) - Main CLI documentation
- [QuickStatements Documentation](https://www.wikidata.org/wiki/Help:QuickStatements) - External documentation for QuickStatements format
