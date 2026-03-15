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

- `entity` is the **only canonical machine identifier** for profile items.
- `profile_id` is removed from the v2 JSON schema.
- Human-readable labels are **presentation-only**.
- Runtime logic MUST NOT use labels for identity, joins, cache keys, linkage resolution, or routing.
- If a short token is needed for local filesystem naming, derive it from `entity` at export time (non-authoritative), and always resolve back to `entity` for logic.

### Design Note: Elimination of metadata.yaml

**Previous approach:** Separate `metadata.yaml` files contained version tracking, authorship, source references, profile graph edges, and discovery metadata.

**V2 approach:** Eliminate metadata.yaml to reduce file overhead and single-source information:
- **Machine-readable metadata** → moved to `registry_metadata` section in `profile.json`
- **Version/provenance tracking** → revision-first workflow metadata, with optional feature-based repository git tags for manual milestones
- **Authorship/attribution** → git commit history or optional `README.md`
- **Source references** → optional `README.md`
- **Profile graph edges** → `manifest.json` (registry-level)
- **Discovery metadata** (datatypes used, statement counts) → computed from `profile.json` structure
- **Change history** → git log filtered by profile tags

**Benefit:** Single source of truth per profile, minimal manual maintenance burden, self-documenting evolution.

### Profile JSON Schema (v2)

**Contract correction (2026-03-15):**

- Use `entity` throughout as the URI identifier key.
- Profile item labels/descriptions and P185-P190 prompt/guidance content live under `metadata.profile_item`, not in statement specification payload.
- Description prompt (P189) and description guidance (P186) are materialized from `mul` content.
- Alias prompt (P190) and alias guidance (P187) are both materialized when present.
- Earlier examples that place labels/descriptions at the profile root are superseded by the structure below.

**Core Structure:**

