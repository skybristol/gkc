# Authentication API

## Overview

The Authentication module provides unified credential management for Global Knowledge Commons services. Currently it supports Wikimedia projects (Wikidata, Wikipedia, Wikimedia Commons) using bot password authentication, with planned support for OpenStreetMap and other external services.

**Current implementations:** Wikimedia projects (Wikidata production, test instance, Wikipedia, Commons); OpenStreetMap auth framework  
**Future implementations:** OpenStreetMap API authentication, additional service integrations

## Quick Start

```python
from gkc import WikiverseAuth

# Authenticate to Wikidata using bot password
auth = WikiverseAuth(
    username="MyUsername@MyBot",
    password="abc123def456ghi789"
)
auth.login()
print(f"Logged in as: {auth.get_account_name()}")
```

## Classes

### AuthenticationError

::: gkc.auth.AuthenticationError
    options:
      show_root_heading: false
      heading_level: 4

### AuthBase

::: gkc.auth.AuthBase
    options:
      show_root_heading: false
      heading_level: 4

### WikiverseAuth

::: gkc.auth.WikiverseAuth
    options:
      show_root_heading: false
      heading_level: 4

### OpenStreetMapAuth

::: gkc.auth.OpenStreetMapAuth
    options:
      show_root_heading: false
      heading_level: 4

## Examples

### Authenticate to Wikidata using environment variables

This is the recommended approach for production workflows and CI/CD environments:

```python
from gkc import WikiverseAuth

# Set environment variables first:
# export WIKIVERSE_USERNAME="MyUsername@MyBot"
# export WIKIVERSE_PASSWORD="abc123def456ghi789"

auth = WikiverseAuth()
auth.login()
print(f"Successfully logged in to: {auth.api_url}")
```

### Authenticate to test.wikidata.org for testing

Use the new `wikidata_test` endpoint for development and testing:

```python
from gkc import WikiverseAuth

auth = WikiverseAuth(
    username="TestBot@BotAccount",
    password="test_password_123",
    api_url="wikidata_test"  # Points to test.wikidata.org/w/api.php
)

if auth.login():
    token = auth.get_csrf_token()
    # Use token for test edits
    print(f"Got CSRF token for test edits")
```

### Switch between Wikimedia projects

The same bot password credentials work across all Wikimedia projects thanks to Single User Login (SUL):

```python
from gkc import WikiverseAuth

# Create auth once with default Wikidata endpoint
auth = WikiverseAuth(
    username="MyUsername@MyBot",
    password="abc123def456ghi789"
)
auth.login()

# Later, query Wikipedia instead
auth.api_url = "https://en.wikipedia.org/w/api.php"
# The session is already authenticated for all Wikimedia projects

# Or use shortcuts for common projects
from gkc.auth import DEFAULT_WIKIMEDIA_APIS
auth.api_url = DEFAULT_WIKIMEDIA_APIS["commons"]  # Wikimedia Commons
```

### Use authentication session for API requests

The authenticated session can be used directly for making API calls:

```python
from gkc import WikiverseAuth

auth = WikiverseAuth(
    username="MyUsername@MyBot",
    password="abc123def456ghi789",
    api_url="wikidata"
)
auth.login()

# Use the authenticated session for queries
response = auth.session.get(auth.api_url, params={
    "action": "query",
    "meta": "userinfo",
    "format": "json"
})

userinfo = response.json()
print(f"Logged in as: {userinfo['query']['userinfo']['name']}")
```

### Extract account and bot names

Parse bot password format to extract components:

```python
from gkc import WikiverseAuth

auth = WikiverseAuth(username="Alice@MyBot")

# Before login - still able to parse username
account_name = auth.get_account_name()  # "Alice"
bot_name = auth.get_bot_name()          # "MyBot"

print(f"Account: {account_name}, Bot: {bot_name}")

# Credentials can be provided via environment or password prompt
auth.login()
token = auth.get_csrf_token()
```

## Error Handling

### Missing credentials

```python
from gkc import WikiverseAuth, AuthenticationError

auth = WikiverseAuth()  # No credentials provided
try:
    auth.login()
except AuthenticationError as e:
    print(f"Login failed: {e}")
    # Output: Login failed: Cannot login: credentials not provided...
```

### Invalid bot password credentials

```python
from gkc import WikiverseAuth, AuthenticationError

auth = WikiverseAuth(
    username="Alice@BadBot",
    password="wrong_password"
)

try:
    auth.login()
except AuthenticationError as e:
    print(f"Authentication error: {e}")
    # Output will describe the specific failure reason
```

### Network errors

```python
from gkc import WikiverseAuth, AuthenticationError

# Invalid API URL
auth = WikiverseAuth(
    username="Alice@MyBot",
    password="secret",
    api_url="https://invalid-wiki-site.example.com/w/api.php"
)

try:
    auth.login()
except AuthenticationError as e:
    print(f"Network error: {e}")
    # Output: Network error during login to https://invalid-wiki-site.example.com/w/api.php: ...
```

### Missing CSRF token (not logged in)

```python
from gkc import WikiverseAuth, AuthenticationError

auth = WikiverseAuth(username="Alice@MyBot", password="secret")
# Forgot to login first!

try:
    token = auth.get_csrf_token()
except AuthenticationError as e:
    print(f"Error: {e}")
    # Output: Error: Not logged in. Call login() first before getting CSRF token.
```

## Available Endpoints

The auth module includes shortcuts for common Wikimedia instances:

| Shortcut | Full URL |
|----------|----------|
| `wikidata` | `https://www.wikidata.org/w/api.php` |
| `wikidata_test` | `https://test.wikidata.org/w/api.php` |
| `wikipedia` | `https://en.wikipedia.org/w/api.php` |
| `commons` | `https://commons.wikimedia.org/w/api.php` |

Custom MediaWiki instances can be used by providing the full API URL.

## See Also

- [Authentication Guide](../authentication.md) - Conceptual overview and setup instructions
- [SPARQL API](sparql.md) - Query Wikidata and other SPARQL endpoints
