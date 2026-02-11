# Sitelinks Validation

**Module:** `gkc.sitelinks`

The sitelinks validation module provides utilities for checking Wikipedia and Wikimedia project pages before attempting to create sitelinks on Wikidata items. This is important because **Wikidata will reject sitelinks to non-existent pages or redirect pages**, which can cause item creation to fail.

## Why Validate Sitelinks?

Wikidata's API has strict requirements for sitelinks:
- The page must exist on the target wiki
- The page cannot be a redirect (unless explicitly allowed)
- The page title must be exact (including capitalization and underscores)

If you try to create an item with invalid sitelinks, the entire item creation may fail. Validating sitelinks beforehand ensures your data will be accepted.

## Quick Start

### Check a Single Wikipedia Page

```python
from gkc import check_wikipedia_page

# Returns title if valid, None if invalid
result = check_wikipedia_page("Python (programming language)")
if result:
    print(f"✓ Valid page: {result}")
else:
    print("✗ Page does not exist or is a redirect")
```

### Validate Multiple Sitelinks

```python
from gkc import SitelinkValidator

validator = SitelinkValidator()

# Check if page exists
exists, message = validator.check_page_exists(
    "Alaska", 
    site_code="enwiki"
)

if exists:
    print("✓ Page is valid")
else:
    print(f"✗ {message}")
```

### Filter Sitelinks Dictionary

```python
from gkc import validate_sitelink_dict

# Sitelinks from transform_to_wikidata
sitelinks = {
    "enwiki": {"site": "enwiki", "title": "Alaska", "badges": []},
    "frwiki": {"site": "frwiki", "title": "Alaska", "badges": []},
}

# Keep only valid sitelinks
valid_sitelinks = validate_sitelink_dict(sitelinks)
print(f"Kept {len(valid_sitelinks)}/{len(sitelinks)} valid sitelinks")
```

## Core Functions

### `check_wikipedia_page(title, site_code, allow_redirects)`

Simple function to check if a single Wikipedia page exists.

