# Wikibase Init V2 - Refactor Revisit Log 

## Purpose

This prompt captures the current working-state deltas to revisit during a simplification/refactor pass before continuing implementation.

Primary goal for V2:

- Keep the dry-run -> inspect -> execute workflow pattern.
- Reduce complexity and realign profile-sync modeling with the GKC Entity Profile spec.
- Re-scope or replace divergent "profile_profile" artifacts with Profile Architect.

---

## **MAJOR ARCHITECTURAL PIVOT (2026-03-09)**

**New Source of Truth: Data Distillery Wikibase**

All previous work on the Wikibase initialization approach is being **scrapped and replaced**.

### What's Changing

**Old Approach (DEPRECATED):**
- Hand-crafted YAML "profile_profile" files attempting to encode transformation rules
- Foundation profiles directory with special-case schemas
- Wikibase init code that tried to generate items from YAML templates

**New Approach (ACTIVE):**
- **Data Distillery Wikibase is the authoritative source** for GKC Entity Profile definitions
- Profiles, properties, and specifications are curated **directly in the Wikibase** using native Wikibase items and statements
- **SpiritSafe becomes a materialized cache** - a transformed, optimized view of Wikibase content for gkc runtime consumption
- SPARQL extraction + transformation pipeline syncs Wikibase → SpiritSafe YAML cache

### Cleanup Required

**Delete These Artifacts:**
- `gkc/wikibase/foundation_profiles/` (entire directory and all YAML files)
  - `entity_profile_profile.yaml`
  - `property_profile.yaml`
  - `specification_profile.yaml`
  - `foundation_metadata.yaml`
  - `PROFILE_PROFILES_README.md`
- Previous wikibase init code in `gkc/wikibase/` module (to be identified and removed)
- `notebooks/WikibaseInit.ipynb` (existing approach obsolete)

**Preserve/Refactor:**
- SpiritSafe profile packages (TribalGovernmentUS, OfficeHeldByHeadOfState) - these become **reference examples** of the cache format
- Profile loading/validation code in `gkc/entity_profile.py` and `gkc/spirit_safe.py` - still needed for reading cache
- SPARQL utilities in `gkc/sparql.py` - will be leveraged for extraction

### Implementation Plan

1. Document the Wikibase ontology structure (in `.drafts/GKC_Entity_Profile_Anatomy.mediawiki`)
2. Build SPARQL-based extraction pipeline (Wikibase → intermediate format)
3. Build transformation layer (intermediate → SpiritSafe YAML cache)
4. Create sync workflow/tooling
5. Validate round-trip: Wikibase → cache → runtime loading

---

## Design Considerations for Implementation (2026-03-09)

### Cache Format: YAML vs Alternatives

**Current State:** SpiritSafe uses YAML as the serialization format for cached profile content.

**Question:** Should we continue with YAML or migrate to JSON/other format?

**Considerations:**
- The primary user-facing artifact is now **the Wikibase itself** (not the cache files)
- gkc already performs JSON transformations internally (except for Curation Packets, which are curator-facing)
- YAML offers human readability, comments, and anchors/aliases for reference patterns
- JSON offers strict parsing, ubiquity, and native Python/JS compatibility

**Recommendation (TBD):** 
- *To be decided based on:*
  - Runtime performance requirements
  - Cache diff/merge workflow needs
  - Curator inspection use cases for cached files
  - Tooling ecosystem compatibility

**Action:** Profile Architect to propose recommendation after examining:
- Current YAML anchor usage patterns in TribalGovernmentUS/OfficeHeldByHeadOfState
- Size/complexity of generated cache files
- Frequency of manual cache inspection vs programmatic consumption

### Atomic Delineation Principle

**Requirement:** Each concept translated from Wikibase structure into gkc code-actionable config logic must be:
1. **Clearly delineated** - a distinct, named construct in the codebase
2. **Relatively atomic** - single-purpose, composable units
3. **Explicitly documented** - mapping from Wikibase property → YAML field → runtime behavior
4. **Incrementally manageable** - changes are localized and testable

**Rationale:** Enables clear documentation, precise testing, and controlled evolution of the ontology-to-runtime translation layer.

**Implementation Implications:**
- Each DD Wikibase qualifier property (P159, P161, P162, P171, P182, P183, etc.) maps to exactly one YAML construct
- Entity identifiers are URI-first: store resolvable entity URIs (e.g., `https://datadistillery.wikibase.cloud/entity/Q4`) rather than bare `Q...` tokens
- Validation/coercion logic is modular and referenced (not embedded) in profiles
- Form generation rules are derived from atomic metadata, not heuristics

**Action:** Maintain a canonical **Property-to-Semantics Mapping Table** (below) as the authoritative contract.

---

## Wikibase Structure Analysis (2026-03-09)

### Profile Item Anatomy (URI Exemplars)

**Core Discovery:** DD Wikibase profile items (`https://datadistillery.wikibase.cloud/entity/Q4` "Tribal Government in the United States", `https://datadistillery.wikibase.cloud/entity/Q39` "Office Held by Head of Government") use a rich statement-with-qualifiers pattern that maps cleanly to the YAML profile model with important extensions.

**Key Structural Patterns:**

1. **Profile Identity** (standard Wikibase item fields)
   - `labels` → YAML `name`, `labels.{lang}.label`
   - `descriptions` → YAML `description`, `descriptions.{lang}.label`
   - `aliases` → YAML `aliases.{lang}.label`

2. **Profile Classification**
   - `P1` (instance of) → `https://datadistillery.wikibase.cloud/entity/Q3` (GKC Entity Profile) — establishes profile class membership

3. **Statement Definitions** (via `P157` with qualifiers)
   - Each `P157` statement represents one profile field/statement
   - **Mainsnak target** = the property item being specified (e.g., `https://datadistillery.wikibase.cloud/entity/Q16` "instance of", `https://datadistillery.wikibase.cloud/entity/Q19` "official website")
   - **Qualifiers** encode field-level metadata:
     - `P171` (consequence message text) — monolingual guidance for curators
     - `P182` (cardinality) — max count (`novalue` = unlimited, `+1` = exactly one, etc.)
     - `P183` (fixed value link) — when value is constrained to a specific external URI
     - `P159` (validation policy) — references validation mode item
     - `P161` (form policy) — references form generation behavior items (can be multiple)
   - `P162` (linked profile) — cross-profile dependency/navigation (`https://datadistillery.wikibase.cloud/entity/Q4` ↔ `https://datadistillery.wikibase.cloud/entity/Q39` linkage)
     - `P164` (allowed values) — references constraint items for value lists

4. **Curator Guidance Properties** (monolingual text)
   - `P185` (label guidance) — instructions for label field
   - `P186` (description guidance example) — format/content examples
   - `P187` (alias guidance) — when/how to use aliases
   - `P188` (label field description) — semantic definition
   - `P189` (description field description) — semantic definition
   - `P190` (alias field description) — semantic definition

5. **Cross-Profile Interlinkage**
   - `https://datadistillery.wikibase.cloud/entity/Q4` P157[target=`https://datadistillery.wikibase.cloud/entity/Q40` "office held by head of government"] has qualifier `P162→https://datadistillery.wikibase.cloud/entity/Q39`
   - `https://datadistillery.wikibase.cloud/entity/Q39` P157[target=`https://datadistillery.wikibase.cloud/entity/Q42` "applies to jurisdiction"] has qualifier `P162→https://datadistillery.wikibase.cloud/entity/Q4`
   - Enables wizard navigation and packet dependency graph construction

### Datatype Taxonomy (GKC Entity Statement Items)

**Query Results:** 16 statement-definition items classified as `https://datadistillery.wikibase.cloud/entity/Q5` (GKC Entity Statement) with declared datatypes via `P194`:

