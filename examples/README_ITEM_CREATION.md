# Item Creation Approach - Quick Start

This directory contains a complete approach for creating Wikidata items from source data using ShEx schemas for validation.

## Overview

The approach combines three key elements:

1. **ShEx Entity Schemas** - Define what valid items should look like
2. **Mapping Configurations** - Connect source data to Wikidata properties
3. **Source Data** - Your data to be uploaded to Wikidata

## Directory Structure

```
docs/item_creation_approach.md    # Detailed design document
examples/
  ├── mappings/
  │   └── tribe_mapping_example.json    # Example mapping config
  ├── data/
  │   └── tribe_source_example.json     # Example source data
  └── item_creation_example.py          # Working examples
gkc/
  └── item_creator.py                   # Core implementation (skeleton)
```

## Quick Start

### 1. Review the Approach

Read the [detailed approach document](../docs/item_creation_approach.md) to understand the overall design.

### 2. Look at the Example Mapping

The [tribe_mapping_example.json](mappings/tribe_mapping_example.json) shows how to map source data fields to Wikidata properties:

```json
{
  "mappings": {
    "labels": [
      {
        "source_field": "tribe_name",
        "language": "en"
      }
    ],
    "aliases": [
      {
        "source_field": "tribe_name_aliases",
        "language": "en",
        "separator": ";"
      }
    ],
    "claims": [
      {
        "property": "P2124",
        "source_field": "member_count",
        "datatype": "quantity",
        "qualifiers": [...]
      }
    ]
  }
}
```

**Separator Support:** Use the `separator` parameter to split multi-value fields. For example, if your spreadsheet has `"Alias1; Alias2; Alias3"` in one cell, setting `"separator": ";"` will create three separate aliases.

### 3. Check the Source Data Format

The [tribe_source_example.json](data/tribe_source_example.json) shows the expected source data structure:

```json
[
  {
    "tribe_name": "Cherokee Nation",
    "member_count": 450000,
    "member_count_date": "2023-01-01",
    "headquarters_qid": "Q986506"
  }
]
```

### 4. Run the Examples

```bash
# See dry-run transformation
python examples/item_creation_example.py

# This will show:
# - How source data transforms to Wikidata JSON
# - Different datatype transformations
# - Batch processing options
```

## Workflow

### Creating Your Own Mapping

#### Option 1: Auto-Generate from ShEx (Recommended)

Start by auto-generating a mapping skeleton:

```python
from gkc import ClaimsMapBuilder
from gkc.item_creator import PropertyMapper
import json

# Method A: Use directly (quick testing)
builder = ClaimsMapBuilder(eid="E502")
mapper = PropertyMapper.from_claims_builder(builder, entity_type="Q7840353")

# Method B: Generate, save, customize (recommended for production)
builder = ClaimsMapBuilder(eid="E502")
mapping = builder.build_complete_mapping(entity_type="Q7840353")

# Save and edit to customize source_field names
with open("my_mapping.json", "w") as f:
    json.dump(mapping, f, indent=2)
    
# Edit my_mapping.json, then:
mapper = PropertyMapper.from_file("my_mapping.json")
```

This fetches live property data from Wikidata to ensure accurate datatypes and provides rich documentation. See [Claims Map Builder](../docs/claims_map_builder.md) for details.

#### Option 2: Manual Creation

1. **Start with a ShEx schema** - Identify the EntitySchema your items should conform to
2. **Map your fields** - Create a mapping config that connects your data to Wikidata properties
3. **Test with dry-run** - Transform your data without submitting
4. **Validate** - Use ShEx validation to ensure compliance
5. **Submit** - Create items on Wikidata (test on test.wikidata.org first!)

### Using Your Mapping

```python
from gkc import WikiverseAuth
from gkc.item_creator import PropertyMapper, ItemCreator

# 1. Setup authentication
auth = WikiverseAuth()
auth.login()

# 2. Load your mapping
mapper = PropertyMapper.from_file("my_mapping.json")

# 3. Create the item creator
creator = ItemCreator(auth=auth, mapper=mapper, dry_run=True)

# 4. Transform and submit your data
import json
with open("my_data.json") as f:
    data = json.load(f)

for record in data:
    qid = creator.create_item(record)
    print(f"Created: {qid}")
```

## Key Features

### Datatype Support

The mapper handles all major Wikidata datatypes:

- ✅ **wikibase-item** - References to other Wikidata items (QIDs)
- ✅ **quantity** - Numbers with optional units
- ✅ **time** - Dates with configurable precision
- ✅ **monolingualtext** - Text in specific languages
- ✅ **globe-coordinate** - Latitude/longitude coordinates
- ✅ **url** - Web addresses
- ✅ **string** - Plain text

### Qualifier Support

Add context to your statements:

```json
{
  "property": "P2124",
  "source_field": "member_count",
  "qualifiers": [
    {
      "property": "P585",
      "source_field": "count_date",
      "comment": "Point in time"
    }
  ]
}
```

### Reference Support

Add sources for your claims:

```json
{
  "references": [
    {
      "P248": {
        "value_from": "source_reference_qid",
        "comment": "Stated in"
      },
      "P813": {
        "value": "current_date",
        "comment": "Retrieved"
      }
    }
  ]
}
```

## Current Status

### ✅ Implemented (Skeleton)

- Core transformation logic
- Mapping configuration format
- Datatype transformers
- Claim/qualifier/reference builders
- Batch processing structure

### 🚧 In Progress

- ShEx validation integration
- Error handling and recovery
- Date parsing improvements
- Item lookup utilities

### 📋 Planned

- Auto-generate mappings from ShEx
- Duplicate detection
- Update/merge capabilities
- QuickStatements export
- Web UI for mapping creation

## Testing Safely

**Always test on test.wikidata.org first!**

```python
# Use test.wikidata.org
auth = WikiverseAuth(
    username="YourUser@YourBot",
    password="your_password",
    api_url="https://test.wikidata.org/w/api.php"
)
```

## Resources

- [Wikidata:Data donation](https://www.wikidata.org/wiki/Wikidata:Data_donation) - Best practices for adding data
- [Wikidata API:wbeditentity](https://www.wikidata.org/w/api.php?action=help&modules=wbeditentity) - API documentation
- [EntitySchema](https://www.wikidata.org/wiki/Wikidata:Database_reports/EntitySchema_directory) - Directory of entity schemas
- [Shape Expressions Primer](http://shex.io/shex-primer/) - Learn ShEx syntax

## Contributing

This is currently a design sketch. To move it forward:

1. Implement robust date/time parsing
2. Add comprehensive error handling
3. Integrate ShEx validation (JSON→RDF→validate)
4. Add item lookup capabilities
5. Improve documentation with more examples
6. Add unit tests

## Questions?

See the [detailed approach document](../docs/item_creation_approach.md) for:
- Complete architecture explanation
- Wikidata JSON format details
- Component descriptions
- Open questions and design decisions
