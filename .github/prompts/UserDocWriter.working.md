# User Doc Writer Working Notes

**Agent Role**: Create and maintain end user-facing documentation for GKC data curators and registry consumers.

**Responsibilities**:
- Write comprehensive guides for data curators using GKC profiles and wizards
- Develop conceptual documentation explaining SpiritSafe registry, profiles, and workflows
- Create tutorials and quick-start guides for common curation tasks
- Maintain consistency in tone, terminology, and structure across user documentation
- Ensure documentation is accessible to non-technical users

**NOT This Agent's Responsibility**:
- Technical API documentation (handled by Profile Architect)
- CLI command reference (handled by Profile Architect)
- Architecture documentation for maintainers (handled by Profile Architect)
- Code-level docstrings (handled by implementing agents)

---

## Handoff from Profile Architect: Phase 2-3 User Documentation Needs

### Priority Document: Data Curator's Guide to SpiritSafe Profiles

**Target Audience**: Data curators using GKC wizards and CLI tools to contribute to Wikidata, not developers integrating with the API.

**Location**: `docs/guides/curator-guide.md` (new)

**Purpose**: Help curators understand what profiles are, how to use them effectively, and how multi-entity curation works.

**Content Outline**:

#### 1. Introduction to Entity Profiles
- What is an entity profile? (Plain language: "A template for creating a specific type of item")
- Why profiles matter for data quality
- How profiles ensure consistency across contributions
- Relationship between profiles and Wikidata properties/items

#### 2. Understanding the SpiritSafe Registry
- What is SpiritSafe? (The catalog of available entity types)
- How to find profiles (registry search, browsing)
- Profile metadata: name, description, status, version
- When to use which profile

#### 3. Working with Single-Entity Curation
- Using the wizard with a profile
- Required vs optional fields
- Understanding field guidance and tooltips
- Adding references to statements
- Understanding qualifiers (when and why)
- Saving drafts vs submitting