| Datatype | Count | Examples (Entity URI: Label → Wikidata Property) |
|----------|-------|-------------------------------------------|
| **item** | 7 | https://datadistillery.wikibase.cloud/entity/Q16: instance of → P31<br>https://datadistillery.wikibase.cloud/entity/Q27: language of work or name → P407<br>https://datadistillery.wikibase.cloud/entity/Q30: stated in → P248<br>https://datadistillery.wikibase.cloud/entity/Q40: office held by head of government → P39 |
| **monolingual text** | 2 | https://datadistillery.wikibase.cloud/entity/Q32: native label → P1705<br>https://datadistillery.wikibase.cloud/entity/Q34: street address → P6375 |
| **url** | 2 | https://datadistillery.wikibase.cloud/entity/Q19: official website → P856<br>https://datadistillery.wikibase.cloud/entity/Q29: reference URL → P854 |
| **commons media file** | 1 | https://datadistillery.wikibase.cloud/entity/Q38: flag image → P41 |
| **datetime** | 1 | https://datadistillery.wikibase.cloud/entity/Q37: inception → P571 |
| **geographic coordinates** | 1 | https://datadistillery.wikibase.cloud/entity/Q36: coordinate location → P625 |
| **quantity** | 1 | https://datadistillery.wikibase.cloud/entity/Q21: member count → P2124 |
| **string** | 1 | https://datadistillery.wikibase.cloud/entity/Q35: postal code → P281 |

**Implication:** The `fermenter` module (TBD) will need atomic validators/coercers for these 8 primitive datatypes as the base validation layer.

### Semantic Clarifications

**Required-But-Optional Pattern:**
- All fields are structurally "required" (must be declared in the profile)
- All fields are data-optional (curator may leave them empty)
- Missing data triggers consequence messaging via `P170` (consequence message text)
- Used for wizard review stage warnings: "You have not supplied X"

**Max Count Encoding:**
- `P182` with `novalue` → unlimited cardinality (0+)
- `P182` with `+1` → exactly one required
- `P182` with `+0` → not used (would mean "forbidden")

**Validation Policy Modes** (via `P159` qualifier):
- References items like `https://datadistillery.wikibase.cloud/entity/Q31` that define validation behavior
- Examples likely include: `strict`, `allow_existing_nonconforming`, `warn_only`, etc.
- **Action:** Enumerate and document all validation policy items in DD Wikibase

**Form Policy Modes** (via `P161` qualifier):
- Can have **multiple** values (array of policy items)
- Examples: `https://datadistillery.wikibase.cloud/entity/Q23`, `https://datadistillery.wikibase.cloud/entity/Q24` (TBD labels/semantics)
- Likely controls: field visibility, editability, default values, conditional display
- **Action:** Enumerate and document all form policy items in DD Wikibase

---

## Current Status Summary (2026-03-08)

### ✅ Completed Work

**Profile Architecture (Profile Architect)**
- ✅ Three new SpiritSafe profile packages created and validated:
  - `GKCEntityProfile` (5 statements)
  - `GKCEntityProperty` (6 statements)
  - `GKCPropertySpecification` (3 statements, shell)
- ✅ All packages follow SpiritSafe conventions (metadata.yaml, profile.yaml, README.md, CHANGELOG.md)
- ✅ Registry README updated with new profile entries
- ✅ Packages parse successfully with ProfileLoader

**Runtime Migration (Semantic Engineer)**
- ✅ `io_map` architecture fully implemented in runtime:
  - Profile models with directional validation
  - JSON schema updated
  - Generators migrated (form_generator, pydantic_generator)
  - Validation components migrated (validator, wikidata_normalizer)
  - Cooperage mapping logic migrated
- ✅ Test fixtures migrated to `io_map`
- ✅ Focused regression suite passing (30/30 tests)
- ✅ Documentation fully rewritten (`docs/gkc/profiles.md`)

### ⚠️ Outstanding Work

**Critical: Profile Routing Correction (Semantic Engineer - Current Priority)**
- ⚠️ All three new profile packages route to Wikidata properties instead of DD Wikibase
- ⚠️ Need DD Wikibase foundation audit results to map correct property URIs
- ⚠️ Audit results exist in `/tmp/dd_wikibase_audit.txt` (43 conformant entities)
- ⚠️ Require property ID mappings for:
  - instance of, version, status, documentation URL, has parts/components
  - property key, datatype, role, belongs to
  - specification key, governs

**Runtime Cleanup (Semantic Engineer - Next Priority)**
- ⚠️ still_charger cleanup needed per architectural corrections
- ⚠️ cooperage refinement needed per architectural corrections
- ⚠️ Test fixture packages for meta-profiles not yet created

**Deferred Work**
- Notebook flow simplification (WikibaseInit.ipynb)
- Profile_profile artifact removal:
  - `gkc/wikibase/foundation_profiles/entity_profile_profile.yaml`
  - `gkc/wikibase/foundation_profiles/property_profile.yaml`
  - `gkc/wikibase/foundation_profiles/specification_profile.yaml`
  - `gkc/wikibase/foundation_profiles/PROFILE_PROFILES_README.md`

---

## Current Untracked Changes to Revisit

These files are currently untracked and should be reviewed explicitly during the refactor pass.

### New profile-sync/modeling artifacts (high priority)

- `gkc/wikibase/foundation_profiles/PROFILE_PROFILES_README.md`
- `gkc/wikibase/foundation_profiles/entity_profile_profile.yaml`
- `gkc/wikibase/foundation_profiles/property_profile.yaml`
- `gkc/wikibase/foundation_profiles/specification_profile.yaml`

Revisit intent:

- Confirm whether these should be removed, replaced, or rewritten to align tightly with the GKC Entity Profile schema.
- Preserve only fields and behaviors needed for the immediate profile+property sync goal.
- Defer specification modeling until fermenter direction is finalized.

### New runtime pipeline artifacts

- `gkc/still_charger.py`
- `gkc/wikibase/orchestration.py`

Revisit intent:

- Keep if aligned to the simplified architecture and shared packet->charge->barrel->ship flow.
- Trim/adjust APIs based on revised profile package design and hydration inputs.

### New docs and notebooks

- `docs/gkc/api/still_charger.md`
- `notebooks/CurationPacket.ipynb`
- `notebooks/WikibaseInit.ipynb`

Revisit intent:

- Keep notebook operator pattern, but reduce scope and cognitive overhead.
- Ensure notebooks reflect only implemented behavior and current architecture decisions.

### New tests

- `tests/test_cooperage_barreling.py`
- `tests/test_still_charger.py`
- `tests/test_utilities_name_resolution.py`
- `tests/test_wikibase_orchestration.py`

Revisit intent:

- Keep coverage for validated behaviors that remain in V2 scope.
- Remove or rewrite tests tied to discarded profile-profile assumptions.

## Modified Files Also In Scope for Refactor Review

These tracked modifications may need cleanup/reconciliation with the V2 architecture:

- `.github/agents/Profile Architect.agent.md`
- `.github/prompts/WikibaseV1.md`
- `docs/architecture/module-contracts.md`
- `docs/gkc/api/cooperage.md`
- `docs/gkc/api/index.md`
- `docs/gkc/api/wikibase.md`
- `docs/gkc/cli/index.md`
- `docs/gkc/cli/wikibase.md`
- `gkc/__init__.py`
- `gkc/cli.py`
- `gkc/cooperage.py`
- `gkc/utilities.py`
- `gkc/wikibase/__init__.py`
- `gkc/wikibase/foundation_profiles/foundation_metadata.yaml`
- `mkdocs.yml`
- `tests/test_cli.py`

## V2 Refactor Checklist (working order)

1. ✅ Align with Profile Architect on minimal profile-sync model shape.
2. ✅ Decide fate of the 3 profile-profile YAML artifacts (drop/replace/rewrite).
   - **Decision:** Replace with proper GKC Entity Profiles in SpiritSafe
3. ✅ Confirm target outputs for first executable milestone:
   - Two profile items in DD Wikibase
   - Derived property items from statements
   - No specification-instance creation (shell package only)
4. ⚠️ Narrow still_charger/orchestration contracts to match the agreed model.
   - **OUTSTANDING:** Semantic Engineer cleanup needed
5. ⚠️ Simplify notebook flow to minimal operator path (dry-run first, explicit execute gate).
   - **OUTSTANDING:** Notebook rework deferred
6. ✅ Re-baseline docs and tests to only the retained architecture.
   - Docs: `profiles.md` rewritten
   - Tests: focused suite migrated and passing

## Baseline Snapshot

Status snapshot source: `git status --short` in `gkc` workspace at creation time.

## Keep / Rewrite / Drop Proposal Matrix

