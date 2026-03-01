# Architecture Overview

## Introduction

The **Global Knowledge Commons (GKC)** is a framework for understanding and working with structured knowledge across multiple open public platforms. The initial design focuses on Wikidata, Wikimedia Commons, Wikipedia templates, and OpenStreetMap.

The project uses a **data distillery** metaphor to describe the pipeline that converts raw, heterogeneous inputs into validated, platform-ready outputs. Mash Bills describe incoming structure, Modulation Profiles guide transformation, GKC Entity Profiles define canonical entity forms, and Barrel Profiles represent downstream platform-specific targets.

## Architecture Documents

This architecture section is split so implemented behavior is easier to locate:

- [Profile Loading Architecture](profile-loading.md)
- [SpiritSafe Infrastructure](spiritsafe-infrastructure.md)
- [Validation Architecture](validation-architecture.md)

## Core Concepts

### GKC Entity

A **GKC Entity** is a semantically coherent representation of a real-world thing rooted in the Wikibase/Wikidata model and extended across platforms in the Global Knowledge Commons.

Multiple platforms contribute to and consume a single GKC Entity:

- **Wikibase/Wikidata foundation**: Labels, descriptions, aliases, statements, qualifiers, references, and sitelinks.
- **Linked entities**: Item-valued statements naturally connect entities.
- **Multi-entity workflows**: One curation action may require adding or updating related entities.
- **Cross-platform integration**: Canonical data in Wikidata can drive content in Commons, Wikipedia, and OSM.

### GKC Entity Profile

A **GKC Entity Profile** is a YAML specification that defines entity structure, datatype constraints, qualifiers, references, and SPARQL-driven allowed-items hydration.

Profiles encode:

- Statement structure and requiredness.
- Datatype constraints for values, qualifiers, and references.
- Allowed-items hydration with fallback behavior.
- Curator guidance content used by profile-driven interfaces.

For profile details, see [Entity Profiles](../gkc/profiles.md).

### SpiritSafe

**SpiritSafe** is the profile registry and supporting query/cache infrastructure. It stores profile packages (`profile.yaml`, `metadata.yaml`, docs, and `queries/`) and provides a source for GKC runtime loading in local or GitHub-backed modes.

For implementation details, see [SpiritSafe Infrastructure](spiritsafe-infrastructure.md).

## Theoretical Design Notes

The following are directionally important but not yet fully implemented as stable architecture in GKC:

- Wizard execution environments beyond current local Python interfaces.
- Expanded profile composition and branching workflow semantics.
- Additional cross-platform publishing orchestration beyond current shipping abstractions.

These are retained as design intent for follow-on implementation work by the Wizard Engineer and Validation Agent.
