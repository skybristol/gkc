# Changelog: OfficeHeldByHeadOfState

All notable changes to the Office Held by Head of State profile will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-03-01

### Added

- **Initial stable release** of the Office Held by Head of State profile
- **4 statement properties** fully defined with validation constraints and guidance:
  - Instance of (P31) for office classification
  - Country (P17) for national context
  - Applies to jurisdiction (P1001) for governmental entity linkage
  - Inception (P571) for office establishment date
- **Multilingual support** for labels, descriptions, and aliases (English primary)
- **Sitelink support** for English Wikipedia with validation policy
- **Reference patterns** using YAML anchors for reusability
- **Validation policies** allowing graceful handling of existing non-conforming data
- **Integration design** with TribalGovernmentUS profile via P1906 relationship
- **Detailed guidance** in README.md including entity description, usage patterns, and integration examples
- **Metadata documentation** for profile discovery and registry integration

### Documentation

- Comprehensive README with entity description, usage guidance, and relationship diagrams
- Metadata file with version, authorship, and capability summary
- CHANGELOG for version tracking
- Inline guidance for all statements

---

## [Unreleased]

### Added

- Metadata-level `profile_graph` edge definition for `TribalGovernmentUS` via `applies_to_jurisdiction` (P1001), including relationship type and cardinality.
- Reciprocal graph-awareness metadata to support bidirectional profile discovery.

### Planned

- Properties for term length and term limits
- Properties for appointment or election methods
- Support for office reorganizations and historical name changes
- Enhanced temporal properties for abolished or reorganized offices
- Expanded qualifier support for office attributes

---

**Note**: This profile is designed to complement governmental entity profiles (such as TribalGovernmentUS) by providing a structured representation of executive office positions.