**Parameters:**
- `title` (str): Page title to check
- `site_code` (str): Wikipedia site code (default: "enwiki")
  - `"enwiki"` - English Wikipedia
  - `"frwiki"` - French Wikipedia
  - `"dewiki"` - German Wikipedia
  - See full list of [Wikimedia site codes](https://www.wikidata.org/wiki/Help:Sitelinks)
- `allow_redirects` (bool): If False, reject redirect pages (default: False)

**Returns:**
- `str` - The title if page is valid
- `None` - If page doesn't exist or is invalid

**Example:**
```python
# Check English Wikipedia
result = check_wikipedia_page("Alaska", "enwiki")

# Check French Wikipedia
result = check_wikipedia_page("Alaska", "frwiki")

# Allow redirects
result = check_wikipedia_page("USA", "enwiki", allow_redirects=True)
```

### `validate_sitelink_dict(sitelinks)`

Convenience function to validate and filter a sitelinks dictionary.

**Parameters:**
- `sitelinks` (dict): Sitelinks dictionary from `transform_to_wikidata()`

**Returns:**
- `dict` - Filtered dictionary containing only valid sitelinks

**Example:**
```python
from gkc.item_creator import PropertyMapper
from gkc import validate_sitelink_dict

# Get sitelinks from transformation
mapper = PropertyMapper.from_file("mapping.json")
wikidata_json = mapper.transform_to_wikidata(record)
sitelinks = wikidata_json.get('sitelinks', {})

# Validate and filter
valid_sitelinks = validate_sitelink_dict(sitelinks)

# Update Wikidata JSON
wikidata_json['sitelinks'] = valid_sitelinks
```

## SitelinkValidator Class

The `SitelinkValidator` class provides full control over validation with detailed results.

### Initialization

```python
from gkc import SitelinkValidator

validator = SitelinkValidator(
    user_agent="MyBot/1.0 (https://example.com)",  # Custom user agent
    timeout=10  # HTTP request timeout in seconds
)
```

### Methods

#### `check_page_exists(title, site_code, allow_redirects)`

Check if a single page exists with detailed result.

**Returns:** `tuple[bool, Optional[str]]`
- `(True, None)` - Page exists and is valid
- `(False, "reason")` - Page is invalid with reason

**Example:**
```python
exists, message = validator.check_page_exists("Alaska", "enwiki")
if exists:
    print("✓ Valid page")
else:
    print(f"✗ Invalid: {message}")
```

#### `validate_sitelinks(sitelinks, delay_between_checks)`

Validate multiple sitelinks at once with rate limiting.

**Parameters:**
- `sitelinks` (dict): Sitelinks dictionary
- `delay_between_checks` (float): Delay in seconds between API requests (default: 0.1)

**Returns:** `dict[str, tuple[bool, Optional[str]]]`
- Dictionary mapping site codes to validation results

**Example:**
```python
sitelinks = {
    "enwiki": {"site": "enwiki", "title": "Alaska", "badges": []},
    "frwiki": {"site": "frwiki", "title": "Alaska", "badges": []},
}

results = validator.validate_sitelinks(sitelinks, delay_between_checks=0.2)

for site, (is_valid, message) in results.items():
    if is_valid:
        print(f"✓ {site}: valid")
    else:
        print(f"✗ {site}: {message}")
```

#### `filter_valid_sitelinks(sitelinks, verbose)`

Filter sitelinks and optionally print validation results.

**Parameters:**
- `sitelinks` (dict): Sitelinks to validate
- `verbose` (bool): If True, print validation results (default: False)

**Returns:** `dict` - Filtered valid sitelinks

**Example:**
```python
# With verbose output
valid = validator.filter_valid_sitelinks(sitelinks, verbose=True)
# Prints:
# ✓ enwiki: Alaska - valid
# ✗ frwiki: Alaska - Page does not exist
```

## Supported Sites

The validator supports all Wikimedia projects:

### Wikipedia
- `"enwiki"` - English
- `"frwiki"` - French
- `"dewiki"` - German
- `"eswiki"` - Spanish
- `"jawiki"` - Japanese
- And [300+ more language editions](https://meta.wikimedia.org/wiki/List_of_Wikipedias)

### Other Projects
- `"commonswiki"` - Wikimedia Commons
- `"specieswiki"` - Wikispecies
- `"{lang}wikisource"` - Wikisource editions
- `"{lang}wiktionary"` - Wiktionary editions
- `"{lang}wikivoyage"` - Wikivoyage editions
- `"{lang}wikiquote"` - Wikiquote editions

The validator automatically constructs the correct API endpoint for any valid site code.

## Integration Workflows

### Workflow 1: Validate CSV Data Before Transformation

```python
import pandas as pd
from gkc import check_wikipedia_page

# Load CSV
df = pd.read_csv("data.csv")

# Validate Wikipedia column
print("Validating Wikipedia pages...")
df['wikipedia_valid'] = df['wikipedia_en'].apply(
    lambda x: check_wikipedia_page(x, "enwiki")
)

# Filter to keep only valid pages
df_clean = df[df['wikipedia_valid'].notna()]
print(f"Kept {len(df_clean)}/{len(df)} records with valid Wikipedia pages")

# Continue with transformation
# ...
```

### Workflow 2: Validate After Transformation

```python
from gkc.item_creator import PropertyMapper
from gkc import validate_sitelink_dict

# Transform record
mapper = PropertyMapper.from_file("mapping.json")
wikidata_json = mapper.transform_to_wikidata(record)

# Extract and validate sitelinks
sitelinks = wikidata_json.get('sitelinks', {})
if sitelinks:
    print(f"Validating {len(sitelinks)} sitelinks...")
    valid_sitelinks = validate_sitelink_dict(sitelinks)
    wikidata_json['sitelinks'] = valid_sitelinks
    print(f"✓ Kept {len(valid_sitelinks)} valid sitelinks")

# Now safe to submit to Wikidata
```

### Workflow 3: Batch Processing with Progress

```python
from gkc import SitelinkValidator
import pandas as pd

df = pd.read_csv("data.csv")
validator = SitelinkValidator()

valid_records = []
for idx, record in df.iterrows():
    # Check Wikipedia page
    title = record.get('wikipedia_en')
    if title:
        exists, message = validator.check_page_exists(title, "enwiki")
        if exists:
            valid_records.append(record)
            print(f"✓ {idx+1}/{len(df)}: {title}")
        else:
            print(f"✗ {idx+1}/{len(df)}: {title} - {message}")
    
    if (idx + 1) % 10 == 0:
        print(f"Processed {idx+1}/{len(df)} records...")

df_valid = pd.DataFrame(valid_records)
print(f"\n✓ Kept {len(df_valid)}/{len(df)} records")
```

## Error Handling

The validator handles various error conditions gracefully:

```python
validator = SitelinkValidator()

# Empty title
exists, msg = validator.check_page_exists("", "enwiki")
# Returns: (False, "Empty title")

# Unknown site code
exists, msg = validator.check_page_exists("Test", "unknownwiki")
# Returns: (False, "Unknown site code: unknownwiki")

# Network timeout
validator = SitelinkValidator(timeout=1)  # Very short timeout
exists, msg = validator.check_page_exists("Test", "enwiki")
# May return: (False, "Timeout checking enwiki")

# All errors return (False, message) - never raise exceptions
```

## Rate Limiting

The validator includes built-in rate limiting to respect Wikimedia API guidelines:

```python
validator = SitelinkValidator()

# Default delay: 0.1 seconds between checks
results = validator.validate_sitelinks(sitelinks)

# Custom delay: 0.5 seconds
results = validator.validate_sitelinks(sitelinks, delay_between_checks=0.5)

# No delay (not recommended for large batches)
results = validator.validate_sitelinks(sitelinks, delay_between_checks=0)
```

**Best Practices:**
- Use at least 0.1 second delay for production
- For large batches (>100), consider 0.2-0.5 seconds
- Set a custom User-Agent identifying your bot/project

## Best Practices

1. **Validate Early**: Check Wikipedia pages before transformation if possible
2. **Use Batch Validation**: More efficient than individual checks
3. **Handle Redirects**: Decide if redirects are acceptable for your use case
4. **Rate Limit**: Respect Wikimedia API with appropriate delays
5. **Custom User Agent**: Identify your bot/project in API requests
6. **Log Results**: Keep track of which sitelinks were filtered and why
7. **Test First**: Try validation on small samples before processing large datasets

## Example: Complete Workflow

```python
import pandas as pd
from gkc import SitelinkValidator, WikiverseAuth
from gkc.item_creator import PropertyMapper, ItemCreator

# 1. Load and validate source data
df = pd.read_csv("tribes.csv")
validator = SitelinkValidator()

print("Validating Wikipedia pages...")
df['wiki_valid'] = df['wikipedia_en'].apply(
    lambda x: check_wikipedia_page(x, "enwiki") if pd.notna(x) else None
)

# 2. Transform to Wikidata JSON
mapper = PropertyMapper.from_file("mapping.json")
auth = WikiverseAuth()
creator = ItemCreator(auth=auth, mapper=mapper)

# 3. Process records with validation
for idx, record in df.iterrows():
    # Transform
    wikidata_json = mapper.transform_to_wikidata(record)
    
    # Validate sitelinks
    sitelinks = wikidata_json.get('sitelinks', {})
    if sitelinks:
        valid_sitelinks = validator.filter_valid_sitelinks(sitelinks, verbose=True)
        wikidata_json['sitelinks'] = valid_sitelinks
    
    # Create item (now safe from sitelink errors)
    try:
        qid = creator._submit_to_wikidata(wikidata_json)
        print(f"✓ Created {qid}")
    except Exception as e:
        print(f"✗ Failed: {e}")
```

## See Also

- [Sitelinks Usage Guide](sitelinks_usage.md) - How to configure sitelinks in mappings
- [Wikidata Sitelinks Help](https://www.wikidata.org/wiki/Help:Sitelinks)
- [Wikimedia Site Codes](https://www.wikidata.org/wiki/Help:Sitelinks#Site_links)
- [MediaWiki API Documentation](https://www.mediawiki.org/wiki/API:Main_page)