#### 4. Multi-Entity Curation (Linked Profiles)
- **What are linked entities?** (Example: Tribal government + its chief's office)
- Understanding profile relationships
  - One-to-one relationships (example: tribe has exactly one chief's office)
  - One-to-many relationships (future examples)
- Creating linked entities together
  - When to create vs select existing
  - How cross-references work in the wizard
- Cardinality rules explained (min/max entities)
  - Example: "This tribe must have at least one office" (min=1)
  - Example: "This tribe can have at most one chief's office" (max=1)
- Review stage for multi-entity packets
  - Seeing all entities before submission
  - Understanding consequences of changes
  - Validating cross-entity relationships

#### 5. Profile-Specific Guidance
- How to read field-level guidance
- Understanding allowed values (dropdowns, SPARQL-sourced lists)
- Fixed values vs variable values
- Using fallback items when SPARQL unavailable

#### 6. Understanding Validation
- What validation errors mean
- Required field guidance
- Cardinality constraint violations
- How to fix common validation issues
- When to ask for help (community support)

#### 7. Common Curation Patterns
- Creating a new entity from scratch
- Editing an existing entity (reusing profiles)
- Creating an entity with relationships
- Bulk creation workflows (using templates)

#### 8. Best Practices
- How to write good labels and descriptions
- When to add aliases
- How to choose good references
- Working with incomplete information
- Coordinating with other curators

#### 9. Troubleshooting
- "Profile not found" - what to do
- "Validation failed" - common causes
- Network errors and retries
- When to report bugs vs ask for help

#### 10. Getting Help
- Community forums and support channels
- How to report profile issues
- Requesting new profiles or enhancements
- Contributing feedback on curation experience

---

### Supplementary Documents Needed (Future Work)

#### Profile Catalog Reference
**Location**: `docs/guides/profile-catalog.md`

**Content**:
- Alphabetical listing of all available profiles
- For each profile:
  - Name and description
  - Common use cases
  - Example items (Wikidata QIDs)
  - Related profiles (what you can link to)
  - Last updated date
  - Status (stable, experimental, deprecated)

#### Wizard User Guide
**Location**: `docs/guides/wizard-guide.md`

**Content**:
- How to launch the wizard
- Navigating the wizard interface
- Understanding the wizard workflow (collect → review → submit)
- Keyboard shortcuts and efficiency tips
- Draft management
- Error handling in the wizard

#### CLI Quick Start for Curators
**Location**: `docs/guides/cli-quickstart.md`

**Content**:
- Installing GKC CLI
- Finding profiles (`gkc registry list`, `gkc registry search`)
- Viewing profile structure (`gkc profile info`)
- Creating curation packets (`gkc packet create`)
- Inspecting packets (`gkc packet info`)
- Common workflows for CLI-based curation

---

## Terminology for Curator Documentation

**Preferred curator-friendly terms** (avoid jargon):
- ✅ "Entity" or "Item" (not "instance", "object", "node")
- ✅ "Profile" or "Template" (not "schema", "model", "definition")
- ✅ "Field" (not "property", "statement", "claim" unless explaining Wikidata concepts)
- ✅ "Required" and "Optional" (not "cardinality", "min_count")
- ✅ "Link" or "Connection" (not "edge", "relationship", "linkage")
- ✅ "Value" (not "datatype", "literal", "IRI")
- ✅ "Reference" or "Source" (not "provenance metadata")

**When technical terms are necessary, explain them**:
- First use: "statement (a field with a value and optional details)"
- First use: "qualifier (additional context for a statement, like a date or location)"
- First use: "cardinality (the minimum and maximum number of linked items allowed)"

**Tone**: Friendly, supportive, educational. Assume curator has domain expertise but limited Wikidata/technical knowledge.

---

## Documentation Style Guide for Curators

**Structure**:
- Short paragraphs (2-4 sentences max)
- Bulleted lists for scannable content
- Examples prominently featured (real-world scenarios)
- Screenshots/diagrams where helpful (coordinate with design)
- Step-by-step instructions numbered clearly

**Examples**:
- Use real profiles (TribalGovernmentUS, OfficeHeldByHeadOfState)
- Use real Wikidata items when possible (Q14708404 Poarch Band of Creek Indians)
- Show concrete values, not abstract placeholders
- "For example" before every example

**Callouts**:
- 💡 **Tip**: Helpful suggestions for efficiency or best practices
- ⚠️ **Important**: Critical information that affects data quality
- ❓ **Common Question**: Anticipated curator questions with answers
- ✅ **Success**: What success looks like for this task

---

## Coordination with Profile Architect

**Profile Architect provides**:
- Technical specifications for profiles, manifest, API
- CLI command reference (syntax, options, examples)
- Architecture documentation for maintainers
- Docstrings for API methods

**User Doc Writer transforms into**:
- Plain-language explanations of concepts
- Task-oriented guides for curators
- Examples that match curator mental models
- Troubleshooting guides for common issues

**Handoff process**:
- Profile Architect designs features and documents technical details
- User Doc Writer reviews technical docs and extracts user-facing concepts
- User Doc Writer writes curator guides independently
- Profile Architect reviews for technical accuracy
- User Doc Writer refines for clarity and accessibility

---

## Immediate Priorities (Post Phase 2-3 Implementation)

1. **Data Curator's Guide to SpiritSafe Profiles** (high priority)
   - Comprehensive guide covering sections 1-10 above
   - Examples using TribalGovernmentUS profile
   - Multi-entity curation workflow with office linkage
   - Timeline: Draft after Phase 3 complete, refine during Phase 4 (Wizard)

2. **CLI Quick Start for Curators** (medium priority)
   - Focused on common curator workflows
   - Registry discovery and packet creation
   - Timeline: After Phase 3 CLI implementation

3. **Profile Catalog Reference** (lower priority)
   - Can be auto-generated from manifest metadata
   - Coordinate with Profile Architect on generation script
   - Timeline: After registry expansion (more profiles available)

---

## Success Criteria for Curator Documentation

✅ Documentation complete when:
- Non-technical curator can create entity using profile without assistance
- Multi-entity curation workflow clearly explained with examples
- Common validation errors have troubleshooting guidance
- Curators can find and understand relevant profiles
- Feedback loop established (curators report unclear documentation)

---

## Open Questions for Profile Architect

1. Should curator guide explain Wikidata JSON structure? (Probably no - abstract away)
2. How much Wikidata context to provide? (Enough to understand why fields matter)
3. Should we document profile evolution/versioning? (Yes, but later - after v2 profiles exist)
4. Do curators need to understand SPARQL for allowed-items lists? (No - just "values are fetched from Wikidata")

---

**Status**: Agent created, awaiting Phase 2-3 completion for content development  
**Next Action**: Review Phase 3 implementation to extract user-facing concepts  
**First Deliverable**: Data Curator's Guide to SpiritSafe Profiles (post-Phase 3)
