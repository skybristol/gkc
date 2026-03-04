# Changelog: TribalGovernmentUS

All notable changes to the Federally Recognized Tribe profile will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-03-01

### Added

- **Initial stable release** of the Federally Recognized Tribe profile
- **11 statement properties** fully defined with validation constraints and guidance
- **Multilingual support** for labels, descriptions, and aliases (English primary)
- **SPARQL-driven choice lists**:
  - Federal Register issues for instance-of references
  - Language items for native name qualifiers
- **Comprehensive statement definitions**:
  - Instance of (P31) with fixed value and SPARQL-sourced references
  - Official website (P856) with auto-derived reference URLs
  - Member count (P2124) with integer constraints and point-in-time qualifiers
  - Native name (P1705) with language qualifiers and validation
  - Headquarters location (P159) with structured address qualifiers
  - Inception (P571) with flexible date precision
  - OpenStreetMap relation ID (P402) with format validation
  - Flag image (P41) with Commons media validation
  - Office held by head of state (P1906) with entity profile linkage
- **Sitelink support** for English Wikipedia with validation policy
- **Reference patterns** using YAML anchors for reusability
- **Validation policies** allowing graceful handling of existing non-conforming data
- **Detailed guidance** in README.md including examples and use cases
- **Metadata documentation** for profile discovery and registry integration

### Fixed

- Corrected P1906 (office held by head of state) reference constraints
- Refined allowed_items fallback list for Federal Register references
- Normalized validation_policy across all statements for consistency

### Documentation

- Comprehensive README with entity description, usage guidance, and examples
- Metadata file with version, authorship, and capability summary
- CHANGELOG for version tracking
- Inline guidance for all statements and qualifiers

---

## [Unreleased]

### Added

- Explicit `linkage` metadata on `office_held_by_head_of_state` (P1906) for relationship semantics, cardinality, workflow policy, and traversal depth.
- Metadata-level `profile_graph` edge definition for `OfficeHeldByHeadOfState` including `via_statement`, relationship type, and cardinality.

### Planned

- Support for additional languages in labels, descriptions, and sitelinks
- Properties for treaty relationships and land cessions
- Enhanced support for tribal cultural heritage attributes
- Integration with Library of Congress and other external identifier systems
- Expanded geographic properties for traditional territories

---

**Note**: This profile is based on Wikidata EntitySchema E502 and expands upon it with enhanced validation, SPARQL-driven choice lists, and comprehensive guidance for data curators.
