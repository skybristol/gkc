# SpiritSafe: The Entity Profile Registry for the Global Knowledge Commons

**Purpose**: A comprehensive guide to understanding, contributing to, and maintaining the SpiritSafe registry—the centralized repository of GKC Entity Profiles that define how entities are structured, validated, and transformed across the Global Knowledge Commons.

---

## Vision: A Better Alternative to Wikidata Entity Schemas

### The Problem

Wikidata's EntitySchema (ShEx) system, while conceptually sound, has struggled to gain adoption and provide the operational clarity needed for profile management. Profiles are created in isolation, versioning is implicit, community contribution processes are unclear, and there's no unified registry that says "here are all the entity types the community understands and maintains."

### The SpiritSafe Solution

SpiritSafe reimagines the entity profile as a **registry entry**—a version-controlled, community-maintained package that brings together:

- **Profile Definition** (YAML)—The canonical structure of an entity type
- **Controlled Vocabularies** (SPARQL queries)—Definitive lists of allowed values for entity properties
- **Metadata & Documentation** (README, CHANGELOG, version history)—Clarity on purpose, authorship, and evolution
- **Governance** (PR review, human curation, CI validation)—Trust and quality assurance

**Metaphor**: In a traditional distillery, the **SpiritSafe** is a locked cabinet where the master distiller inspects and approves each batch of spirit before it moves to barrel aging or bottling. Similarly, SpiritSafe is where entity profiles are registered, reviewed, tested, and maintained as a community asset.

**Key Innovation**: By treating profiles as registry entries with explicit versioning, documentation, and governance, we make entity schema management transparent, auditable, and community-driven—solving the adoption and clarity problems that have plagued EntitySchema.

---

## Architecture: SpiritSafe in the Data Distillery

### The Data Distillery Metaphor

The **Global Knowledge Commons (GKC)** architecture uses whiskey distilling as its organizational metaphor:

- **SpiritSafe** — Registry of entity profiles (this document)
- **Entity Profiles** — The spirit (core product): YAML definitions of entity structure
- **Cooperage** — Code that shapes and prepares data (validation, coercion, transformation)
- **Bottler** — Final packages and exports (Wikidata JSON, Commons uploads, OSM relations)
- **Shipper** — Delivery to target platforms (Wikidata API, Commons, OSM)

### SpiritSafe's Role

SpiritSafe is the **registry layer** that:

1. **Centralizes** entity profiles that curators and developers need
2. **Maintains** definition, versioning, and history of each entity type
3. **Provides** controlled vocabularies (SPARQL-driven choice lists) used by profiles
4. **Enables** community contribution under clear governance
5. **Documents** each entity type's purpose, structure, and authorship
6. **Serves** as the single source of truth for profile definitions in GKC workflows

The **gkc** Python package fetches profiles and controlled vocabularies from SpiritSafe, validates them, and uses them to generate wizards, validators, and export logic. The `gkc.spirit_safe` module is the execution layer that loads profiles, hydrates choice lists, manages caches, and provides configuration for profile sources (GitHub or local).

---

## Directory Structure: Profiles as Registry Entries

### Rationale for Per-Profile Organization

Profiles are organized as **self-contained packages** rather than flat lists. This approach:

- **Isolates changes**: Modifications to one profile don't affect others
- **Clarifies ownership**: Each profile has explicit authorship and responsibility
- **Enables clear versioning**: Profile version history is tracked together with the profile
- **Simplifies PR review**: Reviewers examine a specific profile package
- **Supports curation**: Metadata (README, CHANGELOG) lives with the profile
- **Scales**: Adding new profiles doesn't require structural changes

### Structure

