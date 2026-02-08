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

## Notes

- The examples use environment variables for credentials to avoid hardcoding sensitive information
- Some examples may not fully execute without valid credentials, but they demonstrate the API usage
- For custom MediaWiki instances, replace URLs with your actual instance endpoints
