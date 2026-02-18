# Wikidata EntitySchemas & Barrel Recipe Builder

Wikidata uses **EntitySchemas** (written in ShEx/Shape Expression language) coupled with **property constraints** to define valid item structures. This Barrel Schema defines what constitutes well-formed Wikidata entities.

The **Wikidata Barrel Recipe Builder** (implemented as `RecipeBuilder` in code) automatically generates transformation recipes from EntitySchemas, creating the mapping logic needed to transform [Unified Still Schema](../pipeline_overview.md#schema-architecture-overview) data into valid Wikidata claims.

## Understanding Wikidata's Barrel Schema

Wikidata's Barrel Schema comes from two sources:

### 1. EntitySchemas (ShEx)
Shape Expression schemas that define:
- Required vs optional properties
- Property cardinality (single vs multiple values)
- Value constraints and relationships
- Structural patterns for entity types

Example: [E502](https://www.wikidata.org/wiki/EntitySchema:E502) defines the schema for federally recognized tribes in the United States.

### 2. Property Constraints
Individual property definitions include:
- Datatype specifications (item, quantity, time, etc.)
- Value range constraints
- Formatting requirements
- Conflict detection rules

## Barrel Recipe Builder Overview

The Barrel Recipe Builder helps you create **Wikidata Barrel Recipes** by:

1. **Parsing EntitySchemas** to extract property requirements, cardinality, and comments
2. **Fetching live property data** from Wikidata to get accurate datatypes, labels, and descriptions
3. **Combining both sources** to generate a well-documented transformation recipe skeleton
4. **Providing sensible defaults** for transform configurations based on datatypes

## Key Benefits

- ✅ **Accurate datatypes** - Fetched directly from Wikidata property records
- ✅ **Rich documentation** - Combines ShEx comments with Wikidata labels/descriptions
- ✅ **Cardinality detection** - Identifies required vs. optional properties from ShEx
- ✅ **Transform hints** - Auto-generates transform configurations for complex datatypes
- ✅ **Time-saving** - No need to manually look up every property

## Quick Start

### Generate Barrel Recipe from EntitySchema

```python
from gkc import RecipeBuilder

# Load EntitySchema from Wikidata
builder = RecipeBuilder(eid="E502")

# Generate complete Barrel Recipe (mapping configuration)
mapping = builder.finalize_recipe(entity_type="Q7840353")

# Export to JSON file
import json
with open("wikidata_barrel_recipe.json", "w") as f:
    json.dump(mapping, f, indent=2)
```

### Use Directly with Distillate

You can use the generated Barrel Recipe immediately without saving to a file:

```python
from gkc import RecipeBuilder
from gkc.bottler import Distillate

# Generate Barrel Recipe
builder = RecipeBuilder(eid="E502")

# Create Distillate directly
distillate = Distillate.from_recipe(builder, entity_type="Q7840353")

# Now use mapper to transform your Still Schema data
sample_data = {"label": "Example", "p31_value": "Q7840353"}
wikidata_json = distillate.transform_to_wikidata(sample_data)
```

**Note:** Auto-generated recipes use field names like `p31_value`, `p2124_value`, etc. You'll want to customize these to match your actual Still Schema field names. See the customization workflow below.

### Analyze EntitySchema First

```python
from gkc import RecipeBuilder

# Load and analyze
builder = RecipeBuilder(eid="E502")
builder.load_specification()

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
from gkc import RecipeBuilder
from gkc.bottler import Distillate
from gkc import WikiverseAuth

# Generate and use Barrel Recipe directly
builder = RecipeBuilder(eid="E502")
distillate = Distillate.from_recipe(builder, entity_type="Q7840353")

# Use for dry-run testing
auth = WikiverseAuth()
_ = auth

sample_data = {"label": "Test", ...}  # Use auto-generated field names
distillate.transform_to_wikidata(sample_data)
```

### Workflow 2: Customized Barrel Recipe (Recommended)

For production use with your actual Still Schema:

```python
from gkc import RecipeBuilder
from gkc.bottler import Distillate
import json

# 1. Generate Barrel Recipe
builder = RecipeBuilder(eid="E502")
mapping = builder.finalize_recipe(entity_type="Q7840353")

# 2. Save to file
with open("wikidata_barrel_recipe.json", "w") as f:
    json.dump(mapping, f, indent=2)

# 3. Edit wikidata_barrel_recipe.json to update source_field names:
#    Change: "source_field": "p2124_value"
#    To:     "source_field": "member_count"
#    (These should match your Unified Still Schema field names)

# 4. Load customized Barrel Recipe
distillate = Distillate.from_file("wikidata_barrel_recipe.json")

# 5. Use with your actual Still Schema data
your_data = {"tribe_name": "Cherokee", "member_count": 450000}
wikidata_json = distillate.transform_to_wikidata(your_data)
```

### Workflow 3: Programmatic Customization

For advanced programmatic customization:

```python
from gkc import RecipeBuilder
from gkc.bottler import Distillate

# Generate Barrel Recipe
builder = RecipeBuilder(eid="E502")
mapping = builder.finalize_recipe(entity_type="Q7840353")

# Customize in code to match Still Schema field names
field_name_map = {
    "P2124": "member_count",
    "P571": "established_date",
    "P856": "website",
    # ... etc - map to your Still Schema fields
}

for claim in mapping["mappings"]["claims"]:
    prop = claim["property"]
    if prop in field_name_map:
        claim["source_field"] = field_name_map[prop]

# Also update labels/descriptions
mapping["mappings"]["labels"][0]["source_field"] = "name"
mapping["mappings"]["descriptions"][0]["source_field"] = "description"

# Use customized Barrel Recipe
distillate = Distillate(mapping)
```

### Use Local ShEx File

```python
builder = RecipeBuilder(schema_file="path/to/schema.shex")
mapping = builder.finalize_recipe()
```

## How It Works

### 1. ShEx Parsing

The `SpecificationExtractor` parses ShEx text to extract:

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

### 2. Entity Metadata Fetching

The `EntityCatalog` queries Wikidata via SPARQL (WDQS) and supports mixed
property and item IDs in a single request.

Returns:
- **Labels**: "instance of", "continent", "member count"
- **Descriptions**: Detailed explanations in multiple languages
- **Aliases**: Alternative names for the property
- **Datatype**: `wikibase-item`, `quantity`, `time`, etc. (properties only)

### 3. Combining Information

For each property, the builder creates a Barrel Recipe entry:

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

### Complete Barrel Recipe Configuration

```json
{
  "$schema": "https://example.com/gkc/mapping-schema.json",
  "version": "1.0",
  "metadata": {
    "name": "Auto-generated Wikidata Barrel Recipe",
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
    "This Barrel Recipe was auto-generated from a Wikidata EntitySchema",
    "UPDATE all 'source_field' values to match your Unified Still Schema",
    "REVIEW all 'transform' configurations",
    "ADD appropriate references to claims"
  ]
}
```

### What You Need to Update

The generated Barrel Recipe is a **skeleton** that you customize:

1. ✏️ **source_field** - Change from `p2124_value` to your Still Schema field names
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
builder = RecipeBuilder(eid="E502")
claims_map = builder.assemble_recipe()

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

### Compare with Manual Recipe

```python
# Load manual Barrel Recipe
with open("manual_recipe.json") as f:
    manual = json.load(f)

# Generate auto Barrel Recipe
builder = RecipeBuilder(eid="E502")
auto = builder.finalize_recipe()

# Find missing properties
manual_props = {c["property"] for c in manual["mappings"]["claims"]}
auto_props = {c["property"] for c in auto["mappings"]["claims"]}

missing = auto_props - manual_props
print(f"Properties in EntitySchema but not in manual recipe: {missing}")
```

### Custom User Agent

```python
builder = RecipeBuilder(
    eid="E502",
    user_agent="MyBot/1.0 (myemail@example.com)"
)
```

## API Reference

### RecipeBuilder

Main class for building Wikidata Barrel Recipe configurations.

#### Methods

- **`__init__(eid=None, schema_text=None, schema_file=None, user_agent=None)`**
  - Initialize with ShEx source (choose one of eid, schema_text, or schema_file)

- **`load_specification()`**
  - Load the ShEx schema (returns self for chaining)

- **`assemble_recipe(include_qualifiers=True, include_references=True)`**
  - Build just the claims mapping section
  - Returns: List of claim mapping dictionaries

- **`finalize_recipe(entity_type=None)`**
  - Build complete Barrel Recipe configuration
  - Returns: Complete mapping dictionary

- **`print_summary()`**
  - Print detailed analysis of the ShEx schema

### EntityCatalog

Fetches property and item metadata from Wikidata via SPARQL.

#### Methods

- **`fetch_entities(entity_ids)`**
  - Fetch metadata for mixed property and item IDs
  - Args: List of entity IDs (e.g., `['P31', 'Q5']`)
  - Returns: Dictionary mapping IDs to `PropertyLedgerEntry` or `ItemLedgerEntry` objects

### SpecificationExtractor

Parses ShEx schema text to extract property information.

#### Methods

- **`extract()`**
  - Extract all properties with context
  - Returns: Dictionary mapping property IDs to their context info

## Examples

See [docs/gkc/examples/wikidata_barrel_recipe_from_entityschema.ipynb](https://github.com/skybristol/gkc/blob/main/docs/gkc/examples/wikidata_barrel_recipe_from_entityschema.ipynb) for complete working examples:

1. **Analyze Schema** - Parse and analyze ShEx structure
2. **Build Claims Map** - Generate just the claims section
3. **Complete Mapping** - Generate full Barrel Recipe config
4. **From File** - Use local ShEx file
5. **Export Mapping** - Save to JSON file
6. **Compare Mappings** - Manual vs. auto-generated
7. **Datatype Coverage** - Analyze property datatypes

## Validation with Spirit Safe

Once you've created a Wikidata Barrel Recipe and transformed your data, validate against the EntitySchema:

```python
from gkc import SpiritSafeValidator

# Validate a Wikidata item against EntitySchema
validator = SpiritSafeValidator(qid='Q14708404', eid='E502')
validator.check()

if validator.passes_inspection():
    print("Data conforms to Barrel Schema!")
else:
    print("Validation failed - data doesn't meet schema requirements")
```

See [Spirit Safe documentation](../distillery_glossary.md#spirit-safe) for more on validation.

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
- Integration with Unified Still Schema definitions

## Related Documentation

- [Pipeline Overview](../pipeline_overview.md) - See how Barrel Recipes fit into the workflow
- [Barrel Schemas Overview](index.md) - Understanding the schema architecture
- [Distillery Glossary](../distillery_glossary.md) - Complete terminology reference
- [Cooperage](../distillery_glossary.md#the-cooperage) - Schema management module
- [Spirit Safe](../distillery_glossary.md#spirit-safe) - Validation system