```
SpiritSafe/
├── README.md                           # Registry overview and contribution guide
├── profiles/                           # All registered entity profiles
│   ├── TribalGovernmentUS/
│   │   ├── profile.yaml               # YAML profile definition
│   │   ├── metadata.yaml              # Profile metadata (version, status, authors)
│   │   ├── README.md                  # Profile documentation and use cases
│   │   ├── CHANGELOG.md               # Version history and change log
│   │   └── queries/                   # SPARQL queries for this profile
│   │       ├── tribal-recognition-references.sparql
│   │       └── tribal-government-offices.sparql
│   │
│   ├── OfficeHeldByHeadOfState/
│   │   ├── profile.yaml
│   │   ├── metadata.yaml
│   │   ├── README.md
│   │   ├── CHANGELOG.md
│   │   └── queries/
│   │       ├── government-office-classifications.sparql
│   │       └── head-of-state-government-types.sparql
│   │
│   └── [additional profiles...]
│
├── queries/                            # Shared/common SPARQL queries
│   ├── wikidata-items-by-type.sparql
│   └── [other shared queries...]
│
├── cache/                              # Cached SPARQL results
│   └── [managed by hydration process]
│
└── .github/
    ├── workflows/
    │   ├── validate-profile.yml       # Validate profile on PR
    │   ├── hydrate-caches.yml         # Refresh choice lists
    │   └── publish-release.yml        # Tag and release on merge to main
    └── CONTRIBUTION.md                 # Community contribution guidelines
```

### Directory Descriptions

#### `profiles/`
Registry of all entity profile packages. Each subdirectory represents one entity type and contains:

- **`profile.yaml`** — The GKC Entity Profile definition (canonical structure)
- **`metadata.yaml`** — Profile metadata (see below)
- **`README.md`** — Human-readable documentation of the entity type, use cases, and authorship
- **`CHANGELOG.md`** — Version history with dates and change descriptions
- **`queries/`** — SPARQL queries that generate controlled vocabularies for this profile's choice lists (optional, only if profile has SPARQL-driven allowed-item lists)

#### `queries/`

Shared SPARQL queries used across multiple profiles or commonly referenced. Individual profile queries live in `profiles/[name]/queries/`.

#### `cache/`

Cached results from SPARQL query hydration. Managed by CI workflow (see below). Structure mirrors the hierarchy for organization:

```
cache/
├── profiles/
│   ├── TribalGovernmentUS/
│   │   ├── tribal-recognition-references.json
│   │   └── tribal-government-offices.json
│   └── [...]
└── queries/
    ├── wikidata-items-by-type.json
    └── [...]
```

#### `.github/`

GitHub workflows and contribution guidelines for the registry.

---

## Profile Metadata: Registry Documentation

Each profile includes a `metadata.yaml` file that captures essential information for registry management and profile discovery:

```yaml
# TribalGovernmentUS/metadata.yaml

name: Federally Recognized Tribe
description: >
  Canonical form for representing a federally recognized Native American tribe
  in the United States. Based on Wikidata EntitySchema E502 concepts but extended
  with additional properties and enhanced validation.

version: 1.0.0                          # Semantic versioning
status: stable                          # stable | beta | deprecated
published_date: 2026-02-15

authors:
  - name: Sky Bristol
    contact: sky@example.org
    role: primary

maintainers:
  - name: Sky Bristol
    contact: sky@example.org

source_references:
  - name: Wikidata EntitySchema E502
    url: https://www.wikidata.org/wiki/EntitySchema:E502
  - name: United States Bureau of Indian Affairs
    url: https://www.bia.gov/

related_profiles:
  - OfficeHeldByHeadOfState  # Profiles related to hierarchies/governance
  - GovernmentAgency

community_feedback:
  email: profiles@example.org
  issue_tracker: https://github.com/skybristol/SpiritSafe/issues

# Profile capabilities summary (from profile.yaml - referenced for discovery)
datatypes_used:
  - item
  - string
  - quantity
  - url

statements_count: 12
references_required: true
qualifiers_used:
  - sourcing_circumstances
  - applies_to_territorial_jurisdiction
```

### Metadata Fields

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | Yes | Display name of the entity type |
| `description` | Yes | What this entity type represents |
| `version` | Yes | Semantic version (MAJOR.MINOR.PATCH) |
| `status` | Yes | stable, beta, or deprecated |
| `published_date` | Yes | ISO 8601 date of current version |
| `authors` | Yes | Primary profile designer(s) |
| `maintainers` | Yes | Current profile maintainer(s) |
| `source_references` | No | References (EntitySchema, Wikidata items, external resources) |
| `related_profiles` | No | Other profiles this type relates to |
| `community_feedback` | No | Where to report issues or suggest changes |
| `datatypes_used` | No | List of datatypes used (for discovery) |
| `statements_count` | No | Number of statements (for discovery) |