This is a proposed starting position for the refactor meeting, not a final decision log.

| File | Proposal | Why | Action in V2 pass |
| --- | --- | --- | --- |
| `gkc/still_charger.py` | **KEEP (trim as needed)** | Core packet charging stage aligns with target operator flow. | Keep interface minimal; remove behavior not needed for profile+property hydration.
| `gkc/wikibase/orchestration.py` | **KEEP (narrow scope)** | Shared plan/execute pipeline is useful and reusable. | Keep dry-run/execute semantics; align input contracts to revised profile package model.
| `tests/test_still_charger.py` | **KEEP (adjust)** | Validates charging semantics directly. | Update fixtures if profile-shape contracts change.
| `tests/test_wikibase_orchestration.py` | **KEEP (adjust)** | Protects pipeline composition behavior. | Retain; rewrite assertions to reflect narrowed scope.
| `tests/test_cooperage_barreling.py` | **KEEP (adjust)** | Guards packet->operation transformation behavior. | Keep if cooperage remains packet-barreling layer; trim non-essential cases.
| `tests/test_utilities_name_resolution.py` | **KEEP (optional trim)** | Name resolution will likely still be needed for mapping/upsert. | Keep core cases; remove speculative edge cases.
| `docs/gkc/api/still_charger.md` | **REWRITE** | Docs should mirror simplified contract and current scope. | Re-document only retained behaviors.
| `notebooks/WikibaseInit.ipynb` | **REWRITE (simplify heavily)** | Current operator flow is valid but too dense. | Keep dry-run->inspect->execute path with fewer steps and less branching.
| `notebooks/CurationPacket.ipynb` | **REWRITE or HOLD** | Useful exploration artifact but may distract from V2 goals. | Keep only if used as a targeted hydration prototype notebook.
| `gkc/wikibase/foundation_profiles/entity_profile_profile.yaml` | **REWRITE (or replace)** | Diverges from intended GKC Entity Profile alignment. | Redesign with Profile Architect as minimal profile item model.
| `gkc/wikibase/foundation_profiles/property_profile.yaml` | **REWRITE (or replace)** | Same drift concern; should be close to existing profile schema conventions. | Redesign with Profile Architect as minimal property item model.
| `gkc/wikibase/foundation_profiles/specification_profile.yaml` | **DROP (for now)** | Specification instances explicitly out of immediate milestone. | Remove from active V2 scope; defer to fermenter-stage design.
| `gkc/wikibase/foundation_profiles/PROFILE_PROFILES_README.md` | **REWRITE or DROP** | Documents the divergent model; risks anchoring wrong direction. | Replace with short V2 contract note after alignment.

### Gating Decisions for Refactor Start

Decide these before editing implementation:

- Final minimal schema shape for "profile item" and "property item" modeling.
- Whether specs are fully deferred (recommended for current milestone).
- Exact acceptance output for first end-to-end run:
   - 2 profile items created/updated,
   - derived property items created/updated,
   - no specification item creation.

### Suggested Ownership Split

- **Profile Architect**: schema alignment and profile artifact redesign.
- **Semantic Engineer (this lane)**: still_charger/orchestration alignment, pipeline wiring, notebook simplification, and tests/docs updates.

## Handoff

### Context

The prior implementation pass produced useful scaffolding (packet charging, barreling, orchestration, dry-run/execute notebook pattern), but profile-sync modeling drifted from the intended GKC Entity Profile-aligned design.

### Immediate Objective

Reset profile-sync design so it is minimal, spec-aligned, and executable for the next milestone:

- produce two profile items in Data Distillery Wikibase (from two SpiritSafe prototypes),
- produce derived property items from statements/references/qualifiers,
- do not create specification instances yet.

### What Needs Profile Architect Alignment First

1. Define the minimal structure for profile-sync manifests using GKC Entity Profile conventions.
2. Confirm whether any additional parameters are truly needed for this use case.
3. Decide how interlinkage metadata is represented while staying close to existing profile schema patterns.
4. Confirm deferral boundary for specifications.

### Artifacts to Rework in That Alignment Session

- `gkc/wikibase/foundation_profiles/entity_profile_profile.yaml`
- `gkc/wikibase/foundation_profiles/property_profile.yaml`
- `gkc/wikibase/foundation_profiles/specification_profile.yaml` (expected deferred/drop for current milestone)
- `gkc/wikibase/foundation_profiles/PROFILE_PROFILES_README.md`

---

## Current Status Summary (2026-03-08)

### Completed Work

**Profile Architecture (Profile Architect)**
- ✅ Three new SpiritSafe profile packages created and validated:
  - `GKCEntityProfile` (5 statements)
  - `GKCEntityProperty` (6 statements)
  - `GKCPropertySpecification` (3 statements, shell)
- ✅ All packages follow SpiritSafe conventions (metadata.yaml, profile.yaml, README.md, CHANGELOG.md)
- ✅ Registry README updated with new profile entries
- ✅ Packages parse successfully with ProfileLoader

**Runtime Migration (Semantic Engineer)**
- ✅ `io_map` architecture fully implemented in runtime:
  - Profile models with directional validation
  - JSON schema updated
  - Generators migrated (form_generator, pydantic_generator)
  - Validation components migrated (validator, wikidata_normalizer)
  - Cooperage mapping logic migrated
- ✅ Test fixtures migrated to `io_map`
- ✅ Focused regression suite passing (30/30 tests)
- ✅ Documentation fully rewritten (`docs/gkc/profiles.md`)

### Outstanding Work

**Profile Routing Correction (Semantic Engineer - Current Priority)**
- ⚠️ All three new profile packages route to Wikidata properties instead of DD Wikibase
- ⚠️ Need DD Wikibase foundation audit results to map correct property URIs
- ⚠️ Require property ID mappings for:
  - instance of, version, status, documentation URL, has parts/components
  - property key, datatype, role, belongs to
  - specification key, governs

**Runtime Cleanup (Semantic Engineer - Next Priority)**
- ⚠️ still_charger cleanup needed per architectural corrections
- ⚠️ cooperage refinement needed per architectural corrections
- ⚠️ Test fixture packages for meta-profiles not yet created

**Deferred Work**
- Notebook flow simplification (WikibaseInit.ipynb)
- Profile_profile artifact removal (entity_profile_profile.yaml, property_profile.yaml, specification_profile.yaml)
- PROFILE_PROFILES_README.md removal

---

## Profile Architect Analysis - Architectural Drift Diagnosis

### The Core Problem

The three "profile_profile" YAML files are not GKC Entity Profiles - they're transformation specification documents that attempt to describe how to map profile.yaml structure TO Wikibase items. This violates the fundamental architectural principle: **if you want to model something in Wikibase, create a proper GKC Entity Profile for it**.

### What Went Wrong

**Issue 1: Wrong Abstraction Level**

- Current approach: "meta-profiles" that encode transformation rules (YAML path → Wikibase property mappings)
- Correct approach: GKC Entity Profiles that define what a "GKC Entity Profile" entity looks like when represented in a knowledge base

**Issue 2: Not Dogfooding the Architecture**

- Current approach: special-case YAML structure that doesn't follow GKC Entity Profile conventions
- Correct approach: use the same profile.yaml structure used for TribalGovernmentUS, OfficeHeldByHeadOfState, etc.

**Issue 3: Hardcoded Single-System Property Mapping**

- Current GKC Entity Profiles hardcode `wikidata_property: P31` etc.
- Need: support multiple target systems (Wikidata, Data Distillery Wikibase, etc.)
- Gap: no mechanism to specify which system a property ID refers to or how values transform per system

### Architectural Correction Required

#### 1. Replace "Profile Profiles" with Proper GKC Entity Profiles

If we want GKC Entity Profiles to exist as items in Data Distillery Wikibase, create proper profiles:

**SpiritSafe Structure (or parallel location):**
```
profiles/
  GKCEntityProfile/
    metadata.yaml
    profile.yaml
    CHANGELOG.md
    README.md
  GKCEntityProperty/
    metadata.yaml
    profile.yaml
    CHANGELOG.md
    README.md
  GKCPropertySpecification/
    metadata.yaml
    profile.yaml
    CHANGELOG.md
    README.md
```