```json
{
  "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
  "statements": [
    {
      "id": "instance_of",
      "entity": "https://datadistillery.wikibase.cloud/entity/Q16",
      "label": "instance of",
      "io_map": [
        {"to": "https://www.wikidata.org/entity/P31"}
      ],
      "value": {
        "type": "wikibase-item",
        "fixed": {
          "entity": "https://www.wikidata.org/entity/Q7840353",
          "label": "Tribal Government"
        },
        "default": null,
        "options": []
      },
      "prompt": "...",
      "guidance": "Indicates that this entity is an instance of Tribal Government",
      "consequences_message": null,
      "error_message": null,
      "max_count": 1,
      "qualifiers": [],
      "references": [
        {"entity": "https://datadistillery.wikibase.cloud/entity/Q29", "label": "reference URL"},
        {"entity": "https://datadistillery.wikibase.cloud/entity/Q30", "label": "stated in"}
      ]
    },
    {
      "id": "office_held_by_head_of_government",
      "entity": "https://datadistillery.wikibase.cloud/entity/Q40",
      "label": "office held by head of government",
      "io_map": [
        {"to": "https://www.wikidata.org/entity/P39"}
      ],
      "value": {
        "type": "wikibase-item",
        "fixed": null,
        "default": null,
        "options": [
          {
            "kind": "profile",
            "entity": "https://datadistillery.wikibase.cloud/entity/Q39",
            "label": "Office Held by Head of Government"
          }
        ]
      },
      "prompt": "...",
      "guidance": "Leadership office position held by the head of this tribal government",
      "consequences_message": null,
      "error_message": null,
      "max_count": 1,
      "qualifiers": [
        {"entity": "https://datadistillery.wikibase.cloud/entity/Q34", "label": "start time"},
        {"entity": "https://datadistillery.wikibase.cloud/entity/Q35", "label": "end time"},
        {"entity": "https://datadistillery.wikibase.cloud/entity/Q36", "label": "replaces"}
      ],
      "references": [
        {"entity": "https://datadistillery.wikibase.cloud/entity/Q29", "label": "reference URL"},
        {"entity": "https://datadistillery.wikibase.cloud/entity/Q30", "label": "stated in"}
      ]
    }
  ],
  "metadata": {
    "profile_item": {
      "labels": {
        "mul": "Tribal Government in the United States",
        "en": "Tribal Government in the United States",
        "es": "Gobierno tribal en los Estados Unidos"
      },
      "descriptions": {
        "en": "GKC Entity Profile describing the content model for entities representing the governments of federally recognized Native American and Alaska Native Tribes in the United States"
      },
      "prompt_guidance": {
        "label_guidance_mul": "... (P185)",
        "label_prompt_mul": "... (P188)",
        "description_guidance_mul": "... (P186)",
        "description_prompt_mul": "... (P189)",
        "alias_guidance_mul": "... (P187)",
        "alias_prompt_mul": "... (P190)"
      }
    },
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
  - Value options summary (linked profiles and value lists in `value.options`)
  - Key references/provenance pointers
- Auto-generated `CHANGELOG.md` contains profile history context with scoped depth:
  - SpiritSafe materialization run metadata (export timestamp, revision window, workflow context, optional manual release tag)
  - Wikibase history entries for the profile item itself
  - Optional future expansion to include linked statement-definition/specification item history
- Optional manual release tagging for curated checkpoints (format: `{meaningful-slug}`)

**CHANGELOG Scope Policy (initial):**
- Start with profile-by-profile history only (the profile item itself plus SpiritSafe materialization metadata).
- Do not include full transitive linked-item history in the initial release.
- Add linked history layers incrementally once we define depth limits, grouping rules, and noise controls.

**Workflow Stage: Cache Refresh + Profile Materialization**

SpiritSafe refresh should run as a single workflow stage:

- Detect Wikibase changes
- Refresh entity cache
- Generate optimized, runtime-ready SpiritSafe profile artifacts (`profile.json`, `manifest.json`, `README.md`, `CHANGELOG.md`)
- Write provenance metadata derived from Wikibase revision history and workflow run context

This stage is authoritative for both cache refresh and optimized profile generation; they are not separate operational tracks.

**Provenance Strategy (Revision-First):**

- Canonical provenance source is Wikibase history + extraction workflow metadata.
- Git tags are optional release markers, not required for every sync run.
- Scheduled/automated runs should not require manual tags.

**Optional Manual Release Tagging Convention:**

When manually creating milestone checkpoints (for communication, release notes, or rollback anchors), use feature-based naming instead of semantic versioning.

```bash
# Format: {slug-describing-change}
git tag initial-release
git tag added-office-linkage
git tag enhanced-validation-rules
```

**Tag naming guidelines (manual release mode):**
- Use past-tense verb phrase (2-5 words)
- Use kebab-case (lowercase with hyphens)
- Describe the primary significance of the change
- Examples of good slugs:
  - `added-canadian-jurisdiction-support`
  - `enhanced-reference-requirements`
  - `fixed-date-coercion-rules`
  - `removed-deprecated-statements`
  - `initial-release` (for first version)

**Chronology:** Git provides natural ordering; no semantic version comparison logic is required.

**Discovery:** List releases with `git tag --sort=-creatordate`

**Field Mapping from DD Wikibase Properties:**

| JSON Field | Wikibase Source | Notes |
|------------|----------------|-------|
| `entity` | Profile item entity URI | Canonical machine identifier |
| `metadata.profile_item.labels.{lang}` | Item labels | Presentation metadata; never used for identity |
| `metadata.profile_item.descriptions.{lang}` | Item descriptions | Presentation metadata |
| `metadata.profile_item.prompt_guidance.label_guidance_mul` | P185 statement | Label guidance text in `mul` |
| `metadata.profile_item.prompt_guidance.label_prompt_mul` | P188 statement | Label prompt text in `mul` |
| `metadata.profile_item.prompt_guidance.description_guidance_mul` | P186 statement | Description guidance text in `mul` |
| `metadata.profile_item.prompt_guidance.description_prompt_mul` | P189 statement | Description prompt text in `mul` |
| `metadata.profile_item.prompt_guidance.alias_guidance_mul` | P187 statement | Alias guidance text in `mul` |
| `metadata.profile_item.prompt_guidance.alias_prompt_mul` | P190 statement | Alias prompt text in `mul` |
| `statements[].id` | Normalized label of P157 target (GKC Entity Statement item) | e.g., Q16 → `instance_of`; always accompanied by `entity` (full URI) and `label` (display text) |
| `statements[].entity` | P157 mainsnak target entity URI | URI of the GKC Entity Statement item |
| `statements[].label` | Label from GKC Entity Statement item | Display name; `mul` preferred |
| `statements[].io_map[].to` | P5 on GKC Entity Statement item | Wikidata property URL |
| `statements[].value.type` | P194 on GKC Entity Statement → Wikibase Property Template (Q44) labels | One of 8 Wikibase primitive datatypes (e.g., `wikibase-item`, `string`, `time`, `quantity`, `url`, `monolingualtext`, `external-id`, `geo-shape`) |
| `statements[].value.fixed.entity` | P161 qualifier on P157 → Q52 (Wikidata Entity) target → P212 (same as) URL | Present when a specific Wikidata entity is required; exclusive of `options` |
| `statements[].value.fixed.label` | Label from the Q52 target item | Human-readable label for the fixed value |
| `statements[].value.default.entity` | P202 (default value) URL claim on GKC Entity Statement item | Optional Wikidata entity URI to pre-populate as statement default |
| `statements[].value.default.label` | P203 (default label) qualifier on P202 claim | Human-readable label for the default value entity |
| `statements[].value.options[]` | P161 qualifiers on P157 (or P161 on Q5 item with P205 qualifier) → Q3 or Q7 targets | Array of `{kind, entity, label}`; `kind` is `"profile"` (Q3 target) or `"value_list"` (Q7 target) |
| `statements[].prompt` | P171 qualifier on P157 (profile override) or P171 claim on GKC Entity Statement item | Required in `mul` for materialization; qualifier level takes precedence |
| `statements[].guidance` | P169 qualifier on P157 (profile override) or P169 claim on GKC Entity Statement item | Optional; qualifier level takes precedence |
| `statements[].consequences_message` | P170 qualifier on P157 (profile override) or P170 claim on GKC Entity Statement item | Optional; qualifier level takes precedence |
| `statements[].error_message` | P168 qualifier on P157 (most specific), P168 on GKC Entity Statement item, or P168 on Q44 type item (broadest fallback) | Displayed when validation fails |
| `statements[].max_count` | P182 qualifier on P157 | `novalue` → `null` (one or more); explicit quantity → integer |
| `statements[].qualifiers[]` | P158 (has qualifier) qualifiers on P157 claim | Array of `{entity, label}`; each `entity` is a GKC Entity Statement (Q5) |
| `statements[].references[]` | P211 (has reference) qualifiers on P157 claim | Array of `{entity, label}`; each `entity` is a GKC Entity Statement (Q5); OR semantics — at least one required |
| `metadata.exported_from` | Constructed from source Wikibase item URI | Export provenance |
| `metadata.export_timestamp` | Generated at export time | ISO 8601 timestamp |
| `metadata.source_revision_window` | Derived from Wikibase recentchanges / entity revision fetch | Revision range or change window used for this materialization run |
| `metadata.workflow_run_id` | GitHub Actions run metadata | Run identifier for traceability to automation logs |
| `metadata.workflow_mode` | Extraction pipeline mode | `manual` or `scheduled` |
| `registry_metadata.release` | Optional feature-based release slug | Present for manual milestone releases only |
| `registry_metadata.release_date` | Optional release timestamp | ISO 8601; set when `release` is present |
| `registry_metadata.git_tag` | Optional full git tag reference | Format: `{meaningful-slug}` when manual tag exists |

**Metadata Inclusion Rule:**
- Do not include placeholder metadata fields.
- A metadata field is eligible only when all three are true: (1) it has a concrete definition, (2) extraction can populate it deterministically, and (3) at least one downstream consumer uses it.
- Future candidate: `metadata.extractor_version` (gkc package version) once package release/version semantics are active and consumed by runtime tooling.

**Note on Release Tracking:**
- Default tracking is revision-first via Wikibase history and workflow run metadata.
- Feature-based git tags are optional and intended for manual milestone checkpoints.
- Tag format remains `{slug}` (no entity identifier in tag name).
- `registry_metadata` release/tag fields are populated only when a manual milestone tag is set for a run.
- Release history for manual checkpoints: `git log --tags --oneline --date-order`
- Authorship/attribution tracked via git commit history or documented in optional `README.md`
- No semantic versioning (x.y.z) required; git chronology provides ordering

**Traceability Note:**
- Entity/profile-level traceability is provided by auto-generated per-profile `CHANGELOG.md` content (Wikibase profile-item history + workflow/materialization metadata). Optional manual checkpoint tags augment this, but are not required for provenance completeness.

**Label Usage Guardrail:**
- Labels are for human-readable notice only.
- Identity and linkage must use `entity` (or other explicit entity URI fields).
- Any label changes must be treated as non-breaking presentation changes.

**Language Availability Guardrail:**
- Profiles are the authoritative source of available language content.
- Downstream consumers/processors must only operate on languages present in profile-derived packet metadata.
- Package-level default language should be `mul` for v2 profile processing and display initialization.
- Curation Packets should include language-availability metadata so interfaces (for example, Wizard) can offer language toggles only when supported.
- Profile label convention for pertinent Wikibase items is preferably `mul` label + `en` label, with `en` description.
- Monolingual prompt/guidance claims (including statement prompt/statement guidance and label/description/alias prompt/guidance) use `mul` as primary language; additional languages are optional and only materialized when they are comprehensive (no partial overlays).
- **BCP 47 primary subtag normalization:** DD Wikibase (and Wikidata) store monolingual text with language codes that may include region subtags (e.g., `en-us`, `en-gb`, `en-ca`). During SpiritSafe extraction, all language codes must be normalized to their BCP 47 primary language subtag (`en`, `es`, `de`, etc.) before writing to cache. Region-specific variants are collapsed into the primary subtag. This normalization is a fermenter primitive and must be applied consistently to all monolingual text fields (labels, descriptions, guidance, prompts) and to all language keys in charged entity content. Regional differentiation (e.g., `en-au` vs. `en-gb`) is deferred until there is an explicit content requirement for it.

**Materialization Validity Rules (mul-first enforcement):**

- A profile is minimally valid for SpiritSafe materialization when required prompt content exists in `mul`; at minimum, this includes prompt text mapped from P188.
- Hard-fail language enforcement applies at statement-level prompt/guidance surfaces (label prompt, label guidance, description prompt/guidance, alias prompt/guidance, statement prompt/guidance).
- Item label/description language coverage does not hard-fail materialization by itself.
- Prompt fields are required; guidance fields are optional.
- If required `mul` prompt content is missing, fail materialization for that profile.
- Additional languages are included only when they are comprehensive relative to `mul` for the relevant prompt/guidance surface. Partial language overlays are excluded from materialized output.
- When multiple statements exist for the same language/property slot, materialization deterministically takes the first value and records a finding in metadata.

**Materialization Findings Metadata:**

- Materialization should emit structured non-fatal findings in a run-level manifest report for operator review.
- Generated profile `README.md` files should include a concise listing/summary of relevant non-fatal findings for that profile.
- Findings should include at least:
  - missing required `mul` prompt fields (fatal)
  - duplicate language/property statements where first-value selection was applied
  - excluded partial language overlays
  - locations where optional guidance/consequence/error messages were absent

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

**Resolved Decisions (from current review):**

1. `io_map` remains an array.
2. Language encoding remains flattened by primary BCP 47 subtag.
3. Unlimited cardinality encoding should converge on `null` end-to-end.
4. Package default language is separate from Wikibase profile authoring requirements; profile-side `mul` requirements are not overridden by package default.
5. `statements[].value.type` may be derived from either machine-readable type metadata or canonical datatype labels when labels are guaranteed to match datatype identifiers.
6. Value lists are build-time, cache-first artifacts. Runtime consumers must not depend on live SPARQL execution.

**Resolved Direction: Value List Architecture**

- A value list is activated for materialization when the target item is classed as `GKC Value List` (Q7) and linked to the relevant statement via `has value` (P161). The P161 → Q7 linkage may appear as a qualifier on a profile's P157 claim, or as a claim on a GKC Entity Statement item with an `applies to profile` (P205) qualifier.
- The semantic source of truth stays in Wikibase item metadata (`wikibase_entity`, classification, applies-to linkage, directive text). The operational query definition should not rely on parsing arbitrary talk-page markup as the long-term machine contract.
- Preferred extraction contract: maintain the executable query as a repo-managed artifact keyed by value-list entity URI (for example, SpiritSafe query assets), and treat any talk-page `<sparql>` content as transitional authoring input or human-readable documentation rather than the canonical runtime/build interface.
- Each active value list must materialize to a deterministic cache artifact such as `cache/value_lists/{QID}.json` containing normalized items, build metadata, and freshness state.
- Value-list items should carry explicit refresh intent in Wikibase. Preferred design: add a dedicated property whose value is a controlled refresh-mode item (for example: `manual`, `scheduled-daily`, `scheduled-weekly`, `scheduled-monthly`) so extraction can decide whether a list participates only in manual hydration or in scheduled refresh stages.
- SpiritSafe remains the runtime-enabling cache, but it is not an unlimited blob store. Value-list artifacts should stay compact and optimized for the Wizard's actual type-ahead need, not for archival completeness.
- Practical delivery rule: cache the full materialized list in SpiritSafe only when the artifact remains comfortably usable by clients; when a list grows beyond the agreed interactive threshold, emit metadata marking it as non-inlineable for Wizard-local type-ahead and switch delivery to a static distribution strategy such as sharded JSON published via `datadistillery.org`.
- Initial UX-oriented threshold recommendation: lists in the low hundreds to low thousands should remain fully cacheable and directly usable for client-side type-ahead; anything materially larger should be treated as an optimization problem, not silently pushed into the same artifact contract.
- Materialization succeeds only when extraction can incorporate either: (a) a fresh query result, or (b) a previously committed fallback cache artifact. If neither is available, value-list materialization hard-fails.
- Runtime consumers (`fermenter`, Wizard, CLI, bulk tooling) read only the materialized SpiritSafe artifact. They do not execute SPARQL, scrape wiki pages, or invent fallback behavior independently.
- If a rebuild has to reuse fallback cache because live regeneration failed, that is a build finding with stale-state metadata, not a runtime concern. Consumers may surface staleness, but they still consume the same artifact shape.
- `datadistillery.org` may mirror generated JSON artifacts for browser-native consumers that need static HTTP delivery, but that mirror is a distribution layer, not an authoritative source or a separate cache contract.

**Resolved: Value List Architecture (additional)**

7. **Value list item contract (v1):** Each materialized value list artifact contains an array of `{"qid": "Q123", "label": "English label"}` objects — bare QID (not URI) plus English label. This is the smallest useful package. The SPARQL queries stored in discussion pages use `rdfs:label` filtered to `en`, which directly produces this shape. Matching/coercion behavior against those QIDs is fermenter-authoritative; display and type-ahead ranking are UI concerns.

8. **Interactive size threshold (initial benchmark):** No hard item-count threshold is imposed at this stage. The Office Held by Head of Government value list (~40,761 records from a full transitive `subclass of` `public office` query) is the current upper-bound benchmark and intentional stress test for Wizard and GitHub workflow capability. The `inlineable` metadata flag on cache artifacts is the mechanism for communicating delivery shape to consumers; extraction sets it based on observed artifact size. Threshold policy will be refined from real performance data against this benchmark.

9. **Default values (active, not future):** Default values are a current capability, not a future one. `language of work or name` (Q27) carries a `default value` (P202) claim of `http://www.wikidata.org/entity/Q1860` (English) with a `default label` (P203) qualifier at the qualifier statement level. The `value.default` field in the JSON schema is therefore active. Precedence rule: if a user has already supplied a value for the statement, the default is not applied; if the field is empty, the default is pre-populated. Default does not override user input, and is not enforced like a fixed value.

