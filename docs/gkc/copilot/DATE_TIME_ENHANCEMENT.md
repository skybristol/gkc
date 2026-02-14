# Date/Time Handling Enhancement Summary

## Problem

The mapper was not properly handling date values with varying precisions. When a value like "2005" was provided for a point-in-time qualifier (P585), the system was not correctly formatting it according to Wikidata's requirements or setting the appropriate precision value.

According to Wikidata documentation:
- **Precision 9** (year): `+2005-00-00T00:00:00Z`
- **Precision 10** (month): `+2005-01-00T00:00:00Z`
- **Precision 11** (day): `+2005-01-15T00:00:00Z`

## Solution

Enhanced the `DataTypeTransformer.to_time()` method to:

1. **Auto-detect precision** based on input format:
   - `"2005"` or `2005` → precision 9 (year)
   - `"2005-01"` → precision 10 (month)
   - `"2005-01-15"` → precision 11 (day)

2. **Format dates correctly** for each precision:
   - Year precision uses `-00-00` for month/day
   - Month precision uses `-00` for day
   - Day precision uses full date

3. **Support explicit precision override** via transform config

4. **Handle multiple input types**: strings, integers, ISO dates

## Changes Made

### 1. Enhanced `DataTypeTransformer.to_time()` ([gkc/item_creator.py](https://github.com/skybristol/gkc/blob/main/gkc/item_creator.py#L41-L107))

**Before:**
```python
def to_time(date_str: str, precision: int = 11, calendar: str = "Q1985727") -> dict:
    return {
        "value": {
            "time": f"+{date_str}T00:00:00Z",  # Wrong format for year precision
            "precision": precision,
            ...
        }
    }
```

**After:**
```python
def to_time(date_input: str | int, precision: int | None = None, calendar: str = "Q1985727") -> dict:
    date_str = str(date_input).strip()
    
    if precision is None:
        # Auto-detect precision from format
        if "-" not in date_str:
            precision = 9  # Year only
            time_str = f"+{date_str.zfill(4)}-00-00T00:00:00Z"
        elif len(parts) == 2:
            precision = 10  # Year-month
            time_str = f"+{year}-{month}-00T00:00:00Z"
        elif len(parts) == 3:
            precision = 11  # Full date
            time_str = f"+{year}-{month}-{day}T00:00:00Z"
    # ... handle explicit precision
```

### 2. Updated `SnakBuilder.create_snak()` ([gkc/item_creator.py](https://github.com/skybristol/gkc/blob/main/gkc/item_creator.py#L118-L147))

**Before:**
```python
elif datatype == "time":
    precision = transform_config.get("precision", 11) if transform_config else 11
    datavalue = self.transformer.to_time(value, precision)
```

**After:**
```python
elif datatype == "time":
    # Get precision from transform_config or auto-detect
    precision = None
    if transform_config:
        precision = transform_config.get("precision")
    datavalue = self.transformer.to_time(value, precision)
```

### 3. Enhanced Qualifier Resolution ([gkc/item_creator.py](https://github.com/skybristol/gkc/blob/main/gkc/item_creator.py#L531-L565))

Added support for:
- `"current_date"` special value (auto-inserts today's date)
- Static `"value"` field in qualifiers (previously only supported `"source_field"`)

**Before:**
```python
qual_field = qual_config.get("source_field")
if qual_field and qual_field in source_record:
    # Only handled source_field
```

**After:**
```python
qual_field = qual_config.get("source_field")
if qual_field:
    if qual_field == "current_date":
        value = datetime.now().strftime("%Y-%m-%d")
    elif qual_field in source_record:
        value = source_record[qual_field]
    else:
        continue
elif "value" in qual_config:
    # Now handles static values too
    value = qual_config["value"]
```

## Files Modified

- [`gkc/item_creator.py`](https://github.com/skybristol/gkc/blob/main/gkc/item_creator.py) - Core transformation logic
- [Date/Time Handling](../date_time_handling.md) - Comprehensive documentation
- `examples/date_handling_test.py` - Test suite (new)
- `examples/README.md` - Updated with date handling example

## Testing

Created comprehensive test suite (`examples/date_handling_test.py`) verifying:

✅ Year-only input: `"2005"` → `+2005-00-00T00:00:00Z` (precision 9)  
✅ Integer input: `2005` → `+2005-00-00T00:00:00Z` (precision 9)  
✅ Year-month: `"2005-01"` → `+2005-01-00T00:00:00Z` (precision 10)  
✅ Full date: `"2005-01-15"` → `+2005-01-15T00:00:00Z` (precision 11)  
✅ Explicit precision override works correctly  
✅ Integration with PropertyMapper and qualifiers  
✅ Multiple date formats in mapping configurations  

## Usage Examples

### Example 1: Year-only qualifier (from user's mapping)

```json
{
  "property": "P2124",
  "source_field": "member_count_2005",
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

**Result:**
```json
{
  "qualifiers": {
    "P585": [{
      "datavalue": {
        "value": {
          "time": "+2005-00-00T00:00:00Z",
          "precision": 9,
          "timezone": 0,
          "before": 0,
          "after": 0,
          "calendarmodel": "http://www.wikidata.org/entity/Q1985727"
        },
        "type": "time"
      }
    }]
  }
}
```

### Example 2: Current date in references

```json
{
  "references": [
    {
      "property": "P813",
      "value": "current_date",
      "datatype": "time",
      "comment": "Retrieved date"
    }
  ]
}
```

Automatically sets to today's date with day precision.

### Example 3: Month-precision from source data

```python
source_record = {"publication_date": "2005-03"}

# Automatically detects month precision
# Result: +2005-03-00T00:00:00Z (precision 10)
```

## Wikidata Compliance

The implementation follows Wikidata's official specifications:

- ✅ Time format matches ISO 8601 with Wikidata extensions
- ✅ Precision values correctly set (9=year, 10=month, 11=day)
- ✅ Uses `-00` padding for unknown month/day components
- ✅ Default to Gregorian calendar (Q1985727)
- ✅ Timezone always set to 0 (UTC)
- ✅ before/after values set to 0 (standard practice)

References:
- https://www.wikidata.org/wiki/Help:Dates
- https://www.mediawiki.org/wiki/Wikibase/DataModel/JSON#time

## Migration Notes

**Backward Compatibility:** ✅ Fully backward compatible

- Existing mappings with explicit `"precision"` in transform config continue to work
- Mappings without precision now benefit from auto-detection
- No breaking changes to API or data structures

**Recommended Actions:**
1. Remove explicit `"precision": 11` from mappings where auto-detection is appropriate
2. Add `"precision"` only when you need to override (e.g., force year precision for "2005-01-01")
3. Review mappings using year-only dates to ensure they're formatted correctly

## Benefits

1. **Automatic precision detection** - No need to manually specify precision for most cases
2. **Flexible input** - Accepts strings, integers, partial dates, full ISO dates
3. **Correct formatting** - Properly formats dates with `-00` padding for unknown components
4. **Better data quality** - Matches Wikidata's standards for different precision levels
5. **Reduced configuration** - Less boilerplate in mapping files
6. **Special values** - Supports `"current_date"` for dynamic date insertion

## Next Steps for Users

1. **Test with your data**: Run transformations in dry-run mode to verify date formatting
2. **Update mapping files**: Remove unnecessary explicit precision settings
3. **Review year-only dates**: Ensure fields with just years (like "2005") are formatting correctly
4. **Add retrieval dates**: Use `"current_date"` for P813 (retrieved date) references
5. **Check documentation**: See [Date/Time Handling](../date_time_handling.md) for comprehensive examples
