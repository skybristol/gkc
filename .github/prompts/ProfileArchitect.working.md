# Profile Architect Working Notes

**Purpose**: Capture issues, improvements, and enhancement requests for the SpiritSafe profile schema and metadata structure discovered during GKC Wizard development.

**Status**: Phase 1 Complete; Phase 2 (Pydantic Model Evolution) Ready

---

## High-Priority Items

### 1. ~~README Reevaluation~~ ✅ COMPLETED

**Status**: Simplified both profile READMEs to 3-4 line descriptions with link to external documentation at https://datadistillery.org/gkc/profiles/. Removed dense prose about development dynamics; kept folder structure description only.

---

### 2. Multi-profile Configuration & Cross-Entity Linking Architecture

**Current State**: 
- Profiles can reference other profiles via `entity_profile` field in statements (e.g., `office_held_by_head_of_state` statement in TribalGovernmentUS references OfficeHeldByHeadOfState profile)
- Metadata.yaml has `related_profiles` field listing connected profiles
- GKC Entity JSON Schema (see attached) defines curation packet structure that bundles primary + related entities
- Wizard MVP loads these as multi-entity curation packets but lacks explicit metadata about inter-profile relationships

**Design Direction** (informed by GKC Entity JSON work):
When wizard is invoked with a profile name, it:
1. Loads the primary profile
2. Identifies all `entity_profile` statements and builds a graph of related profiles
3. Creates a curation packet with placeholders for each related entity
4. When loaded with a Wikidata QID (post-MVP), hydrates the packet by fetching the primary item + all linked items via statement traversal
5. Presents to user as a multi-tab or multi-section curation interface where they edit primary + related entities together

Same architecture serves bulk operations: load one or more existing items, modify statements in primary + related entities, save/ship as a packet.

**Components That Need Definition**:

#### 1. Statement-Level Linkage Metadata

Each statement with `entity_profile` type needs to declare:
- **Which profile name** is expected as the target
- **Relationship semantics** (for future semantic linking to external systems)
- **Cardinality rules** (min/max linked entities, 1:1 vs 1:many)
- **Workflow policy** (create new, select existing, or both)

**Current Syntax** (example from TribalGovernmentUS):
```yaml
statements:
  - id: office_held_by_head_of_state
    value:
      type: entity_profile
      profile_name: OfficeHeldByHeadOfState
      # Missing: relationship semantics, cardinality, workflow policy
```

**Desired Enhanced Syntax**:
```yaml
statements:
  - id: office_held_by_head_of_state
    label: Head of State Office
    value:
      type: entity_profile
      profile_name: OfficeHeldByHeadOfState
      
      # NEW: Relationship context for cross-system linking
      relationship:
        type: executive_leadership  # Semantic type for future Wikimedia discussions
        description: The executive office governing this entity
      
      # NEW: Cardinality constraints
      cardinality:
        min: 0
        max: 1  # Most tribal governments have one head-of-state office
      
      # NEW: Workflow policy - how wizard should handle this
      workflow_policy: select_or_create  # vs "select_only" or "create_only"
      
      # Existing fields still present:
      constraints:
        - type: required
          applies_to: [references]
```

#### 2. Metadata-Level Profile Graph

Metadata.yaml needs explicit cross-reference declarations:

**Current Syntax**:
```yaml
name: Tribal Government (US)
description: ...
related_profiles:
  - OfficeHeldByHeadOfState
```

**Desired Enhanced Syntax**:
```yaml
name: Tribal Government (US)
description: ...

# NEW: Explicit profile linkage graph
profile_graph:
  edges:
    - target_profile: OfficeHeldByHeadOfState
      via_statement: office_held_by_head_of_state
      direction: outbound  # This profile LINKS TO the target
      cardinality: 1:1
      
      # Semantic metadata for future Wikidata/sister-project discussions
      relationship_type: executive_leadership
      wikidata_property: P1906  # office held by head of state
      
      # Curation packet generation hints
      auto_load_from_wikidata: true
      # When loading tribal gov Q5093 via QID, fetch P1906 target and auto-load
      
      # UI presentation hints
      presentation:
        wizard_mode: separate_tab  # vs "inline_form" or "related_sidebar"
        required_for_completion: false
        loading_sequence: 1  # Load order if multiple related profiles
```

#### 3. Curation Packet Structure (per GKC Entity JSON Schema)

The packet already defines cross-entity reference pattern in GKC Entity JSON Schema:
- **Packet-local references** (ent-001 → ent-002) that resolve post-shipping to Wikidata QIDs
- **Creation path breadcrumb** tracking where each entity originated in the curation workflow

#### 4. Bulk Operations Use Case

Bulk data operations need to work with the same architecture:

**Scenario**: "Add member count and update office leadership info for all federally recognized tribes"

**Architecture implications**:
- Operation loads N existing tribal government items from Wikidata
- For each, fetches linked office items via P1906
- Creates packet with multiple primary + related entities
- Allows curator to edit 2-3 statements across primary + related (not entire entities)
- Validates cross-entity constraints before shipping

---

**Major Design Decisions To Resolve**:

1. **Graph Directionality**: Should metadata declare edges one direction (primary → related) or bidirectional? 
   - Impact: Affects how wizard discovers related profiles and how bulk ops know what to load
   - **Current thinking**: One-way from primary to related; nav UI can show "primary ← related" reverse link if needed
   - **Architect Guidance** - I think we need to go both directions. I don't actually want to encode the idea that any one profile is primary. Pirmary is only a factor of the principal item type a "curation session" is concerned with. Primary in one circumstance will be secondary in another. It is an important concept in that the graph can't spool out forever, just from the primary point of curation to immediately related items. We should encode the graph structure in SpiritSafe metadata such that any profile is fully aware of all its neighbors.

2. **Cardinality Constraints**: Future profiles may have 1:many (e.g., tribal leaders, band councils)
   - How should packet structure handle multiple entities?
   - **Current thinking**: Allow array of related entities per statement; UI renders tabs if multiple
   - **Architect Guidance** - The basic framework in the UI is one where there are plan and review stages that bracket a set of three entity management screens. Entities being managed in the packet are listed out in a status section on the sidebar/menu. Users see the completion status for each entity and will be able to switch between them. We may need to work on further visual clues as things get more complicated with potentially many items making up a curation session.

3. **Auto-Loading from Wikidata**: When user provides a QID to wizard (post-MVP):
   - Should wizard fetch ALL related profiles recursively, or just direct children?
   - **Current thinking**: Direct children only (depth=1); future versioning can add recursive modes
   - **Architecture Guidance** This is exactly what I was getting at above. I can imagine a future level of maturity in an app where we can load an item and not fetch it's related items until called for, chaining on out as far as a user wants to provide edits. This is essentially what we do in Wikidata now if we are editing things in the UI - go from one related item to the next to the next, recording statements that we have information or judgments for.
   - **Architecture Guidance** I think we do need to look at our load wikidata item utility functionality with this development. I believe we have a couple of different capabilities in the code currently, using both SPARQL and the wbgetentities API. The latter pulls an entire item, but those items have only identifier references to related items in wikidata-item properties. With SPARQL, we can construct a query to pull at least labels from related items for those linkages. We'll want to leverage that when we load an item so that the wizard or any presentation of a curation packet contains human-readable labels in addition to identifiers.

