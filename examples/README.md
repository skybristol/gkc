# GKC Examples

This directory contains example scripts demonstrating how to use the GKC package.

## Prerequisites

Before running the examples, you need to:

1. **Install the package:**
   ```bash
   pip install gkc
   # or for development:
   cd /path/to/gkc
   poetry install
   ```

2. **Set up bot passwords** (for Wikiverse examples):
   - Go to https://www.wikidata.org/wiki/Special:BotPasswords
   - Create a new bot password with appropriate permissions
   - Save your credentials

3. **Set environment variables:**
   ```bash
   export WIKIVERSE_USERNAME="YourUsername@YourBot"
   export WIKIVERSE_PASSWORD="your_bot_password"
   ```

## Examples

### wikidata_auth_example.py

Demonstrates WikiverseAuth functionality:
- Basic authentication to Wikidata
- Using custom MediaWiki instances
- Targeting different Wikimedia projects (Wikipedia, Commons)
- Getting CSRF tokens for edits
- Making authenticated API requests

**Run:**
```bash
python examples/wikidata_auth_example.py
```

### sitelinks_example.py

Demonstrates sitelinks configuration and usage:
- Configuring sitelinks in mapping files
- Linking items to Wikipedia articles (multiple languages)
- Linking to Wikimedia Commons categories
- Using fixed titles vs. data-driven titles
- Handling empty/missing values
- Using article badges (featured articles, etc.)

**Run:**
```bash
python examples/sitelinks_example.py
```

**Features:**
- Multiple Wikipedia language editions (enwiki, frwiki, etc.)
- Wikimedia Commons categories
- Article badges (featured articles, good articles)
- Automatic empty value handling
- Fixed and dynamic title sources

### sitelinks_validation_example.py

Shows how to validate Wikipedia and Wikimedia project pages before creating sitelinks.

**Why validation matters:** Wikidata rejects sitelinks to non-existent pages or redirects, which can cause item creation to fail. This example shows how to check pages before submission.

**Run:**
```bash
python examples/sitelinks_validation_example.py
```

**Features:**
- Check if individual Wikipedia pages exist
- Validate multiple sitelinks at once
- Filter out invalid sitelinks (non-existent or redirects)
- Integration with pandas DataFrame workflows
- Batch processing with validation
- Integration with PropertyMapper transformation

**Related Documentation:** [Sitelinks Validation Guide](../docs/sitelinks_validation.md)

### csv_to_wikidata_dryrun.ipynb

Interactive Jupyter notebook demonstrating the complete CSV-to-Wikidata workflow:
- Loading CSV data
- Building/customizing mapping configurations
- Transforming records to Wikidata JSON
- Dry-run mode for testing
- Batch processing
- Using sitelinks
- Date/time handling with automatic precision detection

**Run:**
```bash
jupyter notebook examples/csv_to_wikidata_dryrun.ipynb
```

### date_handling_test.py

Demonstrates date and time handling capabilities:
- Automatic precision detection (year, month, day)
- Various date input formats (2005, 2005-01, 2005-01-15)
- Explicit precision override
- Integration with qualifiers and references
- Current date special value

**Run:**
```bash
python examples/date_handling_test.py
```

## Notes

- The examples use environment variables for credentials to avoid hardcoding sensitive information
- Some examples may not fully execute without valid credentials, but they demonstrate the API usage
- For custom MediaWiki instances, replace URLs with your actual instance endpoints
