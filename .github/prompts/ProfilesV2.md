# ProfilesV2: Wikibase-First Entity Profile Architecture

**Target Agents:** Profile Architect, Validation Agent, Wizard Engineer  
**Phase:** Comprehensive refactor to fully implement Wikibase-backed profile system  
**Status:** Planning (v2 reset)  

---

## Executive Summary

This document defines the **complete refactor** required to transition from the current YAML-first profile system to a **Wikibase-first architecture** where the Data Distillery Wikibase is the authoritative source of truth for GKC Entity Profiles. This refactor touches the SpiritSafe repository (cache structure), the gkc package (still_charger, cooperage, profiles, bottler modules), and requires coordination across three agent responsibilities.

### Core Architectural Shift

**Current State:**
- Entity Profiles are hand-authored YAML documents in `SpiritSafe/profiles/{ProfileName}/profile.yaml`
- YAML profiles drive validation, form generation, and runtime behavior
- DD Wikibase contains metadata about profiles but is **not consumed by runtime code**

**Target State:**
- **DD Wikibase is authoritative** — all profile structure, constraints, guidance, and linkages defined as Wikibase items/statements
- **SpiritSafe is a materialized cache** stored in **JSON format** (not YAML) for parsing performance
- **gkc runtime consumes JSON cache** from SpiritSafe, treating it as read-only snapshot
- **Authoring workflow:** Edit profiles in DD Wikibase → Export to SpiritSafe via extraction pipeline → Update gkc cache references

**Key Design Constraint:** SpiritSafe cache remains **version-controlled** and **offline-capable** (no runtime dependency on DD Wikibase availability).

## Current Status Snapshot (2026-03-13)

The extraction and cache bootstrap work is sufficiently complete to shift active planning and implementation into ProfilesV2.

What is now working:

- Profile-to-cache route is implemented and validated from root profile traversal (Tribal Government profile successfully pulled linked profile content).
- SpiritSafe entity cache baseline has been generated and refreshed with metadata-enriched entity JSON artifacts.
- Mash-level revision route is implemented (`recentchanges` polling + changed-entity refresh + hard-delete for missing entities) with thin CLI wrapper.
- Manual SpiritSafe GitHub Action exists for cache refresh while iterative development continues.

What this means:

- The project can now treat the ontology/cache substrate as operational enough and focus next on next-gen Entity JSON translation and fermenter integration.

## Temporary Test Forcefits To Unwind

These are pragmatic test-compatibility adjustments made during transition and should be removed once the v2 JSON contract and test harness are stabilized.

1. SpiritSafe phase3 tests now force fixture-backed local source:

- `tests/test_spirit_safe_phase3.py` was switched to use `tests/fixtures/spiritsafe` as the local SpiritSafe source in its autouse fixture.
- Reason: full pre-merge checks were failing because they depended on an external local checkout path (`/Users/sky/code/SpiritSafe/cache/manifest.json`) that is no longer guaranteed after cache reboot work.
- Unwind target: replace this implicit global fixture override with explicit test parametrization against v2 JSON cache fixtures and source configuration injected per test/module.

2. Pre-merge is still validating legacy YAML-era packet/profile behavior during v2 buildout:

- Current test suite continues to assert YAML-oriented profile loading and packet wiring while v2 JSON translation is not yet fully wired end-to-end.
- Unwind target: once translator + fermenter interface are stable, retire YAML-era phase3 assertions and replace with JSON-first packet/profile fixture suites.

3. Foundation-path deletions are coupled to test cleanup sequencing:

- Legacy foundation profile artifacts and related audit/init test paths were removed to align with ProfilesV2 direction.
- Unwind target (final cleanup step): verify there are zero remaining references in docs and tests to foundation profile YAML workflows, then delete any residual compatibility text/examples.

### Forcefit Cleanup Ownership and Exit Criteria

Cleanup sequencing and ownership is now explicitly:

1. Profile Architect freezes contracts and absorbs former wikibase-module cleanup scope.
2. Validation Agent implements and validates Fermenter V1 contract behavior.
3. Wizard Engineer integrates after Validation Agent contract outputs are stable.

| Forcefit / Temporary Compatibility Item | Owner | Exit Criteria |
|---|---|---|
| Phase3 fixture-forced source config in tests | Profile Architect | Tests are parameterized for source mode and no test relies on machine-local SpiritSafe path assumptions |
| YAML-era packet/profile assertions still in active suite | Validation Agent | JSON-first assertions and fixtures replace YAML-era expectations for runtime contract paths |
| Residual foundation workflow references in docs/examples | Profile Architect | No references remain to legacy foundation init/audit workflows in active docs/tests |
| Fermenter V1 conformance checks minimally wired for extraction | Validation Agent | Conformance checks are reusable primitives with deterministic error/report surface consumed by pipeline tests |
| Wizard contract timing coupled to validation stabilization | Wizard Engineer | Wizard integration tests run only against frozen packet/conformance contracts and pass without schema shims |

## Next Steps Toward Next-Gen Entity JSON Translation

1. Translation contract freeze:

- Finalize the profile JSON output contract for runtime translation consumption (field semantics, null/default conventions, cardinality encoding, datatype derivation policy).
- Remove remaining YAML-era assumptions from downstream module contracts.

2. Impacted-profile refresh mapping:

- Implement mapping from changed entity IDs to affected profile JSON outputs.
- Define deterministic incremental rebuild behavior for profile JSON artifacts.

3. Translator implementation pass:

- Build the next-gen Entity JSON translator that consumes cache entities and emits canonical profile JSON outputs for SpiritSafe.
- Ensure translator output includes fermenter-relevant processing metadata and deterministic ordering for stable diffs.

4. Fermenter-facing interface prep:

- Define the explicit packet/translation interface fermenter will consume.
- Validate that statement-level policies and primitive-level coercion guidance pass through translation without UI-specific branching.

5. Validation and rollout:

- Run controlled revision tests: Wikibase change -> cache refresh -> impacted translation rebuild -> artifact diff validation.
- Promote manual workflow to fuller CI automation once gkc main includes all required runtime changes.

### Legacy Foundation/Profile-Profile Deprecation (v2)

- `gkc/wikibase/foundation_profiles/` is deprecated and should be fully removed.
- The legacy Wikibase init/audit flow based on foundation profile YAML declarations is non-authoritative for Profiles v2.
- The later "profile profiles" layering is treated as a misstep and is being unwound, not aligned.
- Profiles v2 should derive semantic truth from live DD Wikibase entities/properties and materialize that truth into SpiritSafe JSON cache artifacts.

---

## SpiritSafe Cache Structure

### Decision: JSON Format

**Rationale:** User confirmed preference for **machine-readable performance** over human-readable diffs. JSON parsing is 2-4x faster than YAML in Python. Human readability is preserved in the **DD Wikibase web interface**, not in the cache.

**Requirements:**
- Valid JSON structure (strict schema enforcement)
- Single file per profile: `profiles/{QID}/profile.json`
- URI-first identifiers: any stored entity identifier must be a fully resolvable URI (e.g., `https://datadistillery.wikibase.cloud/entity/Q4`), not a bare `Q...` token
- Auto-generated `README.md` per profile with practical summary information sourced from export data
- Auto-generated `CHANGELOG.md` per profile, combining Wikibase item history with SpiritSafe cache checkpoints

### Architectural Decision: Identifier Policy

- `wikibase_entity` is the **only canonical machine identifier** for profile items.
- `profile_id` is removed from the v2 JSON schema.
- Human-readable labels (`labels.en.label` and other language labels) are **presentation-only**.
- Runtime logic MUST NOT use labels for identity, joins, cache keys, linkage resolution, or routing.
- If a short token is needed for local filesystem naming, derive it from `wikibase_entity` at export time (non-authoritative), and always resolve back to `wikibase_entity` for logic.

### Design Note: Elimination of metadata.yaml

**Previous approach:** Separate `metadata.yaml` files contained version tracking, authorship, source references, profile graph edges, and discovery metadata.

**V2 approach:** Eliminate metadata.yaml to reduce file overhead and single-source information:
- **Machine-readable metadata** → moved to `registry_metadata` section in `profile.json`
- **Version tracking** → feature-based repository git tags (format: `{meaningful-slug}`)
- **Authorship/attribution** → git commit history or optional `README.md`
- **Source references** → optional `README.md`
- **Profile graph edges** → `manifest.json` (registry-level)
- **Discovery metadata** (datatypes used, statement counts) → computed from `profile.json` structure
- **Change history** → git log filtered by profile tags

**Benefit:** Single source of truth per profile, minimal manual maintenance burden, self-documenting evolution.

### Profile JSON Schema (v2)

**Core Structure:**

