# Sitelinks Validation Implementation

## Overview

Added Wikipedia/Wikimedia sitelinks validation functionality to prevent item creation failures due to invalid sitelinks. Wikidata rejects sitelinks to non-existent pages or redirects, which can cause the entire item creation to fail.

## Implementation

### New Module: `gkc/sitelinks.py`

Created comprehensive sitelinks validation module with:

1. **`SitelinkValidator` class**
   - Validates Wikipedia and Wikimedia project pages via MediaWiki API
   - Supports all Wikimedia projects (Wikipedia, Commons, Wikispecies, etc.)
   - Handles redirects, non-existent pages, and API errors gracefully
   - Includes rate limiting and custom user agent support

2. **Convenience Functions**
   - `check_wikipedia_page(title, site_code, allow_redirects)` - Quick single page check
   - `validate_sitelink_dict(sitelinks)` - Validate and filter sitelinks dictionary

### Key Features

**MediaWiki API Integration:**
- Queries MediaWiki API to check page existence
- Detects redirects (page ID and redirect data)
- Handles API errors gracefully (timeouts, network issues)
- Returns detailed validation results with error messages

**Multi-Site Support:**
- Pre-configured endpoints for major wikis (enwiki, frwiki, dewiki, etc.)
- Auto-construction of API URLs for 300+ Wikipedia editions
- Support for Commons, Wikispecies, Wikisource, Wiktionary, etc.

**Workflow Integration:**
- Standalone validation before transformation
- Post-transformation filtering of invalid sitelinks
- Batch processing with progress tracking
- DataFrame integration for CSV workflows

**Rate Limiting:**
- Configurable delay between API requests
- Default 0.1s delay (Wikimedia API-friendly)
- Customizable timeout per request

## Usage Examples

### Quick Check
```python
from gkc import check_wikipedia_page

# Returns title if valid, None if invalid
result = check_wikipedia_page("Alaska", "enwiki")
if result:
    print(f"✓ Valid page: {result}")
```

### Detailed Validation
```python
from gkc import SitelinkValidator

validator = SitelinkValidator()
exists, message = validator.check_page_exists("Alaska", "enwiki")
if exists:
    print("✓ Valid")
else:
    print(f"✗ Invalid: {message}")
```

### Filter Sitelinks Dictionary
```python
from gkc import validate_sitelink_dict

# Sitelinks from transform_to_wikidata
sitelinks = {
    "enwiki": {"site": "enwiki", "title": "Alaska", "badges": []},
    "frwiki": {"site": "frwiki", "title": "Alaska", "badges": []}
}

# Keep only valid sitelinks
valid = validate_sitelink_dict(sitelinks)
```

### DataFrame Workflow
```python
import pandas as pd
from gkc import check_wikipedia_page

df = pd.read_csv("data.csv")

# Validate Wikipedia column
df["wikipedia_valid"] = df["wikipedia_en"].apply(
    lambda x: check_wikipedia_page(x, "enwiki")
)

# Keep only valid pages
df_clean = df[df["wikipedia_valid"].notna()]
```

## Updated Files

### Core Implementation
- **`gkc/sitelinks.py`** (new, ~260 lines)
  - `SitelinkValidator` class with full API integration
  - `check_wikipedia_page()` convenience function
  - `validate_sitelink_dict()` filter function

### Package Exports
- **`gkc/__init__.py`**
  - Added exports for `SitelinkValidator`, `check_wikipedia_page`, `validate_sitelink_dict`

### Documentation
- **`docs/sitelinks_validation.md`** (new, ~400 lines)
  - Complete API reference
  - Usage examples for all scenarios
  - Integration workflows
  - Error handling guide
  - Best practices

### Examples
- **`examples/sitelinks_validation_example.py`** (new, ~250 lines)
  - 6 comprehensive examples covering:
    - Single page checking
    - Multiple sitelink validation
    - Filtering sitelinks dictionaries
    - DataFrame workflow integration
    - Advanced validation settings
    - Distillate integration

- **`examples/README.md`**
  - Added sitelinks_validation_example.py section

### Notebook Integration
- **`examples/csv_to_wikidata_dryrun.ipynb`**
  - Updated Cell 5 to use `check_wikipedia_page()` from gkc
  - Replaced inline implementation with module import

## Testing

Created and ran comprehensive test suite verifying:
- ✓ Valid page detection (Python (programming language))
- ✓ Invalid page detection (non-existent pages)
- ✓ Empty title handling
- ✓ Redirect detection
- ✓ Multiple site validation (enwiki, frwiki)
- ✓ Sitelinks dictionary filtering
- ✓ Error message generation

All tests passed successfully.

## Benefits

1. **Prevents Item Creation Failures**
   - Catches invalid sitelinks before submission
   - Wikidata API no longer rejects items due to sitelink errors

2. **Data Quality**
   - Ensures Wikipedia pages actually exist
   - Filters out redirects that would be rejected
   - Validates page titles are exact

3. **Workflow Flexibility**
   - Use standalone in data prep
   - Integrate into transformation pipeline
   - Add to future validation systems

4. **Production Ready**
   - Comprehensive error handling
   - Rate limiting for large batches
   - Detailed validation messages
   - Works with all Wikimedia projects

## Next Steps

The validation module is now available for:
- Standalone CSV data cleaning workflows
- Integration into submission workflow validation (future)
- Pre-submission batch validation
- Custom validation pipelines

Users can now validate sitelinks at any stage:
1. **Before transformation** - Clean CSV data
2. **After transformation** - Filter Wikidata JSON
3. **During creation** - Future submission workflow integration
