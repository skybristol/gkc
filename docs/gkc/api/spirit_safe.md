# SpiritSafe API

## Overview

The `gkc.spirit_safe` module provides profile registry integration, SPARQL lookup hydration, and cache management for SpiritSafe-backed workflows.

This module supports two source modes:

- `github` (default): fetches profile and query assets from the SpiritSafe repository
- `local`: uses a local SpiritSafe clone for branch-based development and testing

## Source Configuration

### `SpiritSafeSourceConfig`

::: gkc.spirit_safe.SpiritSafeSourceConfig
    options:
      show_root_heading: false
      heading_level: 4

### `set_spirit_safe_source`

::: gkc.spirit_safe.set_spirit_safe_source
    options:
      show_root_heading: false
      heading_level: 4

### `get_spirit_safe_source`

::: gkc.spirit_safe.get_spirit_safe_source
    options:
      show_root_heading: false
      heading_level: 4

## Profile Registry Access

### `ProfileMetadata`

::: gkc.spirit_safe.ProfileMetadata
    options:
      show_root_heading: false
      heading_level: 4

### `list_profiles`

::: gkc.spirit_safe.list_profiles
    options:
      show_root_heading: false
      heading_level: 4

### `profile_exists`

::: gkc.spirit_safe.profile_exists
    options:
      show_root_heading: false
      heading_level: 4

### `get_profile_metadata`

::: gkc.spirit_safe.get_profile_metadata
    options:
      show_root_heading: false
      heading_level: 4

## Path and Query Resolution

### `resolve_profile_path`

::: gkc.spirit_safe.resolve_profile_path
    options:
      show_root_heading: false
      heading_level: 4

### `resolve_query_ref`

::: gkc.spirit_safe.resolve_query_ref
    options:
      show_root_heading: false
      heading_level: 4

## Lookup Hydration and Caching

### `hydrate_profile_lookups`

::: gkc.spirit_safe.hydrate_profile_lookups
    options:
      show_root_heading: false
      heading_level: 4

### `LookupCache`

::: gkc.spirit_safe.LookupCache
    options:
      show_root_heading: false
      heading_level: 4

### `LookupFetcher`

::: gkc.spirit_safe.LookupFetcher
    options:
      show_root_heading: false
      heading_level: 4

## Usage Examples

### Use default GitHub source

```python
import gkc

source = gkc.get_spirit_safe_source()
print(source.mode)  # github
profiles = gkc.list_profiles()
print(profiles)
```

### Use local clone for branch testing

```python
import gkc

gkc.set_spirit_safe_source(
    mode="local",
    local_root="/path/to/SpiritSafe"
)

metadata = gkc.get_profile_metadata("TribalGovernmentUS")
print(metadata.version)
```

### Hydrate lookups from profile names

```python
import gkc

summary = gkc.hydrate_profile_lookups(
    [gkc.resolve_profile_path("TribalGovernmentUS")],
    dry_run=True,
)
print(summary["unique_queries"])
```
