# Claims Map Builder

Auto-generate mapping configurations from ShEx EntitySchemas by combining schema analysis with live Wikidata property metadata.

## Overview

The `ClaimsMapBuilder` utility helps you create mapping configurations by:

1. **Parsing ShEx schemas** to extract property requirements, cardinality, and comments
2. **Fetching live property data** from Wikidata to get accurate datatypes, labels, and descriptions
3. **Combining both sources** to generate a well-documented mapping skeleton
4. **Providing sensible defaults** for transform configurations based on datatypes

## Key Benefits

- ✅ **Accurate datatypes** - Fetched directly from Wikidata property records
- ✅ **Rich documentation** - Combines ShEx comments with Wikidata labels/descriptions
- ✅ **Cardinality detection** - Identifies required vs. optional properties from ShEx
- ✅ **Transform hints** - Auto-generates transform configurations for complex datatypes
- ✅ **Time-saving** - No need to manually look up every property

## Quick Start

### Generate Mapping from EntitySchema

```python
from gkc import ClaimsMapBuilder

# Load EntitySchema from Wikidata
builder = ClaimsMapBuilder(eid="E502")

# Generate complete mapping configuration
mapping = builder.build_complete_mapping(entity_type="Q7840353")

# Export to JSON file
import json
with open("my_mapping.json", "w") as f:
    json.dump(mapping, f, indent=2)
```

### Use Directly with PropertyMapper

You can use the generated mapping immediately without saving to a file:

```python
from gkc import ClaimsMapBuilder
from gkc.item_creator import PropertyMapper

# Generate mapping
builder = ClaimsMapBuilder(eid="E502")

# Create PropertyMapper directly
mapper = PropertyMapper.from_claims_builder(builder, entity_type="Q7840353")

# Now use mapper to transform your data
sample_data = {"label": "Example", "p31_value": "Q7840353"}
wikidata_json = mapper.transform_to_wikidata(sample_data)
```

**Note:** Auto-generated mappings use field names like `p31_value`, `p2124_value`, etc. You'll want to customize these to match your actual data fields. See the customization workflow below.

### Analyze Schema First

```python
from gkc import ClaimsMapBuilder

# Load and analyze
builder = ClaimsMapBuilder(eid="E502")
builder.load_schema()

# Print detailed analysis
builder.print_summary()
```

Output shows:
- Properties grouped by context (direct, qualifier, reference)
- Datatypes fetched from Wikidata
- Required vs. optional status from ShEx cardinality
- Labels and descriptions from both sources

## Recommended Workflows

### Workflow 1: Quick Testing (Direct Use)

For quick prototyping and testing:

```python
from gkc import ClaimsMapBuilder
from gkc.item_creator import PropertyMapper, ItemCreator
from gkc import WikiverseAuth

# Generate and use mapping directly
builder = ClaimsMapBuilder(eid="E502")
mapper = PropertyMapper.from_claims_builder(builder, entity_type="Q7840353")

# Use for dry-run testing
auth = WikiverseAuth()
creator = ItemCreator(auth=auth, mapper=mapper, dry_run=True)

sample_data = {"label": "Test", ...}  # Use auto-generated field names
creator.create_item(sample_data)
```

### Workflow 2: Customized Mapping (Recommended)

For production use with your actual data:

```python
from gkc import ClaimsMapBuilder
from gkc.item_creator import PropertyMapper
import json

# 1. Generate mapping
builder = ClaimsMapBuilder(eid="E502")
mapping = builder.build_complete_mapping(entity_type="Q7840353")

# 2. Save to file
with open("my_mapping.json", "w") as f:
    json.dump(mapping, f, indent=2)

# 3. Edit my_mapping.json to update source_field names:
#    Change: "source_field": "p2124_value"
#    To:     "source_field": "member_count"

# 4. Load customized mapping
mapper = PropertyMapper.from_file("my_mapping.json")

# 5. Use with your actual data
your_data = {"tribe_name": "Cherokee", "member_count": 450000}
wikidata_json = mapper.transform_to_wikidata(your_data)
```

### Workflow 3: Programmatic Customization

For advanced programmatic customization:

