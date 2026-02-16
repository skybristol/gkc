# Wikimedia Commons Schemas & Barrel Recipe Builder

🚧 **Status**: Planned - Not yet implemented

## Overview

Wikimedia Commons will use structured data schemas based on Wikibase (similar to Wikidata) to define valid media file metadata structures. This Barrel Schema will define what constitutes well-formed Commons structured data.

The **Commons Barrel Recipe Builder** will automatically generate transformation recipes from Commons schemas, creating the mapping logic needed to transform [Unified Still Schema](../pipeline_overview.md#schema-architecture-overview) data into valid Commons structured data statements.

## Understanding Commons' Barrel Schema

Wikimedia Commons uses Wikibase-style structured data with media-specific extensions:

### Key Differences from Wikidata
- **Media-centric properties**: Focus on depicts, creator, copyright, location
- **File-specific metadata**: Resolution, format, creation date, camera info
- **Copyright constraints**: Specific validation for licensing properties
- **Category relationships**: Integration with Commons category system

### Schema Sources (Planned)
1. **Structured data schemas** - Property definitions and constraints
2. **SDC property constraints** - Value restrictions and relationships
3. **Category requirements** - Category-specific metadata expectations

## Barrel Recipe Builder (Planned)

The Commons Barrel Recipe Builder will:

1. Parse Commons structured data schemas
2. Fetch property metadata from Commons/Wikidata
3. Generate transformation recipes from Still Schema to Commons format
4. Provide media-specific transform hints (file metadata, MIME types, etc.)
5. Handle category and depicts relationships

## Example Use Case (Future)

```python
# Planned API (not yet implemented)
from gkc import CommonsRecipeBuilder

# Load Commons schema for a category or media type
builder = CommonsRecipeBuilder(category="Images of scientific specimens")

# Generate Barrel Recipe
recipe = builder.finalize_recipe()

# Use with Distillate
distillate = Distillate.from_commons_builder(builder)
commons_data = distillate.transform_to_commons(still_schema_data)
```

## Expected Features

- Media file metadata transformation
- Depicts statement generation
- Creator and copyright attribution
- Geolocation for geotagged media
- Category assignment logic
- Caption and description handling
- Integration with Wikidata concepts

## Validation (Planned)

Spirit Safe validation against Commons schemas:
- Property constraint checking
- Copyright/licensing validation
- Category requirement validation
- File format compatibility checks

## Related Commons Documentation

- [Commons:Structured data](https://commons.wikimedia.org/wiki/Commons:Structured_data) - Official documentation
- [Commons:Properties](https://commons.wikimedia.org/wiki/Special:ListProperties) - Available properties

## Development Status

- 📋 Requirements analysis needed
- 🔍 Schema format investigation needed
- 🛠️ API design in progress
- ⏳ Implementation not yet started

See [Issue #9](https://github.com/skybristol/gkc/issues/9) for development tracking.

## Related Documentation

- [Pipeline Overview](../pipeline_overview.md) - See how Barrel Recipes fit into the workflow
- [Barrel Schemas Overview](index.md) - Understanding the schema architecture
- [Wikidata EntitySchemas](wikidata_entityschemas.md) - Similar implementation (reference)
- [Distillery Glossary](../distillery_glossary.md) - Complete terminology reference