---

## Profile Documentation: README and CHANGELOG

### README.md

Each profile includes a `README.md` that explains:

1. **What is this entity?** — Plain-language explanation (e.g., "A federally recognized Native American tribe in the United States")
2. **When to use this profile** — Guidance for profile designers on when to apply this entity type
3. **Key statements** — List of primary properties that define this entity type
4. **Example entity** — A real Wikidata item that exemplifies this type (with QID and link)
5. **Known issues or limitations** — If any (e.g., "Sitelinks currently support English Wikipedia only")
6. **Future enhancements** — Planned additions or improvements
7. **Contributing** — How to propose changes to this profile

**Example structure**:
```markdown
# Federally Recognized Tribe

## What is this entity?

A Federally Recognized Tribe is a Native American tribe formally recognized 
by the United States Bureau of Indian Affairs...

## When to use this profile

Use TribalGovernmentUS when creating Wikidata items for:
- A specific federally recognized tribe
- NOT for historical tribes pre-dating federal recognition
- NOT for state-recognized but not federally recognized tribes

## Key Statements

- **Instance of (P31)**: Indicates this is a tribe organization
- **Government type (P1313)**: What form of government (tribal council, elected chief, etc.)
- **Country (P17)**: Always United States

## Example Entity

Bitterroot Salish Tribe: [Q24279783](https://www.wikidata.org/wiki/Q24279783)

## Known Issues

- Geographic data not yet integrated; coordinate fields are theoretical

## Contributing

To propose changes to this profile:
1. Fork SpiritSafe repository
2. Create a branch: `feature/tribal-government-update`
3. Edit `profiles/TribalGovernmentUS/profile.yaml` and this README
4. Submit PR with explanation of change
5. Await maintainer review
```

### CHANGELOG.md

Tracks all changes to a profile, enabling clear version history:

```markdown
# Changelog: TribalGovernmentUS

## [1.0.0] - 2026-02-15

### Added
- Initial stable release
- 12 statements fully defined
- Support for official website, member count, headquarters location
- Per-language labels, descriptions, aliases
- SPARQL-driven allowed-items lists for tribe classification

### Fixed
- Corrected P1313 (government type) reference constraints

### Deprecated
- Legacy `preferred_name` field (use label instead)

## [0.9.0] - 2026-01-20

### Added
- Beta release for community feedback
- Initial profile structure
- SPARQL queries for tribal classification

### Changed
- Restructured qualifiers for sourcing_circumstances
```

---

## Branch Strategy and PR Process

### Branch Naming

- **main**: Production-ready profiles, passing all CI checks, approved by maintainers
- **develop** (optional): Staging integration branch for coordinated changes
- **feature branches**: Created by contributors for new or modified profiles
  - Format: `profile/[profile-name]-[description]` or `feature/[profile-name]-[description]`
  - Example: `profile/tribal-government-update`, `feature/add-office-schema`

### Contribution Workflow

1. **Create branch** from main
   ```bash
   git checkout -b profile/tribal-government-update
   ```

2. **Edit profile files**
   - Modify `profiles/TribalGovernmentUS/profile.yaml`
   - Update `profiles/TribalGovernmentUS/CHANGELOG.md`
   - Update `profiles/TribalGovernmentUS/metadata.yaml` (increment version)
   - Update `profiles/TribalGovernmentUS/README.md` if needed
   - Add/modify SPARQL queries as needed

3. **Push and create PR**
   - Draft PR if work in progress
   - Final PR when ready for review
   - Description includes: why change, what changed, validation results

4. **Automated checks** (run on PR)
   - Profile YAML validation
   - SPARQL query syntax check
   - Metadata completeness validation
   - Choice list hydration from SPARQL queries (cache generation)

