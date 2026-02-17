# Approach: ShEx-Guided Wikidata Item Creation

## Overview

This document outlines an approach for creating new Wikidata items by combining:
1. **ShEx Entity Schemas** - Define the structure and constraints for valid items
2. **Property Mappings** - Map source data fields to Wikidata properties
3. **Source Data** - The raw data to be transformed into Wikidata items
4. **Wikidata API** - Submit items via authenticated API calls

## Components

### 1. ShEx Schema (Validation & Structure Definition)

ShEx schemas define what a valid Wikidata entity should look like. They specify:
- Required and optional properties
- Value constraints (datatypes, allowed values)
- Qualifiers and references
- Cardinality (how many times a property can appear)

**Example from tribe_E502.shex:**
```shex
<FederallyRecognizedTribe> {
    p:P31 @<InstanceOfFedTribe> ;  # Must have P31 (instance of)
    wdt:P30 [ wd:Q49 ] ;           # Must be in North America
    wdt:P17 [ wd:Q30 ] + ;         # Must be in United States
    p:P571 @<Inception> * ;        # Optional inception date
    p:P2124 @<MemberCount> * ;     # Optional member count
    ...
}
```

**Role:** Validation blueprint - tells us what the final item must conform to.

### 2. Property Mapping Configuration

A mapping configuration connects source data fields to Wikidata properties and defines transformation rules.

#### Auto-Generation from ShEx

Rather than manually creating mapping configurations, you can **auto-generate** them from EntitySchemas using the `RecipeBuilder`:

```python
from gkc import RecipeBuilder

# Generate mapping from EntitySchema E502
builder = RecipeBuilder(eid="E502")
mapping = builder.finalize_recipe(entity_type="Q7840353")

# This fetches live property data from Wikidata to ensure
# accurate datatypes, labels, and descriptions
```

See [Recipe Builder documentation](claims_map_builder.md) for details.

#### Separator Support for Multi-Value Fields

When working with spreadsheet-style data, you often have multiple values in a single field separated by a delimiter (e.g., "alias1; alias2; alias3"). The mapping configuration supports a `separator` parameter to automatically split these values:

```json
{
  "source_field": "tribe_name_aliases",
  "language": "en",
  "separator": ";",
  "comment": "Multiple aliases separated by semicolons"
}
```

This will split "CNO; Cherokee Nation of Oklahoma; Eastern Band" into three separate alias entries. Common separators include:
- `;` - Semicolon (recommended for CSV data)
- `,` - Comma (use with caution in CSV)
- `|` - Pipe
- `\t` - Tab

**Proposed Structure (JSON/YAML):**
```json
{
  "schema": {
    "entity_schema_id": "E502",
    "entity_type": "Q7840353",
    "description": "Federally recognized tribe mapper"
  },
  "reference_library": {
    "stated_in_federal_register": {
      "P248": {
        "value": "Q127419548",
        "datatype": "wikibase-item",
        "comment": "Stated in: Federal Register"
      },
      "P813": {
        "value": "current_date",
        "datatype": "time",
        "comment": "Retrieved date"
      }
    }
  },
  "qualifier_library": {
    "point_in_time": {
      "property": "P585",
      "source_field": "point_in_time_date",
      "datatype": "time"
    }
  },
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
        "separator": ";",
        "comment": "Multiple aliases in one field, separated by semicolons"
      }
    ],
    "claims": [
      {
        "property": "P31",
        "comment": "Instance of: federally recognized tribe",
        "value": "Q7840353",
        "datatype": "wikibase-item",
        "references": ["stated_in_federal_register"]
      },
      {
        "property": "P1705",
        "comment": "Native label",
        "source_field": "native_name",
        "datatype": "monolingualtext",
        "references": ["stated_in_federal_register"]
      },
      {
        "property": "P2124",
        "comment": "Member count",
        "source_field": "member_count",
        "datatype": "quantity",
        "qualifiers": [
          {
            "property": "P585",
            "source_field": "count_date",
            "datatype": "time"
          }
        ],
        "references": ["stated_in_federal_register"]
      },
      {
        "property": "P159",
        "comment": "Headquarters location",
        "source_field": "headquarters_qid",
        "datatype": "wikibase-item",
        "qualifiers": [
          {
            "property": "P625",
            "source_field": "headquarters_coordinates",
            "datatype": "globe-coordinate"
          }
        ]
      }
    ]
  },
  "validation": {
    "country": "Q30"
  }
}
```

### 3. Source Data

Source data can come from various formats (CSV, JSON, database, API):

**Example CSV:**
```csv
tribe_name,tribe_name_aliases,official_name_native,member_count,count_date,headquarters_location,source_reference_item
Cherokee Nation,"CNO; Cherokee Nation of Oklahoma",ᏣᎳᎩ ᎠᏰᎵ,400000,2023-01-01,Cherokee,Q123456
```