Each `profile.yaml` would follow standard GKC Entity Profile conventions:
- `name`, `description`, `labels`, `descriptions`, `aliases`
- `statements` array with proper structure
- `sitelinks` if relevant
- Standard reference patterns

#### 2. Extend Property Mapping Schema for Multi-System Support

Current profile schema has:
```yaml
- id: instance_of
  wikidata_property: P31
  type: statement
  value:
    type: item
```

**Proposed extension** (hard-cut, no backward compatibility):
```yaml
- id: instance_of
  type: statement
   io_map:
      - to: https://www.wikidata.org/entity/P31
         value_transform: future_gkc_operator
      - to: https://datadistillery.wikibase.cloud/entity/P1
         value_transform: null
      - from: resolvable_input_fetcher
         value_transform: future_gkc_operator
  value:
    type: item
```

**Architecture decisions (locked for this refactor):**
1. **System identification uses resolvable identifiers**
   - `io_map.to` uses full resolvable property identifiers (example: `https://www.wikidata.org/entity/P31`).
   - `io_map.from` uses resolvable source identifiers (IRI or resolver key string) based on ingestion route.

2. **`value_transform` is a resolver reference**
   - `value_transform` values identify transform operators, with the option to resolve those operators through Data Distillery Wikibase items.
   - Runtime execution remains explicit and controlled in code; profile entries declare intent and routing.

3. **Directional model with extension points**
   - Baseline entries are directional (`to` and `from`).
   - Future constructs such as `to-through` / `from-through` are reserved as additive extensions.

4. **Transformation stage semantics**
   - `from` transforms are treated as inbound/fermentation behavior.
   - `to` transforms are treated as outbound/bottling behavior.
   - Internal inference/distillation logic remains runtime-owned and can reference profile-declared transforms.

#### 3. GKC Property Specification Scope (Current Milestone)

Per architectural direction:
- Include a **minimal shell profile package** for `GKCPropertySpecification` now.
- Keep the shell intentionally small (labels, descriptions, and minimal framing statements).
- Defer deeper specification behavior modeling until the subsequent implementation pass.

### Immediate Refactor Actions

**Phase 1: Profile Architect Responsibilities**

1. **Define minimal GKC Entity Profile schema changes needed for multi-system property mapping**
   - Propose concrete YAML schema extension using `io_map`
   - Remove `wikidata_property` from active schema and fixtures
   - Apply architecture decisions D1-D5 above
   - Document in profile schema docs

2. **Design GKCEntityProfile and GKCEntityProperty profiles**
   - Create proper `profile.yaml` and `metadata.yaml` for each
   - Follow SpiritSafe conventions exactly
   - Map to Data Distillery Wikibase properties (not Wikidata)
   - Keep minimal scope: only properties needed to represent profile metadata in DD Wikibase

   > We may not yet have everything we need in the ontology aspect of DD Wikibase yet. Let's design these at the profile level for what we think the need is, and we'll adjust the init to build out the ontology accordingly.

3. **Determine profile location strategy**
   - Option A: Add to SpiritSafe repository as special meta-profiles
   - Option B: Keep in gkc repo but restructure to match SpiritSafe conventions
   - Option C: Hybrid - SpiritSafe for published/stable, gkc for experimental/bootstrap

   > I prefer option A - let's keep dogfooding here. We'll generate the new profiles in the working clone of SpiritSafe here in the VSCode workspace, and PR-merge it to main, refining anything in that workflow that we need to. We can then run our processing from the local clone files. I'd prefer to do the same thing with the ontology bits that we used in the Wikibase init eventually as well, but we'll defer that for now.

**Phase 2: Handoff to Semantic Engineer**

After Profile Architect completes Phase 1:
- Remove the three profile_profile.yaml files
- Remove PROFILE_PROFILES_README.md
- Adjust still_charger/orchestration to consume proper GKC Entity Profiles
- Update packet hydration logic to use new property mapping schema
- Revise notebook flow to simplified execute path

### Architecture Decisions for Profile Architect

**D1: Property Mapping Structure**

Multi-system mappings are encoded with directional `io_map` entries (`to` and `from`) using full resolvable identifiers.

**D2: System Identification**

Target systems are identified by resolvable identifiers; for Wikibase-class systems this is a full property IRI.

**D3: Value Transformation**

Per-system coercion is declared per mapping entry via `value_transform` as a resolver target; runtime execution policy remains enforced in code.

**D4: Profile Storage Location**

Meta-profiles follow SpiritSafe package conventions (directory with `metadata.yaml`, `profile.yaml`, `README.md`, `CHANGELOG.md`).

**D5: Execution Mode**

Immediate cut-over: remove `wikidata_property` and adopt `io_map` across schema, runtime, fixtures, and docs in this refactor.

### Success Criteria for This Refactor

1. ✅ GKCEntityProfile and GKCEntityProperty are proper GKC Entity Profiles following SpiritSafe conventions
2. ✅ Property mapping schema supports Data Distillery Wikibase property IDs
   - ⚠️ Architecture complete; route correction to DD Wikibase properties outstanding
3. ✅ Schema design is extensible to additional target systems (OSM, Commons, etc.)
4. ✅ `wikidata_property` is fully removed from schema, fixtures, docs, and runtime touchpoints
5. ✅ No transformation logic encoded in profiles - only declarative metadata
6. ✅ Clear handoff artifacts for Semantic Engineer to implement `io_map` resolution in still_charger/cooperage
   - Runtime implementation complete; cooperage/still_charger cleanup pending

---

## Incremental Refactor Plan - Profile Architect Track

This section captures the step-by-step work plan for refactoring the profile architecture. Work incrementally with checkpoint/review cycles.

### Step 1: Create GKCEntityProfile Profile (Minimal Viable) ✅ COMPLETED

**Goal:** Create a proper GKC Entity Profile that defines what a "GKC Entity Profile" entity looks like in Data Distillery Wikibase

**Tasks:**
1. ✅ Create profile package using SpiritSafe conventions
2. ✅ Create folder structure matching SpiritSafe conventions
3. ✅ Write `metadata.yaml` with version, authors, status
4. ✅ Write `profile.yaml` with minimal statements needed for V2 milestone:
   - name (label)
   - description
   - version, status
   - documentation URL
   - has_statement (links to Property items)
5. ✅ Map properties with `io_map` entries using full resolvable identifiers
   - ⚠️ **OUTSTANDING:** Currently routes to Wikidata; needs DD Wikibase property URIs
6. ✅ Create CHANGELOG.md and README.md

**Checkpoint:** ✅ GKCEntityProfile profile validates and can be loaded

**Artifacts:**
- ✅ `SpiritSafe/profiles/GKCEntityProfile/metadata.yaml`
- ✅ `SpiritSafe/profiles/GKCEntityProfile/profile.yaml` (5 statements)
- ✅ `SpiritSafe/profiles/GKCEntityProfile/CHANGELOG.md`
- ✅ `SpiritSafe/profiles/GKCEntityProfile/README.md`

### Step 2: Create GKCEntityProperty Profile (Minimal Viable) ✅ COMPLETED

**Goal:** Create a proper GKC Entity Profile that defines what a "GKC Entity Property" entity looks like in Data Distillery Wikibase

**Tasks:**
1. ✅ Create folder structure matching SpiritSafe conventions
2. ✅ Write `metadata.yaml`
3. ✅ Write `profile.yaml` with minimal statements needed for V2 milestone:
   - property identifier (label)
   - property key, datatype
   - statement role
   - belongs to profile linkage
   - documentation URL
4. ✅ Map properties to Data Distillery Wikibase PIDs
   - ⚠️ **OUTSTANDING:** Currently routes to Wikidata; needs DD Wikibase property URIs
5. ✅ Create CHANGELOG.md and README.md

**Checkpoint:** ✅ GKCEntityProperty profile validates and can be loaded

**Artifacts:**
- ✅ `SpiritSafe/profiles/GKCEntityProperty/metadata.yaml`
- ✅ `SpiritSafe/profiles/GKCEntityProperty/profile.yaml` (6 statements)
- ✅ `SpiritSafe/profiles/GKCEntityProperty/CHANGELOG.md`
- ✅ `SpiritSafe/profiles/GKCEntityProperty/README.md`

### Step 3: Create GKCPropertySpecification Profile (Shell) ✅ COMPLETED