```json
{
  "wikibase_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
  "labels": {
    "en": {"label": "Tribal Government (US)", "guidance": "...", "input_prompt": "..."},
    "es": {"label": "...", "guidance": "...", "input_prompt": "..."}
  },
  "descriptions": {
    "en": {"label": "...", "guidance": "...", "input_prompt": "..."}
  },
  "aliases": {
    "en": {"label": ["...", "..."], "guidance": "..."}
  },
  "statements": [
    {
      "statement_entity": "https://datadistillery.wikibase.cloud/entity/Q16",
      "label": "instance of",
      "io_map": [
        {"to": "https://www.wikidata.org/entity/P31"}
      ],
      "value": {
        "type": "item",
        "fixed": "https://www.wikidata.org/entity/Q55555"
      },
      "guidance": "Indicates that this entity is an instance of Tribal Government",
      "max_count": 1,
      "processing_policies": [
        "https://datadistillery.wikibase.cloud/entity/Q159",
        "https://datadistillery.wikibase.cloud/entity/Q161"
      ],
      "linked_profile_entity": null,
      "expected_qualifiers": [],
      "value_specs": ["https://datadistillery.wikibase.cloud/entity/Q23"],
      "reference_specs": []
    },
    {
      "statement_entity": "https://datadistillery.wikibase.cloud/entity/Q40",
      "label": "office held by head of government",
      "io_map": [
        {"to": "https://www.wikidata.org/entity/P39"}
      ],
      "value": {
        "type": "item",
        "fixed": null
      },
      "guidance": "headquarters location for the tribal government",
      "max_count": 1,
      "processing_policies": [],
      "linked_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q39",
      "expected_qualifiers": [
        "https://datadistillery.wikibase.cloud/entity/Q34",
        "https://datadistillery.wikibase.cloud/entity/Q35",
        "https://datadistillery.wikibase.cloud/entity/Q36"
      ],
      "value_specs": [],
      "reference_specs": ["https://datadistillery.wikibase.cloud/entity/Q31"]
    }
  ],
  "metadata": {
    "exported_from": "https://datadistillery.wikibase.cloud/entity/Q4",
    "export_timestamp": "2026-03-09T12:34:56Z"
  },
  "registry_metadata": {
    "release": "added-office-linkage",
    "release_date": "2026-03-09T10:00:00Z",
    "git_tag": "added-office-linkage"
  }
}

**Note on File Structure:**
- `profile.json` contains all machine-readable content
- Auto-generated `README.md` contains a practical curator/developer summary generated from exported profile data:
  - Profile labels and descriptions
  - Statement summary (ids, datatypes, fixed/default semantics where present)
  - Linked profile summary (`linked_profile_entity` relationships)
  - Key references/provenance pointers
- Auto-generated `CHANGELOG.md` contains profile history context with scoped depth:
  - SpiritSafe cache checkpoints (export timestamp, git tag/release metadata)
  - Wikibase history entries for the profile item itself
  - Optional future expansion to include linked statement-definition/specification item history
- Release tracking via repository-level git tags (format: `{meaningful-slug}`)

**CHANGELOG Scope Policy (initial):**
- Start with profile-by-profile history only (the profile item itself plus SpiritSafe checkpoint metadata).
- Do not include full transitive linked-item history in the initial release.
- Add linked history layers incrementally once we define depth limits, grouping rules, and noise controls.

**Git Tagging Convention:**

SpiritSafe cache checkpoints use **feature-based naming** instead of semantic versioning.

```bash
# Format: {slug-describing-change}
git tag initial-release
git tag added-office-linkage
git tag enhanced-validation-rules
```

**Tag naming guidelines:**
- Use past-tense verb phrase (2-5 words)
- Use kebab-case (lowercase with hyphens)
- Describe the primary significance of the change
- Examples of good slugs:
  - `added-canadian-jurisdiction-support`
  - `enhanced-reference-requirements`
  - `fixed-date-coercion-rules`
  - `removed-deprecated-statements`
  - `initial-release` (for first version)

**Chronology:** Git provides natural ordering; no need for version number comparison logic.

**Discovery:** List releases with `git tag --sort=-creatordate`
```

**Field Mapping from DD Wikibase Properties:**

| JSON Field | Wikibase Source | Notes |
|------------|----------------|-------|
| `wikibase_entity` | Item entity URI | Resolvable source reference |
| `labels.en.label` | `labels.en` | Human-readable notice only; not a machine identifier |
| `labels.{lang}.label` | `labels.{lang}` | Required: `en` |
| `labels.{lang}.guidance` | P185 statement (mainsnak monolingual text) | Curator instruction |
| `labels.{lang}.input_prompt` | P188 statement (mainsnak monolingual text) | Field label in UI |
| `descriptions.{lang}.label` | `descriptions.{lang}` | Required: `en` |
| `descriptions.{lang}.guidance` | P186 statement | Example text |
| `aliases.{lang}.label` | `aliases.{lang}[]` | Array of strings |
| `statements[].id` | Normalized label from P157 target entity | e.g., entity/Q16 → `instance_of` |
| `statements[].statement_entity` | P157 mainsnak target entity URI | Resolvable source reference |
| `statements[].label` | Label from statement-definition item | Display name |
| `statements[].io_map[].to` | P5 from statement-definition item | Currently Wikidata only |
| `statements[].value.type` | P194 from statement-definition item / linked property datatype metadata | One of 8 primitive datatypes; must be derived from machine-readable property/type metadata, not labels |
| `statements[].value.fixed` | P183 qualifier on P157 | Fixed value entity URI (optional) |
| `statements[].guidance` | P171 qualifier on P157 | Curator instruction |
| `statements[].max_count` | P182 qualifier on P157 | `novalue` → `null` (unlimited), `+N` → integer |
| `statements[].processing_policies` | P159 + P161 qualifiers on P157 | Ordered array of fermenter policy entity URIs |
| `statements[].linked_profile_entity` | P162 qualifier on P157 | Target profile entity URI |
| `statements[].expected_qualifiers` | P164 qualifier on P157 | Array of statement-definition entity URIs |
| `statements[].value_specs` | P163 qualifier on P157 (value list linkages) | **TBD:** may move to separate field |
| `statements[].reference_specs` | P159 qualifier on P157 (reference constraints) | Array of specification entity URIs |
| `metadata.exported_from` | Constructed from source Wikibase item URI | Export provenance |
| `metadata.export_timestamp` | Generated at export time | ISO 8601 timestamp |
| `registry_metadata.release` | Feature-based release name from git tag | Slug describing checkpoint change (e.g., `added-office-linkage`) |
| `registry_metadata.release_date` | Timestamp of profile release | ISO 8601; from git tag creation or commit date |
| `registry_metadata.git_tag` | Full git tag reference | Format: `{meaningful-slug}` |

**Metadata Inclusion Rule:**
- Do not include placeholder metadata fields.
- A metadata field is eligible only when all three are true: (1) it has a concrete definition, (2) extraction can populate it deterministically, and (3) at least one downstream consumer uses it.
- Future candidate: `metadata.extractor_version` (gkc package version) once package release/version semantics are active and consumed by runtime tooling.

**Note on Release Tracking:**
- Cache checkpoints are tracked via feature-based git tags in the SpiritSafe repository
- Tag format: `{slug}` (no entity identifier in tag name)
- `registry_metadata` section is updated by the extraction pipeline based on the active checkpoint tag associated with the cache export
- Release history: `git log --tags --oneline --date-order`
- Authorship/attribution tracked via git commit history or documented in optional `README.md`
- No semantic versioning (x.y.z) required; git chronology provides ordering

**Traceability Note:**
- Entity/profile-level traceability is provided by auto-generated per-profile `CHANGELOG.md` content (Wikibase profile-item history + SpiritSafe cache checkpoint metadata), not by encoding entity identifiers in git tag names.

**Label Usage Guardrail:**
- Labels are for human-readable notice only.
- Identity and linkage must use `wikibase_entity` (or other explicit entity URI fields).
- Any label changes must be treated as non-breaking presentation changes.

**Language Availability Guardrail:**
- Profiles are the authoritative source of available language content.
- Downstream consumers/processors must only operate on languages present in profile-derived packet metadata.
- gkc should expose a package-level default language setting so operators can run the system with a different primary language lens.
- Curation Packets should include language-availability metadata so interfaces (for example, Wizard) can offer language toggles only when supported.
- **BCP 47 primary subtag normalization:** DD Wikibase (and Wikidata) store monolingual text with language codes that may include region subtags (e.g., `en-us`, `en-gb`, `en-ca`). During SpiritSafe extraction, all language codes must be normalized to their BCP 47 primary language subtag (`en`, `es`, `de`, etc.) before writing to cache. Region-specific variants are collapsed into the primary subtag. This normalization is a fermenter primitive and must be applied consistently to all monolingual text fields (labels, descriptions, guidance, prompts) and to all language keys in charged entity content. Regional differentiation (e.g., `en-au` vs. `en-gb`) is deferred until there is an explicit content requirement for it.

**Fermenter Policy Guardrail:**
- Policy entities are runtime instructions for fermenter processing, not UI-only behavior.
- Wizard, CLI, and bulk jobs must call the same fermenter API and consume the same result envelope.
- Any UI-specific behavior must be adapter logic over fermenter output, never a separate policy engine.

**Workflow Policy Deprecation Notice (v2):**
- `workflow_policy` is deprecated in the profile contract.
- Effective behavior is now enablement-first: linked-profile statements support both "Create new" and "Select existing" paths by default.
- Constraint behavior should be expressed through statement semantics (`value.fixed`, future `value.default`, cardinality, and validation/specification rules), not through linkage action gates.
- Existing YAML-era `workflow_policy` fields may remain in legacy artifacts during migration, but they are non-authoritative and should not drive runtime branching.

**Sitelink Deprecation Notice (v2 MVP):**
- Sitelink behavior is deprecated in the Profile v2 design for the immediate MVP.
- The current DD Wikibase content model does not include the metadata needed to define sitelink behavior declaratively, so Profile v2 should not attempt to model or validate sitelinks as part of the profile contract.
- UI and bulk workflows should not treat sitelinks as profile-driven structured fields in v2.
- Future reintroduction should happen through a fermenter URL-processing/coercion primitive that accepts simple URL input and normalizes it into sitelink-ready data for downstream handling.
- Existing sitelink-related code paths may remain in legacy modules during migration, but they are non-authoritative for Profile v2 and should not drive new contract design.