**Example JSON:**
```json
{
  "tribe_name": "Cherokee Nation",
  "tribe_name_aliases": "CNO; Cherokee Nation of Oklahoma; Eastern Band",
  "official_name_native": "ᏣᎳᎩ ᎠᏰᎵ",
  "member_count": 400000,
  "count_date": "2023-01-01",
  "headquarters_location": "Cherokee",
  "headquarters_coordinates": {
    "latitude": 35.9149,
    "longitude": -94.8703
  },
  "source_reference_item": "Q123456",
  "data_source_item": "Q789"
}
```

### 4. Wikidata JSON Structure

The Wikidata API expects a specific JSON structure for item creation:

**wbeditentity API format:**
```json
{
  "labels": {
    "en": {
      "language": "en",
      "value": "Cherokee Nation"
    }
  },
  "descriptions": {
    "en": {
      "language": "en",
      "value": "Federally recognized tribe in the United States"
    }
  },
  "claims": {
    "P31": [
      {
        "mainsnak": {
          "snaktype": "value",
          "property": "P31",
          "datavalue": {
            "value": {
              "entity-type": "item",
              "numeric-id": 7840353,
              "id": "Q7840353"
            },
            "type": "wikibase-entityid"
          }
        },
        "type": "statement",
        "rank": "normal",
        "references": [
          {
            "snaks": {
              "P248": [
                {
                  "snaktype": "value",
                  "property": "P248",
                  "datavalue": {
                    "value": {
                      "entity-type": "item",
                      "numeric-id": 123456,
                      "id": "Q123456"
                    },
                    "type": "wikibase-entityid"
                  }
                }
              ],
              "P813": [
                {
                  "snaktype": "value",
                  "property": "P813",
                  "datavalue": {
                    "value": {
                      "time": "+2024-01-15T00:00:00Z",
                      "timezone": 0,
                      "before": 0,
                      "after": 0,
                      "precision": 11,
                      "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
                    },
                    "type": "time"
                  }
                }
              ]
            },
            "snaks-order": ["P248", "P813"]
          }
        ]
      }
    ],
    "P2124": [
      {
        "mainsnak": {
          "snaktype": "value",
          "property": "P2124",
          "datavalue": {
            "value": {
              "amount": "+400000",
              "unit": "1"
            },
            "type": "quantity"
          }
        },
        "type": "statement",
        "rank": "normal",
        "qualifiers": {
          "P585": [
            {
              "snaktype": "value",
              "property": "P585",
              "datavalue": {
                "value": {
                  "time": "+2023-01-01T00:00:00Z",
                  "timezone": 0,
                  "before": 0,
                  "after": 0,
                  "precision": 11,
                  "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
                },
                "type": "time"
              }
            }
          ]
        },
        "qualifiers-order": ["P585"]
      }
    ]
  }
}
```

## Proposed Architecture

### Core Classes

#### 1. `Distillate`
Handles the mapping configuration and transformation logic.

```python
class Distillate:
  """Transforms source data to Wikidata format using a recipe config."""
    
    def __init__(self, mapping_config: dict):
        """Load mapping configuration."""
        
    def load_source_data(self, data: dict | list[dict]):
        """Load source data to be transformed."""
        
    def transform_to_wikidata(self, source_record: dict) -> dict:
        """Transform a single source record to Wikidata JSON format."""
        
    def create_mainsnak(self, property_id: str, value: Any, datatype: str) -> dict:
        """Create a mainsnak (main value) for a claim."""
        
    def create_qualifier(self, property_id: str, value: Any, datatype: str) -> dict:
        """Create a qualifier for a claim."""
        
    def create_reference(self, reference_config: dict, source_record: dict) -> dict:
        """Create a reference block."""
```

#### 2. `WikidataItemBuilder`
Builds the complete Wikidata JSON structure.

```python
class WikidataItemBuilder:
    """Builds Wikidata item JSON structures."""
    
    def __init__(self):
        self.item_data = {"labels": {}, "descriptions": {}, "claims": {}}
        
    def add_label(self, language: str, value: str) -> "WikidataItemBuilder":
        """Add a label in a specific language."""
        return self
        
    def add_description(self, language: str, value: str) -> "WikidataItemBuilder":
        """Add a description in a specific language."""
        return self
        
    def add_claim(self, property_id: str, claim_data: dict) -> "WikidataItemBuilder":
        """Add a claim (statement) to the item."""
        return self
        
    def build(self) -> dict:
        """Return the complete item JSON."""
        return self.item_data
```

#### 3. `WikidataSubmitter` (Planned)
Orchestrates the submission process (not yet implemented in the codebase).