10. **Extraction strategy:** The previous approach (SPARQL identifier discovery → batched `wbgetentities`) had scope creep issues — it pulled in Q1 and other root class items not directly used in profiles. The preferred replacement strategy:

    - Start with a profile-scoped SPARQL query that traverses from `wdt:P1 wd:Q3` roots and collects only directly linked triples:

    ```sparql
    PREFIX wd: <https://datadistillery.wikibase.cloud/entity/>
    PREFIX wdt: <https://datadistillery.wikibase.cloud/prop/direct/>

    SELECT ?s ?p ?o WHERE {
      ?root wdt:P1 wd:Q3 .
      ?root (wdt:P1|wdt:P2)* ?s .
      ?s ?p ?o .
      FILTER(isIRI(?s) && isIRI(?p) && isIRI(?o))
      FILTER( !STRSTARTS(STR(?o), "https://datadistillery.wikibase.cloud/entity/statement/") )
    }
    ```

    - Follow with `wbgetentities` batch pulls for full authoritative JSON on discovered entity IDs.
    - Fallback route (for resilience): fetch GKC Entity Profile items via the initial SPARQL discovery, then follow the JSON graph outward from each profile item's statement structure. SPARQL remains required for the initial `wdt:P1 = wd:Q3` profile discovery step regardless of route.