**Open Questions:**
1. Should `io_map` remain an array to support multi-system export, or simplify to single `wikidata_property` field for now?
2. Where to store value list specifications (e.g., `https://datadistillery.wikibase.cloud/entity/Q28`, `https://datadistillery.wikibase.cloud/entity/Q43`)? Current field `value_specs` may be ambiguous with validation specs.
3. **Multi-language monolingual text encoding (resolved direction):** Flatten by primary language subtag after BCP 47 normalization (region subtags stripped on ingest). Current flat-by-language-code structure is correct; no nested structure needed for v2. Regional subtag differentiation is deferred.
4. **Cardinality null vs. -1:** Profile JSON uses `max_count: null` for unlimited; current packet `cardinality_constraints` uses `-1`. Choose one encoding and apply it throughout. Prefer `null` for alignment with JSON schema; update all packet assembly, validation, and barrel-stage cardinality checks accordingly.
5. **Default values policy (future):** We support fixed values today (`value.fixed`) and may introduce editable defaults (`value.default`) later. Decide whether defaults are represented directly in profile schema, and define clear precedence rules (user-provided value vs default materialization vs fixed enforcement).
6. **Package-level default language configuration:** Define where the gkc default language is configured (runtime config/CLI/env), and define fallback behavior when requested/default language guidance is missing.
7. **Primitive datatype derivation robustness:** Confirm the canonical source for `statements[].value.type` is machine-readable property/type metadata (for example, via linked property entities and datatype classification), not label conventions such as `statement type - item`.
8. **Extraction strategy for cache build:** Evaluate a hybrid method as likely default: (a) SPARQL to pull profile/statement/spec/property identifiers and graph edges, then (b) `wbgetentities` batch pulls for full JSON needed for deterministic transformation. Compare against SPARQL-only and API-only approaches for correctness, completeness, and performance.

## Theoretical Design Notes

- **Cross-interface fermenter contract:** the same fermenter invocation and result envelope should be used by wizard, CLI, and bulk tooling; only post-processing adapters differ by interface.
- **Module-contract follow-up:** `docs/architecture/module-contracts.md` should include an anti-duplication rule that forbids validation/coercion/policy execution logic outside fermenter.
- **Open design question for Validation + Wizard agents:** whether `processing_policies` order should be strictly preserved from Wikibase extraction or normalized by fermenter at runtime.
- **Curation Packet as explicit module output contract:** `gkc.profiles` is not just a profile loader — its primary output contract is a Curation Packet. `module-contracts.md` should explicitly define the Curation Packet as the interface boundary between the profiles module and its consumers (Wizard, CLI, bulk tooling, cooperage). Any refactor that changes the packet structure is a breaking change to downstream consumers and requires coordinated updates.
- **`create_curation_packet` is a critical path function:** Changes to `profile_id` → `wikibase_entity` identity and cross-reference derivation in `create_curation_packet` will break `still_charger`, `cooperage`, `validate_packet_structure`, and Wizard consumers simultaneously. These changes should be implemented and tested atomically; do not partially migrate.

### Manifest JSON Schema (v2)

**Purpose:** Provide graph metadata for profile dependencies, runtime indexing, and cache freshness tracking.

```json
{
  "cache_version": "2.0",
  "manifest_timestamp": "2026-03-09T12:34:56Z",
  "profiles": [
    {
      "wikibase_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
      "release": "added-office-linkage",
      "exported_at": "2026-03-09T10:00:00Z",
      "file_path": "profiles/Q4/profile.json"
    },
    {
      "wikibase_entity": "https://datadistillery.wikibase.cloud/entity/Q39",
      "release": "initial-release",
      "exported_at": "2026-03-08T14:30:00Z",
      "file_path": "profiles/Q39/profile.json"
    }
  ],
  "profile_graph": {
    "edges": [
      {
        "source_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "source_statement_entity": "https://datadistillery.wikibase.cloud/entity/Q40",
        "target_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q39",
        "linkage_type": "P162",
        "bidirectional": true
      },
      {
        "source_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q39",
        "source_statement_entity": "https://datadistillery.wikibase.cloud/entity/Q42",
        "target_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "linkage_type": "P162",
        "bidirectional": true
      }
    ]
  },
  "ontology_items": {
    "entity_profiles": [
      "https://datadistillery.wikibase.cloud/entity/Q3",
      "https://datadistillery.wikibase.cloud/entity/Q4",
      "https://datadistillery.wikibase.cloud/entity/Q39"
    ],
    "entity_statements": [
      "https://datadistillery.wikibase.cloud/entity/Q5",
      "https://datadistillery.wikibase.cloud/entity/Q16",
      "https://datadistillery.wikibase.cloud/entity/Q19",
      "https://datadistillery.wikibase.cloud/entity/Q33",
      "https://datadistillery.wikibase.cloud/entity/Q40",
      "https://datadistillery.wikibase.cloud/entity/Q41",
      "https://datadistillery.wikibase.cloud/entity/Q42"
    ],
    "property_specifications": [
      "https://datadistillery.wikibase.cloud/entity/Q6",
      "https://datadistillery.wikibase.cloud/entity/Q23",
      "https://datadistillery.wikibase.cloud/entity/Q24",
      "https://datadistillery.wikibase.cloud/entity/Q26",
      "https://datadistillery.wikibase.cloud/entity/Q28",
      "https://datadistillery.wikibase.cloud/entity/Q31",
      "https://datadistillery.wikibase.cloud/entity/Q43"
    ],
    "value_lists": [
      "https://datadistillery.wikibase.cloud/entity/Q28",
      "https://datadistillery.wikibase.cloud/entity/Q43"
    ]
  }
}
```

**Requirements:**
- Generated automatically by extraction pipeline
- Used by `gkc.profiles` module for profile loading and dependency resolution
- Used by Wizard for graph traversal and "Create new" / "Select existing" affordances

---

## Curation Packets in v2

### What a Curation Packet Is

A Curation Packet is the **central output contract of the `gkc.profiles` module**. It is the actionable bundle delivered to the Wizard, CLI, and bulk tooling that enables curation of one or more entities. It contains:

- **Entity scaffolds** — one per profile in scope, each with an empty `data: {}` waiting to be charged
- **Cross-references** — the inter-entity linkages derived from statement-level P162 linkages, materialized by SpiritSafe into downstream-friendly graph metadata
- **Cardinality constraints** — packet-level structural rules (min/max per linked entity type)
- **Profile package** — the full profile content embedded for downstream use (validation, form generation)
- **Packet identity** — `packet_id`, `operation_mode`, `created_at`, `manifest_commit_sha`

After assembly, the packet flows through: `still_charger` (charging entity data) → `cooperage` (barreling to Wikibase operation plan) → `shipper` (delivery).

### How v2 JSON Profiles Relate to the Packet

In the current YAML-first system, there is significant transformation between a loaded profile dict and the entity scaffold placed in the packet. The v2 `profile.json` schema substantially reduces this gap — the JSON structure is very close to the packet's `entities[n].profile_structure` content. Most of what packet assembly does is:

1. Load the relevant profile JSON files
2. Assign packet-local entity IDs (`ent-001`, `ent-002`, etc.)
3. Wire cross-references between the entity scaffolds
4. Embed the profiles in `profile_package` for downstream use
5. Initialize `data: {}` as the empty vessel

This is the right outcome. The extraction pipeline does the heavy transformation work (Wikibase JSON → canonical JSON), and packet assembly becomes a thin orchestration layer.

### What Changes in v2 Packet Assembly

**Identity: `profile_id` → `wikibase_entity`**

The current packet uses string profile IDs (`"TribalGovernmentUS"`) as keys everywhere:

- `packet.primary_profile`
- `entities[].profile`
- `cross_references[].from_profile` / `cross_references[].to_profile`
- Internal `entity_id_map` (maps profile_id → ent-NNN)

In v2, all of these must use the `wikibase_entity` URI (e.g., `"https://datadistillery.wikibase.cloud/entity/Q4"`). The human-readable label from `labels.en.label` may be carried alongside for display, but must not be used as an identifier. This cascades through every stage (`still_charger`, `cooperage`, `spiritsafe`) that currently keys on profile name strings.

**Cross-references: manifest linkages vs. statement-embedded linkages**

In the current YAML-first flow, cross-references are assembled from precomputed manifest linkage data. In v2:

- Each statement's `linked_profile_entity` field (P162) is embedded directly in `profile.json`
- The manifest's `profile_graph.edges` is a derived export artifact built from those statement-level P162 linkages for efficient traversal and indexing

**Decision:** The Wikibase source of truth for linked profiles remains the per-statement P162 linkage only. No separate profile-level linkage statement should be added to the DD Wikibase content model.

The DD Wikibase → SpiritSafe extraction process is responsible for converting those per-statement linkages into the most straightforward downstream structures:

- `profile.json` retains the per-statement `linked_profile_entity` values as the canonical semantic linkage record
- `manifest.json.profile_graph.edges` is generated from those same statement linkages for efficient BFS traversal and dependency preloading
- Curation Packet assembly should treat SpiritSafe as the prepared handoff: use manifest graph edges to decide which profiles to load, then use loaded statement data to populate the packet's specific cross-reference entries (`via_statement`, cardinality context, and related metadata)

This sequencing keeps the Wikibase model minimal and expressive while pushing denormalization and optimization into the extraction pipeline, which is the correct place to prepare data for efficient downstream packet assembly.

**`io_map` unification fixes a longstanding gap**