```python
class WikidataSubmitter:
  """Submits Wikidata items from source data using validation."""
    
    def __init__(
        self, 
        auth: WikiverseAuth,
        distillate: Distillate,
        validator: SpiritSafeValidator = None
    ):
        """Initialize with authentication, mapper, and optional validator."""
        
    def create_item(self, source_record: dict, validate: bool = True) -> str:
        """
        Create a new Wikidata item.
        
        Args:
            source_record: Source data record
            validate: Whether to validate against ShEx before submission
            
        Returns:
            QID of created item
        """
        
    def validate_before_submit(self, item_json: dict) -> bool:
        """Validate the constructed item against ShEx schema."""
        
    def submit_to_wikidata(self, item_json: dict) -> dict:
        """Submit the item to Wikidata via API."""
```

## Workflow

### Step 1: Define Mapping Configuration
Create a mapping file that connects source data to Wikidata properties:
```python
from gkc import Distillate

mapping_config = {
    "schema": {"entity_schema_id": "E502"},
    "mappings": [...]  # See mapping structure above
}

distillate = Distillate(mapping_config)
```

### Step 2: Load Source Data
```python
source_data = [
    {
        "tribe_name": "Cherokee Nation",
        "member_count": 400000,
        # ... more fields
    }
]
```

### Step 3: Transform and Validate
```python
from gkc import WikiverseAuth, SpiritSafeValidator

auth = WikiverseAuth()
auth.login()

validator = SpiritSafeValidator(eid="E502")
# Submission client is not yet implemented; use your own submission workflow.

# Transform source record to Wikidata JSON
for record in source_data:
    try:
        # This will:
        # 1. Transform source data to Wikidata JSON
        # 2. Validate against ShEx schema
        # 3. Submit to Wikidata
        _ = distillate.transform_to_wikidata(record)
        print("Transformed record to Wikidata JSON")
    except ValidationError as e:
        print(f"Validation failed: {e}")
    except WikidataAPIError as e:
        print(f"API error: {e}")
```

## Benefits of This Approach

1. **Schema-Driven**: ShEx schemas ensure data quality and consistency
2. **Flexible Mapping**: Supports complex transformations and multiple source formats
3. **Validation First**: Catch errors before submission
4. **Auditable**: Clear mapping from source to Wikidata
5. **Reusable**: Mapping configs can be shared and versioned
6. **Incremental**: Can be extended later for updates and deletions

## Next Steps for Implementation

1. **Phase 1**: Implement core datatype transformations
   - String → label/description
   - Item references → wikibase-entityid
   - Numbers → quantity
   - Dates → time
   - Coordinates → globe-coordinate

2. **Phase 2**: Implement mapping system
   - Load/validate mapping configs
   - Transform source data using mappings
   - Handle qualifiers and references

3. **Phase 3**: Integrate with existing auth system
   - Use WikiverseAuth for API calls
   - Implement wbeditentity API wrapper
   - Handle CSRF tokens

4. **Phase 4**: Add ShEx validation integration
   - Validate transformed JSON before submission
   - Convert JSON to RDF for validation
   - Provide meaningful error messages

5. **Phase 5**: Add batch processing and error handling
   - Process multiple records
   - Retry logic
   - Detailed logging
   - Dry-run mode

## Example Usage Pattern

```python
from gkc import WikiverseAuth, Distillate, SpiritSafeValidator

# 1. Setup authentication
auth = WikiverseAuth()
auth.login()

# 2. Load mapping configuration
distillate = Distillate.from_file("mappings/tribe_mapping.json")

# 3. Setup validator (optional but recommended)
validator = SpiritSafeValidator(eid="E502")

# 4. Create the item creator
# Submission client is not yet implemented; use your own submission workflow.

# 5. Load your source data
import csv
with open("tribes.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        _ = distillate.transform_to_wikidata(row)
        print(f"Transformed {row['tribe_name']} to Wikidata JSON")

# 6. Cleanup
auth.logout()
```

## Open Questions

1. **ShEx to Mapping**: Can we auto-generate initial mapping configs from ShEx schemas?
2. **Item Lookup**: How to handle looking up existing items (e.g., for headquarters location)?
3. **Duplicate Detection**: Should we check for duplicates before creating?
4. **Batch Submission**: Should we support batch uploads via QuickStatements format?
5. **Error Recovery**: How to handle partial failures in batch operations?

## References

- [Wikidata:Data donation](https://www.wikidata.org/wiki/Wikidata:Data_donation)
- [Wikidata API:wbeditentity](https://www.wikidata.org/w/api.php?action=help&modules=wbeditentity)
- [Shape Expressions (ShEx) Primer](http://shex.io/shex-primer/)
