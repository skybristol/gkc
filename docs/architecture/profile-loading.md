# Profile Loading Architecture

## Implementation Status

This page documents implemented and architecturally committed behavior for profile loading in GKC and SpiritSafe-backed sources.

## Resolution Model

GKC resolves a profile reference through `resolve_profile_path()` using the canonical registrant layout:

- `ProfileName` → `profiles/ProfileName/profile.yaml`
- `ProfileName.yaml` → `profiles/ProfileName/profile.yaml`
- Explicit paths are preserved as provided.

Compatibility fallback supports legacy flat layout during migration:

- `profiles/Foo/profile.yaml` can fall back to `profiles/Foo.yaml`
- `profiles/Foo.yaml` can fall back to `profiles/Foo/profile.yaml`

## Source Modes

Profile loading is source-configured through `SpiritSafeSourceConfig`:

- `mode: github` (default)
- `mode: local`

In GitHub mode, SpiritSafe-relative paths resolve to raw GitHub URLs. In local mode, paths resolve against `local_root`.

## Query Reference Resolution

Hydration resolves `query_ref` deterministically with `resolve_query_ref()`:

1. Profile-relative first (for registrant layout).
2. Root-relative fallback.

For registrant profiles, `queries/foo.sparql` is attempted first as:

- `profiles/<Profile>/queries/foo.sparql`

then as:

- `queries/foo.sparql`

## Failure Behavior

- Missing profile files raise path resolution errors after fallback attempts.
- Missing query files raise `FileNotFoundError` with attempted paths.
- Hydration can either collect failures or fail fast based on `fail_on_query_error`.

## Theoretical Design Notes

- Optional pinned-ref contract testing against SpiritSafe testing branches is not yet integrated into default CI behavior.
- Future profile version selection semantics (for example, explicit version targeting) remain open design work.