```python
from gkc import ClaimsMapBuilder
from gkc.item_creator import PropertyMapper

# Generate mapping
builder = ClaimsMapBuilder(eid="E502")
mapping = builder.build_complete_mapping(entity_type="Q7840353")

# Customize in code
field_name_map = {
    "P2124": "member_count",
    "P571": "established_date",
    "P856": "website",
    # ... etc.
}

for claim in mapping["mappings"]["claims"]:
    prop = claim["property"]
    if prop in field_name_map:
        claim["source_field"] = field_name_map[prop]

# Also update labels/descriptions
mapping["mappings"]["labels"][0]["source_field"] = "name"
mapping["mappings"]["descriptions"][0]["source_field"] = "description"

# Use customized mapping
mapper = PropertyMapper(mapping)
```

### Use Local ShEx File

```python
builder = ClaimsMapBuilder(schema_file="path/to/schema.shex")
mapping = builder.build_complete_mapping()
```

## How It Works

### 1. ShEx Parsing

The `ShExPropertyExtractor` parses ShEx text to extract:

```shex
<FederallyRecognizedTribe> {
    p:P31 @<InstanceOfFedTribe> ;  # Must have exactly one P31
    wdt:P30 [ wd:Q49 ] ;           # Continent: North America  
    p:P2124 @<MemberCount> * ;     # Member count (zero or more)
}
```

Extracted information:
- **Property IDs**: P31, P30, P2124
- **Cardinality**: `;` = required, `*` = optional multiple, `?` = optional single
- **Comments**: Inline comments after `#`
- **Context**: Statement property (`p:`), direct property (`wdt:`), qualifier (`pq:`), etc.

### 2. Property Metadata Fetching

The `WikidataPropertyFetcher` queries the Wikidata API:

```python
GET https://www.wikidata.org/w/api.php?action=wbgetentities&ids=P31|P30|P2124
```

Returns:
- **Datatype**: `wikibase-item`, `quantity`, `time`, etc.
- **Labels**: "instance of", "continent", "member count"
- **Descriptions**: Detailed explanations in multiple languages
- **Aliases**: Alternative names for the property

### 3. Combining Information

For each property, the builder creates a mapping entry:

```json
{
  "property": "P2124",
  "comment": "member count - count of members of an organization",
  "source_field": "p2124_value",
  "datatype": "quantity",
  "required": false,
  "transform": {
    "type": "number_to_quantity",
    "unit": "1"
  }
}
```

The comment includes:
- Property label from Wikidata
- Inline comment from ShEx
- Property description from Wikidata

## Generated Output Structure

### Complete Mapping Configuration

```json
{
  "$schema": "https://example.com/gkc/mapping-schema.json",
  "version": "1.0",
  "metadata": {
    "name": "Auto-generated mapping",
    "entity_schema_id": "E502",
    "target_entity_type": "Q7840353"
  },
  "mappings": {
    "labels": [...],
    "aliases": [...],
    "descriptions": [...],
    "claims": [
      {
        "property": "P2124",
        "comment": "member count - number of people/things in a group",
        "source_field": "p2124_value",
        "datatype": "quantity",
        "required": false,
        "transform": {
          "type": "number_to_quantity",
          "unit": "1"
        }
      }
    ]
  },
  "notes": [
    "This mapping was auto-generated from a ShEx schema",
    "UPDATE all 'source_field' values to match your data",
    "REVIEW all 'transform' configurations",
    "ADD appropriate references to claims"
  ]
}
```

### What You Need to Update

The generated mapping is a **skeleton** that you customize:

1. ✏️ **source_field** - Change from `p2124_value` to your actual field names
2. ✏️ **transform** - Adjust precision, units, language codes, etc.
3. ✏️ **qualifiers** - Add qualifiers to appropriate claims
4. ✏️ **references** - Add reference configurations
5. ✏️ **defaults** - Move constant-value properties to the defaults section

## Datatype Transform Hints

The builder auto-generates transform hints based on Wikidata datatypes:

### Time/Date
```json
{
  "datatype": "time",
  "transform": {
    "type": "iso_date_to_wikidata_time",
    "precision": 11
  }
}
```

### Quantity
```json
{
  "datatype": "quantity",
  "transform": {
    "type": "number_to_quantity",
    "unit": "1"
  }
}
```

### Globe Coordinate
```json
{
  "datatype": "globe-coordinate",
  "transform": {
    "type": "lat_lon_to_globe_coordinate",
    "latitude_field": "TODO_latitude",
    "longitude_field": "TODO_longitude"
  }
}
```