4. **Presentation Strategy**: For wizard UI with multiple profiles:
   - Tabs? Collapsible sections? Step sequence?
   - **Current thinking**: Separate tabs (one per entity in packet); can edit in any order; review stage shows all
   - **Architecture Guidance** As discussed above, this is kind of how it is now, but the separate items in a curation packet are shown on the left sidebar status section and in the review page. There's no switching functionality currently, but we'll start with the side menu listing and see what other visual clues are needed. I do think we will fundamentally change both the plan and review screens in the wizard so that these clearly present the curation packet (one or more items) and the three "middle" screens (identification, statements, sitelinks) present one item at a time.

5. **Bulk Operations**: Should we unify bulk + single-entity under same architecture, or keep them separate?
   - **Current thinking**: Unified packet; `operation_mode` flag distinguishes bulk from single; same validation/shipping logic
   - **Architecture Guidance**: We should make this all part of the same architecture. At the end of the day, our GKC Entity Curation Packet needs to get spooled out via transformation logic into whatever items need to be shipped to Commons Partners (Wikidata, Wikimedia Commons, OSM, Wikipedia templates). Each Curation Packet will almost always have only some of the information needed for each linked thing we are working on, whether it comes from a wizard or some other operation.

6. **Statement Filtration for Bulk Ops**: How to express "only edit these statements" across multiple entities?
   - Whitelist or blacklist? How to express nested statements?
   - **Current thinking**: Whitelist (safer); support dot notation (office.inception, office.references)
   - **Architecture Guidance**: I agree with the whitelist approach in principle. We should build this into the mash part of the GKC architecture, and I think this is where we bring back in the Mash Bill metaphor. A Mash Bill works with the profiles that encode what is essentially the GKC's actionable menu of what it can successfully go after from mash sources and assemble into a Curation Packet that the GKC knows how to operate. One mode of operating is with a wizard instance. Other modes will handle bulk validation, transformation, and shipping.

7. **Relationship Semantics Vocabulary**: The `relationship.type` field is preparatory for future Wikimedia discussions.
   - Should we define controlled vocabulary now, or keep freeform and standardize later?
   - **Current thinking**: Start with freeform but document examples; standardize once patterns emerge
   - **Architecture Guidance**: Agreed. Some relationships will be influenced by point-in-time Wikidata or other partner system semantics. We need to be careful not to go too far into defining our own peculiar semantics but instead work to have those expressed in the partner systems themselves and then translated into actionable form for GKC operations.

8. **Cross-Entity Validation**: Some constraints may span multiple entities (e.g., office inception ≤ tribal govt inception).
   - Where do rules live? How does validation access related entities?
   - **Current thinking**: Deferred to post-MVP; keep validation scoped to single-entity for now
   - **Architecture Guidance**: We can only validate, coerce, transform, and otherwise act on entities for which we have created and are iterating GKC Entity Profiles. With that, we should be able to do every single thing that the GKC is capable of on every entity for which we have a registered profile.

**Text for consideration in defining components**

### GKC Entity Profiles
GKC Entity Profiles define the canonical structure, semantics, and cross‑platform meaning of a real‑world entity in the Global Knowledge Commons. They are implemented as Pydantic models and serve as the authoritative source of truth for how an entity should be represented, validated, and transformed across Wikidata, Wikimedia Commons, Wikipedia, OpenStreetMap, and other platforms.

### GKC Entity JSON Schemas
GKC Entity JSON Schemas are the machine‑readable, serializable representations of GKC Entity Profiles. They provide a stable contract for API routes, profile composition, and external tools. JSON Schemas allow profiles to reference one another, form graphs of related entities, and support dynamic generation of user interfaces and curation workflows.

### GKC Curation Packets
A GKC Curation Packet is the actionable bundle of information required to create or edit one or more entities. It combines the relevant GKC Entity Profiles, the dynamically generated Mash Bill for the task, source data harvested from Wikidata or other systems, and the Modulation Profile that governs how the entity may be adjusted. Curation Packets are the units of work that flow through the GKC Wizard, batch processors, and automated bots.

---

**Implementation Plan**:

0. **Phase 0: Documentation Foundation & Architectural Clarity** ✅ COMPLETED
   - Established architectural principles document (copilot-instructions.md)
   - Defined profile schema design patterns and naming conventions
   - See ProfileArchitect.doc_updates.md

1. **Phase 1 - Profile Schema & Metadata Evolution** ✅ COMPLETED (Profile Architect role):
   - ✅ **SpiritSafe Manifest Builder**: Implemented GitHub Actions workflow + script to generate registry manifest on each commit (profiles index, cache metadata, commit SHA, timestamp)
   - ✅ Update TribalGovernmentUS profile.yaml with linkage metadata on office_held_by_head_of_state statement (target_profile, relationship, cardinality, workflow_policy)
   - ✅ Update TribalGovernmentUS metadata.yaml with profile_graph section (bidirectional edge declaration)
   - ✅ Update OfficeHeldByHeadOfState metadata.yaml with reciprocal profile_graph edge
   - ✅ Create schema validation script (validate-profile-schema.py) enforcing linkage/graph rules
   - ✅ Wire validation into CI workflow (validate-profile.yml)
   - ✅ Update profiles/README.md with implemented schema documentation
   - ✅ Update CHANGELOG.md in both profiles with Phase 1 entries
   - ✅ Generate and commit cache/manifest.json as production artifact
   - ✅ PR #4 merged to main with complete Phase 1 scope

2. **Phase 2 - Pydantic Model Evolution** (gkc package) ⏳ READY FOR DEVELOPMENT:

   **Extended EntityProfile Model**:
   - Parse new linkage metadata from statements with `entity_profile` type
   - New fields: `statement_linkages`, `entity_profile_references` (derives from entity_profile statements)
   - Validation: Ensure all target profiles in linkage metadata exist in registry manifest

   **New ProfileGraph Model**:
   - **Nodes**: Profile definitions (name, metadata, cardinality constraints)
   - **Edges**: Bidirectional relationships with full metadata (via_statement, relationship_type, cardinality, traversal_depth)
   - Methods:
     - `get_neighbors(profile_name)` → List of directly connected profiles
     - `get_edges(source, target)` → Relationship metadata between two profiles
     - `traverse(start_profile, max_depth=1)` → Builder for multi-level profile queries
     - `validate_bidirectional_awareness()` → Ensure all edges are reciprocal
     - `get_cardinality(source, target)` → Returns (min, max) for linked entities

   **Enhanced EntityProfile Methods**:
   - `get_statement_linkages()` → Returns all statements that reference entity_profile
   - `get_linked_profile_names()` → Derives all connected profiles from statements + metadata
   - `validate_cardinality_constraints()` → Check min/max rules for linked entities
   - `get_link_definition(target_profile)` → Return full linkage metadata for specific connection

   **Tests**:
   - Graph traversal with various depth levels
   - Cardinality validation across linked entities
   - Bidirectional edge consistency checks
   - Round-trip: Profile → YAML → Pydantic model → graph traversal