5. **Human review** (maintainer)
   - Review profile changes against design principles
   - Validate metadata accuracy
   - Ensure documentation is clear and complete
   - Approve or request changes

6. **Merge to main**
   - Once approved, PR is merged
   - Version tags created automatically (from metadata.yaml)
   - Release notes generated from CHANGELOG.md

---

## CI/CD Pipeline: Validation and Hydration

The SpiritSafe repository uses GitHub Actions workflows to ensure profile quality and maintain cached choice lists. Workflows are triggered on PR creation, PR updates, and manual triggers.

### Workflow 1: `validate-profile.yml` (On PR)

**Purpose**: Validate all profiles and SPARQL queries in the PR

**Steps**:

1. **Profile YAML Validation**
   - Load each profile YAML
   - Validate against GKC profile schema
   - Check for required fields (profile name, description, statements)
   - Report any validation errors

2. **SPARQL Query Validation**

   - Syntax check: Is each SPARQL query well-formed?
   - Test query execution: Can the query run against Wikidata?
   - Report query execution errors or warnings

3. **Metadata Validation**

   - Check metadata.yaml completeness
   - Verify semantic versioning (MAJOR.MINOR.PATCH)
   - Validate author/maintainer existence
   - Report missing or malformed metadata

4. **Documentation Check**

   - README.md exists and has required sections
   - CHANGELOG.md documents the version being published
   - Check for obvious typos or formatting issues

**Output**: Required checks pass/fail on PR; blocks merge if critical issues found

### Workflow 2: `hydrate-caches.yml` (On PR + Manual)

**Purpose**: Generate cached choice lists by executing SPARQL queries

**Steps**:

1. **For each profile with SPARQL queries**:
   - Execute each SPARQL query against live Wikidata endpoint
   - Transform results to JSON format expected by GKC
   - Cache results in `cache/profiles/[profile-name]/`

2. **For shared queries in `queries/`**:
   - Execute each query
   - Cache results in `cache/queries/`

3. **Fallback behavior**:
   - If Wikidata endpoint is unavailable, use previously cached results
   - Log warnings about cache staleness

**Trigger**: 
- Manual trigger on-demand (when editor knows Wikidata data has changed)
- Scheduled weekly or monthly (configurable)
- Run on merge to main (to ensure main always has fresh caches)

**Output**: Updated cache files committed to PR or automatically committed to main after merge

### Workflow 3: `publish-release.yml` (On main merge)

**Purpose**: Tag and release profile changes

**Steps**:

1. **Extract version** from metadata.yaml
2. **Create git tag** with version (e.g., `v1.0.0`)
3. **Generate release notes** from CHANGELOG.md
4. **Create GitHub Release** with tag, notes, and attached cache files
5. **Optional**: Push updated cache to CDN or package registry for distribution

**Output**: Versioned release of profile package available for download

---

## Integration with GKC: The spirit_safe Module

The `gkc.spirit_safe` module in the GKC Python package is the execution layer that consumes SpiritSafe registry assets. It:

### Profile Loading

```python
from gkc.spirit_safe import SpiritSafeSourceConfig, set_spirit_safe_source
from gkc.profiles import ProfileLoader

# Configure source (GitHub or local SpiritSafe)
set_spirit_safe_source(
    mode="github",
    github_repo="skybristol/SpiritSafe",
    github_ref="main"
)

# Load profile
loader = ProfileLoader()
profile = loader.load_from_file("profiles/TribalGovernmentUS/profile.yaml")
```

### Choice List Hydration

```python
from gkc.spirit_safe import LookupCache

# Initialize cache (uses configured SpiritSafe source)
cache = LookupCache()

# Get cached choice list results
tribal_refs = cache.get("profiles/TribalGovernmentUS/tribal-recognition-references")

# If cache miss or refresh needed, execute SPARQL query and update cache
```

### Configuration

- **GitHub mode** (default): Profiles fetched from https://raw.githubusercontent.com/skybristol/SpiritSafe/main/...
- **Local mode**: Profiles loaded from local SpiritSafe clone (for development)

---

## Source-of-Truth Status

