# Authentication Commands

Plain meaning: Verify and manage credentials for external services.

## Overview

The authentication commands help you verify that your credentials are properly configured and can successfully authenticate with Wikiverse (Wikidata, Wikipedia, Wikimedia Commons) and OpenStreetMap services.

## Wikiverse Authentication

Wikiverse commands manage authentication for all Wikimedia projects (Wikidata, Wikipedia, Wikimedia Commons) using bot password credentials.

### Login

```bash
gkc auth wikiverse login
```

Logs into Wikiverse using bot password credentials.

**Options:**
- `--interactive`: Prompt for credentials if environment variables are missing
- `--api-url`: Override the Wikiverse API URL

**Example:**
```bash
gkc auth wikiverse login --interactive
```

### Status

```bash
gkc auth wikiverse status
```

Checks whether credentials are available and whether a CSRF token can be obtained. This is the recommended way to verify your authentication setup.

**Options:**
- `--api-url`: Override the Wikiverse API URL

**Example:**
```bash
gkc auth wikiverse status
gkc --json auth wikiverse status
```

### Token

```bash
gkc auth wikiverse token
```

Retrieves a CSRF token for debugging purposes. Tokens are redacted by default for security.

**Options:**
- `--interactive`: Prompt for credentials if environment variables are missing
- `--api-url`: Override the Wikiverse API URL
- `--show-token`: Display the full token (use with caution)

**Example:**
```bash
gkc auth wikiverse token
gkc auth wikiverse token --show-token
```

## OpenStreetMap Authentication

OpenStreetMap commands verify that OSM credentials are properly configured.

### Login

```bash
gkc auth osm login
```

Confirms whether OpenStreetMap credentials are present.

**Options:**
- `--interactive`: Prompt for credentials if environment variables are missing

**Example:**
```bash
gkc auth osm login --interactive
```

### Status

```bash
gkc auth osm status
```

Reports whether OpenStreetMap credentials are available.

**Example:**
```bash
gkc auth osm status
gkc --json auth osm status
```

## Environment Variables

### Wikiverse

These environment variables configure Wikiverse authentication:

- `WIKIVERSE_USERNAME`: Your bot username (format: `YourUsername@BotName`)
- `WIKIVERSE_PASSWORD`: Your bot password
- `WIKIVERSE_API_URL`: API URL (optional, defaults to Wikidata)

**Example:**
```bash
export WIKIVERSE_USERNAME="MyUser@MyBot"
export WIKIVERSE_PASSWORD="abc123def456"
```

### OpenStreetMap

These environment variables configure OSM authentication:

- `OPENSTREETMAP_USERNAME`: Your OSM username
- `OPENSTREETMAP_PASSWORD`: Your OSM password

**Example:**
```bash
export OPENSTREETMAP_USERNAME="myuser"
export OPENSTREETMAP_PASSWORD="secret123"
```

## Output Formats

### Human-Readable Output

By default, commands output simple status messages:

```bash
$ gkc auth wikiverse status
Credentials and token validated
authenticated: True
logged_in: True
api_url: https://www.wikidata.org/w/api.php
token_ok: True
```

### JSON Output

Use the `--json` flag for machine-readable output suitable for scripts:

```bash
$ gkc --json auth wikiverse status
{
  "command": "auth.wikiverse.status",
  "ok": true,
  "message": "Credentials and token validated",
  "details": {
    "authenticated": true,
    "logged_in": true,
    "api_url": "https://www.wikidata.org/w/api.php",
    "token_ok": true
  }
}
```

## Security Notes

- Tokens are automatically redacted in output unless `--show-token` is explicitly used
- Never commit credentials or tokens to version control
- Use environment variables or interactive prompts instead of command-line arguments for credentials
- The `--json` output is safe to log as it redacts sensitive information by default

## Related Documentation

- [Authentication Guide](../authentication.md) - Detailed guide for setting up authentication in your code
- [CLI Overview](index.md) - Main CLI documentation