**Goal:** Create a conformant shell package for `GKCPropertySpecification` to support near-term expansion

**Tasks:**
1. ✅ Create folder structure matching SpiritSafe conventions
2. ✅ Write `metadata.yaml` with minimal stable package metadata
3. ✅ Write `profile.yaml` with shell-level structure and minimal core statements:
   - labels, descriptions, aliases
   - instance_of, specification_key
   - governed property linkage
4. ✅ Use `io_map` for all statement mappings
   - ⚠️ **OUTSTANDING:** Currently routes to Wikidata; needs DD Wikibase property URIs
5. ✅ Create README.md with Theoretical Design Notes and CHANGELOG.md

**Checkpoint:** ✅ Shell package validates and is ready for expansion

**Artifacts:**
- ✅ `SpiritSafe/profiles/GKCPropertySpecification/metadata.yaml`
- ✅ `SpiritSafe/profiles/GKCPropertySpecification/profile.yaml` (3 statements)
- ✅ `SpiritSafe/profiles/GKCPropertySpecification/README.md`
- ✅ `SpiritSafe/profiles/GKCPropertySpecification/CHANGELOG.md`

### Step 4: Finalize IO Mapping Contract ✅ COMPLETED

**Goal:** Lock the `io_map` contract as the canonical architecture model

**Tasks:**
1. ✅ Finalize `io_map` examples in architecture docs
2. ✅ Remove all references to `wikidata_property` as an active field
3. ✅ Define accepted resolver identifier patterns for `to` and `from`
4. ✅ Define current execution expectations for `value_transform`

**Checkpoint:** ✅ Contract is clear enough to implement in runtime code without interpretation drift

**Implementation Notes:**
- `io_map` entries require exactly one of `to` (outbound) or `from` (inbound)
- `to` uses full resolvable property identifiers (e.g., `https://www.wikidata.org/entity/P31`)
- `value_transform` is an optional resolver reference key
- Hard cut completed: no `wikidata_property` backward compatibility

### Step 5: Update Profile Schema Documentation ✅ COMPLETED

**Goal:** Document the new multi-system property mapping schema and meta-profile patterns

**Tasks:**
1. ✅ Update `docs/gkc/profiles.md` with `io_map` schema as canonical mapping model
2. ✅ Add section on meta-profiles (profiles that model GKC infrastructure itself)
3. ✅ Add examples showing Data Distillery Wikibase property mappings
4. ✅ Add directional mapping examples for input routes

**Checkpoint:** ✅ Schema docs complete and accurate

**Artifacts:**
- ✅ `docs/gkc/profiles.md` (fully rewritten, architecture-first)
- ✅ Cross-document anchor fixes for strict docs build validation

### Step 6: Update Test Fixtures ⚠️ PARTIALLY COMPLETE

**Goal:** Ensure test fixtures reflect new profile schema

**Tasks:**
1. ⚠️ Add test fixtures for:
   - GKCEntityProfile profile (in `tests/fixtures/profiles/GKCEntityProfile/`)
   - GKCEntityProperty profile (in `tests/fixtures/profiles/GKCEntityProperty/`)
   - **OUTSTANDING:** Not yet added as test fixtures
2. ✅ Convert existing fixtures from `wikidata_property` to `io_map`
   - TribalGovernmentUS, OfficeHeldByHeadOfState, EntityProfileExemplar
   - Flat legacy fixtures, SpiritSafe fixture profiles
3. ✅ Ensure fixtures validate against schema

**Checkpoint:** ⚠️ Core fixtures migrated; meta-profile fixtures pending

**Artifacts:**
- ✅ Updated `tests/fixtures/profiles/TribalGovernmentUS/profile.yaml`
- ✅ Updated `tests/fixtures/profiles/EntityProfileExemplar/profile.yaml`
- ✅ Updated `tests/fixtures/profiles/*.yaml` (flat legacy)
- ✅ Updated `tests/fixtures/spiritsafe/profiles/*`
- ⚠️ `tests/fixtures/profiles/GKCEntityProfile/` (not created yet)
- ⚠️ `tests/fixtures/profiles/GKCEntityProperty/` (not created yet)

### Step 7: Migrate Runtime to `io_map` ✅ COMPLETED

**Goal:** Migrate all runtime components from `wikidata_property` to `io_map` resolution

**Tasks:**
1. ✅ Update profile models (`gkc/profiles/models.py`)
   - Added `IOMapEntry` model with directional validation
   - Added property resolution helpers (`_resolve_property_id_from_io_map`, etc.)
   - Replaced `wikidata_property` fields with `io_map` in all definition models
   - Added convenience methods (`property_id()`, `wikidata_property_id()`)
2. ✅ Update profile JSON schema (`gkc/profiles/schemas/profile.schema.json`)
   - Added `io_map_entry` definition
   - Required `io_map` on field/qualifier/reference_target
3. ✅ Update generators
   - `form_generator.py`: emit `io_map` instead of `wikidata_property`
   - `pydantic_generator.py`: use resolved property IDs from `io_map`
4. ✅ Update validation components
   - `wikidata_normalizer.py`: resolve PID from `io_map` routes
   - `validator.py`: switched to resolved property IDs
5. ✅ Update cooperage (`gkc/cooperage.py`)
   - Statement mapping extraction now parses `io_map.to` routes
6. ✅ Update tests
   - Migrated focused test suite (profiles, SpiritSafe, cooperage, orchestration)
   - 30/30 tests passing after migration

**Checkpoint:** ✅ Runtime fully migrated; focused regression suite green

**Artifacts:**
- ✅ Updated `gkc/profiles/models.py`
- ✅ Updated `gkc/profiles/schemas/profile.schema.json`
- ✅ Updated `gkc/profiles/generators/*`
- ✅ Updated `gkc/profiles/validation/*`
- ✅ Updated `gkc/cooperage.py`
- ✅ Updated tests and docs snippets

### Step 8: Archive Deprecated Profile_Profile Artifacts ⚠️ OUTSTANDING

**Goal:** Remove the divergent profile_profile artifacts

**Tasks:**
1. ⚠️ Archive or delete:
   - `gkc/wikibase/foundation_profiles/entity_profile_profile.yaml`
   - `gkc/wikibase/foundation_profiles/property_profile.yaml`
   - `gkc/wikibase/foundation_profiles/specification_profile.yaml`
   - `gkc/wikibase/foundation_profiles/PROFILE_PROFILES_README.md`
2. ⚠️ Remove these artifacts from active architecture references

**Checkpoint:** ⚠️ Awaiting completion

**Artifacts:**
- Files to be deleted/archived (pending)
- Updated WikibaseInitV2.md with completion notes (pending)

### Step 9: Handoff to Semantic Engineer

**Goal:** Provide clear handoff artifacts for implementation in still_charger/cooperage/orchestration

**Tasks:**
1. Document handoff requirements in WikibaseInitV2.md
2. Specify expected inputs/outputs for:
   - Profile loading from new locations
   - Property mapping resolution for multiple systems
   - Packet hydration from GKCEntityProfile/GKCEntityProperty profiles
3. Identify any edge cases or open questions

**Checkpoint:** ⚠️ Handoff documentation in progress

**Artifacts:**
- Handoff section in WikibaseInitV2.md with:
  - What changed in profile schema
  - Where new profiles are located
  - What implementation changes are needed in still_charger/cooperage
  - Expected behavior for multi-system property mapping

---

## Current Architecture Focus

- ✅ Conformant profile packages implemented (`GKCEntityProfile`, `GKCEntityProperty`, `GKCPropertySpecification` shell)
- ⚠️ Route correction needed (DD Wikibase properties instead of Wikidata)
- Use those packages as the source model for runtime alignment in still_charger/cooperage/orchestration
- Treat `io_map` as the only active mapping construct

### Post-Alignment Engineering Sequence

1. ⚠️ **Correct routing in three new profile packages (Semantic Engineer)**
2. ⚠️ Re-scope `still_charger` and `wikibase.orchestration` contracts to the agreed minimal model
3. ⚠️ Verify packet generation and hydration from SpiritSafe prototypes
4. ⚠️ Run dry-run planning and inspect outputs
5. ⚠️ Gate execute submission behind explicit toggle
6. ⚠️ Simplify notebook to the shortest clear operator path

