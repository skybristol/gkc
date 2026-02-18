# Initial CLI Design Proposal

Plain meaning: This document proposes a minimal CLI framework for GKC, focused first on authentication workflows, so we can add more commands later without breaking the architecture.

## Initial design prompt

To my knowledge, we have not implemented a CLI for GKC. Some new functionality I want to add as part of this issue/branch would make good use of that. Can you scope out a similar document called temp/INITIAL_CLI_DESIGN.md, laying out how you would go about adding the CLI framework. We do not need to add every bit of functionality already created in the GKC package, but go ahead and start with the logical aspects of the auth module as we'll need that for most things. Similar to the last time, place major design decisions in a section at the end, and we will iterate before proceeding.

## Goals

- Provide a clear CLI entry point for common workflows.
- Start with authentication tasks that are reused across features.
- Keep commands composable and testable.
- Avoid coupling CLI logic to internal modules beyond public APIs.

## Non-goals

- Do not expose every module or feature in v1.
- Do not bake in network-heavy workflows beyond auth checks.

## CLI framework proposal

### Packaging and entry points

- Add a CLI module: `gkc/cli.py` (or `gkc/cli/__init__.py` for a package).
- Register a console script entry point in `pyproject.toml`, e.g. `gkc`.
- Use `argparse` for now (keeps dependencies minimal), with a later path to `typer` if needed.

Plain meaning: `gkc` should be a stable command you can run from the terminal.

### Command layout (initial)

`gkc auth` commands should cover common needs for both Wikiverse and OpenStreetMap.

Proposed commands:

- `gkc auth wikiverse login`
- `gkc auth wikiverse status`
- `gkc auth wikiverse token`
- `gkc auth osm login`
- `gkc auth osm status`

### Behavior summary

- `login`: validate credentials and persist a session token or report success.
- `status`: report whether credentials are present and whether the auth system can obtain tokens.
- `token`: return a CSRF token (Wikiverse only), primarily for debugging.

## Authentication handling

### Wikiverse

Use `WikiverseAuth` from `gkc/auth.py`:

- Credentials sourced from env vars by default.
- Optional `--interactive` flag to prompt for user/password if env vars are missing.
- `status` reports if credentials exist and whether a CSRF token is obtainable.

### OpenStreetMap

Use `OpenStreetMapAuth` from `gkc/auth.py`:

- Credentials sourced from env vars by default.
- Optional `--interactive` flag to prompt for user/password if env vars are missing.
- `status` only checks credential presence (no token flow yet).

## Command-to-API mapping

This section maps each CLI command to the public API calls it invokes. This keeps CLI logic thin and aligned with the core modules.

### Wikiverse

- `gkc auth wikiverse login`
	- `auth = WikiverseAuth(interactive=--interactive, api_url=--api-url)`
	- `auth.login()`
- `gkc auth wikiverse status`
	- `auth = WikiverseAuth(interactive=False, api_url=--api-url)`
	- `auth.is_authenticated()`
	- `auth.is_logged_in()` (if session already established)
- `gkc auth wikiverse token`
	- `auth = WikiverseAuth(interactive=--interactive, api_url=--api-url)`
	- `auth.login()` (if not already logged in)
	- `auth.get_csrf_token()`

### OpenStreetMap

- `gkc auth osm login`
	- `auth = OpenStreetMapAuth(interactive=--interactive)`
	- `auth.is_authenticated()` (presence check)
- `gkc auth osm status`
	- `auth = OpenStreetMapAuth(interactive=False)`
	- `auth.is_authenticated()`

Plain meaning: the CLI should just instantiate auth classes and call their public methods.

## Command UX

### Global options

- `--verbose` for extra output (e.g., endpoint URL).
- `--json` for machine-readable outputs.

### Examples

```bash
gkc auth wikiverse status
gkc auth wikiverse login --interactive
gkc auth wikiverse token
gkc auth osm status
gkc auth osm login --interactive
```

## JSON output schema

When `--json` is used, emit a single JSON object with stable keys. This makes it easy to parse in scripts.

### Common fields

- `command`: the full command path (e.g., `auth.wikiverse.status`).
- `ok`: boolean success indicator.
- `message`: human-readable status summary.
- `details`: nested object for command-specific data.

### Wikiverse examples

`gkc auth wikiverse status --json`:

```json
{
	"command": "auth.wikiverse.status",
	"ok": true,
	"message": "Credentials present",
	"details": {
		"authenticated": true,
		"logged_in": false,
		"api_url": "https://www.wikidata.org/w/api.php"
	}
}
```

`gkc auth wikiverse token --json`:

```json
{
	"command": "auth.wikiverse.token",
	"ok": true,
	"message": "CSRF token obtained",
	"details": {
		"token": "<redacted or full token depending on flags>",
		"api_url": "https://www.wikidata.org/w/api.php"
	}
}
```

### OpenStreetMap example

`gkc auth osm status --json`:

```json
{
	"command": "auth.osm.status",
	"ok": true,
	"message": "Credentials present",
	"details": {
		"authenticated": true
	}
}
```

## Logging and output

- Default output is human-friendly.
- `--json` emits a structured object with status fields.
- Avoid printing raw passwords or tokens unless explicitly requested (token command).

## Optional configuration file

To keep v1 simple, configuration can remain environment-driven. If we want a small config file, propose a single TOML file with a minimal schema:

- Location: `~/.config/gkc/config.toml` (or `~/.gkc/config.toml` if we want a simpler path)
- Purpose: store default API URLs and preferred output mode

Example:

```toml
[wikiverse]
api_url = "https://www.wikidata.org/w/api.php"

[cli]
output = "human"
```

Plain meaning: a lightweight place for defaults, no secrets.

## CLI documentation placement

Add a dedicated doc page in the MkDocs tree and link it from the main docs index:

- New page: `docs/gkc/cli.md`
- Link from [docs/gkc/index.md](../index.md) under a "CLI" or "Getting Started" section
- Include a short command reference, env var list, and examples

Keep the CLI docs minimal in v1, and expand as more subcommands are added.

## Testing plan

- CLI unit tests for argument parsing and command routing.
- Mocked auth classes for login/token behavior.
- No live network calls in tests.

## Design decisions

- CLI framework: use `argparse` initially to avoid new dependencies.
- CLI entry point name: `gkc`.
- Auth-first scope: focus on `auth` subcommands before adding other workflows.
- Output format: support `--json` for automation, default to human output.
- Token redaction in JSON output: should `gkc auth wikiverse token --json` return the full token or a redacted placeholder unless `--show-token` is passed?
    - Use the redacted placeholder as default
- Config file location: prefer `~/.config/gkc/config.toml` or `~/.gkc/config.toml`?
    - `~/.gkc/config.toml`
- Should `gkc auth osm login` attempt a network validation (if an API endpoint is added later), or remain a pure credential presence check in v1?
    - Keep it as a pure credential presnece check for now.