In the current architecture, YAML profiles express Wikidata property bindings as `wikidata_property: P31` at the statement level, while the cooperage barrel stage reads `io_map[]` to build its `{statement_id → property_id}` mapping. These two systems are not connected, which means barreling silently skips statements when a packet is assembled from real YAML profiles (rather than manually constructed test packets). In v2, `statements[].io_map[].to` is the canonical, standardized way to carry this binding. The barrel stage should work correctly without override once all profiles carry `io_map` entries.

**`value.fixed` charging semantics (additive, non-destructive)**

In v2, `statements[].value.fixed` is an explicit field carrying the required fixed value. `still_charger` should enforce fixed values in an additive, non-destructive way:

1. If the fixed value is missing from incoming data for that statement, add it.
2. If the fixed value is present, leave it as-is.
3. If additional non-fixed values are present, keep them in place (do not auto-delete during charging).
4. Emit a structured notice when values exist beyond profile guidance so downstream interfaces can decide whether to keep or remove them.

This aligns with Wikidata-first curation: preserve existing modeling where possible, ensure required classification/value presence, and surface non-conformance for curator review instead of silently mutating source data.

### Non-conformance signaling in filled packets

When existing data extends beyond profile intent, the packet should carry explicit machine-readable notices for Wizard and bulk review workflows. This should be produced by fermenter/charger processing and attached to the packet so all downstream consumers can read the same signals.

Recommended packet extension:

```json
{
  "conformance_report": {
    "status": "has_notices",
    "summary": {
      "fixed_value_added": 1,
      "statement_not_in_profile": 2,
      "value_not_in_profile_specs": 3,
      "extra_value_for_fixed_statement": 1
    },
    "notices": [
      {
        "severity": "notice",
        "entity_id": "ent-001",
        "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "statement_id": "instance_of",
        "code": "fixed_value_added",
        "message": "Added fixed value Q123 required by profile.",
        "details": {
          "fixed_value": "Q123"
        }
      },
      {
        "severity": "notice",
        "entity_id": "ent-001",
        "profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "statement_id": "instance_of",
        "code": "extra_value_for_fixed_statement",
        "message": "Additional values present beyond fixed profile value.",
        "details": {
          "fixed_value": "Q123",
          "extra_values": ["Q456"]
        }
      }
    ]
  }
}
```

Recommended language metadata extension:

```json
{
  "language_context": {
    "default_language": "en",
    "available_languages": ["en", "es"],
    "coverage": {
      "labels": ["en", "es"],
      "descriptions": ["en"],
      "guidance": ["en", "es"],
      "input_prompts": ["en", "es"]
    }
  }
}
```

Notes:

1. Notices are informational by default (`severity: notice`), not hard errors.
2. Strict workflows may escalate selected notice codes to warnings/errors, but base charging should preserve data and annotate.
3. This replaces ad hoc interface-specific behavior with one shared signal source for Wizard, CLI, and bulk tooling.
4. `language_context` allows consumers to initialize UI/processing in package default language and safely offer alternate-language views only when present.

**`max_count` null vs. `-1` encoding**

The v2 `profile.json` encodes unlimited cardinality as `null` (`max_count: null`). The current packet's `cardinality_constraints[].max` uses `-1` for unlimited. A canonical encoding should be chosen and applied consistently through packet assembly and downstream consumption. Using `null` throughout is preferred for alignment with the JSON schema.

### What Does Not Change

The following aspects of the Curation Packet contract are expected to stay the same in v2:

- Packet-local entity ID format (`ent-001`, `ent-002`, etc.)
- The three-stage flow: scaffold → charge → barrel
- `operation_mode: "single" | "bulk"` semantics
- `packet_id` generation and `created_at` timestamps
- The `data: {}` → charged `data` pattern in `still_charger`
- `validate_packet_structure` as the post-assembly integrity check
- Specificationless mode for permissive charging
- `data.wikibase_id` signaling edit vs. create in the barrel stage

### Design Decisions Needed

The following questions must be resolved before implementing v2 packet assembly. Each affects at least two modules (profiles, still_charger, cooperage, or wizard).

**1. Source of truth for cross-reference assembly**

Resolved direction: statement-level P162 linkages in Wikibase are the only authoritative semantic source for linked profiles. SpiritSafe extraction derives `manifest.json.profile_graph.edges` from those statement linkages so downstream packet assembly can remain efficient.

`create_curation_packet` should therefore use:

- manifest edges for traversal and profile-loading order
- loaded profile statement data for populating specific packet cross-reference entries (`via_statement`, cardinality context, and related linkage metadata)

This avoids adding any new profile-level linkage modeling in Wikibase while still giving downstream code a precomputed graph for straightforward processing.

**2. `workflow_policy` deprecation and replacement semantics**

The YAML-era `workflow_policy` field is deprecated for v2 and should not be carried forward as authoritative runtime logic. Linked profile flows are enablement-first and support both create and select-existing by default. Constraint behavior belongs in statement semantics and validators (fixed values, future defaults, cardinality, and specs), not in linkage action gates.

**3. Sitelink deprecation for MVP**

Sitelinks are deprecated in the Profile v2 contract for the immediate MVP. The current DD Wikibase content model does not provide a declarative profile-layer representation for sitelink behavior, and the desired future behavior is better expressed as a fermenter URL-coercion primitive over simple URL input rather than as static profile structure.

For v2 MVP:

- do not introduce new sitelink semantics into the Wikibase profile model
- do not require `create_curation_packet`, Wizard, or bulk routines to treat sitelinks as profile-driven fields
- preserve room for a later URL processor that can normalize simple URL entry into sitelink-ready output

**4. `profile_id` transitional identifier**

The v2 architecture removes `profile_id` (string slug) in favor of `wikibase_entity` URIs. However, filesystem paths in SpiritSafe use the entity's QID (e.g., `Q4/`) derived from the URI. Any code that currently uses `profile_id` as a cache key or comparison target must be updated. A temporary adapter that maps `wikibase_entity` URI → QID string → filesystem path must be explicit and isolated so it can be replaced if the URI structure changes.

**5. Packet profile_package contents**

Currently packets embed full raw profile dicts in `profile_package.profiles`. In v2, these would be the parsed JSON objects (or Pydantic model instances). The question is whether `profile_package` should contain:
 
- Raw JSON dicts (fastest, no conversion cost)
- Pydantic model instances (typed, but serialization to JSON requires `.model_dump()`)
- A new `PackageProfile` lightweight struct that omits large or redundant fields

Given that the Wizard and validation consumers both need typed access, Pydantic model instances are preferred. The packet should carry models, and `validate_packet_structure` should operate on models rather than dicts.

**6. Unifying the two profile loading paths**

Currently there are two parallel paths for profile data: raw dicts (used by `create_curation_packet`) and typed Pydantic `ProfileDefinition` objects (used by `ProfileLoader` for validation and form generation). This split is a known source of bugs. In v2, packet assembly should use the typed loader exclusively, eliminating the raw dict path.

**7. Non-conformance reporting contract**

Define the shared notice contract emitted during packet charging/fermenting and attached to the packet (for Wizard review screens and bulk pipelines). At minimum, define canonical notice codes, severities, and payload fields for:

1. Fixed value auto-added
2. Statement present in source but not in profile
3. Value present but outside profile guidance/specs
4. Extra values present for fixed-value statements

This contract should be stable and interface-agnostic.

**8. Language context contract**

Language availability in a Curation Packet has three distinct sources that must be explicitly layered:

1. **Package-level default language** — a configurable gkc setting (e.g., `gkc.config.default_language`, defaulting to `"en"`) that governs initial display and processing behavior for consumers such as Wizard instances and CLI output. This is a runtime concern, not stored in the packet; it provides the baseline when no other signal is present.

2. **Profile-declared languages** — the languages in which a profile provides input labels, guidance text, consequence metadata, and other monolingual content (P185–P190 fields). These are determined at SpiritSafe extraction time from the actual multilingual content present in DD Wikibase items. The `language_context.profile_languages` field captures this as the set of languages across all loaded profiles in the packet. A profile's available languages are the authoritative upper bound on what the Wizard can offer for guidance display; no UI should claim a language is available unless at least one loaded profile declares content in it.

3. **Charged-content languages** — when `still_charger` loads existing Wikibase entity data into the packet's `data` fields, that content may include language codes not declared in any loaded profile (for example, a previously curated entity has `de` labels even though the profile has no German guidance). These additional languages emerge during charging and must be captured in `language_context.content_languages` so consumers can surface them without suppressing existing content.

The `language_context` envelope in the packet should reflect the union outcome of sources 2 and 3, computed at charge time:

```json
{
  "language_context": {
    "package_default": "en",
    "profile_languages": ["en", "es"],
    "content_languages": ["en", "es", "de"],
    "guidance_coverage": {
      "en": "full",
      "es": "partial",
      "de": "none"
    }
  }
}
```

Where `guidance_coverage` indicates, per language, whether the profile provides full guidance (all monolingual fields present), partial guidance (some present), or none (language present only in charged content, no profile guidance available).

**Key rule:** `package_default` should always be satisfied by `profile_languages`. If the configured package default language is not present in any loaded profile's declared languages, the system should warn and fall back to the first available profile language rather than silently proceeding with unsupported guidance display.

### Impact on Downstream Modules

