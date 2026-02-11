# Date and Time Handling in GKC

GKC provides intelligent date/time handling that automatically detects precision and formats dates according to Wikidata's requirements.

## Overview

Wikidata's time datatype includes a **precision** field that indicates the granularity of the date:

| Precision | Meaning | Format Example | Use Case |
|-----------|---------|----------------|----------|
| 9 | Year | `+2005-00-00T00:00:00Z` | Birth year unknown, only decade known |
| 10 | Month | `+2005-01-00T00:00:00Z` | Event occurred in January 2005 |
| 11 | Day | `+2005-01-15T00:00:00Z` | Specific date known |

## Automatic Precision Detection

GKC automatically detects the appropriate precision based on the input format:

```python
from gkc.item_creator import DataTypeTransformer

transformer = DataTypeTransformer()

# Year only → precision 9
result = transformer.to_time("2005")
# Result: +2005-00-00T00:00:00Z (precision: 9)

# Year-month → precision 10  
result = transformer.to_time("2005-01")
# Result: +2005-01-00T00:00:00Z (precision: 10)

# Full date → precision 11
result = transformer.to_time("2005-01-15")
# Result: +2005-01-15T00:00:00Z (precision: 11)

# Integer year also works
result = transformer.to_time(2005)
# Result: +2005-00-00T00:00:00Z (precision: 9)
```

## Usage in Mapping Files

### Claims with Time Values

```json
{
  "property": "P571",
  "source_field": "inception_date",
  "datatype": "time",
  "comment": "Inception date - format: YYYY, YYYY-MM, or YYYY-MM-DD"
}
```

### Qualifiers with Time Values

```json
{
  "property": "P2124",
  "source_field": "member_count",
  "datatype": "quantity",
  "qualifiers": [
    {
      "property": "P585",
      "value": "2005",
      "datatype": "time",
      "comment": "Point in time - just the year"
    }
  ]
}
```

### References with Time Values

```json
{
  "property": "P854",
  "value": "https://example.com/source",
  "datatype": "url"
},
{
  "property": "P813",
  "value": "2024-02-11",
  "datatype": "time",
  "comment": "Retrieved date"
}
```

## Explicit Precision Control

You can override automatic detection by specifying precision in the transform config:

```json
{
  "property": "P569",
  "source_field": "birth_date",
  "datatype": "time",
  "transform": {
    "precision": 9,
    "comment": "Force year precision even if full date provided"
  }
}
```

## Special Values

### Current Date

Use the special value `"current_date"` to automatically insert today's date:

```json
{
  "property": "P813",
  "value": "current_date",
  "datatype": "time",
  "comment": "Retrieved date - automatically set to today"
}
```

This works in qualifiers and references:

```json
{
  "references": [
    {
      "property": "P854",
      "source_field": "source_url",
      "datatype": "url"
    },
    {
      "property": "P813",
      "value": "current_date",
      "datatype": "time"
    }
  ]
}
```

## Examples by Use Case

### Birth/Death Dates (Often Only Year Known)

```json
{
  "property": "P569",
  "source_field": "birth_year",
  "datatype": "time",
  "comment": "date of birth - source has year only"
}
```

Source data: `{"birth_year": "1950"}`  
Result: `+1950-00-00T00:00:00Z` (precision: 9)

### Publication Dates (Often Month-Year)

```json
{
  "property": "P577",
  "source_field": "publication_date",
  "datatype": "time",
  "comment": "publication date - format: YYYY-MM"
}
```

Source data: `{"publication_date": "2005-03"}`  
Result: `+2005-03-00T00:00:00Z` (precision: 10)

### Event Dates (Specific Day)

```json
{
  "property": "P585",
  "source_field": "event_date",
  "datatype": "time",
  "comment": "point in time - full date"
}
```

Source data: `{"event_date": "2005-01-15"}`  
Result: `+2005-01-15T00:00:00Z` (precision: 11)

### Member Counts with Point in Time

```json
{
  "property": "P2124",
  "source_field": "member_count",
  "datatype": "quantity",
  "qualifiers": [
    {
      "property": "P585",
      "value": "2005",
      "datatype": "time"
    }
  ]
}
```

Result qualifier: `+2005-00-00T00:00:00Z` (precision: 9)

## Data Source Formats

GKC accepts various input formats from your CSV/JSON data:

| Input Format | Detected Precision | Output Format |
|--------------|-------------------|---------------|
| `2005` (string) | 9 (year) | `+2005-00-00T00:00:00Z` |
| `2005` (integer) | 9 (year) | `+2005-00-00T00:00:00Z` |
| `"2005-01"` | 10 (month) | `+2005-01-00T00:00:00Z` |
| `"2005-01-15"` | 11 (day) | `+2005-01-15T00:00:00Z` |
| `"2005-01-01"` | 11 (day) | `+2005-01-01T00:00:00Z` |