SpiritSafe is now fully externalized and serves as the active source of truth at:

- https://github.com/skybristol/SpiritSafe

GKC no longer relies on a `.SpiritSafe/` directory inside the GKC repository.

For local development overrides, clone SpiritSafe and point GKC to that clone path when needed.

```bash
git clone https://github.com/skybristol/SpiritSafe.git
cd SpiritSafe
git checkout -b your-feature-branch
```

Then use local override in GKC runtime/CLI for branch validation and hydration tests.

---

## Theoretical Design Notes for Infrastructure Development

The following elements are designed but not yet fully implemented. These notes guide infrastructure development:

### 1. Automated Cache Refresh Pipeline

**Goal**: Keep choice list caches fresh without manual intervention  
**Approach**:

- Schedule hydration workflow weekly or monthly
- Fallback to previous cache if Wikidata endpoint unavailable
- Log staleness warnings so curators know if data is outdated
- Optional: Push updated caches to CDN for faster retrieval

**Open Questions**:

- What refresh cadence makes sense? (weekly, monthly, quarterly by profile?)
- Should each profile have its own refresh schedule or unified?
- How to handle transient Wikidata outages without generating false positives?

### 2. Profile Versioning and Backward Compatibility

**Goal**: Support multiple profile versions without breaking existing curated data  
**Approach**:

- Each profile version gets a git tag (v1.0.0, v1.1.0, etc.)
- GKC can specify which profile version to use: `ProfileLoader.load("TribalGovernmentUS@1.0.0")`
- Profile schema migration paths for major version changes
- Curated data can be validated against original profile version used

**Open Questions**:

- How to store multiple versions in single directory (folder per version, or git history)?
- When to enforce migration vs. allow legacy data?
- How to document breaking changes in CHANGELOG for curators?

### 3. Profile Discoverability and Registry Index

**Goal**: Curators and developers can discover available profiles  
**Approach**:

- Generate registry index (JSON) listing all profiles with metadata
- Web UI or CLI command to search/browse profiles
- Tag-based discovery (e.g., "government", "tribal", "organization")
- Community contributions feed to show recently updated profiles

**Open Questions**:

- Should profiles be tagged/categorized?
- How to balance ease of discovery vs. avoiding profile explosion?
- How to recommend profiles for a given use case?

### 4. Profile Lifecycle Management


- `status: deprecated` in metadata sends signal to users
- Automatic archive after X period of no updates
- Formal retirement process with data migration guidance
- Audit trail of profile creation → active → deprecated → archived

**Open Questions**:
ofile creation → active → deprecated → archived

**Open Questions**:
- What triggers deprecation (maintainer decision, community vote)?
- How to handle curated data when profile retires?
- How to preserve profile history (GitHub releases)?

---

## Community and Governance

### Who Can Contribute?

Community members can propose new profiles or changes to existing profiles via PR. All contributions must:

- Follow the profile schema and structure
- Include complete documentation (README, CHANGELOG, metadata)
- Pass all CI validation
- Be reviewed and approved by at least one maintainer

### Decision Making

- **Profile additions**: Maintainer approval + community consensus for significant new types
- **Profile changes**: Maintainer approval; breaking changes require community discussion
- **Infrastructure decisions**: Maintainers meet quarterly or as needed

### Reporting Issues or Suggestions

- **Bug reports**: GitHub Issues (e.g., "Profile X documentation is unclear")
- **Feature suggestions**: Discussion forum or email (see metadata.yaml `community_feedback`)
- **Contributing a new profile**: Create PR with complete profile package

---

## Conclusion

SpiritSafe reimagines entity schema management through a community-driven registry model. By treating profiles as curated, versioned, documented packages with transparent governance, we overcome adoption barriers that have hindered Wikidata EntitySchema. The per-profile folder structure keeps contributions manageable, the metadata and documentation make profiles discoverable, and CI/CD automation ensures quality.

As the GKC ecosystem matures, SpiritSafe will become the standard registry of entity types for the Global Knowledge Commons—a reference point where users can find, understand, and contribute to canonical entity definitions across platforms.