### Monolingualtext
```json
{
  "datatype": "monolingualtext",
  "transform": {
    "type": "monolingualtext",
    "language": "en"
  }
}
```

## Advanced Usage

### Analyze Datatype Coverage

```python
builder = ClaimsMapBuilder(eid="E502")
claims_map = builder.build_claims_map()

# Group by datatype
by_datatype = {}
for claim in claims_map:
    dtype = claim["datatype"]
    if dtype not in by_datatype:
        by_datatype[dtype] = []
    by_datatype[dtype].append(claim["property"])

for dtype, props in by_datatype.items():
    print(f"{dtype}: {len(props)} properties")
```

### Compare with Manual Mapping

```python
# Load manual mapping
with open("manual_mapping.json") as f:
    manual = json.load(f)

# Generate auto mapping
builder = ClaimsMapBuilder(eid="E502")
auto = builder.build_complete_mapping()

# Find missing properties
manual_props = {c["property"] for c in manual["mappings"]["claims"]}
auto_props = {c["property"] for c in auto["mappings"]["claims"]}

missing = auto_props - manual_props
print(f"Properties in ShEx but not in manual mapping: {missing}")
```

### Custom User Agent

```python
builder = ClaimsMapBuilder(
    eid="E502",
    user_agent="MyBot/1.0 (myemail@example.com)"
)
```

## API Reference

### ClaimsMapBuilder

Main class for building mapping configurations.

#### Methods

- **`__init__(eid=None, schema_text=None, schema_file=None, user_agent=None)`**
  - Initialize with ShEx source (choose one of eid, schema_text, or schema_file)

- **`load_schema()`**
  - Load the ShEx schema (returns self for chaining)

- **`build_claims_map(include_qualifiers=True, include_references=True)`**
  - Build just the claims mapping section
  - Returns: List of claim mapping dictionaries

- **`build_complete_mapping(entity_type=None)`**
  - Build complete mapping configuration
  - Returns: Complete mapping dictionary

- **`print_summary()`**
  - Print detailed analysis of the ShEx schema

### WikidataPropertyFetcher

Fetches property metadata from Wikidata API.

#### Methods

- **`fetch_properties(property_ids)`**
  - Fetch metadata for multiple properties
  - Args: List of property IDs (e.g., `['P31', 'P571']`)
  - Returns: Dictionary mapping IDs to `PropertyInfo` objects

### ShExPropertyExtractor

Parses ShEx schema text to extract property information.

#### Methods

- **`extract()`**
  - Extract all properties with context
  - Returns: Dictionary mapping property IDs to their context info

## Examples

See [mapping_builder_example.py](https://github.com/skybristol/gkc/blob/main/examples/mapping_builder_example.py) for complete working examples:

1. **Analyze Schema** - Parse and analyze ShEx structure
2. **Build Claims Map** - Generate just the claims section
3. **Complete Mapping** - Generate full mapping config
4. **From File** - Use local ShEx file
5. **Export Mapping** - Save to JSON file
6. **Compare Mappings** - Manual vs. auto-generated
7. **Datatype Coverage** - Analyze property datatypes

## Limitations

### Current

- Qualifier and reference associations are not yet parsed from ShEx structure
- Shape inheritance is not fully supported
- Complex ShEx patterns (AND, OR) are simplified
- Some edge-case cardinality patterns may not be detected

### Future Improvements

- Parse full ShEx structure to associate qualifiers with statements
- Support shape inheritance and composition
- Handle value constraints (e.g., `[ wd:Q30 ]` → default value Q30)
- Generate example source data from ShEx
- Detect duplicate/overlapping properties

## Tips

1. **Start with auto-generation** - Let the builder create the skeleton
2. **Review every field** - Don't assume generated values are perfect
3. **Test with sample data** - Validate the mapping with real source data
4. **Iterate** - Regenerate as ShEx schemas evolve
5. **Document changes** - Add comments explaining your customizations

## Related

- [Item Creation Approach](item_creation_approach.md) - Overall architecture
- [Mapping Example](https://github.com/skybristol/gkc/blob/main/examples/mappings/tribe_mapping_example.json) - Hand-crafted mapping
- [ShEx Validation](https://github.com/skybristol/gkc/blob/main/README.md) - Using ShEx for validation