## Complete Example

```python
from gkc.item_creator import PropertyMapper

mapping_config = {
    "version": "1.0",
    "mappings": {
        "labels": [
            {"source_field": "name", "language": "en", "required": True}
        ],
        "claims": [
            {
                "property": "P2124",
                "source_field": "member_count_2005",
                "datatype": "quantity",
                "transform": {"type": "number_to_quantity", "unit": "1"},
                "qualifiers": [
                    {
                        "property": "P585",
                        "value": "2005",
                        "datatype": "time",
                        "comment": "Point in time for member count"
                    }
                ],
                "references": [
                    {
                        "property": "P854",
                        "value": "https://example.com/report.pdf",
                        "datatype": "url"
                    },
                    {
                        "property": "P813",
                        "value": "current_date",
                        "datatype": "time",
                        "comment": "Retrieved date"
                    }
                ]
            }
        ]
    }
}

mapper = PropertyMapper(mapping_config)

source_record = {
    "name": "Example Organization",
    "member_count_2005": 1500
}

item_json = mapper.transform_to_wikidata(source_record)
```

Result:
```json
{
  "claims": {
    "P2124": [{
      "mainsnak": {
        "datavalue": {
          "value": {"amount": "+1500", "unit": "1"},
          "type": "quantity"
        }
      },
      "qualifiers": {
        "P585": [{
          "datavalue": {
            "value": {
              "time": "+2005-00-00T00:00:00Z",
              "precision": 9
            },
            "type": "time"
          }
        }]
      },
      "references": [{
        "snaks": {
          "P854": [{"datavalue": {"value": "https://example.com/report.pdf"}}],
          "P813": [{"datavalue": {
            "value": {"time": "+2024-02-11T00:00:00Z", "precision": 11}
          }}]
        }
      }]
    }]
  }
}
```

## Calendar Models

By default, GKC uses the Gregorian calendar (`Q1985727`). For historical dates before 1582, you may want to specify the Julian calendar:

```json
{
  "property": "P569",
  "source_field": "birth_date",
  "datatype": "time",
  "transform": {
    "calendar": "Q1985786",
    "comment": "Julian calendar for dates before 1582"
  }
}
```

Common calendar models:
- **Q1985727**: Proleptic Gregorian calendar (default)
- **Q1985786**: Proleptic Julian calendar

## Best Practices

1. **Use appropriate precision**: Don't claim day precision when you only know the year
2. **Store dates as reported**: If your source says "2005", use year precision
3. **Document precision**: Add comments explaining why certain precision is used
4. **Test with your data**: Run dry-run transformations to verify date formatting
5. **Handle missing dates**: Mark optional with `"required": false`

## Common Patterns

### Pattern 1: Year-only dates from CSV

```python
# CSV has: year_founded,1995
# Mapping:
{
  "property": "P571",
  "source_field": "year_founded",
  "datatype": "time"
}
# Result: +1995-00-00T00:00:00Z (precision: 9)
```

### Pattern 2: Full dates from ISO strings

```python
# CSV has: event_date,2005-06-15
# Mapping:
{
  "property": "P585",
  "source_field": "event_date",
  "datatype": "time"
}
# Result: +2005-06-15T00:00:00Z (precision: 11)
```

### Pattern 3: Fixed year in qualifier

```python
# All records share the same reference year
# Mapping:
{
  "qualifiers": [
    {
      "property": "P585",
      "value": "2005",
      "datatype": "time"
    }
  ]
}
# Result: +2005-00-00T00:00:00Z (precision: 9)
```

## Troubleshooting

### Issue: Wrong precision detected

**Problem**: Date "2005-01-01" gets precision 11 (day) but should be year.

**Solution**: Explicitly set precision:
```json
{
  "datatype": "time",
  "transform": {"precision": 9}
}
```

### Issue: Date format not recognized

**Problem**: Custom date format like "Jan 2005" not parsed.

**Solution**: Pre-process dates to ISO format (YYYY, YYYY-MM, or YYYY-MM-DD) before transformation. Use pandas or Python's datetime in your data pipeline.

### Issue: Current date not updating

**Problem**: `"current_date"` shows old date.

**Solution**: `"current_date"` is evaluated at transformation time. If using cached/saved transformations, regenerate them.

## See Also

- [Wikidata Help:Dates](https://www.wikidata.org/wiki/Help:Dates)
- [Wikidata Datamodel JSON - Time](https://www.mediawiki.org/wiki/Wikibase/DataModel/JSON#time)
- [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) date format standard
