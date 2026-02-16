# Wikipedia Infobox Schemas & Barrel Recipe Builder

🚧 **Status**: Planned - Not yet implemented

## Overview

Wikipedia infobox templates have parameter definitions that function as schemas - they define what data an article's structured summary should contain. This Barrel Schema defines what constitutes a well-formed infobox.

The **Wikipedia Barrel Recipe Builder** will automatically generate transformation recipes from infobox template definitions, creating the mapping logic needed to transform [Unified Still Schema](../pipeline_overview.md#schema-architecture-overview) data into valid infobox wikitext or template JSON.

## Understanding Wikipedia's Barrel Schema

Wikipedia infoboxes are structured templates with defined parameters:

### Infobox Structure
- **Template parameters**: Named fields with specific expectations
- **Parameter documentation**: TemplateData JSON defines parameter types and descriptions
- **Required vs optional**: Some parameters must be present
- **Value formats**: Some parameters expect specific formats (dates, quantities, etc.)

### Schema Sources (Planned)
1. **TemplateData specifications** - Structured parameter definitions
2. **Template documentation pages** - Usage guidelines and constraints
3. **Parameter examples** - Common value patterns and formats
4. **Category patterns** - Templates grouped by subject domain

## Examples of Infobox Templates

- [Template:Infobox person](https://en.wikipedia.org/wiki/Template:Infobox_person)
- [Template:Infobox organization](https://en.wikipedia.org/wiki/Template:Infobox_organization)
- [Template:Infobox settlement](https://en.wikipedia.org/wiki/Template:Infobox_settlement)
- [Template:Infobox university](https://en.wikipedia.org/wiki/Template:Infobox_university)

## Barrel Recipe Builder (Planned)

The Wikipedia Barrel Recipe Builder will:

1. Parse TemplateData specifications for a template
2. Extract parameter definitions, types, and documentation
3. Generate transformation recipes from Still Schema to template parameters
4. Provide wikitext formatting hints
5. Handle parameter aliases and deprecated names
6. Support template nesting and composition

## Example Use Case (Future)

```python
# Planned API (not yet implemented)
from gkc import WikipediaRecipeBuilder

# Load template specification
builder = WikipediaRecipeBuilder(template="Infobox university")

# Generate Barrel Recipe
recipe = builder.finalize_recipe()

# Use with Distillate
distillate = Distillate.from_wikipedia_builder(builder)
infobox_wikitext = distillate.transform_to_infobox(still_schema_data)
```

## Expected Features

- TemplateData parsing
- Parameter type detection (string, number, date, URL, etc.)
- Wikitext formatting (links, formatting, citations)
- Multi-language template support
- Parameter aliasing and deprecation handling
- Template composition (nested infoboxes)
- Citation and reference formatting

## Validation (Planned)

Spirit Safe validation against infobox schemas:
- Required parameter checking
- Parameter type validation
- Format constraint checking (dates, URLs, etc.)
- Value range validation
- Link target verification

## Challenges

- **No formal schema**: TemplateData is optional and coverage varies
- **Template diversity**: Thousands of templates with different conventions
- **Wikitext complexity**: Need to generate valid wikitext formatting
- **Language variations**: Different Wikipedias have different templates
- **Evolution**: Templates change frequently

## Output Formats

The Barrel Recipe will support multiple output formats:

1. **Wikitext**: Traditional template syntax
   ```wiki
   {{Infobox university
   | name = Example University
   | established = 1850
   | type = Public
   }}
   ```

2. **Template JSON**: For API-based editing
3. **HTML**: For preview/validation

## Related Wikipedia Documentation

- [Help:Infobox](https://en.wikipedia.org/wiki/Help:Infobox) - General infobox documentation
- [Extension:TemplateData](https://www.mediawiki.org/wiki/Extension:TemplateData) - TemplateData specification
- [Wikipedia:List of infoboxes](https://en.wikipedia.org/wiki/Wikipedia:List_of_infoboxes) - Complete template list

## Development Status

- 📋 Requirements analysis needed
- 🔍 TemplateData format investigation needed
- 🛠️ API design in progress
- ⏳ Implementation not yet started

See [Issue #9](https://github.com/skybristol/gkc/issues/9) for development tracking.

## Related Documentation

- [Pipeline Overview](../pipeline_overview.md) - See how Barrel Recipes fit into the workflow
- [Barrel Schemas Overview](index.md) - Understanding the schema architecture
- [Wikidata EntitySchemas](wikidata_entityschemas.md) - Similar implementation (reference)
- [Distillery Glossary](../distillery_glossary.md) - Complete terminology reference
