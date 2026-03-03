## Implementation Plan

### Phase 0: Documentation Foundation & Architectural Clarity

**Goal**: Establish clear, authoritative definitions for core GKC architectural components and align existing documentation with multi-profile linking requirements discovered during Wizard MVP development.

**Rationale**: Before implementing technical changes to profiles, code, and UI, we need precise semantic definitions that all agents (Profile Architect, Validation Agent, Wizard Engineer) and future contributors can reference. The three core components—Entity Profiles, Entity JSON Schemas, and Curation Packets—are now mature enough to warrant formal documentation.

---

#### Deliverables

1. **New Documentation File: `docs/gkc/architecture.md`**
   
   Create comprehensive architectural overview including:
   
   - **GKC Entity Profiles** (expanded from draft text provided)
     - Definition as Pydantic models + YAML declarative source
     - Role as single source of truth for entity structure
     - Relationship to validation, UI generation, and cross-platform serialization
     - Profile graph concept (how profiles link to one another)
   
   - **GKC Entity JSON Schemas** (expanded from draft text)
     - Relationship to Entity Profiles (machine-readable serialization)
     - Role in API contracts and external tool integration
     - How profiles reference one another via `entity_profile` statements
     - JSON Schema generation from Pydantic models
   
   - **GKC Curation Packets** (expanded from draft text)
     - Definition as actionable bundle of 1+ entities + metadata
     - Structure: primary entity + related entities (via profile graph)
     - `packet_id` local reference system (ent-001, ent-002, etc.)
     - Status tracking (`in_progress`, `ready_to_resolve_refs`, etc.)
     - Creation path breadcrumbs showing entity provenance
     - Role in wizard workflows vs bulk operations
     - Relationship to Mash Bills and Modulation Profiles
   
   - **Architecture Diagram** (text-based or recommendation for tool)
     - Flow: Profile YAML → Pydantic Model → JSON Schema → Curation Packet → Wizard/Bulk Op → Serialized Output
     - Show profile graph edges (TribalGovernmentUS → OfficeHeldByHeadOfState)

2. **Update: `docs/gkc/entity-json-schema.md`**
   
   Enhancements to existing Entity JSON Schema documentation:
   
   - Add **Multi-Entity Packets** section:
     - Expand on packet array structure
     - Document `packet_id` reference system in detail
     - Show how `entity_profile` statements create cross-entity references
     - Examples of primary + related entity packets
   
   - Add **Profile Graph Integration** section:
     - How packet structure reflects profile linkages
     - Loading strategy (primary → related, depth=1)
     - Future: recursive loading, lazy loading of related entities
   
   - Add **Bulk Operations** section:
     - How packets support statement filtration
     - Difference between full-entity curation vs partial-statement updates
     - Examples: "Update member_count + office leadership across N tribes"
   
   - Add **Round-Trip Transformation** section:
     - Wikidata JSON → GKC Entity JSON (loading existing items)
     - GKC Entity JSON → Wikidata JSON (shipping)
     - Sitelinks: Wikidata format ↔ URL-based format (for future implementation)
     - How profile metadata informs transformation logic