3. **Phase 3 - GKC Spirit Safe Module** (gkc package) ⏳ READY FOR DEVELOPMENT:

   **Manifest & Registry Operations**:
   - `load_manifest(source="github"|"local", cache=True)` → Load SpiritSafe manifest.json with optional caching
   - `get_manifest_metadata()` → Returns (commit_sha, generated_at, commit_timestamp) for version tracking
   - `list_profiles()` → Returns all profile names in registry
   - `search_profiles(query_term)` → Find profiles by name, description, or related profiles
   - `get_profile_metadata(name)` → Load metadata.yaml for specific profile
   - `validate_manifest_integrity()` → Check all declared relationships are reciprocal, all cache paths exist

   **Profile Loading**:
   - `load_profile(name, with_metadata=True)` → Load single profile as EntityProfile Pydantic model
   - `load_profile_package(name, include_graph=True)` → Load primary profile + all directly connected profiles (returns dict with profile_graph structure)
   - `get_profile_graph(name)` → Load and return ProfileGraph model for a profile
   - `load_profiles_at_depth(name, max_depth=1)` → Load profile graph expanding to N levels
   - Caching strategy: Cache profiles by name + source commit SHA (enables version tracking)

   **Profile Graph Operations**:
   - `get_profile_linkage(source_name, target_name)` → Return linkage definition from statement + metadata
   - `resolve_profile_link(source_profile, statement_id)` → Return target profile name + linkage metadata
   - `get_related_profiles(name, depth=1)` → Returns list of profiles accessible within depth
   - `validate_package_graph(profiles_dict)` → Ensures loaded profiles maintain graph consistency

   **Curation Packet Creation** (foundation for wizard):
   - `create_curation_packet(primary_profile_name, operation_mode="single"|"bulk", load_wikidata_qids=None)` → Returns packet structure with:
     - Primary entity scaffold (empty form structure from profile)
     - Related entity scaffolds (from profile_graph, with linkage metadata)
     - Placeholder cross-references between entities (ent-001 → ent-002 pattern)
     - Curation context (which profiles are linked, cardinality constraints)
   - `validate_packet_structure(packet)` → Ensure all profiles in packet are registered, graph is consistent

   **Tests**:
   - Load manifest from GitHub vs local cache
   - Profile package loading (primary + 1 level related)
   - Deep profile graph traversal (3+ levels)
   - Curation packet creation for single and multi-entity scenarios
   - Cardinality enforcement in packet (e.g., max 1 office per tribal government)
   - Round-trip: manifest → profile load → packet creation → validation

---

## SpiritSafe Repository Enhancements (Phase 2-3 Preparation)

To support efficient Phase 2-3 spirit_safe module development, SpiritSafe repository should provide:

### 1. Manifest Format Documentation & Contract

**In SpiritSafe repository**:
- Document the cache/manifest.json format in detail (add to profiles/README.md)
- Specify all fields that consumers can rely on for profile discovery and loading
- Clarify versioning strategy using Git commit SHA (stable version identifier)
- Include format changelog and breaking change policy
- Provide manifest contract examples for different use cases:
  - Simple discovery: list all profiles with basic metadata
  - Deep discovery: profiles with full profile_graph and statement_linkage details
  - Cache lookup: where to find cached SPARQL results

### 2. Manifest Cache Optimization

**Current state** (Phase 1):
- Manifest generated on every commit
- Includes all profile metadata, graph declarations, statement linkages
- Committed to cache/manifest.json

**Suggested enhancements**:
- Profile cache index mapping profile name → SHA, generated_at
- Optional manifest summaries (lightweight vs full) for fast discovery vs deep inspection
- Manifest "change delta" indicating which profiles changed since last commit
- Document cache invalidation strategy for gkc consumers

### 3. Example Manifest Consumers

Add to `.github/` or documentation:
- Python script showing how to load manifest.json and discover profiles
- Example: Query manifest to find all profiles with bidirectional graph edges
- Example: Use manifest to load only profiles in a specific category
- Example: Ver verify manifest integrity (all reciprocal edges present, all cache paths valid)

### 4. Test Fixtures & Schema Examples

**In tests/ (future)**:
- Example manifests at different versions
- Example profile packages (primary + related profiles)
- Test data for curation packet creation scenarios

### 5. CI/CD: Manifest Stability Checks

**Suggested addition to validation pipeline**:
- Ensure manifest.json is always up-to-date
- Fail CI if profiles changed but manifest not regenerated
- Verify all cross-profile dependencies (as implemented in Phase 1 validator)

---



**Trigger**: After Phase 2-3 spirit_safe module is complete and tested.

**Wizard will consume**:
- `load_profile_package()` - Gets primary profile + related profiles in a single call
- `create_curation_packet()` - Creates multi-entity scaffold with cross-references
- `ProfileGraph` model - Knows the relationships, cardinalities, and linkage metadata
- Profile-level `missing_consequence` fields (from profile schema refinements)

**Wizard must implement**:

1. **Multi-Entity Curation Interface**:
   - Load packet with `create_curation_packet(profile_name)`
   - Display entity list in sidebar (status indicator for each: empty, in-progress, complete)
   - Implement tab/section switching to edit different entities in packet
   - Each entity tabs through: Identification → Statements → Sitelinks → Review (for that entity)
   - Cross-entity review stage shows: primary entity, all related entities, cross-references between them

2. **Linkage-Aware Statement Collection**:
   - When rendering statements on a profile that has `entity_profile` type:
     - Show guidance that this references another profile
     - For `workflow_policy: create_new`, offer "Create new [target_profile]" option (adds to packet)
     - For `workflow_policy: select_existing`, offer linked-entity dropdown with cardinality validation
     - For current MVP, linked entities start as empty placeholders

3. **Cardinality Enforcement**:
   - `ProfileGraph.validate_cardinality()` during packet lifecycle
   - Block adding more entities than cardinality allows
   - Warn on incomplete cardinality (min not reached)

4. **Statement-Level Guidance**:
   - Use `missing_consequence` field in review stage
   - Show severity indicator (⚠️ for high-severity missing statements)
   - Help curator decide if current state is acceptable to save

5. **Future (Post-MVP)**:
   - QID loading: `load_profile_package_with_wikidata_hydration(qid)` to fetch primary + related items
   - Store entity links in packet as QIDs (not ent-001 placeholders)
   - Pre-populate form fields from Wikidata item data

---

## Handoff: Validation Agent

**Trigger**: After Phase 2-3 and ProfileArchitect schema refinements are complete.

**Validation Agent will consume**:
- Extended `EntityProfile` model with linkage metadata
- `ProfileGraph` model with cardinality and traversal info
- Curation packet structure (primary + related entities)

**Validation Agent must implement** (see ValidationAgent.working.md for detailed task breakdown):

1. **Statement-Level Validation** (existing, extends to linked entities):
   - Required fields validation within each entity
   - Datatype coercion (date, quantity, item, URL, monolingualtext)
   - Qualifier and reference validation
   - **New**: Account for `auto_create: true` statements (fixed value, focus on references only)

2. **Packet-Level Validation** (cross-profile constraints):
   - Cardinality validation: Ensure linked entities match min/max from profile_graph edges
   - Bidirectional consistency: If primary entity has statement linking to related_entity, ensure related_entity is in packet
   - Entity interdependencies: Validate any constraints that span multiple entities (e.g., office inception ≤ tribal govt inception)
   - Missing statement consequences: Track which high/medium-severity statements are missing across all entities

3. **Business Logic Validation**:
   - Cross-entity statement ordering (e.g., primary statement inception before related statement inception)
   - Cardinality assertions: Exactly N, at least N, at most N linked entities
   - Any cross-profile rules defined in metadata

4. **Output Structure**:
   - Return validation results keyed by entity (primary_entity, related_entity_1, etc.)
   - Each entity gets comprehensive issue list (errors block save, warnings record, info advisory)
   - Issue severity considers profile requirements AND graph constraints

