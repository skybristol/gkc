# SpiritSafe Infrastructure

## Implementation Status

This page describes implemented and committed SpiritSafe infrastructure as consumed by GKC.

## Registry Package Shape

SpiritSafe profile registrants use package directories:

- `profiles/<ProfileID>/profile.yaml`
- `profiles/<ProfileID>/metadata.yaml`
- `profiles/<ProfileID>/queries/*.sparql` (when applicable)

Additional documentation files (`README.md`, `CHANGELOG.md`) are supported as registry artifacts.

## GKC Registry Abstractions

GKC currently exposes registry-oriented utilities in `gkc.spirit_safe`:

- `list_profiles()`
- `profile_exists(profile_id)`
- `get_profile_metadata(profile_id)`
- `ProfileMetadata` dataclass for structured metadata access

These APIs operate in both configured source modes (`github` and `local`).

## Caching and Hydration

SPARQL hydration is profile-driven and cache-backed:

- Query templates can be inline (`query`) or referenced (`query_ref`).
- Hydration deduplicates rendered query text per endpoint.
- Cache files are written under source-specific cache directories.

## Current Constraints

- Profile discovery in GitHub mode currently depends on GitHub API directory listing.
- Metadata validation currently enforces required fields at runtime (`name`, `version`, `status`) without a separate published schema contract.

## Theoretical Design Notes

- A central SpiritSafe `registry.yaml` index is proposed but not yet implemented.
- Richer metadata taxonomy (categories, deprecation flags, featured profiles) remains an open design item.
- Explicit version/dependency constraints between profiles are not yet implemented.
