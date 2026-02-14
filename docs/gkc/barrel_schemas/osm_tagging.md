# OpenStreetMap Tagging Schemas & Barrel Recipe Builder

🚧 **Status**: Planned - Not yet implemented

## Overview

OpenStreetMap uses tagging schemes documented in the OSM wiki to define valid feature structures. While OSM doesn't have formal schemas, tagging conventions, documented patterns, and key/value combinations function as implicit schemas.

The **OSM Barrel Recipe Builder** will automatically generate transformation recipes from OSM tagging documentation, creating the mapping logic needed to transform [Unified Still Schema](../pipeline_overview.md#schema-architecture-overview) data into valid OSM features with appropriate tags.

## Understanding OSM's Barrel Schema

OSM tagging schemes are community-documented conventions:

### Tagging Structure
- **Key-value pairs**: Fundamental OSM data structure (e.g., `amenity=restaurant`)
- **Tag combinations**: Certain tags commonly appear together
- **Tagging guidelines**: Wiki documentation for feature types
- **Value constraints**: Some keys expect specific value sets
- **Conditional tags**: Some tags depend on other tag values

### Schema Sources (Planned)
1. **OSM Wiki tagging pages** - Documented tag usage and conventions
2. **Tag popularity statistics** - Actual usage patterns from OSM data
3. **iD/JOSM editor presets** - Editor-specific tagging schemas
4. **TagInfo database** - Comprehensive tag usage database
5. **Map Features documentation** - Primary reference for standard tags

## Examples of OSM Tagging Patterns

### Building/Place
```
amenity=place_of_worship
religion=christian
denomination=baptist
name=First Baptist Church
```

### Natural Feature
```
natural=water
water=river
name=Colorado River
width=100
```

### Administrative Boundary
```
boundary=administrative
admin_level=6
name=Boulder County
```

## Barrel Recipe Builder (Planned)

The OSM Barrel Recipe Builder will:

1. Parse OSM wiki tagging documentation
2. Fetch tag usage statistics from TagInfo
3. Extract tagging patterns and conventions
4. Generate transformation recipes from Still Schema to OSM tags
5. Provide suggestions for related/dependent tags
6. Handle conditional tagging logic
7. Support namespaced tags

## Example Use Case (Future)

```python
# Planned API (not yet implemented)
from gkc import OSMRecipeBuilder

# Load tagging pattern for a feature type
builder = OSMRecipeBuilder(feature_type="amenity=restaurant")

# Generate Barrel Recipe
recipe = builder.build_complete_mapping()

# Use with PropertyMapper
mapper = PropertyMapper.from_osm_builder(builder)
osm_tags = mapper.transform_to_osm(still_schema_data)
```

## Expected Features

- Wiki scraping for tagging documentation
- TagInfo integration for usage patterns
- Preset file parsing (iD, JOSM)
- Conditional tag logic
- Geometry type validation (point, way, area, relation)
- Name tag multilingual support
- Address tag structuring
- Related tag suggestions

## Validation (Planned)

Spirit Safe validation against OSM tagging schemes:
- Required tag checking (based on feature type)
- Value constraint validation
- Tag combination validation
- Geometry type compatibility
- Deprecated tag detection
- Common tagging mistake detection

## Challenges

- **No formal schema**: OSM has no authoritative schema, only conventions
- **Evolving standards**: Tagging practices change over time
- **Regional variations**: Different regions may tag similarly differently
- **Multiple valid patterns**: Often several ways to tag the same thing
- **Documentation quality**: Wiki pages vary in completeness and currency
- **Conflicting guidance**: Different sources may contradict each other

## Key Resources for Schema Building

- [OSM Map Features](https://wiki.openstreetmap.org/wiki/Map_features) - Primary tagging reference
- [TagInfo](https://taginfo.openstreetmap.org/) - Tag usage statistics
- [iD presets](https://github.com/openstreetmap/id-tagging-schema) - iD editor schemas
- [JOSM presets](https://josm.openstreetmap.de/wiki/Presets) - JOSM editor schemas
- [OSM Elements](https://wiki.openstreetmap.org/wiki/Elements) - Core data structures

## Output Formats

The Barrel Recipe will support multiple output formats:

1. **OSM XML**: Traditional OSM format
   ```xml
   <node id="-1" lat="40.0150" lon="-105.2705">
     <tag k="amenity" v="restaurant"/>
     <tag k="name" v="Mountain View Cafe"/>
     <tag k="cuisine" v="american"/>
   </node>
   ```

2. **GeoJSON with OSM tags**: For modern APIs
   ```json
   {
     "type": "Feature",
     "geometry": {"type": "Point", "coordinates": [-105.2705, 40.0150]},
     "properties": {
       "amenity": "restaurant",
       "name": "Mountain View Cafe",
       "cuisine": "american"
     }
   }
   ```

3. **Overpass QL**: For querying/validation

## Geometry Considerations

OSM features have geometry types that constrain valid tags:
- **Nodes** (points): Single coordinates
- **Ways** (lines/areas): Ordered list of nodes
- **Relations**: Groups of elements with roles

The Barrel Recipe must account for which geometry types are valid for each tag combination.

## Development Status

- 📋 Requirements analysis needed
- 🔍 TagInfo API investigation needed
- 🔍 Wiki parsing strategy needed
- 🛠️ API design in progress
- ⏳ Implementation not yet started

See [Issue #9](https://github.com/skybristol/gkc/issues/9) for development tracking.

## Related Documentation

- [Pipeline Overview](../pipeline_overview.md) - See how Barrel Recipes fit into the workflow
- [Barrel Schemas Overview](index.md) - Understanding the schema architecture
- [Wikidata EntitySchemas](wikidata_entityschemas.md) - Similar implementation (reference)
- [Distillery Glossary](../distillery_glossary.md) - Complete terminology reference