### Acceptance Criteria for Next Pass

- Curation Packet generated from the agreed profile package shape
- Hydration from the two prototype profiles succeeds without ad-hoc mapping logic outside defined contracts
- Dry-run output clearly previews resulting profile and property creates/updates
- Execute mode can submit those operations with traceable summaries
- No specification-instance creation path is active

---

## Property-to-Semantics Mapping Table (Contract for Wikibase → YAML → Runtime)

This table defines the authoritative contract for translating DD Wikibase profile structure into SpiritSafe YAML cache format and runtime behavior in gkc. Each row is an atomic, independently testable mapping.

**Status:** Draft foundation — requires completion through ontology enumeration and runtime implementation alignment.

### Profile-Level Mappings

| Wikibase Element | YAML Field Path | Validator Behavior | Wizard Behavior | Notes |
|------------------|-----------------|-------------------|-----------------|-------|
| `labels.{lang}` | `labels.{lang}.label` | String, required for `en` | Primary name field, auto-suggest in other langs | — |
| `descriptions.{lang}` | `descriptions.{lang}.label` | String, required for `en` | Guidance text display | — |
| `aliases.{lang}[]` | `aliases.{lang}.label` | String array, optional | Alternative name suggestions | — |
| `P1` (instance of) | (metadata only) | Must link to `https://datadistillery.wikibase.cloud/entity/Q3` (GKC Entity Profile) | Not displayed to curator | Profile classifier |
| `P3` (schema documentation URL) | (metadata, not in YAML yet) | URL validation | Link to external schema docs | Future addition |
| `P185` (label guidance) | `labels.{lang}.guidance` | Monolingual text | Help tooltip/inline text | Curator instruction |
| `P186` (description example) | `descriptions.{lang}.guidance` | Monolingual text | Help tooltip/example text | Format examples |
| `P187` (alias guidance) | `aliases.{lang}.guidance` | Monolingual text | Help tooltip | When/how to use aliases |
| `P188` (label field description) | `labels.{lang}.input_prompt` | Monolingual text | Field label in UI | Semantic definition |
| `P189` (description field description) | `descriptions.{lang}.input_prompt` | Monolingual text | Field label in UI | Semantic definition |
| `P190` (alias field description) | `aliases.{lang}.input_prompt` | Monolingual text | Field label in UI | Semantic definition |

### Statement-Level Mappings (P157 with Qualifiers)

Each `P157` statement represents one entry in `statements[]` array. The mainsnak target is the statement-definition item (e.g., `https://datadistillery.wikibase.cloud/entity/Q16`, `https://datadistillery.wikibase.cloud/entity/Q19`, `https://datadistillery.wikibase.cloud/entity/Q40`).

| Wikibase Element | YAML Field Path | Validator Behavior | Wizard Behavior | Notes |
|------------------|-----------------|-------------------|-----------------|-------|
| `P157` mainsnak target entity URI | `statements[].id` (via lookup) | Links to statement-definition item | Maps to property/field in form | Requires statement registry |
| `P171` (consequence message) | `statements[].guidance` | Monolingual text | Warning text when field empty | "Required but optional" messaging |
| `P182` (cardinality) | `statements[].max_count` | `novalue` → `null` (unlimited)<br>`+1` → `1`<br>`+N` → `N` | Controls repeatable field UI | `0` not used |
| `P183` (fixed value link) | `statements[].value.fixed` (TBD field) | Enforces exact match to URI | Display only, not editable | Fixed values scenarios |
| `P159` (validation policy) | `statements[].validation_policy` | Maps to validator mode enum | — | e.g., `strict`, `allow_existing_nonconforming` |
| `P161` (form policy) | `statements[].form_policy` (may be array) | — | Controls visibility, editability, defaults | Can have multiple policies |
| `P162` (linked profile) | `statements[].linked_profile` | Validates value conforms to linked profile | "Create new" or "Select existing" affordance | **See Cross-Profile Interlinkage section below** |
| `P164` (expected qualifier) | `statements[].expected_qualifiers[]` | List of required/allowed qualifier entity URIs | Renders qualifier sub-form fields | Maps to statement-definition items |

### Statement-Definition Item Mappings (`https://datadistillery.wikibase.cloud/entity/Q5` instances)

Statement-definition items (e.g., `https://datadistillery.wikibase.cloud/entity/Q16` "instance of", `https://datadistillery.wikibase.cloud/entity/Q19` "official website") provide property-level metadata.

| Wikibase Element | YAML Field Path | Validator Behavior | Wizard Behavior | Notes |
|------------------|-----------------|-------------------|-----------------|-------|
| `labels.{lang}` | `statements[].label` | — | Field label in wizard | Property display name |
| `P5` (Wikidata property ID) | `statements[].io_map[0].to` | Used for Wikidata export | — | Currently hardcoded to WD; needs multi-system support |
| `P194` (datatype) | `statements[].value.type` | Maps to fermenter validator | Controls input widget type | 8 primitive types identified |

### Datatype-to-Validator Mapping (Fermenter Module Contract)

**Requirement:** `fermenter` module must provide atomic validators/coercers for these 8 primitive datatypes:

| Datatype (P194 value label) | YAML `value.type` | Validator Function | Coercer Function | Notes |
|-----------------------------|-------------------|-------------------|------------------|-------|
| `item` | `item` | `validate_item_reference()` | `coerce_to_item_entity_uri()` | Wikibase item reference (entity URI) |
| `monolingual text` | `monolingualtext` | `validate_monolingualtext()` | `coerce_to_monolingualtext()` | Text + language code |
| `url` | `url` | `validate_url()` | `coerce_to_url()` | Valid URI/IRI |
| `string` | `string` | `validate_string()` | `coerce_to_string()` | Free text |
| `datetime` | `time` | `validate_datetime()` | `coerce_to_wikibase_time()` | ISO datetime → Wikibase time format |
| `quantity` | `quantity` | `validate_quantity()` | `coerce_to_quantity()` | Number + unit + bounds |
| `geographic coordinates` | `globecoordinate` | `validate_coordinates()` | `coerce_to_globecoordinate()` | Lat/long + precision |
| `commons media file` | `commonsMedia` | `validate_commons_file()` | `coerce_to_commons_filename()` | Wikimedia Commons file reference |

---

## Cross-Profile Interlinkage Architecture (P162)

### Design Rationale

**P162 (linked profile)** is used as a qualifier on P157 statements to encode cross-profile dependencies at the **statement level** (not profile level). This provides precise context about when and how one profile references another.

**Example from `https://datadistillery.wikibase.cloud/entity/Q4` (Tribal Government US) → `https://datadistillery.wikibase.cloud/entity/Q39` (Office Held by Head of Government):**
- `https://datadistillery.wikibase.cloud/entity/Q4` has P157 statement targeting `https://datadistillery.wikibase.cloud/entity/Q40` "office held by head of government"
- That P157 statement includes qualifier `P162 → https://datadistillery.wikibase.cloud/entity/Q39`
- Semantics: "When curating the 'office held by head of government' field on a Tribal Government entity, the value should conform to the Office Held by Head of Government profile (`https://datadistillery.wikibase.cloud/entity/Q39`)."

**Reciprocal linkage:**
- `https://datadistillery.wikibase.cloud/entity/Q39` has P157 statement targeting `https://datadistillery.wikibase.cloud/entity/Q42` "applies to jurisdiction"
- That P157 statement includes qualifier `P162 → https://datadistillery.wikibase.cloud/entity/Q4`
- Semantics: "When curating the 'applies to jurisdiction' field on an Office entity, the value should conform to the Tribal Government US profile (`https://datadistillery.wikibase.cloud/entity/Q4`)."

### Architectural Strengths

1. **Precise Context** — Statement-level linkage preserves exactly which field triggers the profile dependency, not just "these two profiles are related somehow."

2. **Graph Traversal** — Natural packet assembly: when building entity A using profile P1, if field F has `P162 → P2`, the system knows it needs entity B conforming to profile P2.

3. **Declarative Metadata** — No hardcoded lookups in runtime code; profile dependency graph is extracted from the ontology and cached in the SpiritSafe manifest.

