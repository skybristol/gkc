# Mash Formatters API

## Overview

Convert Wikidata templates to different output formats for bulk editing, validation, or export. Currently supports QuickStatements V1 format for creating and updating items on Wikidata.

## Quick Start

```python
from gkc.mash import WikidataLoader
from gkc.mash_formatters import QSV1Formatter

# Load a template
loader = WikidataLoader()
template = loader.load("Q42")

# Format for new item creation
formatter = QSV1Formatter()
qs_text = formatter.format(template, for_new_item=True)
print(qs_text)
```

---

## Classes

### QSV1Formatter

::: gkc.mash_formatters.QSV1Formatter
    options:
      show_root_heading: false
      heading_level: 4

---

## Examples

### Format for new item creation

```python
from gkc.mash import WikidataLoader
from gkc.mash_formatters import QSV1Formatter

loader = WikidataLoader()
template = loader.load("Q42")

# Filter to simplify output
template.filter_languages("en")
template.filter_properties(["P18", "P373"])  # Exclude images

# Format with CREATE/LAST syntax
formatter = QSV1Formatter()
qs_text = formatter.format(template, for_new_item=True)

print(qs_text)
# CREATE
# LAST	Len	"Douglas Adams"
# LAST	Den	"English science fiction writer"
# LAST	P31	Q5
# ...
```

### Format for updating existing item

```python
from gkc.mash import WikidataLoader
from gkc.mash_formatters import QSV1Formatter

loader = WikidataLoader()
template = loader.load("Q42")

# Format with QID syntax for updates
formatter = QSV1Formatter()
qs_text = formatter.format(template, for_new_item=False)

print(qs_text)
# Q42	en	"Douglas Adams"
# Q42	Dn	"English science fiction writer"
# Q42	P31	Q5
# ...
```

### Add human-readable comments

```python
from gkc.mash import WikidataLoader, fetch_property_labels
from gkc.mash_formatters import QSV1Formatter

loader = WikidataLoader()
template = loader.load("Q42")

# Collect all property and item IDs
entity_ids = set()
for claim in template.claims:
    entity_ids.add(claim.property_id)
    if claim.value.startswith("Q"):
        entity_ids.add(claim.value)

# Fetch labels for comments
from gkc.sparql import fetch_entity_labels
entity_labels = fetch_entity_labels(list(entity_ids), languages=["en"])

# Format with inline comments
formatter = QSV1Formatter(entity_labels=entity_labels)
qs_text = formatter.format(template, for_new_item=True)

print(qs_text)
# CREATE
# LAST	Len	"Douglas Adams"
# LAST	Den	"English science fiction writer"
# LAST	P31	Q5	/* instance of is human */
# LAST	P21	Q6581097	/* sex or gender is male */
# ...
```

### Exclude qualifiers and references

```python
from gkc.mash import WikidataLoader
from gkc.mash_formatters import QSV1Formatter

loader = WikidataLoader()
template = loader.load("Q42")

# Create formatter that excludes qualifiers and references
formatter = QSV1Formatter(
    exclude_qualifiers=True,
    exclude_references=True
)

qs_text = formatter.format(template, for_new_item=True)
# Output will only include main statements, no qualifiers/references
```

### Exclude specific properties

```python
from gkc.mash import WikidataLoader
from gkc.mash_formatters import QSV1Formatter

loader = WikidataLoader()
template = loader.load("Q42")

# Exclude properties that aren't relevant
formatter = QSV1Formatter(
    exclude_properties=["P18", "P373", "P856"]  # image, commons cat, website
)

qs_text = formatter.format(template, for_new_item=True)
```

### Complete workflow with all options

```python
from gkc.mash import WikidataLoader, fetch_property_labels
from gkc.mash_formatters import QSV1Formatter
from gkc.sparql import fetch_entity_labels

# Load template
loader = WikidataLoader()
template = loader.load("Q42")

# Filter template
template.filter_languages("en")
template.filter_properties(["P18", "P373"])

# Fetch entity labels for comments
entity_ids = set()
for claim in template.claims:
    entity_ids.add(claim.property_id)
    if claim.value.startswith("Q"):
        entity_ids.add(claim.value)

entity_labels = fetch_entity_labels(list(entity_ids), languages=["en"])

# Format with all options
formatter = QSV1Formatter(
    exclude_properties=["P31"],  # Skip 'instance of' for this example
    exclude_qualifiers=False,
    exclude_references=True,
    entity_labels=entity_labels
)

qs_text = formatter.format(template, for_new_item=True)
print(qs_text)
```

---

## QuickStatements V1 Format Notes

### Syntax Overview

- **CREATE**: Start a new item
- **LAST**: Refer to the most recently created item
- **Labels**: `LAST\tLen\t"English label"`
- **Descriptions**: `LAST\tDen\t"English description"`
- **Aliases**: `LAST\tAen\t"English alias"`
- **Statements**: `LAST\tP31\tQ5` (property, value)
- **Qualifiers**: `LAST\tP31\tQ5\tP580\t+1952-03-11T00:00:00Z/11` (append with pipes)
- **Comments**: `/* human-readable note */` at end of line

### Precision in Time Values

Time values include precision indicators:

- `/9` - year precision
- `/10` - month precision  
- `/11` - day precision
- `/14` - second precision

Example: `+1952-03-11T00:00:00Z/11` (precise to day)

### Entity References

- **Items**: Q-IDs (e.g., `Q42`)
- **Properties**: P-IDs (e.g., `P31`)
- **Strings**: Quoted values (e.g., `"Douglas Adams"`)
- **Quantities**: Numeric values with optional units
- **Coordinates**: `@lat/lon` format

---

## See Also

- [Mash API](mash.md) - Load and manipulate Wikidata templates
- [Mash CLI](../cli/mash.md) - Command-line interface with QS output examples
- [QuickStatements Documentation](https://www.wikidata.org/wiki/Help:QuickStatements) - Official QS reference
