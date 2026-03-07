# Authentication Guide

The GKC package provides authentication classes for Global Knowledge Commons services. You can provide credentials directly, via environment variables, or through interactive prompts.

For detailed API documentation and examples, see the [Authentication API Reference](api/auth.md).

## Wikiverse (Wikidata, Wikipedia, Wikimedia Commons)

The `WikiverseAuth` class provides unified authentication for all Wikimedia projects using **bot passwords**. The same credentials work across Wikidata, Wikipedia, and Wikimedia Commons due to Wikimedia's Single User Login (SUL) system.

The `WikiverseAuth` class can also target a custom MediaWiki-compatible API URL, but credential behavior depends on the platform you are targeting.

### Setting up Bot Passwords

1. Go to [Special:BotPasswords](https://www.wikidata.org/wiki/Special:BotPasswords) on Wikidata
2. Create a new bot password with appropriate permissions
3. Your username will be in the format `YourUsername@BotName`
4. Save the generated password (you won't see it again!)

### Basic Usage

```python
from gkc import WikiverseAuth, AuthenticationError

# Method 1: Using environment variables (recommended)
auth = WikiverseAuth()
auth.login()

# Method 2: Using explicit credentials
auth = WikiverseAuth(
    username="YourUsername@BotName",
    password="abc123def456ghi789"
)
auth.login()

# Method 3: Interactive prompt
auth = WikiverseAuth(interactive=True)
auth.login()

# Check login status
if auth.is_logged_in():
    print(f"Logged in as: {auth.get_account_name()}")
    print(f"Bot name: {auth.get_bot_name()}")
```

### Targeting Different Wikimedia Projects

```python
# Wikidata (default)
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="wikidata"  # or just omit for default
)
auth.login()

# Wikidata Test Instance (for testing and development)
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="wikidata_test"  # Points to test.wikidata.org
)
auth.login()

# English Wikipedia
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="wikipedia"
)
auth.login()

# Wikimedia Commons
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="commons"
)
auth.login()

# Custom MediaWiki instance (e.g., enterprise wiki)
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="https://wiki.mycompany.com/w/api.php"
)
auth.login()
```

## Data Distillery Wikibase (wikibase.cloud)

Data Distillery is **not** part of Wikimedia SUL. Treat it as a separate platform with its own account and password management.

Use a dedicated Data Distillery service account (or user account) and do not assume Wikimedia bot passwords will work there.

Note: the class name `WikiverseAuth` is historical; in practice it is used as a MediaWiki-compatible auth client when you supply an explicit `api_url`.

### Python Usage

```python
from gkc import WikiverseAuth, AuthenticationError

auth = WikiverseAuth(
    username="YourDDUsername",
    password="your-dd-password",
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
)

try:
    auth.login()
    print("Logged in to Data Distillery Wikibase")
except AuthenticationError as exc:
    print(f"Login failed: {exc}")
```

### CLI Usage (`gkc wikibase audit`)

`gkc wikibase audit` reads Data Distillery settings from `DD_WB_*` variables.

- `DD_WB_API_URL`
- `DD_WB_USERNAME`
- `DD_WB_PASSWORD`
- `DD_WB_SPARQL_ENDPOINT` (for SPARQL-based operations)

Authentication in audit mode is optional by default:

- If credentials work, audit runs authenticated.
- If login fails, audit continues anonymously and reports a warning.
- Use `--require-auth` to fail fast on login errors.

## Making Authenticated API Requests

```python
# After login, use the session for API requests
auth = WikiverseAuth(
    username="YourDDUsername",
    password="your-dd-password",
    api_url="https://datadistillery.wikibase.cloud/w/api.php",
)
auth.login()

# Example: Query user information
response = auth.session.get(auth.api_url, params={
    "action": "query",
    "meta": "userinfo",
    "format": "json"
})
print(response.json())

# For editing, get a CSRF token
try:
    csrf_token = auth.get_csrf_token()
    print(f"CSRF Token: {csrf_token}")
except AuthenticationError as e:
    print(f"Error: {e}")

# When done, logout
auth.logout()
```

## Wikimedia Bot Username Helpers

These helper methods are most useful for Wikimedia bot-password usernames in `Username@BotName` format.

```python
auth = WikiverseAuth(username="Alice@MyBot", password="secret")

# Extract account name
print(auth.get_account_name())  # Output: "Alice"

# Extract bot name
print(auth.get_bot_name())  # Output: "MyBot"

# Check authentication state
print(auth.is_authenticated())  # Has credentials
print(auth.is_logged_in())      # Successfully logged in to API
```

## OpenStreetMap

```python
from gkc import OpenStreetMapAuth

# Method 1: Using explicit credentials
auth = OpenStreetMapAuth(username="your_username", password="your_password")

# Method 2: Using environment variables (OPENSTREETMAP_USERNAME, OPENSTREETMAP_PASSWORD)
auth = OpenStreetMapAuth()

# Method 3: Interactive prompt
auth = OpenStreetMapAuth(interactive=True)

# Check authentication status
if auth.is_authenticated():
    print("Authenticated successfully!")
```

## Environment Variables

You can set the following environment variables for automatic authentication:

### Wikimedia Projects

- `WIKIVERSE_USERNAME` - Bot password username (format: Username@BotName)
- `WIKIVERSE_PASSWORD` - Bot password
- `WIKIVERSE_API_URL` - (Optional) MediaWiki API endpoint. Defaults to Wikidata. Can use shortcuts: "wikidata", "wikidata_test", "wikipedia", "commons"

### Data Distillery Wikibase

- `DD_WB_API_URL` - Data Distillery API URL (for example `https://datadistillery.wikibase.cloud/w/api.php`)
- `DD_WB_USERNAME` - Data Distillery account username
- `DD_WB_PASSWORD` - Data Distillery account password
- `DD_WB_SPARQL_ENDPOINT` - SPARQL endpoint for Data Distillery profile lookup hydration and related query operations

`DD_WB_*` variables are used for Data Distillery flows (for example `gkc wikibase audit`) and are intentionally separate from `WIKIVERSE_*`.

### OpenStreetMap

- `OPENSTREETMAP_USERNAME` - OpenStreetMap username
- `OPENSTREETMAP_PASSWORD` - OpenStreetMap password

### Example Configuration

```bash
# Wikidata (default)
export WIKIVERSE_USERNAME="Alice@MyBot"
export WIKIVERSE_PASSWORD="abc123def456ghi789"

# Wikidata Test Instance (for development and testing)
export WIKIVERSE_USERNAME="Alice@MyBot"
export WIKIVERSE_PASSWORD="abc123def456ghi789"
export WIKIVERSE_API_URL="wikidata_test"

# Wikipedia
export WIKIVERSE_USERNAME="Alice@MyBot"
export WIKIVERSE_PASSWORD="abc123def456ghi789"
export WIKIVERSE_API_URL="wikipedia"

# Custom MediaWiki instance
export WIKIVERSE_USERNAME="Alice@MyBot"
export WIKIVERSE_PASSWORD="abc123def456ghi789"
export WIKIVERSE_API_URL="https://wiki.mycompany.com/w/api.php"

# Data Distillery Wikibase
export DD_WB_API_URL="https://datadistillery.wikibase.cloud/w/api.php"
export DD_WB_USERNAME="my_dd_account"
export DD_WB_PASSWORD="my_dd_password"
export DD_WB_SPARQL_ENDPOINT="https://datadistillery.wikibase.cloud/query/sparql"

# OpenStreetMap
export OPENSTREETMAP_USERNAME="your_osm_username"
export OPENSTREETMAP_PASSWORD="your_osm_password"
```

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use environment variables** or secure credential storage
3. **Limit bot password permissions** to only what your application needs
4. **Rotate credentials regularly** and revoke unused bot passwords
5. **Use interactive prompts** for development/testing workflows

## Troubleshooting

### Login Failures

If login fails, check:

1. **Credentials format**: Username should be `Username@BotName` for Wikimedia projects
2. **Bot password permissions**: Ensure the bot password has required grants
3. **Platform/account boundary**: Wikimedia bot passwords and Data Distillery credentials are separate
4. **API URL**: Verify you're targeting the correct endpoint for the account type
5. **Network connectivity**: Ensure you can reach the API endpoint

### Authentication Errors

Common errors and solutions:

- `AuthenticationError: Not logged in` - Call `auth.login()` before making authenticated requests
- `AuthenticationError: Invalid credentials` - Double-check your username and password
- `AuthenticationError: No credentials provided` - Set environment variables or pass credentials to constructor

## See Also

- [Authentication API Reference](api/auth.md) - Complete API documentation with detailed examples
- [Wikidata:Bots](https://www.wikidata.org/wiki/Wikidata:Bots) - Wikidata bot policy
- [Special:BotPasswords](https://www.wikidata.org/wiki/Special:BotPasswords) - Create bot passwords
- [MediaWiki API](https://www.mediawiki.org/wiki/API:Main_page) - MediaWiki API documentation
- [OpenStreetMap API](https://wiki.openstreetmap.org/wiki/API) - OpenStreetMap API documentation
