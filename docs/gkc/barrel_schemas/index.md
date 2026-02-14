# Barrel Schemas

Barrel Schemas define the shape, structure, and validation rules for target knowledge systems. Each target system has its own way of encoding schemas and constraints - GKC's Cooperage manages these and provides tools to build **Barrel Recipes** that transform data from the [Unified Still Schema](../pipeline_overview.md#schema-architecture-overview) into target-specific formats.

## What Are Barrel Schemas?

A Barrel Schema is any target system's specification of valid data structure:
- **Shape constraints**: What properties/fields are required vs optional
- **Datatype definitions**: What types of values are allowed
- **Relationship rules**: How entities connect to each other
- **Validation logic**: What constitutes well-formed data

## Target Systems

GKC supports (or will support) Barrel Schemas for multiple knowledge systems:

### [Wikidata EntitySchemas](wikidata_entityschemas.md) ✅ Implemented
Wikidata uses ShEx (Shape Expression) EntitySchemas coupled with property constraints to define valid item structures. The Cooperage fetches these schemas from Wikidata and provides tools to build Barrel Recipes that transform Still Schema data into Wikidata claims, qualifiers, and references.

**Status**: Fully implemented with validation support
- Fetch EntitySchemas from Wikidata
- Parse ShEx constraints
- Extract property requirements and cardinality
- Fetch property metadata via Wikidata API
- Generate Barrel Recipes automatically
- Validate using Spirit Safe

### [Wikimedia Commons](commons_schemas.md) 🚧 Planned
Wikimedia Commons uses structured data schemas based on Wikibase. Similar to Wikidata but with media-specific properties and constraints.

**Status**: Planned

### [Wikipedia Infoboxes](wikipedia_infoboxes.md) 🚧 Planned
Wikipedia infobox templates define structured data presentations. Each infobox template has parameter definitions that act as a de facto schema.

**Status**: Planned

### [OpenStreetMap Tagging](osm_tagging.md) 🚧 Planned
OSM uses tagging schemes documented in the OSM wiki. Tags have conventions, value constraints, and usage patterns that function as schemas.

**Status**: Planned

## Barrel Recipes

A **Barrel Recipe** transforms data from the Unified Still Schema to a specific Barrel Schema's format. The Cooperage provides tools to build these recipes:

- **Wikidata Barrel Recipe Builder** - Generates transformation specs from EntitySchemas (formerly ClaimsMapBuilder)
- **Commons Barrel Recipe Builder** - Coming soon
- **Wikipedia Barrel Recipe Builder** - Coming soon  
- **OSM Barrel Recipe Builder** - Coming soon

## The Role of the Cooperage

The [Cooperage](../distillery_glossary.md#the-cooperage) module manages Barrel Schemas:
- Fetches schema ingredients from target systems
- Caches property metadata and constraints
- Provides APIs for schema querying
- Enables Barrel Recipe generation
- Supports Spirit Safe validation

## Validation with Spirit Safe

The [Spirit Safe](../distillery_glossary.md#spirit-safe) validates transformed data against Barrel Schemas before bottling:
- ShEx validation for Wikidata EntitySchemas
- Schema compliance checking for Commons
- Template parameter validation for Wikipedia
- Tagging scheme validation for OSM

This ensures data quality before delivery to target systems.

## Next Steps

- Explore [Wikidata EntitySchemas](wikidata_entityschemas.md) to understand the current implementation
- Review the [Pipeline Overview](../pipeline_overview.md) to see how Barrel Schemas fit into the workflow
- See [Distillery Glossary](../distillery_glossary.md) for complete terminology reference