4. **Wizard Navigation Affordances** — UI can present context-specific actions:
   - "Create new [Office]" button on the "office held by head of government" field
   - "Select existing [Tribal Government]" dropdown on the "applies to jurisdiction" field
   - Navigation breadcrumb: Tribal Government → Office → (back to) Tribal Government

5. **Bulk Data Intelligence** — When processing CSV/JSON with nested references, the system knows which profile to apply to each column based on field-level linkage.

### Use Cases

**1. Curation Packet Assembly**
- User requests packet for Tribal Government (`https://datadistillery.wikibase.cloud/entity/Q4`)
- System extracts profile structure for `https://datadistillery.wikibase.cloud/entity/Q4` from cache
- Encounters statement with `P162 → https://datadistillery.wikibase.cloud/entity/Q39` (Office profile)
- Includes profile structure for `https://datadistillery.wikibase.cloud/entity/Q39` in packet as a nested/referenced schema
- Packet metadata records the dependency: `https://datadistillery.wikibase.cloud/entity/Q4` depends on `https://datadistillery.wikibase.cloud/entity/Q39` at field "office_held_by_head_of_government"

**2. GKC Wizard Session**
- User creating Tribal Government entity
- Reaches "office held by head of government" field
- Wizard detects `P162 → https://datadistillery.wikibase.cloud/entity/Q39` linkage
- Presents two affordances:
   - **"Create new office"** → opens profile wizard for `https://datadistillery.wikibase.cloud/entity/Q39` in modal/tab, returns item reference when complete
   - **"Select existing office"** → type-ahead search constrained to items conforming to `https://datadistillery.wikibase.cloud/entity/Q39`
- After selection/creation, validates that the linked item conforms to `https://datadistillery.wikibase.cloud/entity/Q39` profile

**3. Bulk Data Curation**
- CSV upload for Tribal Governments includes "office_title" column
- System maps "office_title" to "office held by head of government" statement
- Detects `P162 → https://datadistillery.wikibase.cloud/entity/Q39` linkage
- Applies profile validation/coercion for `https://datadistillery.wikibase.cloud/entity/Q39` to "office_title" values
- Creates/matches Office items as needed, conforming to `https://datadistillery.wikibase.cloud/entity/Q39` structure

**4. Validation Propagation**
- Validator checks Tribal Government entity against `https://datadistillery.wikibase.cloud/entity/Q4` profile
- Encounters "office held by head of government" statement with item reference
- Detects `P162 → https://datadistillery.wikibase.cloud/entity/Q39` linkage
- **Policy decision (TBD):**
   - **Strict mode:** Recursively validate the referenced Office item against `https://datadistillery.wikibase.cloud/entity/Q39` profile
  - **Reference-only mode:** Only validate that the reference exists and is an item (type check)
  - **Deferred mode:** Record the linkage for later batch validation, don't block on recursive checks

### Implementation Contracts

**Manifest Representation:**

SpiritSafe cache should include a profile dependency graph structure:

```yaml
# In manifest.json or equivalent
profile_graph:
  edges:
    - source_profile: TribalGovernmentUS
      source_statement: office_held_by_head_of_government
      target_profile: OfficeHeldByHeadOfState
      linkage_type: P162
      bidirectional: true  # https://datadistillery.wikibase.cloud/entity/Q39 also links back to https://datadistillery.wikibase.cloud/entity/Q4
```

**YAML Profile Representation:**

```yaml
# In TribalGovernmentUS profile.yaml
statements:
  - id: office_held_by_head_of_government
    label: Office held by head of government
    io_map:
      - to: https://www.wikidata.org/entity/P39
    type: statement
    value:
      type: item
   linked_profile: OfficeHeldByHeadOfState  # Resolved from P162 → https://datadistillery.wikibase.cloud/entity/Q39 → label lookup
```

**Runtime Validator Contract:**

```python
def validate_statement_value(
    value: Any,
    statement_spec: StatementSpec,
    validation_mode: str = "strict"
) -> ValidationResult:
    """
    Validate statement value against spec, including linked profile checks.
    
    If statement_spec.linked_profile is set and value is an item reference:
      - strict: recursively validate the item against linked profile
      - reference_only: check that item exists and is accessible
      - deferred: record linkage for batch validation, return success
    """
    ...
```

**Wizard UI Contract:**

When rendering a statement field with `linked_profile`:
1. Display field label with type indicator (e.g., "Office held by head of government (Office item)")
2. Provide dual affordances:
   - Primary button: "Create new [Profile Name]"
   - Secondary input: Type-ahead search constrained to conforming items
3. On "Create new" click:
   - Load linked profile structure
   - Open wizard modal/panel for linked profile
   - On completion, capture created item reference and populate field
4. Validate selected/created item against linked profile (mode-dependent)

### Edge Cases & Design Decisions

**Cycles:**
- Bidirectional linkage (`https://datadistillery.wikibase.cloud/entity/Q4` ↔ `https://datadistillery.wikibase.cloud/entity/Q39`) is valid and useful
- Depth limit for recursive validation: **default 2 levels** (configurable)
- Cycle detection: track visited profiles in validation stack, warn on re-entry

**Multiple Linked Profiles:**
- One statement can have multiple `P162` qualifiers (e.g., "related entity" accepting multiple types)
- YAML representation: `linked_profiles: [ProfileA, ProfileB]` (array)
- Wizard affordance: dropdown menu of "Create new..." options, one per linked profile
- Validation: value must conform to **at least one** of the linked profiles (OR logic)

**Linked Profile Version Compatibility:**
- Linkage references profile by name/entity URI, not version
- Runtime resolves to **latest cached version** of linked profile
- Version pinning: future extension via additional qualifier (e.g., P192 "profile version constraint")

**Performance Optimization:**
- Manifest pre-computes full dependency graph (transitive closure)
- Wizard pre-loads all linked profiles when session begins (reduce latency)
- Bulk validator batches recursive checks (avoid N+1 queries)

**Open Questions:**
1. Should P162 linkage be **mandatory** when value type is `item`, or optional annotation?
   - **Recommendation:** Optional — not all item-valued fields need linked profiles (e.g., generic "country" field)
2. How to handle incomplete profiles (linked profile exists but is draft/incomplete)?
   - **Recommendation:** Include `status` metadata in manifest; wizard warns but allows usage
3. Should wizard support **inline editing** of linked items, or strictly modal/navigation?
   - **Recommendation:** Start with modal; inline editing is future enhancement

---

## Validation/Coercion Architecture (Property Specifications)

### Specification Taxonomy

**GKC Property Specification (`https://datadistillery.wikibase.cloud/entity/Q6`)** is the parent classifier for all validation/coercion specifications. These items define how the `fermenter` module should handle validation and data transformation.

**Subclass: GKC Value List (`https://datadistillery.wikibase.cloud/entity/Q7`)** represents specifications that provide allowed-values lists via SPARQL queries.

### Core Specification Items (with P191 Validation Directives)

Query results from DD Wikibase (6 property specification items):

| Entity URI | Label | Directive (P191) | Type | Notes |
|-----|-------|------------------|------|-------|
| **https://datadistillery.wikibase.cloud/entity/Q23** | require fixed value | "apply a supplied fixed value without any need for deliberate input action on the part of a user" | Policy | Used with P161 qualifier on P157 statements |
| **https://datadistillery.wikibase.cloud/entity/Q24** | allow nonconforming statements | "allow other statements for an entity beyond what is strictly specified" | Policy | Validation relaxation mode |
| **https://datadistillery.wikibase.cloud/entity/Q26** | value applied as reference | "apply the statement value as reference URL type of reference" | Transform | Value routing directive |
| **https://datadistillery.wikibase.cloud/entity/Q28** | Federal Register Notices Listing Tribes | "use the value list as values for stated in references" | Value List (`https://datadistillery.wikibase.cloud/entity/Q7`) | Applies to `https://datadistillery.wikibase.cloud/entity/Q30` (stated in) via P163 |
| **https://datadistillery.wikibase.cloud/entity/Q31** | reference must be at least one of URL or stated in | "require a reference that is at least one of qualifier values" | Constraint | reference cardinality rule |
| **https://datadistillery.wikibase.cloud/entity/Q43** | List of World Countries | "use the value list as values for country statements" | Value List (`https://datadistillery.wikibase.cloud/entity/Q7`) | Applies to `https://datadistillery.wikibase.cloud/entity/Q41` (country) via P163 |