## Theoretical Design Notes

- **Cross-interface fermenter contract:** the same fermenter invocation and result envelope should be used by wizard, CLI, and bulk tooling; only post-processing adapters differ by interface.
- **Module-contract follow-up:** `docs/architecture/module-contracts.md` should include an anti-duplication rule that forbids validation/coercion/policy execution logic outside fermenter.
- **Deferred: Statement-level processing policies** — properties for encoding statement-level processing or coercion policies exist in the Wikibase but are not currently modeled in the profile JSON contract. If fermenter-layer policy linkage is needed, those properties should be revisited before introducing new ones. Deferred until the Validation Agent fermenter contract is stable enough to define required inputs.
- **Value-list distribution note:** if browser-based consumers cannot conveniently read bundled SpiritSafe assets from local package state, publish the generated `cache/value_lists/*.json` artifacts to `datadistillery.org` as static files. This is only a transport convenience for clients and must not introduce a second source of truth.
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
      "entity": "https://datadistillery.wikibase.cloud/entity/Q4",
      "release": "added-office-linkage",
      "exported_at": "2026-03-09T10:00:00Z",
      "file_path": "profiles/Q4/profile.json"
    },
    {
      "entity": "https://datadistillery.wikibase.cloud/entity/Q39",
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
        "linkage_type": "P161",
        "bidirectional": true
      },
      {
        "source_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q39",
        "source_statement_entity": "https://datadistillery.wikibase.cloud/entity/Q42",
        "target_profile_entity": "https://datadistillery.wikibase.cloud/entity/Q4",
        "linkage_type": "P161",
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
- **Cross-references** — the inter-entity linkages derived from statement-level P161 (has value → Q3) options, materialized by SpiritSafe into downstream-friendly graph metadata
- **Cardinality constraints** — packet-level structural rules (min/max per linked entity type)
- **Profile package** — the full profile content embedded for downstream use (validation, form generation)
- **Value list routes** — resolved routing metadata for every value list referenced across loaded profiles, keyed by entity URI, providing the SpiritSafe cache path, item count, and inlineability flag so consumers can load lists without re-deriving paths
- **Packet identity** — `packet_id`, `operation_mode`, `created_at`, `manifest_commit_sha`

After assembly, the packet flows through: `still_charger` (charging entity data) → `cooperage` (barreling to Wikibase operation plan) → `shipper` (delivery).

### Value List Routing In The Packet

When a packet is assembled, the `value_list_routes` section is populated by scanning all statements across all loaded profiles for `value.options` entries of `kind: "value_list"`. Each unique value list entity URI found is resolved against the SpiritSafe manifest and its materialized cache metadata is embedded in the packet. This gives every downstream consumer a direct, pre-resolved pointer to the right artifact without needing to inspect the manifest independently.

```json
{
  "value_list_routes": {
    "https://datadistillery.wikibase.cloud/entity/Q28": {
      "label": "Tribal Government",
      "cache_path": "cache/value_lists/Q28.json",
      "item_count": 847,
      "inlineable": true
    },
    "https://datadistillery.wikibase.cloud/entity/Q43": {
      "label": "Public Office",
      "cache_path": "cache/value_lists/Q43.json",
      "item_count": 40761,
      "inlineable": false
    }
  }
}
```

Rules:

- `cache_path` is relative to the SpiritSafe root. Consumers resolve it against the configured SpiritSafe source path.
- `inlineable` reflects whether the full artifact is suitable for Wizard-local type-ahead. When `false`, the Wizard should use server-side search or static delivery (e.g., `datadistillery.org`) rather than loading the file in-process.
- `item_count` is sourced from the artifact's build metadata, not computed by the consumer.
- A value list whose cache artifact is absent at packet assembly time is a hard failure — the packet cannot be assembled for that profile.

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

In v2, all of these must use the `wikibase_entity` URI (e.g., `"https://datadistillery.wikibase.cloud/entity/Q4"`). The human-readable label from `labels.mul.label` (and localized labels such as `labels.en.label`) may be carried alongside for display, but must not be used as an identifier. This cascades through every stage (`still_charger`, `cooperage`, `spiritsafe`) that currently keys on profile name strings.

**Cross-references: manifest linkages vs. statement-embedded linkages**

In the current YAML-first flow, cross-references are assembled from precomputed manifest linkage data. In v2:

- Each statement's linked-profile options in `value.options` (P161 → Q3 targets) are embedded directly in `profile.json`
- The manifest's `profile_graph.edges` is a derived export artifact built from those statement-level P161 (has value → Q3) options for efficient traversal and indexing

**Decision:** The Wikibase source of truth for linked profiles remains the per-statement P161 (has value → Q3) linkage only. No separate profile-level linkage statement should be added to the DD Wikibase content model.

The DD Wikibase → SpiritSafe extraction process is responsible for converting those per-statement linkages into the most straightforward downstream structures:

- `profile.json` retains the per-statement linked-profile entries in `value.options` as the canonical semantic linkage record
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
    "default_language": "mul",
    "available_languages": ["mul", "en", "es"],
    "coverage": {
      "labels": ["mul", "en", "es"],
      "descriptions": ["en"],
      "guidance": ["mul", "en", "es"],
      "input_prompts": ["mul", "en", "es"]
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

Resolved direction: statement-level P161 (has value → Q3) linkages in Wikibase are the only authoritative semantic source for linked profiles. SpiritSafe extraction derives `manifest.json.profile_graph.edges` from those statement linkages so downstream packet assembly can remain efficient.

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

1. **Package-level default language** — a configurable gkc setting (e.g., `gkc.config.default_language`, defaulting to `"mul"`) that governs initial display and processing behavior for consumers such as Wizard instances and CLI output. This is a runtime concern, not stored in the packet; it provides the baseline when no other signal is present.

2. **Profile-declared languages** — the languages in which a profile provides input labels, guidance text, consequence metadata, and other monolingual content (P185–P190 fields). These are determined at SpiritSafe extraction time from the actual multilingual content present in DD Wikibase items. The `language_context.profile_languages` field captures this as the set of languages across all loaded profiles in the packet. A profile's available languages are the authoritative upper bound on what the Wizard can offer for guidance display; no UI should claim a language is available unless at least one loaded profile declares content in it.

3. **Charged-content languages** — when `still_charger` loads existing Wikibase entity data into the packet's `data` fields, that content may include language codes not declared in any loaded profile (for example, a previously curated entity has `de` labels even though the profile has no German guidance). These additional languages emerge during charging and must be captured in `language_context.content_languages` so consumers can surface them without suppressing existing content.

The `language_context` envelope in the packet should reflect the union outcome of sources 2 and 3, computed at charge time:

```json
{
  "language_context": {
    "package_default": "mul",
    "profile_languages": ["mul", "en", "es"],
    "content_languages": ["mul", "en", "es", "de"],
    "guidance_coverage": {
      "mul": "full",
      "en": "full",
      "es": "partial",
      "de": "none"
    }
  }
}
```

Where `guidance_coverage` indicates, per language, whether the profile provides full guidance (all monolingual fields present), partial guidance (some present), or none (language present only in charged content, no profile guidance available).

**Key rule:** `package_default` should always be satisfied by `profile_languages`. If configured/default `mul` is not present in loaded profile languages, emit a high-visibility conformance warning and fall back to `en` (if present), otherwise first available profile language.

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

- `workflow_policy` is deprecated in v2. Wizard linked-profile affordances should default to showing both "Create new" and "Select existing" for statements with `value.options` entries of `kind: "profile"`. Any limits should come from profile semantics (fixed/default behavior, cardinality, validation results), not a separate linkage policy gate.
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
  - Extract all P161, P158, P211, P194 referenced entity identifiers from fetched statement-definition items
  - Fetch full Wikibase JSON for value targets (Q52, Q3, Q7 items), additional qualifier/reference spec items (Q5), and statement type items (Q44)
  - Cache raw JSON

4. **Transform to JSON Cache**
   - For each profile item:
     - Map Wikibase claims structure → JSON profile schema
    - Resolve entity URIs to display labels for UI/help text only
     - Flatten monolingual text fields by language code, normalizing all BCP 47 region subtags to primary subtags (`en-us` → `en`, `en-gb` → `en`, etc.) before writing to cache
  - Compute language availability metadata from labels/descriptions/guidance/prompt fields
    - Extract statement-level P161 (has value → Q3) options as the authoritative linkage source and build the derived edge list for manifest
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
  - Build profile graph from statement-level P161 (has value → Q3) link options extracted from profile content
  - Treat manifest graph data as a denormalized traversal/index artifact, not an independent semantic source
  - Enumerate all ontology items used
  - Write `cache/manifest.json`

7. **Validate Cache Integrity**
   - JSON schema validation on all profile.json files
  - Verify all P161 (has value → Q3) linked profile options resolve to existing profile entities
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
- Circular P161 (has value → Q3) linkages → detect and flag in manifest (not an error)
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
       - `value.options` linked-profile entries (reference integrity against manifest)
   - **Dependencies:** None (pure data model)
   - **Handoff:** Validation Agent to update models

4. **`gkc/profiles/validation/`** (consume new schema for validation)
   - **Current State:** Validators consume YAML-based profile structure
   - **Required Changes:**
     - Update `ProfileValidator` to use new `StatementDefinition` structure
     - Add P161 (has value → Q3) linked profile recursive validation (with depth limit)
     - Add P158 (has qualifier) sub-statement validation
    - Add P211/P161 reference and value handling as fermenter API dispatch metadata (no UI-specific branching)
   - **Dependencies:** `gkc.profiles.models` updates, fermenter module (future)
   - **Handoff:** Validation Agent to update validators

5. **`gkc/profiles/forms/` or `gkc/profiles/generators/`** (wizard form generation)
   - **Current State:** `FormSchemaGenerator` consumes YAML profiles
   - **Required Changes:**
     - Update form generator to read from JSON cache
     - Extract P185-P190 guidance properties for field-level help text
     - Generate P161 (has value → Q3) linked profile affordances ("Create new" / "Select existing" buttons)
     - Extract P158 expected qualifiers for sub-form rendering
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
      - Add "Profile Graph and Cross-Profile Linkages" section (P161 has-value→Q3 linked profile architecture)
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
- [ ] `gkc/profiles/forms/*.py` or `gkc/profiles/generators/*.py` (P161 linked profiles, P185-P190 guidance)
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
4. Updated `gkc.profiles.validation` to enforce P161/P158/P211 constraints
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
3. Validation depth limit for P161 (has value → Q3) recursive linked-profile checks: 2 levels sufficient, or configurable?
4. What is the minimal authoritative value-list payload fermenter requires for validation/coercion without overfitting to Wizard search convenience?
5. (OQ9) What is the minimum conformance surface for Wikibase → SpiritSafe ingestion? Resolution needed before extraction pipeline implementation begins; see Development Sequencing Note above.

**Note on Fermenter / Validation sequencing:** Per the Development Sequencing Note above, a minimal fermenter primitive layer is part of the extraction pipeline deliverable — not deferred. The `spirit_safe` module deliverables should include at minimum a composable conformance check function that evaluates raw `wbgetentities` output against the minimum ingestion surface. Design these primitives for reuse in `still_charger` and other Wikibase/Wikidata inbound pipelines from the start.

### To Wizard Engineer

**Scope:** Update form generation to consume new JSON schema and render P161 (has value → Q3) linked profile affordances

**Start Condition:** Begin only after Profile Architect + Validation Agent finalize packet shape and conformance notice codes.

**Deliverables:**
1. Updated `FormSchemaGenerator` (or equivalent) to:
   - Read from JSON cache via updated `ProfileLoader`
   - Extract P185-P190 monolingual text fields for field-level guidance display
   - Generate "Create new [Linked Profile]" button for statements with P161 (has value → Q3) options
   - Generate "Select existing [Linked Profile]" type-ahead search widget
   - Render P158 (has qualifier) expected qualifier statements as sub-form fields
2. Profile graph navigation affordances:
   - Display profile dependency graph (visualize P161 linked-profile edges from manifest.json)
   - Breadcrumb trail for nested profile curation sessions
   - Modal/panel UI for "Create new" workflow (open linked profile wizard, return item reference)
3. Test coverage for:
   - Form rendering with P161 (has value → Q3) linked profile affordances (visual regression tests or snapshot tests)
   - Graph traversal navigation (integration tests simulating multi-profile workflows)

**Expected Inputs:**
- JSON schema specifications from this document
- Manifest profile_graph structure (edges with source/target profiles)
- Cross-Profile Interlinkage Architecture section from WikibaseInitV2.md (lines 800-1243)

**Open Questions for Wizard Engineer:**
1. Should "Create new" open a modal, new tab, or inline expansion? (UX decision)
2. How to handle **bidirectional linkages** in UI (`https://datadistillery.wikibase.cloud/entity/Q4` ↔ `https://datadistillery.wikibase.cloud/entity/Q39`)? Show both directions, or hide reciprocal?
3. Type-ahead search constraints: filter by P161 (has value → Q3) linked profile only, or allow broader search with validation warning?
4. How to display P158 (has qualifier) expected qualifier statements: always visible, or collapsible "Advanced" section?

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
- [ ] Manifest.json generated with profile graph edges (P161 has-value→Q3 linkages)
- [ ] `ProfileLoader` reads JSON cache without errors
- [ ] `ProfileValidator` enforces new schema constraints (P161/P158/P211)
- [ ] Existing test suite passes against JSON cache (regression-free)
- [ ] `foundation_profiles/` directory deleted, no remaining references in codebase

**Should Have (High Priority):**
- [ ] `FormSchemaGenerator` renders P161 (has value → Q3) linked profile affordances
- [ ] P185-P190 guidance properties displayed in wizard forms
- [ ] P158 (has qualifier) expected qualifier statements rendered as sub-form fields
- [ ] Documentation updated (profiles.md, module-contracts.md)
- [ ] Test coverage for extraction pipeline (unit + integration tests)
- [ ] `wikidata_normalizer` relocated to shipper module

**Nice to Have (Future Enhancement):**
- [ ] Automated sync workflow (GitHub Actions or webhook trigger)
- [ ] Profile cache staleness detection and refresh recommendations
- [ ] Recursive profile validation with configurable depth limit
- [ ] Value-list static distribution optimization for large artifacts
- [ ] Multi-system io_map support (Wikidata + OpenStreetMap + Commons)

---

## GitHub Issue Triage Mapping (2026-03-13)

### Already Closed as OBE — Superseded by V2 Reset

These were closed in the V2 reset. Listed here for audit trail only.

| # | Title | Absorbed Into |
|---|-------|---------------|
| #87 | Develop an approach on profile-level override/reconciliation on languages setting | Language and Text Policy in `wikibase_ontology_orientation.md` |
| #90 | Auto-Creation Pattern for Fixed-Value Statements | P161 (has value → Q52) fixed value semantics |
| #92 | Language Declaration & Configuration Clarity | Language and Text Policy |
| #93 | Quantity Datatype Unit Behavior Signaling | Deferred; no V2 quantity support planned |
| #94 | Form Policy Clarity and Extensibility | Curation Packets v2 / Wizard contract |
| #95 | Missing Consequence Warnings and Implications | P170 `consequences_message` in unified statement model |
| #101 | Issue template: Profile Concept / Design Issue | Template issue; superseded by architecture docs |
| #120 | Design and plan fermenter module | §Wikibase → SpiritSafe Extraction Pipeline |

### Open Issues to Close as ProfilesV2 Work Lands

#### Foundation — DD Wikibase Ontology & SpiritSafe (Milestone: V2 Core, priority:p0)

Close these when the SpiritSafe extraction pipeline passes CI and the ontology docs are merged.

| # | Title | ProfilesV2 Section That Addresses It | Closure Trigger |
|---|-------|---------------------------------------|-----------------|
| #121 | Define DD semantic model for Fermenter registries | `wikibase_ontology_orientation.md` entity class hierarchy + property reference tables | Ontology doc merged and reviewed by Semantic Engineer |
| #122 | Build SpiritSafe manifest projection + sync pipeline | §Wikibase → SpiritSafe Extraction Pipeline | Extraction pipeline produces valid SpiritSafe JSON cache artifacts in CI |
| #124 | Specify DD query contracts for Fermenter resolvers | Resolved Decision #10 (extraction strategy: profile-scoped SPARQL + wbgetentities) | SPARQL queries committed to SpiritSafe `queries/` and validated against DD Wikibase SPARQL endpoint |
| #125 | Design DD snapshot/export path for deterministic offline fallback | §SpiritSafe Cache Structure | SpiritSafe JSON cache is consumable offline with no live Wikibase dependency |
| #126 | Add Fermenter contract tests for DD online/offline parity | §Fermenter First Instantiation | Online/offline parity contract tests pass in CI |
| #123 | Define multilingual validation message registry and key namespace | Language and Text Policy + P168/P169/P170/P171 guidance architecture in `wikibase_ontology_orientation.md` | Guidance message model implemented; `en` fallback requirement validated |

#### Coercion & Validation Primitives (Milestone: V2 Core, priority:p0–p1)

Close each issue individually as the corresponding coercion module or validation component passes unit tests.

| # | Title | ProfilesV2 Section That Addresses It | Closure Trigger |
|---|-------|---------------------------------------|-----------------|
| #102 | ValidationIssue model and coercion return contract | §Curation Packets v2 (`conformance_report` notice contract) | `ValidationIssue` Pydantic model merged; all coercion returns use it |
| #103 | Coercion dispatcher and datatype registry | §Code Refactor Plan; P194 (statement type → Q44) architecture | Dispatcher routes correctly to all declared Q44-typed statement primitives |
| #104 | Time datatype coercion and precision normalization | §Fermenter primitives; P194/Q44 typing | Time coercion unit tests pass |
| #105 | Item QID coercion and allowed-items validation | Value list + fixed value semantics; Resolved Decision #7 | Item coercion validates against value list cache and fixed-value constraint; unit tests pass |
| #106 | Monolingual text coercion and language code normalization | Language and Text Policy; fermenter primitive | Monolingual coercion normalizes BCP-47 codes; unit tests pass |
| #107 | URL coercion and normalization | §Fermenter primitives (sitelink URL routing deferred to #91) | URL coercion unit tests pass |
| #108 | Wizard inline coercion hooks for values, qualifiers, and references | §Curation Packets v2; Fermenter/Wizard boundary in §Handoff Boundaries | Wizard coercion hooks call fermenter dispatcher and surface `ValidationIssue` notices inline |
| #109 | Review-stage comprehensive entity validation pass | §Curation Packets v2 (`conformance_report` structure) | Review-stage validation populates `conformance_report` and all notice types surface in wizard UI |
| #110 | Packet-level cardinality enforcement | §Curation Packets v2 (`max_count` null = unlimited encoding) | Cardinality enforcement respects `max_count` across all statement types; unlimited case handled |
| #111 | Packet cross-reference and reciprocal consistency checks | §Curation Packets v2 (cross-entity assembly section) | Reciprocal consistency checks run at packet review stage and issues surface in `conformance_report` |
| #112 | Cross-entity constraint validator framework | §Curation Packets v2 (cross-reference / conformance report) | Framework invoked automatically for all multi-entity packets |
| #113 | Packet validation test matrix and fixtures | §Temporary Test Forcefits To Unwind | All forcefit tests replaced with v2 fixture-based test matrix |

#### Wizard & UX (Milestone: V2 Core, priority:p1)

| # | Title | ProfilesV2 Section That Addresses It | Closure Trigger |
|---|-------|---------------------------------------|-----------------|
| #117 | Wizard multi-entity packet integration | §Curation Packets v2 (`value_list_routes`, cross-entity assembly) | Multi-entity wizard flow is integrated with packet contract; `value_list_routes` consumed by UI |
| #118 | Wizard packet persistence and recovery | §Curation Packets v2 (packet structure and state) | Packet persistence and recovery implemented in wizard; partial packet survives session interruption |

#### Documentation (Milestone: V2 Core, priority:p1)

| # | Title | ProfilesV2 Section That Addresses It | Closure Trigger |
|---|-------|---------------------------------------|-----------------|
| #114 | Curator guide to SpiritSafe profiles | §SpiritSafe Cache Structure + `wikibase_ontology_orientation.md` | Curator-facing guide published in `docs/` |
| #115 | Curator CLI quickstart guide | §Code Refactor Plan (CLI command surface) | CLI commands implemented and documented in `docs/` |
| #116 | Profile catalog reference for curators | §SpiritSafe Cache Structure (per-profile README generation) | Profile catalog published in `docs/` or SpiritSafe README; auto-generated from manifest |

#### Cooperage Cleanup (Milestone: V2 Core, priority:p1)

| # | Title | ProfilesV2 Section That Addresses It | Closure Trigger |
|---|-------|---------------------------------------|-----------------|
| #133 | Clean-up old stuff from cooperage | §Code Refactor Plan (cooperage boundary redefinition) | Cooperage stripped of deprecated methods; all existing tests pass against refactored module |

### Open Issues Not Directly Addressed by ProfilesV2

These follow-on enhancements are out of scope for V2 Core. Leave open and revisit after V2 Core is complete. ProfilesV2 establishes the architectural foundation they depend on.

| # | Title | Milestone | Relationship to ProfilesV2 |
|---|-------|-----------|---------------------------|
| #96 | Cross-Entity Statement Forwarding and Dependency Chains | V2 Follow-ons | P161 → Q3 linked profile semantics establishes the required foundation |
| #97 | Specialized References Government Document Hydration | V2 Follow-ons | P211 (`has reference`) OR-semantics architecture supports this; domain-specific paths not yet designed |
| #98 | Whitelist-Based Statement Filtering Multi-Entity Workflows | V2 Follow-ons | Requires packet + validator framework from V2 Core first |
| #99 | Profile Versioning and Backward Compatibility | V2 Follow-ons | ProfilesV2 JSON schema is now frozen; versioning strategy is Open Question #4 in this doc |
| #100 | Bulk Reference Operations and Batch Hydration | V2 Follow-ons | Bulk reference tooling mentioned; full specification deferred to post-V2 Core |
| #91 | Sitelinks URL-Based Entry & Bidirectional URL Resolution | V2 Follow-ons | Sitelinks deferred per Resolved Decision #7; revisit after URL coercion (#107) lands |

### Issue Hygiene Guidance

- Close issues in the "Open Issues to Close" tables above as each closure trigger is satisfied. Add a comment on the issue referencing the relevant ProfilesV2 section.
- Open new issues only for executable units with concrete acceptance criteria and module-level ownership. Do not open issues for items that already have a clear home in the architecture docs.
- Do not reopen OBE issues. If a requirement resurfaces, open a new issue with a forward reference.

---

## Schema Freeze Checkpoint (2026-03-14)

The profile JSON schema is now frozen for implementation handoff.

Freeze evidence from refreshed local SpiritSafe cache:

- No remaining P159 entries in `cache/entities/*`.
- No remaining P183 entries in `cache/entities/*`.
- P211 is present in statement qualifier structures for active profiles (for example, Q4 and Q39).
- Refresh summary timestamp confirms latest local sync window (`since: 2026-03-14T23:50:50.412369Z`, `next_since: 2026-03-14T23:55:19Z`).

Frozen contract decisions:

1. `io_map` remains an array in v2.
2. Value-list handling remains cache-first; runtime consumers do not execute SPARQL.
3. Reference expectations are modeled only through P211 (`has reference`) with hard OR semantics: at least one listed reference type is required.
4. P159 is in hiatus and is non-authoritative for v2 extraction and validation.
5. Reference and qualifier links stay as entity URIs in cache; labels are resolved in UI via manifest ontology lookup.
6. Default values (`value.default`) are active and non-overriding when user input already exists.
7. Profile item labels/descriptions and P185-P190 profile-level guidance/prompt surfaces are materialized under `metadata.profile_item`, not in root statement specification fields.

Follow-on policy items that remain implementation-level (not schema blockers):

- Version mismatch behavior between cache and source (`warn vs block`).
- Recursive linkage traversal depth defaults and configurability.

---

## Next Actions (Immediate)

**Profile Architect:**
1. Confirm schema freeze in this document and hand off implementation contract to Validation Agent and Wizard Engineer.
2. Draft SPARQL extraction queries and test against DD Wikibase query service.
3. Create example JSON profile fixture for `https://datadistillery.wikibase.cloud/entity/Q4` in `tests/fixtures/profiles/`.
4. Track cache refresh drift: if P159 or P183 reappear, block materialization and open a semantic-model issue immediately.

**Profile Architect + Validation Agent (kickoff now):**
1. Implement first iteration of `ProfileExtractor` directly in `gkc.spirit_safe` against refreshed cache entities.
2. Scope Iteration 1 to deterministic transformation only: `entity`, statement extraction, P211 OR-reference sets, P158 qualifiers, P161 fixed/default/options, and `metadata.profile_item` (labels/descriptions + P185-P190 prompts/guidance).
3. Add fixture-backed extractor tests using Q4 cache input and assert no legacy P159/P183 dependency in output.

**Validation Agent (after Profile Architect approval):**
1. Implement `gkc.spirit_safe` extraction pipeline (ProfileExtractor + ManifestGenerator)
2. Update `gkc.profiles.models` Pydantic schemas to match v2 JSON structure
3. Update `gkc.profiles.loaders` to read JSON cache
4. Write test suite for extraction and loading (unit + integration tests)

**Wizard Engineer (after Validation Agent completes Priority 1):**
1. Update `FormSchemaGenerator` to consume new JSON schema
2. Implement P161 (has value → Q3) linked profile affordances ("Create new" / "Select existing")
3. Extract and render P185-P190 guidance properties in forms
4. Test form rendering with SpiritSafe JSON fixtures

**Profile Architect (absorbed wikibase cleanup scope):**
1. Keep foundation-path deprecation and orchestration contract cleanup on the architecture track
2. Freeze orchestration contract assumptions for Validation Agent implementation
3. Document compatibility constraints for `cooperage` and `bottler`
4. Hand off only after validation-facing contract artifacts are explicit and testable

---

**Document Version:** 1.5  
**Last Updated:** 2026-03-15  
**Next Review:** After Phase 1 completion (JSON cache extraction functional)
