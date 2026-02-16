# Sitelinks Support in GKC

Sitelinks connect Wikidata items to corresponding articles on Wikipedia and other Wikimedia projects. The GKC mapping system now supports automatic sitelink creation from your source data.

## Overview

Sitelinks are part of the Wikidata item JSON structure and appear alongside labels, descriptions, aliases, and claims:

```json
{
  "labels": {...},
  "descriptions": {...},
  "aliases": {...},
  "claims": {...},
  "sitelinks": {
    "enwiki": {
      "site": "enwiki",
      "title": "Example Article",
      "badges": []
    }
  }
}
```

## Mapping Configuration

Add a `sitelinks` section to your mapping configuration:

```json
{
  "mappings": {
    "labels": [...],
    "aliases": [...],
    "descriptions": [...],
    "sitelinks": [
      {
        "site": "enwiki",
        "source_field": "wikipedia_en_title",
        "required": false,
        "badges": [],
        "comment": "English Wikipedia article"
      }
    ],
    "claims": [...]
  }
}
```

## Configuration Options

### Required Fields

- **site**: The site identifier (e.g., `"enwiki"`, `"frwiki"`, `"commonswiki"`)

### Title Source (choose one)

- **source_field**: Pull the article title from your CSV/source data
- **title**: Use a fixed title value

### Optional Fields

- **required** (default: `false`): Raise an error if the field is missing or empty
- **badges** (default: `[]`): Array of badge QIDs (e.g., `["Q17437798"]` for featured article)
- **comment**: Documentation for your reference

## Common Site Codes

### Wikipedia
- English: `enwiki`
- French: `frwiki`
- German: `dewiki`
- Spanish: `eswiki`
- Japanese: `jawiki`
- See all: https://en.wikipedia.org/wiki/List_of_Wikipedias

### Other Wikimedia Projects
- **Wikimedia Commons**: `commonswiki`
- **Wikispecies**: `specieswiki`
- **Wikisource**: `enwikisource`, `frwikisource`, etc.
- **Wikivoyage**: `enwikivoyage`, `frwikivoyage`, etc.
- **Wiktionary**: `enwiktionary`, `frwiktionary`, etc.

Full list: https://www.wikidata.org/w/api.php?action=help&modules=wbsetsitelink

## Examples

### Example 1: Wikipedia Article from CSV Data

```json
{
  "sitelinks": [
    {
      "site": "enwiki",
      "source_field": "wikipedia_title",
      "required": false
    }
  ]
}
```

With source data:
```json
{
  "name": "Example Organization",
  "wikipedia_title": "Example Organization"
}
```

Results in:
```json
{
  "sitelinks": {
    "enwiki": {
      "site": "enwiki",
      "title": "Example Organization",
      "badges": []
    }
  }
}
```

### Example 2: Multiple Language Editions

```json
{
  "sitelinks": [
    {
      "site": "enwiki",
      "source_field": "wikipedia_en",
      "comment": "English Wikipedia"
    },
    {
      "site": "frwiki",
      "source_field": "wikipedia_fr",
      "comment": "French Wikipedia"
    },
    {
      "site": "dewiki",
      "source_field": "wikipedia_de",
      "comment": "German Wikipedia"
    }
  ]
}
```

### Example 3: Fixed Title for Commons Category

```json
{
  "sitelinks": [
    {
      "site": "commonswiki",
      "title": "Category:Example Topic",
      "comment": "Wikimedia Commons category"
    }
  ]
}
```

### Example 4: With Badges

```json
{
  "sitelinks": [
    {
      "site": "enwiki",
      "source_field": "wikipedia_en",
      "badges": ["Q17437798"],
      "comment": "Featured article on English Wikipedia"
    }
  ]
}
```

## Badge QIDs

Common article/page badges:
- **Q17437798**: Featured article
- **Q17437796**: Good article
- **Q17559452**: Featured list
- **Q17580674**: Featured portal

See full list: https://www.wikidata.org/wiki/Help:Badges

## Handling Empty Values

The sitelinks processor automatically:
- Skips empty strings
- Skips `NaN` or `None` values
- Skips fields not present in source data (unless `required: true`)
- Trims whitespace from titles

## Usage in Code

```python
from gkc.bottler import Distillate

# Load mapping with sitelinks
distillate = Distillate.from_file("mapping.json")

# Transform source record
source_record = {
    "name": "Example Item",
    "wikipedia_title": "Example Item"
}

item_json = distillate.transform_to_wikidata(source_record)

# item_json now includes:
# {
#   "labels": {...},
#   "sitelinks": {
#     "enwiki": {
#       "site": "enwiki",
#       "title": "Example Item",
#       "badges": []
#     }
#   },
#   ...
# }
```

## API Notes

When submitting to Wikidata:
- Sitelinks are included in the `wbeditentity` API call
- The title must exactly match the target article name
- Spaces and special characters are automatically handled
- Each item can only link to one page per site
- Attempting to link to a page already linked to another item will fail

## Validation

Before submitting to Wikidata:
1. Verify article titles exist on the target site
2. Ensure articles aren't already linked to other items
3. Use proper capitalization (most wikis are case-sensitive after first character)
4. Test on test.wikidata.org first

## Auto-Generation

When using `RecipeBuilder`, sitelinks configuration is automatically added:

```python
from gkc import RecipeBuilder
from gkc.bottler import Distillate

builder = RecipeBuilder(eid="E502")
distillate = Distillate.from_recipe(builder, entity_type="Q7840353")

# Generated mapping includes stub sitelinks section
# Edit source_field values to match your data
```

## Troubleshooting

### Title Not Found
Ensure the article exists and the title exactly matches. Use underscores or spaces (both work).

### Already Linked
The article is already linked to another Wikidata item. You may need to merge items or choose a different article.

### Invalid Site Code
Verify the site code at: https://www.wikidata.org/w/api.php?action=help&modules=wbsetsitelink

### Empty/Missing Fields
Check your CSV data. Use pandas to inspect: `df['wikipedia_title'].isna().sum()`