### Property Specification Linkages

**P161 (value specification):** Qualifier on P157 statements linking to specification items (e.g., `https://datadistillery.wikibase.cloud/entity/Q23`, `https://datadistillery.wikibase.cloud/entity/Q24`) that define how statement values should be handled.

**P159 (reference specification):** Qualifier on P157 statements linking to specification items (e.g., `https://datadistillery.wikibase.cloud/entity/Q31`) that define reference requirements.

**P164 (expected qualifier):** Qualifier on P157 statements listing which statement-definition items (e.g., `https://datadistillery.wikibase.cloud/entity/Q34`, `https://datadistillery.wikibase.cloud/entity/Q35`, `https://datadistillery.wikibase.cloud/entity/Q36`) should appear as qualifiers on the target statement.

**Example from `https://datadistillery.wikibase.cloud/entity/Q4` P157 targeting `https://datadistillery.wikibase.cloud/entity/Q33` (headquarters location):**
- P171: "headquarters location for the tribal government" (guidance)
- P182: `+1` (exactly one required)
- P159: `https://datadistillery.wikibase.cloud/entity/Q31` (reference must be at least one of URL or stated in)
- P164: `https://datadistillery.wikibase.cloud/entity/Q34` (street address), `https://datadistillery.wikibase.cloud/entity/Q35` (postal code), `https://datadistillery.wikibase.cloud/entity/Q36` (coordinate location) — expected qualifiers

### Value List Architecture

Value list items (instances of `https://datadistillery.wikibase.cloud/entity/Q7`) provide SPARQL-generated allowed-values lists:

**`https://datadistillery.wikibase.cloud/entity/Q28`: Federal Register Notices Listing Tribes**
- Applies to: `https://datadistillery.wikibase.cloud/entity/Q30` (stated in) — via P163
- Usage: reference value constraint
- SPARQL location: Discussion page (MediaWiki Talk page) for `https://datadistillery.wikibase.cloud/entity/Q28`
- Directive: "use the value list as values for stated in references"

**`https://datadistillery.wikibase.cloud/entity/Q43`: List of World Countries**
- Applies to: `https://datadistillery.wikibase.cloud/entity/Q41` (country) — via P163
- Usage: statement value constraint
- SPARQL location: Discussion page (MediaWiki Talk page) for `https://datadistillery.wikibase.cloud/entity/Q43`
- Directive: "use the value list as values for country statements"

**P163 (applies to property):** Links a value list item to the statement-definition item (property) that should be populated using values from the list.

### SPARQL Storage Strategy

**Current approach:** SPARQL query text is stored in the MediaWiki Discussion (Talk) page associated with each value list item (`https://datadistillery.wikibase.cloud/entity/Q28`, `https://datadistillery.wikibase.cloud/entity/Q43`).

**Potential alternatives:**
1. Store SPARQL query text in a dedicated property (string datatype)
2. Store materialized CSV in Discussion page (up to instance size limit)
3. Store both SPARQL (for regeneration) and truncated CSV (for fallback) in Discussion page

**Requirements for value list infrastructure:**
- Type-ahead wizard functionality (fast prefix matching)
- Best-match coercion for bulk data operators (fuzzy matching, label resolution)
- Periodic regeneration via SPARQL (freshness policy)
- Fallback list when SPARQL endpoint unavailable

**Open question:** Where to cache materialized lists?
- **Option A:** SpiritSafe cache (version-controlled, alongside profiles)
- **Option B:** Separate infrastructure (Redis, S3, or local cache in gkc runtime)
- **Option C:** Hybrid — truncated lists in SpiritSafe, full lists in runtime cache

**Action:** Document caching strategy decision in dev doc after evaluating:
- List size distribution (how many items per list?)
- Update frequency requirements
- Wizard performance constraints
- Offline/fallback requirements

### Validation/Coercion Property Contract Extensions

Add to Property-to-Semantics Mapping Table:

| Wikibase Element | YAML Field Path | Validator Behavior | Wizard Behavior | Notes |
|------------------|-----------------|-------------------|-----------------|-------|
| `P161` (value specification) | `statements[].value_spec` (TBD) | References fermenter action directive | Controls input method (fixed, list, free) | Can have multiple specs |
| `P159` (reference specification) | `statements[].reference_spec` (TBD) | References fermenter reference validation | Enforces reference requirements | Can have multiple specs |
| `P164` (expected qualifier) | `statements[].expected_qualifiers[]` | List of required/allowed qualifier entity URIs | Renders qualifier sub-form fields | Maps to statement-definition items |
| `P163` (applies to property) | (metadata on value list items) | Links value list to target property | — | Used to resolve which lists apply to which fields |
| `P191` (validation directive) | (metadata on spec items) | Human-readable fermenter instruction | — | Guides fermenter module implementation |

### Fermenter Module Requirements (Extended)

In addition to primitive datatype validators/coercers, `fermenter` must implement:

**Specification Processors:**
1. `apply_fixed_value(spec_item, context)` — `https://datadistillery.wikibase.cloud/entity/Q23` handler
2. `allow_nonconforming(spec_item, context)` — `https://datadistillery.wikibase.cloud/entity/Q24` handler
3. `route_value_to_reference(spec_item, value)` — `https://datadistillery.wikibase.cloud/entity/Q26` handler
4. `validate_reference_constraint(spec_item, references)` — `https://datadistillery.wikibase.cloud/entity/Q31` handler
5. `validate_value_from_list(spec_item, value, list_cache)` — `https://datadistillery.wikibase.cloud/entity/Q28`/`https://datadistillery.wikibase.cloud/entity/Q43` handler

**Value List Resolvers:**
1. `get_value_list(list_item_entity_uri, cache_policy)` — retrieves materialized list
2. `execute_value_list_sparql(list_item_entity_uri)` — regenerates list from SPARQL
3. `match_value_to_list(input_value, list_items, match_policy)` — fuzzy matching/coercion

**Qualifier Validators:**
1. `validate_expected_qualifiers(statement, expected_entities)` — P164 enforcement
2. `coerce_qualifier_values(qualifier_dict, specs)` — recursive coercion for nested qualifiers

---

## Next Implementation Steps (Profile Architect Track)

### Immediate Actions

1. **Enumerate Policy Items in DD Wikibase**
   - Query all items referenced by `P159` (validation policy)
   - Query all items referenced by `P161` (form policy)
   - Document their labels, semantics, and intended runtime behavior
   - Add to Property-to-Semantics table above

2. **Finalize Cache Format Decision**
   - Review current YAML usage patterns in SpiritSafe profiles
   - Assess benefits of YAML vs JSON for:
     - Human readability (curator inspection)
     - Diff/merge workflows (version control)
     - Runtime performance (loading/parsing)
   - Document recommendation with rationale
   - Update dev doc with decision

3. **Design SPARQL Extraction Queries**
   - Query 1: Extract all GKC Entity Profile items (P1 → `https://datadistillery.wikibase.cloud/entity/Q3`) with full claim structure
   - Query 2: Extract all GKC Entity Statement items (P1 → `https://datadistillery.wikibase.cloud/entity/Q5`) with datatype + Wikidata property mappings
   - Query 3: Extract all policy/constraint items referenced by profiles
   - Test queries against DD Wikibase and verify completeness

4. **Design Wikibase → YAML Transformation Logic**
   - Map P157 qualifier structure → YAML `statements[]` entries
   - Handle monolingual text fields across multiple languages
   - Resolve statement-definition entity URIs to canonical `id` strings
   - Encode cross-profile linkages (P162) into appropriate YAML metadata
   - Determine ordering/grouping strategy for wizard field sequence

### Handoff to Semantic Engineer

After Profile Architect completes immediate actions, hand off:
- Completed Property-to-Semantics Mapping Table
- SPARQL extraction query suite
- Wikibase → YAML transformation specification
- Cache format recommendation

Semantic Engineer to implement:
- SPARQL query execution module
- Transformation pipeline (Wikibase JSON → SpiritSafe cache format)
- Fermenter datatype validators/coercers
- Runtime loading with property-to-semantics contract enforcement
- Sync CLI/workflow tooling