| Module | Impact | Notes |
|---|---|---|
| `spirit_safe.create_curation_packet` | Major rewrite | `profile_id` → URI, JSON source, cross-ref assembly from statement fields |
| `spirit_safe.validate_packet_structure` | Moderate update | URI comparisons, `null` cardinality encoding |
| `still_charger.charge_curation_packet` | Major update | URI profile keys, additive fixed-value enforcement, non-conformance notice emission, `null` max_count |
| `cooperage.barrel_curation_packet_to_wikibase_plan` | Minor update | `io_map` now reliable (no override needed), URI profile metadata |
| `ProfileLoader` | Major rewrite | JSON source, Pydantic model update |
| `FormSchemaGenerator` | Moderate update | New guidance fields (P185-P190), linked profile affordances |
| `ProfileGraph` | Moderate update | URI-keyed edges, source from manifest `profile_graph.edges` |

### Notes for Validation and Wizard Agents

**For Validation Agent:**

- The `charge_curation_packet` function in `still_charger` needs to handle URI-keyed entities in the packet. All lookups by `entity["profile"]` currently compare against string slugs; these must compare against full `wikibase_entity` URIs after v2. This is a subtle but pervasive change.
- The `auto-charge for fixed values` behavior (see decision 3 above) must be additive and non-destructive: inject missing fixed values, preserve additional existing values, and emit notices for non-conformance rather than deleting data during charge.
- `specificationless` mode must still work in v2 — it should fall back gracefully when a statement `id` in `source_values` does not match any statement in the profile.
- Define and implement a shared `conformance_report` notice envelope attached to charged packets so Wizard/CLI/bulk all consume identical non-conformance signals.

**For Wizard Engineer:**

- `workflow_policy` is deprecated in v2. Wizard linked-profile affordances should default to showing both "Create new" and "Select existing" for `linked_profile_entity` statements. Any limits should come from profile semantics (fixed/default behavior, cardinality, validation results), not a separate linkage policy gate.
- Wizard review/planning screens should read packet-level `conformance_report.notices` and present them as actionable guidance (for example, optional removal of out-of-profile statements/values), without silently mutating source data.
- Wizard should consume packet `language_context` to initialize content display in package default language and expose a language toggle only for languages declared as available.
- The `creation_path` breadcrumb pattern documented in `docs/architecture/index.md` (e.g., `primary.office_held_by_head_of_state`) will need to be re-expressed using entity URIs or statement IDs rather than human-readable strings in v2, since profile labels are no longer authoritative identifiers.

---

## Wikibase → SpiritSafe Extraction Pipeline

### Pipeline Architecture

**Trigger:** Manual CLI command (initial), with routine change detection as future enhancement

**Command:**
```bash
poetry run gkc spirit-safe sync --source datadistillery --target /path/to/SpiritSafe
```

### SpiritSafe Bootstrap Configuration Artifact

The current document defines pipeline stages and query patterns, but v2 also needs a first-class configuration artifact that makes the extraction process portable and reset-friendly.

**Design decision:** SpiritSafe should carry a versioned bootstrap config artifact that contains all identifier-resolution and endpoint configuration needed to run the extraction pipeline against a supported Wikibase instance.

**Proposed location:** `SpiritSafe/cache/pipeline_config.json`

**Purpose:**

- Keep extraction logic declarative and instance-specific details externalized
- Support future ontology resets by updating one config artifact instead of rewriting pipeline code
- Support community-run infrastructure by allowing a different config artifact with equivalent logical term mappings
- Provide stable, English-aligned logical ontology terms that compile to efficient internal resolution maps for SPARQL/API usage

**Required sections in `pipeline_config.json`:**

- `source`: base URLs for API, SPARQL endpoint, and entity URI namespace
- `logical_terms`: English-aligned logical keys mapped to canonical entity/property URIs used by the pipeline (for example, `gkc_entity_profile`, `gkc_entity_statement`, `gkc_property_specification`, `instance_of_property`)
- `query_bindings`: references to extraction query templates and the logical terms they require
- `resolution_policy`: identifier normalization/coercion rules (URI-first enforcement, BCP 47 primary-subtag normalization, and related fermenter primitives used at ingest)
- `strategy`: extraction strategy toggles (hybrid SPARQL + `wbgetentities`, batch size, retry policy)
- `artifact_contracts`: required outputs (`profile.json`, `manifest.json`, `README.md`, `CHANGELOG.md`) and validation gates

**Operational rule:** `gkc spirit-safe sync` should load this artifact first, compile it into runtime resolver maps, and then execute pipeline stages. Pipeline code should not hardcode DD Wikibase entity IDs except as defaults in the checked-in config artifact.

**Pipeline Stages:**

1. **Fetch Profile Items**
  - Load and validate `cache/pipeline_config.json`; initialize logical-term resolver map and source endpoints
   - Query DD Wikibase for all items where `P1 → Q3` (instance of GKC Entity Profile)
   - Fetch full Wikibase JSON for each profile item
   - Cache raw JSON to temporary location

2. **Fetch Statement-Definition Items**
  - Extract all P157 target entity identifiers from fetched profile items
   - Query DD Wikibase for full metadata on each statement-definition item (P5, P194, labels)
   - Cache raw JSON

3. **Fetch Specification Items**
  - Extract all P159, P161, P163, P191 referenced entity identifiers
  - Query DD Wikibase for specification items (`https://datadistillery.wikibase.cloud/entity/Q6` instances)
   - Cache raw JSON

4. **Transform to JSON Cache**
   - For each profile item:
     - Map Wikibase claims structure → JSON profile schema
    - Resolve entity URIs to display labels for UI/help text only
     - Flatten monolingual text fields by language code, normalizing all BCP 47 region subtags to primary subtags (`en-us` → `en`, `en-gb` → `en`, etc.) before writing to cache
  - Compute language availability metadata from labels/descriptions/guidance/prompt fields
    - Extract statement-level P162 linkages as the authoritative linkage source and build the derived edge list for manifest
     - Populate `registry_metadata` section from git tag metadata (if available)
   - Write `profiles/{EntityID}/profile.json` (where `EntityID` is derived from `wikibase_entity`, e.g., `Q4`)
  - Generate `README.md` from exported summary data (labels/descriptions/statements/linkages)

5. **Generate Profile Changelog Artifacts**
  - Build `CHANGELOG.md` for each profile by combining:
    - Wikibase profile-item revision history (scoped to that profile)
    - SpiritSafe cache checkpoint metadata (export timestamp, git tag, release slug)
  - Emit entries in newest-first order with stable event types
  - Persist changelog artifacts alongside `profile.json`

6. **Generate Manifest**
  - Build profile graph from statement-level P162 edges extracted from profile content
  - Treat manifest graph data as a denormalized traversal/index artifact, not an independent semantic source
   - Enumerate all ontology items used
   - Write `cache/manifest.json`

7. **Validate Cache Integrity**
   - JSON schema validation on all profile.json files
  - Verify all P162 linkages resolve to existing profile entities
   - Check datatype consistency (P194 values match allowed set)
   - Verify io_map targets are valid URIs
  - Verify generated `README.md` and `CHANGELOG.md` are present and structurally valid

### Refresh Policy

**Near term (committed):**
- Manual cache refresh via CLI (`gkc spirit-safe sync ...`) is the authoritative update path.
- No background auto-refresh at runtime.

**Planned evolution:**
- Add routine change detection against DD Wikibase (scheduled check or CI-triggered job).
- Rebuild cache/changelog artifacts only when relevant profile revisions are detected.
- Preserve offline-first operation: runtime continues consuming version-controlled SpiritSafe artifacts.

**Error Handling:**
- Missing statement-definition items → warn and skip statement entry
- Circular P162 linkages → detect and flag in manifest (not an error)
- Invalid monolingual text format → warn and use fallback empty string
- Missing required labels (e.g., `en`) → hard error, abort export

**Module Responsibility:** `gkc.spirit_safe` module (new or refactored)

### SPARQL Extraction Queries

**Query 1: Fetch All GKC Entity Profiles**

