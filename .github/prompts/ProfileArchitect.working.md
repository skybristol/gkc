# Profile Architect Working Notes

**Date:** 2026-03-01

## Purpose

Track what still blocks a safe return to active GKC code revisions after the SpiritSafe repository redesign (per-profile registrants, metadata-first organization, CI hydration/release scaffolding).

## Current Reality Check

- SpiritSafe repo scaffolding now exists and is published.
- GKC still has legacy assumptions in several places (flat profile files, path examples, and fixture layout).
- Architectural documentation split planned in `EntityProfileDocRevised_20260301.md` is not yet implemented.

## Remaining Blockers

### 1) ~~Profile path model mismatch~~ ✅ RESOLVED

**What blocked progress**

- GKC helper `resolve_profile_path()` still maps simple profile names to `profiles/<Name>.yaml`.
- New SpiritSafe layout uses `profiles/<Name>/profile.yaml` and includes `metadata.yaml`, `README.md`, and `CHANGELOG.md`.

**Why this mattered**

- Any profile-by-name workflow in CLI/hydration could resolve to non-existent files once fully switched to SpiritSafe registrants.

**Resolution implemented**

- `resolve_profile_path()` now maps simple names to registrant package paths (`profiles/<Name>/profile.yaml`)
- Bidirectional fallback maintains compatibility during transition
- Tests verify both registrant and legacy path resolution

---

### 2) ~~Query reference resolution contract is undefined~~ ✅ RESOLVED

**What blocked progress**

- Existing profile `query_ref` values are authored as if global (`queries/<file>.sparql`).
- New registrant model introduces per-profile query directories (`profiles/<Name>/queries/`).
- No explicit rule was enforced for whether `query_ref` is SpiritSafe-root-relative, profile-relative, or both with fallback.

**Resolution implemented**

- `resolve_query_ref()` implements deterministic resolution: profile-relative first, then root-relative fallback
- For registrant profiles (`profiles/Foo/profile.yaml`), tries `profiles/Foo/queries/file.sparql` before `queries/file.sparql`
- Legacy flat profiles only try root-relative paths
- Tests verify all resolution scenarios including fallback behavior

**Why this mattered**

- Hydration logic could fetch the wrong query path or fail after migration.

---

### 3) ~~No profile registry abstraction in GKC yet~~ ✅ RESOLVED

**What blocked progress**

- GKC could load a YAML file but had no first-class notion of a profile registrant package.
- No API to discover profiles, read registrant metadata, or resolve latest/explicit version semantics.

**Why this mattered**

- Next-stage code work (wizard planning, validation selection, CLI ergonomics) needs profile discovery and metadata, not just direct file loading.

**Resolution implemented**

- Added `ProfileMetadata` dataclass for structured metadata representation
- Implemented discovery functions:
  - `list_profiles()` - enumerate available profiles (directory scanning for local mode, GitHub API for GitHub mode)
  - `profile_exists(profile_id)` - quick availability check
  - `get_profile_metadata(profile_id)` - load and parse metadata.yaml with validation
- All functions respect the configured SpiritSafe source (local or GitHub)
- Tests cover all discovery scenarios including validation of required metadata fields

**Design considerations for SpiritSafe repo:**

1. **Central registry index**: Currently using directory scanning for local mode and GitHub API for GitHub mode. Should we add a central `registry.yaml` file listing all profiles with categories, deprecation status, or featured/recommended flags? This would:
   - Avoid GitHub API calls for discovery
   - Support richer metadata (categories, tags, deprecation warnings)
   - Enable faster profile enumeration
   - Allow profile grouping/organization

2. **Version semantics**: Current implementation loads metadata but doesn't enforce version constraints. Future enhancements could include:
   - Version range requirements (e.g., "requires gkc >= 0.5.0")
   - Profile dependency versioning (e.g., "requires OfficeHeldByHeadOfState >= 1.2.0")
   - Deprecation/superseded-by tracking

3. **Metadata validation**: Currently validates presence of required fields (`name`, `version`, `status`). Should we add:
   - JSON Schema or Pydantic validation for metadata.yaml structure?
   - CI workflow validation of metadata completeness?
   - Standardized status values (e.g., enum of "draft", "stable", "deprecated")?

---

### 4) ~~Test fixtures still model legacy flat profiles~~ ✅ RESOLVED

**What blocked progress**

- `tests/fixtures/profiles/` contained only flat YAML examples.
- No fixture coverage existed for registrant package shape (`profile.yaml` + `metadata.yaml` + `queries/`).