3. **Update: `docs/gkc/profiles.md`**
   
   Add new sections:
   
   - **Profile Graphs & Cross-References**:
     - What `entity_profile` statement type means
     - How `metadata.yaml` declares profile relationships
     - Cardinality and workflow policies for linked entities
     - Examples from TribalGovernmentUS → OfficeHeldByHeadOfState
   
   - **Statement Types Reference**:
     - Comprehensive table of all value types
     - Special focus on `entity_profile` type (new/enhanced)
     - Include `form_policy`, `workflow_policy`, relationship semantics
   
   - **Profile Metadata Schema**:
     - Document all `metadata.yaml` fields
     - Explain `related_profiles` vs future `profile_graph` structure
     - Version history tracking via CHANGELOG integration
   
   - **Bidirectional Profile Relationships**:
     - Clarify that graph edges are bidirectional (architecture guidance #1)
     - Primary vs secondary is session-specific, not profile-intrinsic
     - Examples: Office profile knows it's referenced by TribalGov; TribalGov knows it references Office

4. **Update: `docs/gkc/wizard.md`** (if exists; create if not)
   
   Document wizard-specific profile consumption:
   
   - **Multi-Entity Curation Sessions**:
     - How wizard loads primary + related profiles into packet
     - UI presentation strategy (sidebar listing, tab switching)
     - Plan → Identify/Statement/Sitelinks → Review flow for multiple entities
   
   - **Profile-Driven UI Generation**:
     - How `guidance`, `input_prompt`, `constraints` drive form rendering
     - Statement type → input widget mapping
     - `allowed_items` → UI control selection (dropdown vs searchable vs autocomplete)
   
   - **Future: QID Loading**:
     - How wizard will hydrate packets from existing Wikidata items
     - SPARQL vs wbgetentities API for fetching related items
     - Depth-1 loading (direct children only)

5. **SpiritSafe Repository: Profile-Level Documentation**
   
   - **Update: `profiles/README.md`** (if exists at repo root):
     - Overview of profile structure (profile.yaml, metadata.yaml, CHANGELOG.md, queries/)
     - Link to `docs/gkc/profiles.md` for detailed schema
     - Link to `docs/gkc/architecture.md` for conceptual overview
   
6. **Cross-Reference Audit**
   
   - Review all existing documentation for references to:
     - "Entity Profile" → ensure consistent capitalization (GKC Entity Profile)
     - "Curation packet" → standardize to "GKC Curation Packet"
     - Outdated architectural terminology
   
   - Add navigation links between related docs:
     - `architecture.md` ↔ `profiles.md` ↔ `entity-json-schema.md` ↔ `wizard.md`

---

#### Success Criteria

- [x] New `docs/gkc/architecture.md` exists with comprehensive component definitions
- [x] `entity-json-schema.md` includes multi-entity packet, profile graph, bulk ops, and round-trip sections
- [x] `profiles.md` documents profile graphs, statement types, metadata schema, and bidirectional relationships
- [x] Wizard documentation (new or updated) explains multi-entity curation sessions
- [x] SpiritSafe profiles/ README provides clear entry point to documentation
- [x] Cross-references between docs are consistent and navigable
- [x] All agents (Profile Architect, Validation Agent, Wizard Engineer) can reference authoritative definitions

---

#### Timeline Estimate

- **architecture.md creation**: 2-3 hours (comprehensive definitions + examples)
- **entity-json-schema.md updates**: 1-2 hours (new sections + examples)
- **profiles.md updates**: 1-2 hours (new sections + cross-reference cleanup)
- **wizard.md**: 1 hour (if creating new) or 30 min (if updating existing)
- **SpiritSafe README updates**: 15 min
- **Cross-reference audit**: 30 min

**Total**: ~6-8 hours of focused documentation work

---

#### Dependencies for Subsequent Phases

Phase 0 completion unblocks:
- **Phase 1** (Profile Schema): Clear definitions inform YAML enhancements
- **Phase 2** (Pydantic Models): Architecture doc guides model design decisions
- **Phase 3** (Spirit Safe Module): Packet structure is formally defined
- **Phase 4** (Wizard Integration): UI design aligns with documented architectural patterns

---

**Next Steps After Approval**:
1. Create `docs/gkc/architecture.md` with draft content based on provided text
2. Expand `entity-json-schema.md` with multi-entity sections
3. Update `profiles.md` with profile graph documentation
4. Review existing docs for cross-reference opportunities
5. Submit for review before proceeding to Phase 1 schema changes

---

## Phase 0 Completion Report

**Status:** ✅ COMPLETED  
**Completion Date:** March 3, 2026

### Deliverables Completed

#### 1. Updated: `docs/architecture/index.md` (comprehensive root-level architecture overview)

**Content:**
- Expanded from 57 lines to ~400+ lines with comprehensive architectural component definitions
- Merged in detailed sections on core architectural components (Entity Profiles, Entity JSON Schemas, Curation Packets)
- Added architectural data flow diagram and design principles sections
- Added implementation status and related documentation sections

**Key Highlights:**
- Maintained existing high-level introduction and architecture documents index
- Blended detailed component documentation with existing overview structure
- Cross-references updated to point to both gkc/ subdocs and architecture/ detailed docs
- Now serves as authoritative root-level architectural overview for all agents

#### 2. Updated `docs/gkc/entity-json-schema.md` (+~300 lines)

**Sections Added:**
- **Multi-Entity Curation Packets**: Packet structure, cross-entity references, creation_path metadata, status tracking
- **Profile Graph Integration**: Discovery and loading strategy, multi-entity examples with depth-1 loading, automated population from profile relationships
- **Bulk Operations**: Statement filtration, operation_mode flag, partial-update patterns
- **Round-Trip Transformation**: Wikidata JSON ↔ GKC Entity JSON bidirectional conversion, sitelinks format transformation

**Key Highlights:**
- Documented packet array structure with primary + related entities
- Clarified packet_id reference patterns (ent-001-primary, ent-002-office)
- Established convention for creation breadcrumbs (primary.office_held_by_head_of_state)
- Included "Related Documentation" section with cross-links

#### 3. Updated `docs/gkc/profiles.md` (+~400 lines)

**Sections Added:**
- **Profile Graphs & Cross-References**: Graph structure, cardinality semantics, workflow policies, bidirectional relationships, examples from TribalGovernmentUS
- **Statement Types Reference**: Comprehensive table of all value types (item, string, url, datetime, entity_profile, etc.), field-level documentation for each type
- **Profile Metadata Schema**: Complete documentation of metadata.yaml fields (name, version, authors, schema_version, status, related_profiles, profile_graph)

**Key Highlights:**
- Clarified that profile graph edges are logically bidirectional (Office profile knows TribalGov references it)
- Emphasized entity_profile statement type as distinct from item type
- Documented workflow_policy and form_policy as future enhancements for linking semantics
- Updated "See Also" section with architecture.md, entity-json-schema.md, wizard.md references

#### 4. Created `docs/gkc/wizard.md` (~600 lines)

**Content:**
- Complete wizard documentation from profile → UI generation pipeline
- Detailed 5-step wizard structure (Plan, Identification, Statements, Sitelinks, Review)
- Multi-entity curation sessions with profile graph loading
- UI presentation strategies (sidebar navigation, tab-based switching)
- Profile-driven features (guidance text, input prompts, allowed-items rendering)
- Validation and error handling strategies
- Future enhancements (QID loading, entity editing workflows)

**Key Highlights:**
- Documented how profile fields map to UI components (label → input widget, allowed_items → dropdown/searchable select)
- Explained multi-entity packet creation when "Create new office" is clicked
- Clarified cardinality enforcement in UI (max_count: 1 disables additional creation buttons)
- Included detailed examples of each wizard step with mockup-style text diagrams
- Cross-referenced architecture.md, profiles.md, entity-json-schema.md

#### 5. Created `SpiritSafe/profiles/README.md` (~120 lines)

**Content:**
- Overview of Entity Profile Registry purpose and structure
- Profile directory structure documentation (profile.yaml, metadata.yaml, CHANGELOG.md, queries/)
- Current profiles summary (TribalGovernmentUS, OfficeHeldByHeadOfState)
- Usage examples (curator wizard launch, developer programmatic loading, architect profile creation)
- Profile graph concept introduction
- Links to external documentation at datadistillery.org

**Key Highlights:**
- Provides clear entry point for anyone exploring SpiritSafe repository
- Documents standard file layout expected in every profile directory
- Points users to comprehensive docs at datadistillery.org/gkc/

#### 6. Cross-Reference Audit & Linking

**Actions Taken:**
- Updated `docs/gkc/index.md` to add direct links to architecture.md, entity-json-schema.md, wizard.md
- Reorganized index.md "Getting Started" section to distinguish high-level docs from detailed implementation architecture
- Added "See Also" section to `docs/SpiritSafe.md` linking to all four core GKC docs
- Added "See Also" section to `docs/gkc/architecture.md` linking to profiles.md, entity-json-schema.md, wizard.md, SpiritSafe.md
- Verified `docs/gkc/profiles.md` "See Also" section includes all new references
- Verified `docs/gkc/entity-json-schema.md` "Related Documentation" section includes new references

**Terminology Consistency:**
- All documents now use "GKC Entity Profile" (capitalized, with GKC prefix)
- All documents use "GKC Curation Packet" (capitalized, with GKC prefix)
- Consistent use of "packet_id" for local references within packets
- Consistent use of "profile graph" for network of linked profiles

---

**Architectural Location Realignment**: Merged detailed architecture content from `docs/gkc/architecture.md` into `docs/architecture/index.md` (root-level architecture documentation section) as originally intended. 

- Original `docs/gkc/architecture.md` contains redundant content and should be removed manually or via git rm
- All cross-references in `docs/gkc/profiles.md`, `docs/gkc/entity-json-schema.md`, and `docs/gkc/wizard.md` updated to point to `../architecture/index.md`
- `docs/architecture/index.md` now serves as authoritative root-level architectural overview combining high-level introduction with detailed component definitions

**SpiritSafe Documentation Reorganization**: Consolidated SpiritSafe documentation from two locations into single authoritative file.

- Created new `docs/architecture/SpiritSafe.md` (consolidated registry documentation)
- Merged content from `docs/SpiritSafe.md` (high-level guide) and `docs/architecture/spiritsafe-infrastructure.md` (implementation details)
- Updated `mkdocs.yml`: Removed top-level `SpiritSafe: SpiritSafe.md`; changed architecture section entry to `SpiritSafe Registry: architecture/SpiritSafe.md`
- Updated all cross-references across docs to point to new location (`../architecture/SpiritSafe.md`)
- Old files to be removed: `docs/SpiritSafe.md`, `docs/architecture/spiritsafe-infrastructure.md` (via git rm)

**Design Decisions:**

1. **Separate architecture.md from architecture/ directory**: Created standalone `gkc/architecture.md` as high-level conceptual overview for curators/users, while keeping `architecture/` folder for detailed implementation docs (profile-loading.md, validation-architecture.md, etc.)

2. **wizard.md as new file**: Created comprehensive wizard documentation rather than scattered notes, establishing it as authoritative reference for Wizard Engineer

3. **Bidirectional profile relationships**: Documented that profile graph edges are logically bidirectional even if YAML only declares uni-directional edge (Office profile doesn't need to declare TribalGov relationship; this is inferred)

4. **packet_id naming convention**: Established pattern of ent-NNN-descriptor (e.g., ent-001-primary, ent-002-office) for maximum clarity in packet serialization

5. **Theoretical Design Notes sections**: Included clearly labeled sections in wizard.md and architecture.md for future enhancements (QID loading, recursive profile graph loading) to capture architectural intent without implying current implementation

**Cross-Reference Strategy:**

- Used "See Also" sections consistently at end of each major doc
- Linked from general → specific (architecture.md → profiles.md → specific profile structure)
- Created bidirectional links (architecture ↔ profiles, profiles ↔ entity-json-schema, etc.)
- Updated index.md to serve as navigation hub

**Documentation Style:**

- Followed MkDocs Python-Markdown strict mode (blank lines around lists, consistent indentation)
- Used formal section headers (##) for major sections, (###) for subsections
- Included concrete examples throughout (TribalGovernmentUS, OfficeHeldByHeadOfState)
- Added metadata footers to new docs (Last Updated, Maintainer, Status)

---

### Next Actions

Phase 0 documentation foundation is now complete. Ready to proceed with:

- **Phase 1**: Profile Schema Enhancements (YAML syntax for entity_profile statements, workflow_policy, form_policy)
- **Phase 2**: Pydantic Model Updates (EntityProfileStatement dataclass enhancements, profile graph parsing)
- **Phase 3**: Spirit Safe Module (Profile graph discovery, related profile loading, packet initialization)
- **Phase 4**: Wizard Integration (Multi-entity UI rendering, profile graph navigation, cross-entity reference management)

All agents (Profile Architect, Validation Agent, Wizard Engineer) now have authoritative definitions to reference during Phase 1-4 implementation.

---

**Files Changed:**
- ✅ Created `/Users/sky/code/gkc/docs/gkc/architecture.md`
- ✅ Updated `/Users/sky/code/gkc/docs/gkc/entity-json-schema.md`
- ✅ Updated `/Users/sky/code/gkc/docs/gkc/profiles.md`
- ✅ Created `/Users/sky/code/gkc/docs/gkc/wizard.md`
- ✅ Created `/Users/sky/code/SpiritSafe/profiles/README.md`
- ✅ Updated `/Users/sky/code/gkc/docs/gkc/index.md`
- ✅ Updated `/Users/sky/code/gkc/docs/SpiritSafe.md`

**Total Documentation Added:** ~1,500+ lines across 7 files