5. **Integration Points**:
   - Real-time validation on value entry (single datatype coercion)
   - Comprehensive validation at review stage (full packet, all entities, cross-entity constraints)
   - Enable inline feedback to curator about linked entities

---

## Future Phases (Deferred)

**Phase 4 - Wizard Full Integration** (Wizard Engineer):
- Multi-entity UI implementation with profile graphs
- Statement collection for linked entities
- Cross-entity review and validation
- QID loading and live Wikidata hydration (post-MVP)

**Phase 5 - Bulk Operations Architecture** (Future):
- Bulk operation templates and workflows
- Statement filtration (whitelist approach, dot notation for nested qualifiers)
- Bulk data entry with curation packets
- Mash Bill integration for operation composition

---

### 3. Auto-Creation Pattern for Fixed-Value Statements

**Current State**: The `instance_of` statement in TribalGovernmentUS profile uses `behavior.value: fixed` to lock the value to Q7840353, but the intended workflow is unclear.

**Intended Behavior** (as clarified by user):
- If statement doesn't exist on entity: automatically create it with fixed value
- If statement exists: keep existing value (don't overwrite)
- User task: Only collect references, not the value itself
- Wizard should focus user attention on adding source references, not value entry

**Current Profile Syntax**:
```yaml
statements:
  - id: instance_of
    behavior:
      value: fixed           # Value locked to Q7840353
      references: editable   # References manually provided from SPARQL list
    
    value:
      type: item
      fixed: Q7840353
      label: federally recognized Native American tribe in the United States
    
    references:
      min_count: 1
      input_prompt: Add the Federal Register source for this classification statement
```

**Problem**: 
- Not clear from schema that this should auto-create if missing
- Not clear that wizard should skip value input UI entirely
- Not clear distinction between "fixed value, skip UI" vs "fixed value, show read-only"

**Needed Clarification**:
1. **Auto-creation flag**: Add explicit `auto_create: true` to indicate wizard should create this statement automatically?
2. **UI behavior flag**: Distinguish between:
   - `fixed + auto_create` → Skip value UI, focus on references
   - `fixed + no auto_create` → Show read-only value display
3. **Workflow hints**: Add field like `user_workflow: references_only` to clarify what user should do

**Proposed Enhanced Syntax**:
```yaml
statements:
  - id: instance_of
    behavior:
      value: fixed
      auto_create: true          # NEW: Create automatically if missing
      ui_mode: references_only   # NEW: Only show reference collection UI
    
    value:
      type: item
      fixed: Q7840353
      label: federally recognized Native American tribe in the United States
    
    references:
      min_count: 1
      input_prompt: Add the Federal Register source for this classification statement
```

**Alternative Approach**: Use a simpler top-level flag:
```yaml
statements:
  - id: instance_of
    workflow: auto_create_with_references  # Explicit workflow pattern
    value:
      type: item
      fixed: Q7840353
```

**Use Cases for This Pattern**:
- Classification statements where value is predetermined by profile
- Statements where curator's task is verification/sourcing, not value selection
- Profile-enforced consistency (all items in this profile MUST have this value)
- Focus curator attention on highest-value tasks (adding sources rather than selecting obvious values)

**Wizard Implementation Impact**:
- Need clear semantics to determine when to show value input UI
- Need clear semantics for when to auto-create vs require user action
- Pattern likely applies to other statements beyond instance_of

---

### 4. Sitelinks: URL-Based Entry with Semantic Relationships

**Current State**: Sitelinks section uses language dropdown → project dropdown → title input pattern. Profile defines allowed languages for each project.

**Proposed Change**: URL-based entry where users paste Wikipedia/sister project URLs and system parses them.

**Key Requirements**:

1. **User Experience**: 
   - Single text input per sitelink (paste URL)
   - System parses URL to extract: language code, project type, article title
   - Validates URL actually exists via `requests.head()`
   - More intuitive than language/project dropdowns
   - Easier to extend to arbitrary Wikimedia projects

2. **Bidirectional Transformation** (critical for loading existing items, post-MVP):
   - Must translate existing Wikidata sitelinks → editable URL format
   - Must transform user-entered URLs → Wikidata sitelink format
   - Round-trip integrity required

3. **Two-Part Structure Needed**:
   - **Part 1**: The URL itself
   - **Part 2**: Relationship/significance indicator
   
4. **Semantic Gap in Wikidata Model**:
   - **Problem**: Wikidata sitelinks have no semantic relationship indicator
   - Is Wikipedia article directly about this entity and ONLY this entity?
   - Or does article mention/discuss entity among other topics?
   - Same issue affects External IDs (assumed "same as" but rarely true semantically)
   
5. **Relationship Type Vocabulary**:
   - Need short, well-defined vocabulary of relation types
   - Examples (TBD by Profile Architect):
     - `primary`: Article/resource is primarily and exclusively about this entity
     - `shared`: Article/resource discusses this entity among others
     - `contextual`: Entity mentioned in context of broader topic
     - `same_as`: External identifier represents same entity (rare true case)
   - Helps determine how to handle links in different contexts
   - May inform future data quality / trust scoring

6. **Initial Scope**:
   - Start with vocabulary sufficient for Wikidata sitelinks
   - Only implement what we have placement for in Wikidata model
   - Design extensibility for future semantic enrichment

7. **Profile Schema Implications**:
   ```yaml
   sitelinks:
     input_mode: url_based  # vs language_selection
     
     relationship_types:
       - id: primary
         label: Primary article
         description: This article is exclusively about this entity
         
       - id: shared
         label: Shared article
         description: This article discusses multiple related entities
     
     validation:
       check_url_exists: true
       allowed_domains:
         - "*.wikipedia.org"
         - "*.wikimedia.org"
         - "*.wikidata.org"
       
     # Legacy structure still needed for serialization:
     languages:
       en:
         projects: [wikipedia, wikivoyage]
       chr:
         projects: [wikipedia]
   ```

8. **MVP Plan**:
   - Document this architectural direction for Profile Architect
   - Make minimal setup changes to current `SitelinksStep` structure
   - Keep existing functionality aligned with current profile schema
   - Full URL-based implementation post-MVP after profile schema updated

**Use Case**: User curating Tribal Government pastes:
```
https://en.wikipedia.org/wiki/Cherokee_Nation
```
System:
- Validates URL exists
- Parses: language=en, project=wikipedia, title="Cherokee_Nation"
- Asks: "What type of relationship?" → user selects "Primary article"
- Stores both URL and relationship metadata
- On save: serializes to Wikidata sitelink format
- On load: reconstructs URL from Wikidata sitelink for editing

**Benefits**:
- Dramatically better UX (paste vs multiple dropdowns)
- Captures semantic relationship (missing from current Wikidata model)
- Extensible to arbitrary sister projects
- Lays groundwork for external ID semantic modeling
- Enables future data quality analysis

---

## Profile Schema Improvements

### 5. Language Configuration Clarity

**Current State**: Languages are implicitly defined by presence in labels/descriptions/aliases sections.

**Problem**:
- Wizard must scan all three sections to determine supported languages
- No way to declare "this profile supports languages X, Y, Z but only requires X"
- Unclear whether absence of a language in one section is intentional or oversight

**Needed**: Explicit language declaration at profile level:
```yaml
languages:
  supported:
    - en
    - chr  # Cherokee
    - nv   # Navajo
  required:
    - en
  default: en
  guidance: >
    Provide labels and descriptions in English. Additional languages are optional
    but strongly encouraged for Cherokee and Navajo when applicable.
```

**Use Case**: Wizard can:
- Show tab UI only when multiple languages supported
- Validate required vs optional languages
- Guide users on language expectations

---

### 6. Profile/Metadata Description Redundancy

**Current State**: Both `profile.yaml` and `metadata.yaml` contain `name` and `description` fields.

**Observation**:
- profile.yaml: `name` and `description` (shorter, 1-2 sentences)
- metadata.yaml: `name` and `description` (longer, multiple paragraphs)

**Question for Profile Architect**:
- Is this intentional design (short vs long description)?
- Should profile.yaml contain minimal info and defer to metadata.yaml?
- How should wizard prioritize which description to show?

**Current Wizard Behavior**: Uses `metadata.description` if available, falls back to `profile.description`.

---

## Spirit Safe Module Enhancements

### 7. Profile Loading with Metadata

**Current State**: Wizard must make two separate calls:
```python
profile = load_profile(profile_name)
metadata = load_profile_metadata(profile_name)
```

**Suggestion**: Consider a unified loader:
```python
profile_package = gkc.load_profile_package(profile_name)
# Returns: ProfilePackage(profile=..., metadata=..., readme=...)
```

**Benefits**:
- Single source of truth for "everything about a profile"
- Ensures metadata and profile stay in sync
- Simplifies wizard code
- Could include parsed README if that becomes structured

---

### 8. README Access API

**Current State**: No programmatic way to access profile README files.

**If READMEs become structured/useful**: Add to spirit_safe module:
```python
readme_content = gkc.get_profile_readme(profile_name)
# or
readme_sections = gkc.get_profile_readme(profile_name, parsed=True)
```

---

## Wizard-Specific Observations

### 9. Guidance Field Structure

**Current State**: `guidance` fields are freeform text strings.

**Working Well**: Displaying guidance in help icons or captions.

**Potential Enhancement**: Consider structured guidance:
```yaml
guidance:
  text: >
    Use the name that the tribe uses in referring to itself as the primary label.
  examples:
    - "Cherokee Nation"
    - "Navajo Nation"
    - "Muscogee (Creek) Nation"
  warnings:
    - "Avoid historical or outdated names"
    - "Check official tribal government website for current usage"
  references:
    - url: https://example.com/tribal-naming-guidelines
      title: Tribal Naming Best Practices
```

**Use Case**: Wizard could render examples, warnings, and reference links in collapsible sections.

---

### 10. Form Policy Semantics

**Current State**: `form_policy: target_only` appears on `office_held_by_head_of_state` statement.

**Question**: What does this mean for wizard rendering?
- Only show QID input (no sub-wizard)?
- Show lookup/search interface?
- Disable creation of new entities inline?

**Needed**: Documentation of all `form_policy` values and their wizard implications.

**Current Understanding**: Unknown to wizard engineer; needs clarification.

---

### 11. Allowed Items Display

**Current State**: SPARQL-driven `allowed_items` return long lists (e.g., Federal Register issues).

**Wizard Need**: Know whether to:
- Show as dropdown (if list is short, e.g., < 20 items)
- Show as searchable select (if list is medium, e.g., 20-200 items)
- Show as lookup/autocomplete (if list is large, e.g., > 200 items)

**Suggestion**: Add cardinality hints to allowed_items configuration:
```yaml
allowed_items:
  source: sparql
  query_ref: queries/bia_federal_register_issues.sparql
  expected_count: large  # small, medium, large
  ui_hint: searchable_select  # dropdown, searchable_select, autocomplete
```

---

### 12. Quantity Datatype: Unit Pre-population

**Current State**: Quantity datatype properties (e.g., `member_count`) render as two inputs: amount + unit (QID).

**Problem**: No way to signal in profile whether units should be:
- Omitted entirely (no unit field shown)
- Optional (unit field shown but can be left blank)
- Required with specific allowed values
- Pre-populated with a default unit

**Use Cases**:
1. **No units** (e.g., `member_count`): Count of people has no units, just a number
   - Current behavior: Shows unit QID input field that should be left blank
   - Desired: Hide unit field entirely or mark as "not applicable"

2. **Optional units** (e.g., distance measurement): Could be meters, kilometers, miles
   - Show unit field, allow user to select from list or leave blank

3. **Required specific unit** (e.g., monetary amount): Must have currency
   - Show unit field, require selection from allowed units list

4. **Default unit** (e.g., temperature in scientific context): Assume Kelvin unless specified
   - Pre-populate unit field, allow user to change if needed

**Current Profile Syntax** (member_count example):
```yaml
- id: member_count
  value:
    type: quantity
    constraints:
      - type: integer_only
```

**Proposed Enhancement**:
```yaml
- id: member_count
  value:
    type: quantity
    unit_behavior: none  # or "optional", "required", "default"
    constraints:
      - type: integer_only

# Alternative for cases with units:
- id: height
  value:
    type: quantity
    unit_behavior: required
    allowed_units:
      - Q11573  # metre
      - Q3710  # foot
    default_unit: Q11573  # metre
```

**Wizard Impact**:
- `unit_behavior: none` → Don't show unit input field
- `unit_behavior: optional` → Show unit field, can be blank
- `unit_behavior: required` → Show unit field, validate not empty
- `default_unit: Q...` → Pre-populate unit field with specified QID

**Current Workaround**: Wizard shows unit field for all quantities; users must know to leave it blank for unitless quantities.

---

## Questions for Profile Architect

1. **README Purpose**: What should profile READMEs contain? Should wizard guidance live there or in metadata.yaml?

2. **Sub-Wizard Invocation**: How should profiles declare workflow organization for entity_profile statements?

3. **Auto-Creation Pattern**: How should profiles express "auto-create this statement with fixed value, only collect references"? Should this use `auto_create: true` + `ui_mode: references_only`, or a simpler `workflow: auto_create_with_references` pattern? What other workflow patterns will need similar expression?

4. **Sitelinks Relationship Vocabulary**: What relationship types should be defined for URL-based sitelinks? How should they map to Wikidata serialization? Are there placement options in Wikidata for semantic relationship metadata?

5. **Sitelinks URL Validation**: What domains should be allowed? Should validation include checking for URL existence? How should failed validation be handled (block save vs warning)?

6. **Sitelinks Bidirectional Transform**: What transformation logic is needed for existing Wikidata sitelinks → editable URLs? Should this be part of profile schema or wizard logic?

7. **Language Declaration**: Should languages be explicitly declared at profile level vs inferred from sections?

8. **Description Hierarchy**: Is the profile.description vs metadata.description split intentional? Which should wizard prioritize?

9. **Form Policy**: What are all valid `form_policy` values and what do they mean for UI rendering?

10. **Quantity Units**: How should profiles signal unit behavior for quantity datatypes? Should this use `unit_behavior: none|optional|required|default` with optional `allowed_units` and `default_unit` fields? How should unitless quantities (like member_count) be distinguished from quantities that require units?

---

### 13. Missing Statement Consequences

**Current State**: Profiles define a complete set of statements expected to be contributed. MVP philosophy acknowledges that curators will miss some statements (at least temporarily) as they work through the wizard.

**Problem**: 
- No way to communicate **why** a missing statement matters
- Review stage has no context for curators about downstream impact
- Validation shows "required field missing" but not useful consequences

**Design Decision**:
- Profile can express consequences of missing statements explicitly
- Review stage displays these consequences to help curators prioritize
- Examples of consequences:
  - "Member count is essential for tribal government profiling"
  - "Lead official office determines primary leadership structure"
  - "Sitelinks provide critical linkage to Wikipedia knowledge base"
  - "Federal recognition evidence supports data quality validation"

**Proposed Schema**:
```yaml
statements:
  - id: member_count
    label: Member Count
    description: Number of enrolled tribal members
    
    # NEW: Explain impact of being missing
    missing_consequence: >
      Member count is one of the most important metrics for tribal government profile.
      Without it, the profile is significantly incomplete and appears unverified across
      the Global Knowledge Commons.
    missing_severity: high  # high, medium, low
    
    # ... rest of statement definition

  - id: head_office_location
    label: Office Location
    
    missing_consequence: >
      Office location helps verify current operational status and supports geographic
      data quality checks.
    missing_severity: medium
```

**Wizard Impact**:
- StatementsStep: No change (continue allowing missing optional statements)
- ReviewStep: Display consequences for any statements not provided
- Could add visual indicator (⚠️) for high-severity missing statements
- Helps curators make informed decision: "Is this good enough to save draft?"

**Use Cases**:
1. **In-progress work**: Curator saves draft after collecting some statements, sees consequences for missing ones
2. **Data quality**: Community can see which profile elements were prioritized vs skipped
3. **Future enhancement**: Could feed into quality scoring algorithms

**Not "Required" Validation**: 
- Missing statements with consequences shown as guidance, not errors
- Allows flexible curation workflow (collect what you can find)
- Respects curator judgment about what's worth the effort to research

---

## Coordinating Phase 2-3 Development Across Repositories

**Goal**: Complete next-gen GKC Entity Profile support by implementing Pydantic models (Phase 2) and spirit_safe module (Phase 3) in the gkc package, using Phase 1 SpiritSafe registry infrastructure as the data source.

### Work Breakdown

#### Phase 2: gkc Package Pydantic Models

**Location**: `gkc/entity_profile.py`, `gkc/profiles/` module

**Tasks**:
1. Extend `EntityProfile` model:
   - Add fields for linkage metadata extraction from statements
   - Add validation that cross-references to existing profiles
   - Add derivation of linked profile names from entity_profile statements

2. Create new `ProfileGraph` model:
   - Nodes: Profile IDs and metadata
   - Edges: Bidirectional relationships with cardinality, traversal info
   - Methods: neighbors, edges, traverse, validate_bidirectional_awareness

3. Extend `EntityProfile.methods`:
   - `get_statement_linkages()`
   - `get_linked_profile_names()`
   - `validate_cardinality_constraints()`
   - `get_link_definition(target_profile)`

4. Tests:
   - Load TribalGovernmentUS profile, verify linkage metadata parsed
   - Traverse profile graph (1–3 levels)
   - Validate cardinality rules

**Dependencies**: Uses Phase 1 profile schema (linkage metadata, profile_graph in metadata.yaml)

**Timeline**: 2-3 days (includes tests, documentation)

#### Phase 3: gkc spirit_safe Module

**Location**: `gkc/spirit_safe.py` (or expand existing module)

**Tasks**:

1. **Manifest & Registry**:
   - Implement `load_manifest()` with GitHub/local source + caching
   - List/search profiles
   - Validate manifest integrity
   - Tests with Phase 1 manifest.json

2. **Profile Loading**:
   - Implement `load_profile(name)` using manifest
   - Implement `load_profile_package(name, include_graph)` for primary + related
   - Add caching strategy (name + commit SHA)
   - Tests: Load single profile, load profile package with graph

3. **Profile Graph Operations**:
   - Implement `get_profile_graph(name)`
   - Implement `resolve_profile_link(source_profile, statement_id)`
   - Implement `get_related_profiles(name, depth)`
   - Tests: Graph traversal at different depths

4. **Curation Packet Foundation**:
   - Implement `create_curation_packet(profile_name, operation_mode, load_wikidata_qids)`
   - Returns packet with entity scaffolds + cross-reference placeholders
   - Implement `validate_packet_structure(packet)`
   - Tests: Single entity packet, multi-entity packet with cardinality constraints

5. Tests:
   - Load manifest from GitHub (fixtures with Phase 1 manifest)
   - Load profile + related profiles
   - Create curation packet for TribalGovernmentUS (should include OfficeHeldByHeadOfState placeholder)
   - Validate packet with cardinality constraints

**Dependencies**: Phase 2 (EntityProfile, ProfileGraph models)

**Timeline**: 3-4 days (includes tests, integration tests)

#### Parallel Work: SpiritSafe Repository

**Location**: SpiritSafe repo (docs, CI enhancements, examples)

**Tasks**:
1. Document manifest.json format and contract (for consumers like gkc)
2. Add example manifest consumers (Python scripts showing how to query)
3. Add cache optimization notes (profiles index, change deltas)
4. Enhance CI with manifest stability checks (ensures regenerated on changes)
5. Consider adding example test fixtures for manifest versions

**Dependencies**: None (complements Phase 2-3 work)

**Timeline**: 1-2 days (documentation + CI enhancements)

---

## Documentation Requirements for Phase 2-3

> **Note**: User-facing curator documentation (guides, tutorials, conceptual overviews) is handled by **UserDocWriter** agent.  
> See `.github/prompts/UserDocWriter.working.md` for curator guide plans.
>
> Profile Architect focuses on: **Technical API documentation**, **CLI command reference**, and **Architecture documentation**.

---

### Architecture Documentation (docs/architecture/spirit_safe.md)

### Architecture Documentation (docs/architecture/spirit_safe.md)

**New document**: Technical design decisions and implementation details for maintainers and contributors.

**Location**: `docs/architecture/spirit_safe.md` (alongside SpiritSafe.md, SpiritSafe-testing.md)

**Audience**: Developers extending the spirit_safe module, not end users.

**Content**:
1. **Design Principles**
   - Manifest as "registry contract" (consumers rely on specific fields and format)
   - ProfileGraph as "queryable relationship model" (enables multi-level traversal)
   - Curation Packet as "workflow unit" (self-contained, validates independently)
   - Cache strategy (by name + commit SHA for version stability)

2. **Manifest Format Deep Dive**
   - Fields and their semantics
   - Why Git SHA is the version identifier
   - Backward compatibility approach
   - Extending manifest without breaking consumers

3. **Profile Graph Model**
   - Edge representation (statement-level linkage + metadata-level edges)
   - Bidirectional validation (reciprocal awareness requirement)
   - Traversal algorithm and depth limiting
   - Cardinality enforcement

4. **Curation Packet Structure**
   - Entity scaffold generation (form template from profile)
   - Cross-reference placeholder system (ent-001 → ent-002)
   - Linkage preservation in packet (who references whom)
   - Extension for post-MVP Wikidata hydration

5. **Testing Strategy Across Modules**
   - Manifest fixtures (golden file approach)
   - Profile loading fixtures (local vs GitHub)
   - Graph traversal test scenarios
   - Packet creation with various cardinality constraints
   - End-to-end scenarios (manifest → profiles → packet → usage)

6. **Error Handling**
   - Profile not found scenarios
   - Manifest integrity issues (missing reciprocal edges)
   - Cardinality violations
   - Cache invalidation and recovery

7. **Performance Considerations**
   - Manifest caching strategy
   - Profile loading lazy evaluation
   - Graph traversal efficiency (depth limiting)
   - Packet creation for large graphs (where to optimize)

---

### API Documentation (In-Code Docstrings)

**Location**: Inline docstrings in `gkc/spirit_safe.py`, `gkc/profiles/models.py`, `gkc/profiles/graph.py`

**Format**: Follow GKC docstring conventions (plain meaning, args, returns, side effects, examples)

**Content**:
- All public methods in spirit_safe module
- All Pydantic models (LinkageRelationship, ProfileGraph, StatementLinkage, etc.)
- Helper methods on ProfileDefinition
- Example code snippets for common usage patterns

**Auto-generation**: Docstrings will be rendered via mkdocstrings in technical documentation.

---

### SpiritSafe Repository Documentation

**Location**: SpiritSafe repo (profiles/README.md, docs/profile_schema.md)

### SpiritSafe Repository Documentation

**Location**: SpiritSafe repo (profiles/README.md, docs/profile_schema.md)

**Purpose**: Technical specifications for registry consumers (gkc, other tools)

#### Manifest Format Specification (profiles/README.md enhancement)

**Existing document enhancement**: Add technical manifest specification for developers.

**New section: "Manifest JSON Format Specification"**:
1. Complete schema documentation (all fields, nesting)
2. Example manifest with annotations
3. Consumer checklist (what fields to rely on vs optional)
4. Breaking change policy (versioning, deprecation)
5. Common queries and patterns (how to traverse manifest)

### Profile Schema Documentation (in SpiritSafe repo: docs/profile_schema.md)

**Enhancement**: Add sections specific to Phase 1-3 implementation.

**New sections**:
1. **Linkage Metadata (Statement Level)**
   - Purpose and use cases
   - Required subfields (target_profile, relationship, cardinality, workflow_policy)
   - Examples with real profiles

2. **Profile Graph (Metadata Level)**
   - Purpose and use cases
   - Bidirectional edge requirements
   - Cardinality field semantics
   - Validation rules (what CI enforces)

3. **Profile to Pydantic Mapping**
   - How YAML linkage maps to EntityProfile fields
   - How metadata.yaml profile_graph becomes ProfileGraph model
   - Type coercion and validation during load

---

### Documentation Scope Summary

**Profile Architect owns**:
- ✅ Architecture documentation (`docs/architecture/spirit_safe.md`)
- ✅ API documentation (docstrings in code, rendered via mkdocstrings)
- ✅ CLI command reference (syntax, options, examples)
- ✅ SpiritSafe technical specifications (manifest format, profile schema)
- ✅ Testing documentation (architecture docs, fixture strategies)

**UserDocWriter owns** (see `.github/prompts/UserDocWriter.working.md`):
- ✅ Data curator guides (conceptual, task-oriented)
- ✅ Wizard user documentation
- ✅ CLI quick-start for curators (workflow-focused, not command reference)
- ✅ Profile catalog documentation
- ✅ Troubleshooting guides for end users

---

## CLI Enhancements for Phase 2-3

### Current CLI Structure

**Existing commands** (main categories):
- `gkc auth` - Authentication helpers (Wikiverse, OpenStreetMap)
- `gkc mash` - Load Wikidata entities (qid, pid, eid, wp_template)
- `gkc shex` - ShEx validation utilities
- `gkc profile` - YAML profile utilities (validate, form-schema, form, lookups)

### Proposed New Commands for Phase 2-3

#### 1. `gkc registry` - SpiritSafe Registry Operations

**Purpose**: Discover profiles and inspect registry metadata without loading full profiles.

**Subcommands**:

```bash
# List all profiles in registry
gkc registry list [--limit N] [--format table|json]
  Output: Profile name, description, version, status

# Search profiles by name, description, or related profiles  
gkc registry search <query> [--field name|description|related] [--format table|json]
  Output: Matching profiles with context

# Show manifest metadata
gkc registry info [--format json|yaml]
  Output: Manifest version (commit SHA), generated date, profile count, cache paths

# Validate manifest integrity (check bidirectional edges, cache paths exist)
gkc registry validate [--verbose]
  Output: Validation report (all checks pass or errors found)

# Show profile relationships graph
gkc registry graph <profile_name> [--depth N] [--format ascii|json|dot]
  Output: ASCII tree, JSON structure, or Graphviz DOT for visualization
  Example: gkc registry graph TribalGovernmentUS --depth 2
```

**Use cases**:
- Explore what profiles exist without downloading them
- Find profiles related to a topic (search)
- Visualize profile relationships (graph)
- Verify registry health (validate)
- Check registry version (info)

**Options**:
- `--source github|local` (override SpiritSafe source, same as profile commands)
- `--github-repo owner/SpiritSafe` (override default GitHub repo)
- `--local-root /path` (use local SpiritSafe directory)

#### 2. `gkc profile package` - Load Profile Packages with Graphs

**Purpose**: Load primary profile + related profiles in a single command (foundation for curation packets).

**Subcommands**:

```bash
# Load profile package (primary + related profiles at depth 1)
gkc profile package load <profile_name> [--depth N] [--format json|yaml]
  Output: Profile package with graph structure and all profiles at specified depth
  Example: gkc profile package load TribalGovernmentUS --depth 1

# Show cardinality constraints for linked entities
gkc profile package cardinality <profile_name> [--format table|json]
  Output: Table of linked profiles with min/max cardinality constraints
  Example: Rows showing "TribalGovernmentUS -> OfficeHeldByHeadOfState: max=1"

# Validate package structure (graph consistency, cardinality)
gkc profile package validate <profile_name> [--verbose]
  Output: Validation report (structure consistent or errors found)
```

**Use cases**:
- Inspect what profiles will be loaded in a curation session
- Understand cardinality constraints before creating packet
- Verify graph structure is valid
- Debug cross-profile relationships

**Output example** (gkc profile package load):
```json
{
  "primary_profile": "TribalGovernmentUS",
  "profiles": {
    "TribalGovernmentUS": { "name": "...", "statements": [...] },
    "OfficeHeldByHeadOfState": { "name": "...", "statements": [...] }
  },
  "graph": {
    "edges": [
      {
        "source": "TribalGovernmentUS",
        "target": "OfficeHeldByHeadOfState",
        "via_statement": "office_held_by_head_of_state",
        "cardinality": { "min": 0, "max": 1 }
      }
    ]
  }
}
```

#### 3. `gkc packet` - Curation Packet Operations

**Purpose**: Create, inspect, and validate curation packets (multi-entity work units). **This is CLI's primary entry point for the packet workflow.**

**Subcommands**:

```bash
# Create empty curation packet from profile
gkc packet create <profile_name> [--output packet.json] [--mode single|bulk]
  Output: JSON packet with entity scaffolds, cross-references, linkage metadata
  Example: gkc packet create TribalGovernmentUS --output packet.json

# Show packet structure and entity list
gkc packet info <packet.json> [--format json|yaml|tree]
  Output: Packet structure, entities, cross-references, cardinality rules
  Example: Shows "2 entities in packet: TribalGovernmentUS (ent-001), OfficeHeldByHeadOfState (ent-002)"

# Validate packet structure and cardinality constraints
gkc packet validate <packet.json> [--verbose]
  Output: Validation report (structure valid, cardinality OK, or errors/warnings)

# Load existing Wikidata items into packet (post-MVP)
gkc packet load-wikidata <packet.json> --qid Q... [--output hydrated.json]
  Output: Packet with primary + related items fetched from Wikidata, cross-references resolved
  (Future: enables editing existing items)

# Export packet to serialization format
gkc packet export <packet.json> --format wikidata_json|quickstatements [--output output.json]
  Output: Transformed packet ready for shipping to Wikidata/QuickStatements
  (Future: implements serialization logic)
```

**Use cases**:
- CLI-based curation workflow: create packet → inspect → validate → load into wizard → submit
- Script-based workflows: create packets for bulk operations
- Inspect what will be created before launching wizard
- Debug multi-entity packet issues
- Export curation results to external systems

**Example workflow**:
```bash
# Create packet for tribal government curation
gkc packet create TribalGovernmentUS --output packet.json

# Inspect what will be curated
gkc packet info packet.json --format tree

# Validate packet structure
gkc packet validate packet.json --verbose

# (Optional) Pre-populate from Wikidata if editing existing tribal government
gkc packet load-wikidata packet.json --qid Q... --output hydrated.json

# Launch wizard with packet (wizard loads this structure)
gkc profile form --profile TribalGovernmentUS --packet packet.json  
  (New flag: --packet to load pre-created packet instead of empty form)

# Export results after wizard completes
gkc packet export completed_packet.json --format wikidata_json --output submission.json
```

#### 4. `gkc profile form` - Enhancement for Multi-Entity Support

**Existing command enhancement** (not new, but extends with new flags):

```bash
# Existing: gkc profile form --profile <path>

# NEW FLAGS:
--packet <packet.json>     # Load pre-created packet instead of empty form
--depth N                  # Auto-create packet with profile + N-level related
```

**Enables**:
- CLI-based packet creation → wizard loading in one workflow
- Depth-based multi-entity loading ("load primary + all related, up to 2 levels")

### CLI Implementation Guidance

**Organization**:
- `gkc registry` commands → `_handle_registry_*` functions (manifest queries, no profile loading)
- `gkc profile package` commands → `_handle_profile_package_*` functions (profile loading with graph)
- `gkc packet` commands → `_handle_packet_*` functions (packet lifecycle)
- Extend `gkc profile form` → Add new `_handle_profile_form` flags

**Argument Patterns** (consistent with existing CLI):
- `--source github|local` with `--github-repo` and `--local-root` overrides (reuse existing helper functions)
- `--format json|yaml|table|tree|dot` for flexible output
- `-o, --output` for writing to file vs stdout
- `--verbose` for detailed output
- `--json` for machine-readable output (top-level flag from main parser)

**Error Handling**:
- Profile not found → Exit code 1, suggest available profiles
- Manifest integrity issues → Exit code 1, suggest running `gkc registry validate`
- Cardinality violations → Exit code 1, show constraint that failed
- Network errors → Exit code 1, suggest checking network / GitHub access

**Output Examples**:

```bash
$ gkc registry list --format table
Name                      Description                          Version  Status   Related Profiles
TribalGovernmentUS        Federally recognized Native tribes   1.0.0    stable   OfficeHeldByHeadOfState
OfficeHeldByHeadOfState   Executive government offices        1.0.0    stable   TribalGovernmentUS

$ gkc registry graph TribalGovernmentUS --depth 1 --format ascii
TribalGovernmentUS
└─ OfficeHeldByHeadOfState (max=1)

$ gkc packet create TribalGovernmentUS
{
  "packet_id": "pkt-...",
  "operation_mode": "single",
  "entities": [
    { "id": "ent-001", "profile": "TribalGovernmentUS", "data": {...} },
    { "id": "ent-002", "profile": "OfficeHeldByHeadOfState", "data": {...} }
  ],
  "cross_references": [
    { "from": "ent-001", "to": "ent-002", "via_statement": "office_held_by_head_of_state" }
  ]
}
```

### Testing CLI Commands

**In gkc/tests/test_cli.py** (or new test_cli_registry.py, test_cli_packet.py):
- Test registry commands with fixtures (manifest, profiles)
- Test packet creation with various cardinality scenarios
- Test validation (both passing and error cases)
- Test --format output variations (json, yaml, table, tree)
- Test error handling (missing profile, corrupt packet, etc.)



**1. Dependencies & Handoffs**:
- Phase 2 completes first (no external dependencies)
  - Wizard Engineer and Validation Agent can review/test in parallel
  - SpiritSafe repo work is independent
- Phase 3 starts after Phase 2 testing complete
  - Inherits EntityProfile and ProfileGraph models from Phase 2
  - Consumes Phase 1 manifest from SpiritSafe
  - Provides APIs for Wizard Engineer and Validation Agent

**2. Testing Approach**:
- Phase 2: Unit tests for Pydantic models, integration tests with profiles
- Phase 3: End-to-end tests loading manifest → profiles → packet creation
- SpiritSafe: CI validation + documentation examples
- Shared: Fixtures with Phase 1 manifest.json (golden file)

**3. Validation Agent Alignment**:
- After Phase 2-3 complete: Validation Agent integrates with ProfileGraph and packet structures
- Implements packet-level validation (cardinality, cross-entity constraints)
- Tests multi-entity scenarios with `create_curation_packet()` output

**4. Wizard Engineer Alignment**:
- After Phase 3 complete: Wizard consumes `load_profile_package()` and `create_curation_packet()`
- Implements multi-entity UI for managing curation packets
- Review stage displays cross-entity data and consequences

### Success Criteria

✅ Phase 2-3 development complete when:
- All spirit_safe module methods implemented and tested
- Manifest loading works (GitHub source + local fallback)
- Profile package loading returns correct graph structure
- Curation packet creation handles single and multi-entity scenarios
- Cardinality validation enforces profile_graph constraints
- All tests passing (unit + integration + end-to-end)
- Documentation complete (docstrings + README)
- Wizard and Validation agents can begin implementation

---

## Implementation Notes for Profile Architect

- Wizard Engineer is now ready to work on multi-entity UI (Phase 4) once Phase 3 complete
- Validation Agent can implement core coercion functions in parallel with Phase 2-3, integrating with ProfileGraph after completion
- Any schema changes to SpiritSafe profiles should coordinate with both Phase 2 (model parsing) and Phase 3 (manifest consumer)
- Backward compatibility with Phase 1 manifest format is important for early adoption

---

**Status**: 
- Phase 1: Complete ✅ (SpiritSafe registry + profiles with linkage metadata)
- Phase 2: Complete ✅ (gkc Pydantic models + ProfileGraph + EntityProfile extensions)
- Phase 3: Ready for Implementation 🚀 (spirit_safe module, manifest loading, curation packet creation)
- Phase 4: Pending Phase 3 (Wizard Engineer multi-entity UI)

**Last Updated**: 2026-03-10 (Phase 2 completion confirmation, Phase 3 ready for development)

**Phase 3 Handoff Status**: 
- Validation Agent can begin core coercion function implementation in parallel with Phase 3
- Wizard Engineer should await Phase 3 completion before starting multi-entity UI work
- All Phase 2 tests passing; fixtures validated with SpiritSafe Phase 1 profiles
- Shared test data strategy confirmed (manifest.json + profiles in fixtures/)

**Next Review**: After Phase 3 spirit_safe module implementation begins