```sparql
SELECT ?profile ?profileLabel WHERE {
  ?profile wdt:P1 wd:Q3 .  # instance of GKC Entity Profile
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

(Full claim structure fetched via Wikibase API using entity identifiers from query results)

**Query 2: Fetch Statement-Definition Items**

```sparql
SELECT ?statement ?statementLabel ?datatype ?wdProperty WHERE {
  ?statement wdt:P1 wd:Q5 .  # instance of GKC Entity Statement
  OPTIONAL { ?statement wdt:P194 ?datatype . }
  OPTIONAL { ?statement wdt:P5 ?wdProperty . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

**Query 3: Fetch Property Specification Items**

```sparql
SELECT ?spec ?specLabel ?directive WHERE {
  ?spec wdt:P1 wd:Q6 .  # instance of GKC Property Specification
  OPTIONAL { ?spec wdt:P191 ?directive . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

**Implementation Notes:**
- Use `gkc.mash.WikibaseLoader` with `api_url="https://datadistillery.wikibase.cloud/w/api.php"`
- Execute SPARQL via DD Wikibase query service endpoint
- Fetch full JSON via `wbgetentities` API calls (batch size: 50 items per request)

### Datatype Mapping & Extraction Investigation Note

- Avoid brittle datatype inference from labels (for example, `statement type - item`).
- Prefer deriving primitive statement datatype from machine-readable property/type metadata reachable from statement-definition items.
- Investigate and benchmark a hybrid extraction path:
  1. SPARQL identifier harvest (profiles, statement definitions, specification entities, and linked property/type entities)
  2. `wbgetentities` full JSON retrieval for all harvested identifiers
  3. Deterministic transform from full entity JSON into SpiritSafe cache fields
- Decision criteria: correctness under label changes, completeness of qualifier/reference coverage, query/API reliability, and end-to-end sync performance.

---

## Code Refactor Plan

### Modules Requiring Changes

**Priority 1: Critical Path**

1. **`gkc/spirit_safe.py`** (extract/transform/load pipeline)
   - **Current State:** Stub module or empty
   - **Required Changes:**
     - Implement `sync_from_wikibase(source_url, target_dir)` function
     - Implement `PipelineConfigLoader` to read/validate `cache/pipeline_config.json`
     - Implement logical-term identifier resolver compilation (English logical keys → concrete Wikibase URIs/properties)
     - Implement `ProfileExtractor` class with Wikibase → JSON transformation logic
     - Implement `ManifestGenerator` class for profile graph construction
     - Implement JSON schema validators for cache integrity checks
   - **Dependencies:** `gkc.mash` (Wikibase API client), `gkc.sparql` (query execution), SpiritSafe `cache/pipeline_config.json`
   - **Handoff:** Validation Agent to implement transformation logic according to schema above

2. **`gkc/profiles/loaders/`** (consume JSON cache instead of YAML)
   - **Current State:** `ProfileLoader` class reads YAML from SpiritSafe
   - **Required Changes:**
     - Update `ProfileLoader.load()` to read JSON instead of YAML
     - Update `ProfileLoader.resolve_references()` to use manifest.json for dependency resolution
     - Add `ProfileLoader.load_with_dependencies()` for graph-based loading
   - **Dependencies:** SpiritSafe JSON cache
   - **Handoff:** Validation Agent to update loader implementation

3. **`gkc/profiles/models.py`** (Pydantic models for JSON schema)
   - **Current State:** Pydantic models based on YAML schema
   - **Required Changes:**
     - Redefine `ProfileDefinition` model to match JSON schema above
     - Add `StatementDefinition` nested model with all qualifier fields
     - Add `IOMapping` model for io_map structure
     - Add `ProfileManifest` model for manifest.json
     - Add validators for:
       - `max_count` field (`null` or positive integer)
       - `value.type` field (enum of 8 primitive datatypes)
       - `linked_profile_entity` field (reference integrity against manifest)
   - **Dependencies:** None (pure data model)
   - **Handoff:** Validation Agent to update models

4. **`gkc/profiles/validation/`** (consume new schema for validation)
   - **Current State:** Validators consume YAML-based profile structure
   - **Required Changes:**
     - Update `ProfileValidator` to use new `StatementDefinition` structure
     - Add P162 linked profile recursive validation (with depth limit)
     - Add P164 expected qualifiers validation
     - Add P159/P161 policy reference handling as fermenter API dispatch metadata (no UI-specific branching)
   - **Dependencies:** `gkc.profiles.models` updates, fermenter module (future)
   - **Handoff:** Validation Agent to update validators

5. **`gkc/profiles/forms/` or `gkc/profiles/generators/`** (wizard form generation)
   - **Current State:** `FormSchemaGenerator` consumes YAML profiles
   - **Required Changes:**
     - Update form generator to read from JSON cache
     - Extract P185-P190 guidance properties for field-level help text
     - Generate P162 linked profile affordances ("Create new" / "Select existing" buttons)
     - Extract P164 expected qualifiers for sub-form rendering
   - **Dependencies:** `gkc.profiles.models` updates
   - **Handoff:** Wizard Engineer to update form generation logic

**Priority 2: Cleanup & Deprecation**

6. **`gkc/wikibase/foundation_profiles/`** (DELETE entire directory)
   - **Current State:** 7 YAML files (entity_profile_profile.yaml, property_profile.yaml, specification_profile.yaml, foundation_entities/metadata.yaml, foundation_properties/metadata.yaml, 2 README files)
   - **Required Action:** Delete directory and all contents
   - **Dependencies:** None (deprecated artifacts)
   - **Validation:** Ensure no active imports of these files in codebase (grep search required)

7. **`gkc/profiles/validation/wikidata_normalizer.py`** (RELOCATE to `gkc/shipper.py` as `wikibase_normalizer`)
   - **Current State:** Located in validation submodule, used for Wikidata JSON serialization prep
   - **Required Action:**
     - Move logic into `gkc.shipper` module (closer to write boundary)
     - Rename to `wikibase_normalizer` (generalize beyond Wikidata)
     - Update imports in `gkc.bottler` and `gkc.cooperage` if used there
   - **Rationale:** Normalizer is about output serialization, not validation; belongs in shipper responsibility zone per module-contracts.md
   - **Handoff:** Validation Agent to perform relocation and verify no regressions

**Priority 3: Architecture Alignment**

8. **`gkc/wikibase/foundation.py` and `gkc/wikibase/orchestration.py`**
   - **Current State:** Contains legacy assumptions tied to foundation profile YAML/init workflows
   - **Required Changes:**
     - Remove any YAML profile loading logic and any coupling to `foundation_profiles` artifacts
     - Deprecate legacy foundation init/audit assumptions for v2 runtime paths
     - Update orchestration to source profile metadata from SpiritSafe JSON cache
     - Remove assumptions that initialization metadata lives in `gkc.wikibase`; treat SpiritSafe `pipeline_config.json` as the extraction bootstrap source for identifier/query resolution
  - **Dependencies:** Priority 1 changes complete
  - **Ownership:** Profile Architect (absorbed wikibase cleanup scope)

9. **`docs/architecture/module-contracts.md`** (UPDATE boundary definitions)
   - **Current State:** 238 lines defining module responsibilities
   - **Required Changes:**
     - Add entry for `gkc.spirit_safe` module (extract/transform/load from Wikibase)
     - Add explicit `gkc.fermenter` API boundary as the single validation/coercion engine for wizard, CLI, and batch pipelines
     - Define a shared fermenter result envelope contract (codes, severity, normalized values, messages, provenance)
     - Add `wikibase_normalizer` to shipper boundary (note relocation from profiles.validation)
     - Clarify that `gkc.profiles` consumes SpiritSafe cache (read-only, no direct writes)
     - Document that SpiritSafe repository is external to gkc package (version-controlled cache)
   - **Dependencies:** Priority 1-2 changes complete
   - **Handoff:** Profile Architect to draft updates, Validation Agent to review

10. **`docs/gkc/profiles.md`** (UPDATE documentation to reflect new architecture)
    - **Current State:** Documents YAML-first workflow
    - **Required Changes:**
      - Rewrite "How Profiles Work" section for Wikibase-first model
      - Add "Extracting Profiles from DD Wikibase" section with CLI examples
      - Update JSON schema examples (replace YAML examples)
      - Add "Profile Graph and Cross-Profile Linkages" section (P162 architecture)
      - Add "Offline Operation" section (cache freshness policy, update workflows)
    - **Dependencies:** Priority 1-2 changes complete
    - **Handoff:** Profile Architect to draft, User Doc Writer to polish

### File-Level Action Checklist

**Files to DELETE:**
- [ ] `gkc/wikibase/foundation_profiles/entity_profile_profile.yaml`
- [ ] `gkc/wikibase/foundation_profiles/property_profile.yaml`
- [ ] `gkc/wikibase/foundation_profiles/specification_profile.yaml`
- [ ] `gkc/wikibase/foundation_profiles/foundation_entities/metadata.yaml`
- [ ] `gkc/wikibase/foundation_profiles/foundation_properties/metadata.yaml`
- [ ] `gkc/wikibase/foundation_profiles/README.md`
- [ ] `gkc/wikibase/foundation_profiles/foundation_entities/README.md` (if exists)

**Files to CREATE:**
- [ ] `gkc/spirit_safe.py` (or refactor existing stub)
- [ ] `SpiritSafe/cache/manifest.json` (via extraction pipeline)
- [ ] `SpiritSafe/profiles/Q4/profile.json` (migrate from YAML; `Q4` derived from `wikibase_entity`)
- [ ] `SpiritSafe/profiles/Q39/profile.json` (migrate from YAML; `Q39` derived from `wikibase_entity`)
- [ ] `SpiritSafe/profiles/{EntityID}/profile.json` for all remaining profiles (derived from `wikibase_entity`)

**Files to RELOCATE:**
- [ ] `gkc/profiles/validation/wikidata_normalizer.py` → `gkc/shipper.py` (merge as `wikibase_normalizer` function/class)

**Files to MODIFY (Major Refactor):**
- [ ] `gkc/spirit_safe.py` — `create_curation_packet`: rewrite for URI-keyed identities, JSON source, cross-reference derivation from statement fields; atomically coordinated breaking change
- [ ] `gkc/spirit_safe.py` — `validate_packet_structure`: URI comparisons, `null` cardinality encoding
- [ ] `gkc/still_charger.py` — `charge_curation_packet`: URI profile keys in entity lookup, auto-charge for `value.fixed`, `null` max_count handling
- [ ] `gkc/profiles/loaders/*.py` (JSON instead of YAML)
- [ ] `gkc/profiles/models.py` (Pydantic v2 schema; unify raw-dict and typed-model loading paths)
- [ ] `gkc/profiles/validation/validator.py` (new statement fields)
- [ ] `gkc/profiles/forms/*.py` or `gkc/profiles/generators/*.py` (P162 linkages, P185-P190 guidance)
- [ ] `gkc/wikibase/foundation.py` (deprecate legacy init/audit path and remove foundation_profiles references)
- [ ] `gkc/wikibase/orchestration.py` (update profile sourcing)

**Files to MODIFY (Documentation/Minor):**
- [ ] `docs/architecture/module-contracts.md` (add spirit_safe module, update shipper/profiles boundaries)
- [ ] `docs/gkc/profiles.md` (rewrite for Wikibase-first)
- [ ] `SpiritSafe/README.md` (update to explain JSON cache format)
- [ ] `SpiritSafe/profiles/README.md` (update examples to JSON)

**Files to VALIDATE (No Changes Expected, But Verify):**
- [ ] `gkc/cooperage.py` — `barrel_curation_packet_to_wikibase_plan`: `io_map` is now reliable from JSON profiles (no override needed in most cases); URI profile keys in metadata; minor update expected
- [ ] `gkc/mash/core.py` (ensure WikibaseLoader.api_url flexibility preserved)
- [ ] `gkc/sparql.py` (ensure DD Wikibase query endpoint compatibility)
- [ ] `gkc/bottler.py` (verify Wikidata JSON shaping logic still compatible)
- [ ] `gkc/shipper.py` (after wikidata_normalizer relocation)

---

## Handoff Boundaries

### Responsibility Boundary (Current Operating Model)

For the current agent workflow, treat most work in this document up to and including SpiritSafe cache design as **Profile Architect responsibility**.

**Profile Architect owns now (architecture + contract definition):**

1. Wikibase → SpiritSafe JSON schema and manifest shape
2. README/CHANGELOG artifact definitions, scope policy, and refresh policy
3. Identifier policy (`wikibase_entity` as canonical identity)
4. Curation Packet contract shape (scaffolds, cross-references, metadata, conformance report envelope)
5. Non-conformance semantics (preserve existing data, annotate notices, no silent destructive mutation)
6. Exact boundary definitions for downstream engineering implementation

**Current practical implementation boundary:**

- The architectural target is to get profile sourcing and SpiritSafe caching fully specified and implementable, including Curation Packet generation contract updates.
- `still_charger` fulfillment behavior that depends on the not-yet-built fermenter should be treated as the **next boundary**: define contract now, implement once fermenter capability exists.

**Validation Agent responsibility starts when contracts are frozen:**

- Implement the agreed contracts in code (loader/model/validator/pipeline/packet plumbing), with no schema-level reinterpretation.

**Wizard Engineer responsibility starts when packet + notice contracts are frozen:**

- Implement UI behavior against packet and conformance-report contracts (review/plan affordances, optional cleanup actions).

### Development Sequencing Note: Fermenter as First Instantiation

**Chicken-and-egg issue:** The extraction pipeline needs validation primitives to evaluate whether Wikibase-extracted data is well-formed enough to be trusted as a SpiritSafe cache entry. But those validation primitives are architecturally part of the fermenter module — which is otherwise described as future work dependent on later pipeline stages.

**Observed context:** Existing validation code in `gkc/profiles/` (`models.py`, `validation/`) currently handles YAML-based schema enforcement and entity-level checks. That logic is Validation Agent responsibility to migrate into the v2 model. However, those validators operate *after* a profile has already been loaded from cache — they do not evaluate the raw Wikibase extraction output before caching.

**Proposed approach:** Build the DD Wikibase → SpiritSafe extraction conformance checking as the **first fermenter instantiation**, rather than deferred infrastructure. This means:

1. The fermenter module's first concrete composition is a set of validation primitives that evaluate the shape and conformance of Wikibase-extracted profile data (JSON from `wbgetentities`) before it enters the SpiritSafe cache.
2. These same primitives are designed with reuse in mind — they should be composable for other Wikibase/Wikidata inbound use cases (`still_charger`, bulk curation jobs, etc.).
3. Module-level location of validation code becomes less important than its composition pattern: any code that validates inbound Wikibase data should route through fermenter primitives, not be duplicated in `profiles/validation/` or `spirit_safe/`.

**Known fermenter primitives for first instantiation (not exhaustive):**

- **Language code coercion:** Normalize BCP 47 region-qualified language codes (`en-us`, `en-gb`) to primary language subtags (`en`). Must be applied to all monolingual text fields sourced from Wikibase on ingest. Reusable for `still_charger` charged-content normalization and any other Wikibase/Wikidata inbound pipeline. Regional subtag support is deferred; when it becomes a requirement it can be added as an opt-in variant of this primitive.
- **URI-first identifier enforcement:** Validate that all entity identifiers in extracted data are fully qualified URIs before writing to SpiritSafe cache.
- **Required field presence check:** Confirm minimum field set is populated per the agreed conformance surface (OQ9).
- **Primitive datatype resolution:** Resolve `value.type` from machine-readable property metadata, not label strings (OQ7).

**Dogfooding benefit:** The DD Wikibase itself is the authoritative source for GKC Entity Profile meta-information (the schema that defines profiles is itself stored as Wikibase items). Running fermenter primitives against DD Wikibase profile items means the system validates its own configuration using the same engine it will use for all other entity types. This is a meaningful architectural signal that the fermenter design is sound.

**Sequencing implication for Validation Agent:** The fermenter primitive layer is not purely future work — a minimal version is needed as part of the `spirit_safe` extraction pipeline implementation. Treat the Wikibase → SpiritSafe conformance checks as the first fermenter deliverable, not a separate milestone. Coordination with Profile Architect is needed to define the minimum conformance surface before implementation begins.

**Open Question #9:** What is the minimum conformance surface for Wikibase → SpiritSafe ingestion? Candidates: required fields present, identifier policy satisfied (URI-first), all `value.type` fields resolve to known primitives, language coverage meets profile minimum. Needs resolution before Validation Agent starts extraction pipeline implementation.

### To Validation Agent

**Scope:** Implement extraction pipeline, update loaders/models/validators, relocate normalizer

**Start Condition:** Begin only after Profile Architect marks schema, packet envelope, and artifact generation contracts as frozen for implementation.

**Deliverables:**
1. `gkc.spirit_safe` module with:
   - `sync_from_wikibase()` CLI-callable function
   - `ProfileExtractor` class implementing Wikibase → JSON transformation per schema above
   - `ManifestGenerator` class implementing profile graph construction
   - JSON schema validators for cache integrity
2. Updated `gkc.profiles.loaders` to consume JSON cache
3. Updated `gkc.profiles.models` Pydantic schemas matching v2 JSON structure
4. Updated `gkc.profiles.validation` to enforce P162/P164/P159/P161 constraints
5. Relocated `wikidata_normalizer` → `gkc.shipper` as `wikibase_normalizer`
6. Test coverage for:
   - Wikibase → JSON transformation (unit tests with mocked Wikibase responses)
   - JSON cache loading (integration tests against SpiritSafe test fixtures)
   - Profile validation with new schema (unit + integration tests)

**Expected Inputs:**
- JSON schema specifications from this document
- Property-to-Semantics mapping table from WikibaseInitV2.md (lines 800-1243)
- Existing `ProfileValidator` test suite as baseline

**Open Questions for Validation Agent:**
1. Should `io_map` support multiple targets now, or remain single Wikidata property for v2?
2. How to handle language fallback for P185-P190 guidance fields (if `en` missing, use what default)?
3. Validation depth limit for P162 recursive checks: 2 levels sufficient, or configurable?
4. Value list caching strategy: materialize in SpiritSafe JSON, or lazy-load from SPARQL at runtime?
5. (OQ9) What is the minimum conformance surface for Wikibase → SpiritSafe ingestion? Resolution needed before extraction pipeline implementation begins; see Development Sequencing Note above.

**Note on Fermenter / Validation sequencing:** Per the Development Sequencing Note above, a minimal fermenter primitive layer is part of the extraction pipeline deliverable — not deferred. The `spirit_safe` module deliverables should include at minimum a composable conformance check function that evaluates raw `wbgetentities` output against the minimum ingestion surface. Design these primitives for reuse in `still_charger` and other Wikibase/Wikidata inbound pipelines from the start.

### To Wizard Engineer

**Scope:** Update form generation to consume new JSON schema and render P162 linkages

**Start Condition:** Begin only after Profile Architect + Validation Agent finalize packet shape and conformance notice codes.

**Deliverables:**
1. Updated `FormSchemaGenerator` (or equivalent) to:
   - Read from JSON cache via updated `ProfileLoader`
   - Extract P185-P190 monolingual text fields for field-level guidance display
   - Generate "Create new [Linked Profile]" button for P162-linked statements
   - Generate "Select existing [Linked Profile]" type-ahead search widget
   - Render P164 expected qualifiers as sub-form fields
2. Profile graph navigation affordances:
   - Display profile dependency graph (visualize P162 edges from manifest.json)
   - Breadcrumb trail for nested profile curation sessions
   - Modal/panel UI for "Create new" workflow (open linked profile wizard, return item reference)
3. Test coverage for:
   - Form rendering with P162 linkages (visual regression tests or snapshot tests)
   - Graph traversal navigation (integration tests simulating multi-profile workflows)

**Expected Inputs:**
- JSON schema specifications from this document
- Manifest profile_graph structure (edges with source/target profiles)
- Cross-Profile Interlinkage Architecture section from WikibaseInitV2.md (lines 800-1243)

**Open Questions for Wizard Engineer:**
1. Should "Create new" open a modal, new tab, or inline expansion? (UX decision)
2. How to handle **bidirectional linkages** in UI (`https://datadistillery.wikibase.cloud/entity/Q4` ↔ `https://datadistillery.wikibase.cloud/entity/Q39`)? Show both directions, or hide reciprocal?
3. Type-ahead search constraints: filter by P162 linked profile only, or allow broader search with validation warning?
4. How to display P164 expected qualifiers: always visible, or collapsible "Advanced" section?

### Profile Architect Absorbed Wikibase Scope

**Scope:** Clean up `gkc.wikibase` module and orchestration-path contracts as part of Profile Architect ownership

**Deliverables:**
1. Delete `gkc/wikibase/foundation_profiles/` directory and all contents
2. Remove foundation profile YAML references and legacy init/audit runtime entrypoints from active v2 pathing
3. Update orchestration-path contract assumptions to:
  - Source profile metadata from SpiritSafe JSON cache (via `ProfileLoader`)
  - Remove hardcoded legacy profile structure assumptions
  - Keep packet hydration logic declarative via profile io mappings
4. Verify `gkc.cooperage` and `gkc.bottler` compatibility constraints are documented for Validation Agent implementation
5. Ensure test coverage expectations are defined for:
  - Legacy foundation-path deprecation behavior
  - Orchestration with JSON-backed profiles against SpiritSafe fixtures

**Open Questions now owned by Profile Architect:**
1. Should orchestration directly import `ProfileLoader`, or receive profiles as dependency injection?
2. How should profile release staleness be handled (warn, error, or explicit sync workflow)?
3. Which `cooperage`/`bottler` behaviors still assume YAML-era profile structure and need explicit contract updates?

---

## Migration Strategy

### Phase 1: Preparation (Non-Breaking)

**Goal:** Build extraction pipeline and JSON cache without disrupting current YAML workflow

**Tasks:**
1. Implement `gkc.spirit_safe` module with extraction pipeline (Validation Agent)
2. Run extraction against DD Wikibase to generate JSON cache in parallel to YAML profiles (Profile Architect verification)
3. Validate JSON cache integrity and schema compliance (Validation Agent)
4. Add JSON profile fixtures to `tests/fixtures/profiles/` (Validation Agent)
5. Update Pydantic models for JSON schema (Validation Agent)
6. Write unit tests for new models and extraction logic (Validation Agent)

**Checkpoint:** JSON cache generated, validated, and version-controlled alongside YAML profiles (both formats coexist)

### Phase 2: Runtime Migration (Breaking Change)

**Goal:** Switch `gkc.profiles` module to consume JSON cache instead of YAML

**Tasks:**
1. Update `ProfileLoader` to read JSON (Validation Agent)
2. Update `ProfileValidator` to use new schema (Validation Agent)
3. Update `FormSchemaGenerator` to use new schema (Wizard Engineer)
4. Run full test suite against JSON cache (All agents)
5. Fix regressions and integration issues (All agents)
6. Update documentation (Profile Architect, User Doc Writer)

**Checkpoint:** All tests passing, JSON cache is sole source of truth for runtime

### Phase 3: Cleanup (Optional)

**Goal:** Remove deprecated YAML profiles and foundation_profiles artifacts

**Tasks:**
1. Delete `SpiritSafe/profiles/*/profile.yaml` and `metadata.yaml` files (keep optional README)
2. Delete `gkc/wikibase/foundation_profiles/` directory (Profile Architect)
3. Relocate `wikidata_normalizer` to shipper (Validation Agent)
4. Update architecture docs (Profile Architect)
5. Git commit with clear migration notes (All agents)

**Checkpoint:** Codebase fully migrated to Wikibase-first architecture, no YAML profile remnants

---

## Success Criteria

**Must Have (Blocking):**
- [ ] JSON cache extraction pipeline functional (CLI command runs successfully)
- [ ] All 5 current SpiritSafe profiles exported to JSON format with valid schema
- [ ] Manifest.json generated with profile graph edges (P162 linkages)
- [ ] `ProfileLoader` reads JSON cache without errors
- [ ] `ProfileValidator` enforces new schema constraints (P162, P164, P159, P161)
- [ ] Existing test suite passes against JSON cache (regression-free)
- [ ] `foundation_profiles/` directory deleted, no remaining references in codebase

**Should Have (High Priority):**
- [ ] `FormSchemaGenerator` renders P162 linked profile affordances
- [ ] P185-P190 guidance properties displayed in wizard forms
- [ ] P164 expected qualifiers rendered as sub-form fields
- [ ] Documentation updated (profiles.md, module-contracts.md)
- [ ] Test coverage for extraction pipeline (unit + integration tests)
- [ ] `wikidata_normalizer` relocated to shipper module

**Nice to Have (Future Enhancement):**
- [ ] Automated sync workflow (GitHub Actions or webhook trigger)
- [ ] Profile cache staleness detection and refresh recommendations
- [ ] Recursive profile validation with configurable depth limit
- [ ] Value list caching with SPARQL regeneration on-demand
- [ ] Multi-system io_map support (Wikidata + OpenStreetMap + Commons)

---

## GitHub Issue Triage Mapping (2026-03-09)

### Closed as OBE (Superseded by V2 Reset)

- #87 Develop an approach on profile-level override/reconciliation on languages setting
- #90 Auto-Creation Pattern for Fixed-Value Statements
- #92 Language Declaration & Configuration Clarity
- #93 Quantity Datatype Unit Behavior Signaling
- #94 Form Policy Clarity and Extensibility
- #95 Missing Consequence Warnings and Implications
- #101 Issue template: Profile Concept / Design Issue
- #120 Design and plan fermenter module

### Kept Open and Mapped to Active Work

- **Profiles architecture and cache/sync:** #121, #122, #124, #125, #126, #127
- **Versioning and compatibility policy:** #99
- **Cooperage cleanup aligned to new boundaries:** #133

### Guidance for Ongoing Issue Hygiene

- Keep #127 as the umbrella progress rollup for Fermenter/Data Distillery integration.
- Continue closing design-only issues when the requirement is fully absorbed into execution docs and no standalone code path remains.
- Open new issues only for executable units with concrete acceptance criteria and module-level ownership.

---

## Open Questions & Decisions Needed

1. **IO Mapping Strategy:**
   - Keep `io_map` as array for future multi-system support, or simplify to single `wikidata_property` string for v2?
   - **Recommendation:** Keep array structure with single Wikidata entry for now; easier to extend later than to refactor from string to array.

2. **Value List Caching:**
   - Materialize SPARQL results in SpiritSafe JSON cache, or execute SPARQL at runtime with local cache?
   - **Trade-offs:** SpiritSafe cache = version-controlled, offline-capable but stale; runtime cache = fresh but requires endpoint availability.
   - **Recommendation:** Hybrid — materialize truncated lists (first 1000 items) in SpiritSafe, full lists in runtime cache with TTL-based refresh.

3. **Language Fallback Policy:**
   - If P185-P190 guidance fields missing for `en` language, use what default? Empty string, or fall back to another language?
   - **Recommendation:** Hard requirement for `en` language in guidance fields; extraction pipeline should error if missing.

4. **Profile Versioning:**
   - How to handle version mismatches between SpiritSafe cache and DD Wikibase source?
   - **Options:** (a) Warn on mismatch, allow usage; (b) Error on mismatch, force re-sync; (c) Auto-sync on load if outdated.
   - **Recommendation:** Warn on first load, log sync suggestion, allow usage (user controls sync timing).

5. **Circular Linkage Depth:**
  - P162 bidirectional linkages (`https://datadistillery.wikibase.cloud/entity/Q4` ↔ `https://datadistillery.wikibase.cloud/entity/Q39`) require depth limit for recursive validation. Default to 2 levels, or make configurable?
   - **Recommendation:** Default 2 levels, configurable via CLI flag or environment variable for advanced users.

6. **Specification Items Handling:**
  - P159/P161 reference multiple specification items (e.g., `https://datadistillery.wikibase.cloud/entity/Q23`, `https://datadistillery.wikibase.cloud/entity/Q24`, `https://datadistillery.wikibase.cloud/entity/Q26`, `https://datadistillery.wikibase.cloud/entity/Q31`). Should these be resolved to human-readable labels in JSON cache, or kept as entity URIs?
  - **Recommendation:** Keep as entity URIs in cache (resolvable stable identifiers), resolve to labels in wizard UI via manifest ontology_items lookup.

---

## Next Actions (Immediate)

**Profile Architect:**
1. Finalize JSON schema based on open questions above (document decisions in this file)
2. Draft SPARQL extraction queries and test against DD Wikibase query service
3. Create example JSON profile fixture for `https://datadistillery.wikibase.cloud/entity/Q4` in `tests/fixtures/profiles/`
4. Review and approve schema before Validation Agent begins implementation

**Validation Agent (after Profile Architect approval):**
1. Implement `gkc.spirit_safe` extraction pipeline (ProfileExtractor + ManifestGenerator)
2. Update `gkc.profiles.models` Pydantic schemas to match v2 JSON structure
3. Update `gkc.profiles.loaders` to read JSON cache
4. Write test suite for extraction and loading (unit + integration tests)

**Wizard Engineer (after Validation Agent completes Priority 1):**
1. Update `FormSchemaGenerator` to consume new JSON schema
2. Implement P162 linked profile affordances ("Create new" / "Select existing")
3. Extract and render P185-P190 guidance properties in forms
4. Test form rendering with SpiritSafe JSON fixtures

**Profile Architect (absorbed wikibase cleanup scope):**
1. Keep foundation-path deprecation and orchestration contract cleanup on the architecture track
2. Freeze orchestration contract assumptions for Validation Agent implementation
3. Document compatibility constraints for `cooperage` and `bottler`
4. Hand off only after validation-facing contract artifacts are explicit and testable

---

**Document Version:** 1.2  
**Last Updated:** 2026-03-13  
**Next Review:** After Phase 1 completion (JSON cache extraction functional)
