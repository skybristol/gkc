# Sitelinks Implementation Summary

## Overview
Added comprehensive sitelinks support to the GKC mapping and transformation system, enabling automatic linking of Wikidata items to Wikipedia articles and other Wikimedia project pages.

## Changes Made

### 1. Core Implementation (`gkc/bottler.py`)

#### `Distillate.transform_to_wikidata()`
- Added `"sitelinks": {}` to the item structure
- Implemented sitelinks processing loop after descriptions and before claims
- Features:
  - Supports both `source_field` (data-driven) and `title` (fixed value) configurations
  - Automatic empty/NaN value handling using `_is_empty_value()`
  - Required field validation
  - Badge support
  - Proper whitespace trimming

#### Sitelinks Structure
```python
"sitelinks": {
    "enwiki": {
        "site": "enwiki",
        "title": "Article Title",
        "badges": []
    }
}
```

### 2. Recipe Builder (`gkc/recipe.py`)

#### `RecipeBuilder.finalize_recipe()`
- Added default sitelinks section to generated mappings
- Includes English Wikipedia (`enwiki`) as example
- Updated notes with sitelinks guidance

### 3. Examples

#### New File: `examples/sitelinks_example.py`
Comprehensive example demonstrating:
- Basic sitelinks configuration
- Multiple Wikipedia language editions
- Wikimedia Commons categories
- Fixed vs. data-driven titles
- Badge usage (featured articles)
- Empty value handling
- Common site codes reference

#### Updated: `examples/csv_to_wikidata_dryrun.ipynb`
- Added sitelinks display cell after aliases/descriptions
- Added documentation cell with configuration examples and site codes

#### Updated: `examples/mappings/fed_tribe_from_missing_ak_tribes.json`
- Added sitelinks section with English Wikipedia example
- Updated notes with sitelinks guidance

### 4. Documentation

#### New File: `docs/sitelinks_usage.md`
Comprehensive documentation covering:
- Sitelinks overview and structure
- Mapping configuration options
- Common site codes (Wikipedia, Commons, etc.)
- Configuration examples (data-driven, fixed, badges)
- Empty value handling
- API submission notes
- Validation guidance
- Auto-generation with RecipeBuilder
- Troubleshooting tips

#### Updated: `examples/README.md`
- Added sitelinks_example.py to examples list
- Mentioned sitelinks in notebook description

## Features

### Configuration Options
```json
{
  "site": "enwiki",           // Required: site identifier
  "source_field": "wiki_en",  // OR "title": "Fixed Title"
  "required": false,          // Optional: validation
  "badges": [],               // Optional: article badges
  "comment": "..."            // Optional: documentation
}
```

### Supported Site Types
- **Wikipedia**: All language editions (enwiki, frwiki, etc.)
- **Wikimedia Commons**: commonswiki
- **Wikispecies**: specieswiki
- **Wikisource**: All language editions
- **Wikivoyage**: All language editions
- **Wiktionary**: All language editions

### Empty Value Handling
Automatically skips:
- `None` values
- `NaN` (including pandas NA)
- Empty strings
- Missing fields (when not required)

### Badge Support
Supports article quality badges:
- Q17437798: Featured article
- Q17437796: Good article
- Q17559452: Featured list
- Q17580674: Featured portal

## Testing

Verified with `examples/sitelinks_example.py`:
- ✅ Multiple sitelinks (enwiki, frwiki, commonswiki)
- ✅ Empty/None value skipping
- ✅ Missing field handling
- ✅ Fixed title configuration
- ✅ Badge attachment
- ✅ Whitespace trimming
- ✅ Integration with full item JSON

## Usage Example

```python
from gkc.bottler import Distillate

# Configure mapping with sitelinks
mapping_config = {
    "mappings": {
        "labels": [...],
        "sitelinks": [
            {
                "site": "enwiki",
                "source_field": "wikipedia_title",
                "badges": []
            }
        ],
        "claims": [...]
    }
}

distillate = Distillate(mapping_config)
item_json = distillate.transform_to_wikidata({
    "name": "Example",
    "wikipedia_title": "Example Article"
})

# item_json["sitelinks"] now contains:
# {
#   "enwiki": {
#     "site": "enwiki",
#     "title": "Example Article",
#     "badges": []
#   }
# }
```

## API Compatibility

The generated sitelinks structure is fully compatible with Wikidata's `wbeditentity` API:
- Included in item creation JSON
- Submitted in the same API call as labels/descriptions/claims
- No separate API endpoint needed for initial creation
- For updates, can use `wbsetsitelink` endpoint

## Backward Compatibility

- ✅ Fully backward compatible
- ✅ Existing mappings without sitelinks section continue to work
- ✅ Empty sitelinks object `{}` is valid and ignored by Wikidata API
- ✅ No breaking changes to existing functionality

## Next Steps for Users

1. **Add sitelinks to mapping files**: Update JSON with Wikipedia article field names
2. **Test with examples**: Run `sitelinks_example.py` to understand behavior
3. **Dry-run first**: Use notebook to preview transformations
4. **Verify titles**: Ensure article titles exactly match target wiki pages
5. **Test on test.wikidata.org**: Always test before production

## Files Modified

- [`gkc/bottler.py`](https://github.com/skybristol/gkc/blob/main/gkc/bottler.py) - Core transformation logic
- [`gkc/recipe.py`](https://github.com/skybristol/gkc/blob/main/gkc/recipe.py) - Auto-generation support
- `docs/sitelinks_usage.md` - Comprehensive documentation (new)
- `examples/sitelinks_example.py` - Working examples (new)
- `examples/csv_to_wikidata_dryrun.ipynb` - Interactive demo updates
- `examples/mappings/fed_tribe_from_missing_ak_tribes.json` - Example mapping
- `examples/README.md` - Documentation updates

## Benefits

1. **Automated Integration**: Connect Wikidata items to Wikipedia automatically
2. **Multi-language Support**: Link to multiple Wikipedia editions at once
3. **Data Quality**: Empty value handling prevents invalid submissions
4. **Flexibility**: Supports both data-driven and fixed title configurations
5. **Comprehensive**: Works with all Wikimedia projects, not just Wikipedia
6. **Well-documented**: Examples and documentation for all use cases