**Why this mattered**

- Refactors to loaders/resolvers were risky without regression coverage for new directory semantics.

**Resolution implemented**

- Added registrant-style fixture packages:
  - `tests/fixtures/profiles/TribalGovernmentUS/`
  - `tests/fixtures/profiles/EntityProfileExemplar/`
- Added `profile.yaml`, `metadata.yaml`, and profile-local `queries/` files for each package.
- Updated tests to reference `profiles/<ProfileID>/profile.yaml` paths where applicable.

**Future issue note (optional integration hook)**

- Add an optional test hook in GKC CI to run contract tests against a configurable SpiritSafe testing branch/ref (for example `SPIRITSAFE_TEST_REF`), while keeping default unit tests pinned to local fixtures for determinism.

---

### 5) ~~Docs are still mixed (implemented + theoretical in one large file)~~ ✅ RESOLVED

**What blocked progress**

- Architecture docs were not split into focused pages.
- Architecture content was nested under `docs/gkc/` despite system-wide scope.
- `docs/gkc/profiles.md` lacked explicit framing for implemented vs theoretical behavior.

**Why this mattered**

- Engineers could not quickly determine stable implementation details versus forward-looking design intent.

**Resolution implemented**

- Created top-level architecture section under `docs/architecture/`:
  - `docs/architecture/index.md`
  - `docs/architecture/profile-loading.md`
  - `docs/architecture/spiritsafe-infrastructure.md`
  - `docs/architecture/validation-architecture.md`
- Moved prior architecture page from `docs/gkc/architecture.md` to `docs/architecture/index.md` and updated content to list/summarize split pages.
- Updated `mkdocs.yml` nav to include top-level Architecture section and new pages.
- Updated internal links that referenced the old `gkc/architecture.md` path.
- Added explicit **Implementation Status** and **Theoretical Design Notes** framing in `docs/gkc/profiles.md`.

---

### 6) ~~Source-of-truth transition policy is not locked~~ ✅ RESOLVED

**What blocked progress**

- GKC had residual assumptions around `.SpiritSafe/` as a local in-repo source.
- Source-of-truth and local override policy were not explicitly finalized in docs.

**Why this mattered**

- Parallel profile sources could drift and create brittle loading/hydration behavior.

**Resolution implemented**

- Deprecation timeline executed immediately: `.SpiritSafe/` removed from GKC workspace usage.
- Canonical source of truth set to SpiritSafe repository (`skybristol/SpiritSafe`).
- Local override policy standardized: clone SpiritSafe, create branch, develop and test against clone path, submit PR to SpiritSafe.
- API and CLI docs updated to reflect GitHub-default behavior and clone-based local override flow.

## Decisions Made

1. **Canonical profile locator format**: `ProfileName` -> `profiles/ProfileName/profile.yaml` ✅ IMPLEMENTED with legacy fallback.
2. **Canonical `query_ref` behavior**: Option C implemented ✅ - profile-relative first, then root-relative (migration-safe compromise).
3. **Primary source mode policy**: `github` mode is default, local override supported via SpiritSafe clone path, `.SpiritSafe/` in GKC is deprecated now.

## Minimal Unblock Sequence (Updated)

1. ~~Implement path/lookup compatibility layer in `gkc.spirit_safe` for registrant packages + legacy fallback.~~ ✅ DONE
2. ~~Add query resolution with profile-relative first, root-relative fallback.~~ ✅ DONE
3. ~~Add profile registrant discovery helper (list profile IDs, resolve `profile.yaml`, optionally surface metadata fields).~~ ✅ DONE
4. ~~Add fixture set representing registrant package layout and migrate key tests.~~ ✅ DONE
5. ~~Write the three architecture docs and add "Implementation Status + Theoretical Design Notes" framing in `docs/gkc/profiles.md`.~~ ✅ DONE
6. ~~Update CLI/help/examples to stop advertising flat `profiles/<Name>.yaml` assumptions.~~ ✅ DONE

## Definition of “Ready to Resume Broad Code Work”

- ✅ Loading by profile name resolves correctly for registrant packages.
- ✅ Hydration resolves `query_ref` deterministically under the chosen rule.
- ✅ Profile discovery and metadata access available via clean API.
- ✅ Tests cover both legacy and registrant profile layouts.
- ✅ Docs clearly separate implemented architecture from theoretical wizard design.
- ✅ Team agrees on SpiritSafe source-of-truth transition plan.
