# Distillery Terminology Glossary

This document defines the core vocabulary used throughout the GKC package, organized by concept. Each term includes its technical meaning and plain-language explanation.

## Schema Architecture

### Barrel Schema
**Plain meaning:** A target system's schema or constraint specification.

The shape, structure, and validation rules defined by a specific target knowledge system. Each barrel (target system) has its own way of encoding what data should look like. Examples include Wikidata EntitySchemas (ShEx) coupled with property constraints, Wikimedia Commons schemas, Wikipedia infobox template parameters, and OpenStreetMap tagging schemes. Barrel Schemas define what constitutes valid, well-formed data for that particular system.

### Barrel Recipe
**Plain meaning:** Instructions for transforming data into a specific target system's format.

A transformation specification that maps from source data (or the Unified Still Schema) to a specific Barrel Schema's requirements. Each target system needs its own Barrel Recipe. A Wikidata Barrel Recipe transforms data into Wikidata claims, qualifiers, and references. An OSM Barrel Recipe transforms data into OSM features and tags. Barrel Recipes are often generated semi-automatically from Barrel Schemas.

### Unified Still Schema
**Plain meaning:** A canonical, system-agnostic data model for the distillery.

The meta schema that sits between source data and all target systems. Rather than mapping sources directly to each Barrel Schema separately, the distillery transforms source data into the Unified Still Schema once, then distributes from there to multiple target systems. This promotes cases where the same data gets pushed to Wikidata, OSM, Wikimedia Commons, and Wikipedia (versions of infobox templates at least) simultaneously. The Still Schema is the "common language" of the distillery.

### Still Recipe
**Plain meaning:** Instructions for transforming source data into the Unified Still Schema.

A transformation specification that maps raw source data fields to the canonical Unified Still Schema. This is typically the first transformation step, converting heterogeneous sources (CSV, JSON, API dumps) into a consistent internal representation. Each data source needs its own Still Recipe, but once transformed, the data can flow to any target system.

### Mash Bill
**Plain meaning:** The recipe for preparing and standardizing heterogeneous raw sources.

The specification that defines how to read, parse, and interpret diverse raw data sources during the Mash stage. Just as a distillery's mash bill specifies the mix of grains, proportions, and preparation methods before fermentation, the GKC Mash Bill defines how to handle variety in source formats, field names, encodings, and structures. It's the recipe that makes sense of the raw ingredients before they enter the transformation pipeline - often the most source-specific part of the entire process.

## Core Processing StagesGuided by the Mash Bill, this stage handles the diversity of source formats and structures. 

### Mash
**Plain meaning:** Initial data ingestion and parsing.

The raw input layer where heterogeneous data sources (CSV, JSON, spreadsheets, API dumps, RDF) are read, validated structurally, and prepared for transformation. Equivalent to the "must" or raw ingredient preparation in traditional distillation.

### Ferment
**Plain meaning:** Cleaning, normalization, and schema alignment.

The transformation layer where data is sanitized (whitespace, type coercion, encoding) and normalized to a consistent structure. Using insights from both the Mash Bill and target Barrel Schemas, this stage transforms the prepared ingredients into something ready for distillation. This is where messy becomes workable.

### Distill
**Plain meaning:** Core extraction and entity reconciliation.

The reconciliation layer where source records are matched to canonical entities (Wikidata items, OSM features), creating explicit links and resolving ambiguity through heuristics, authority files, and confidence scoring.

### Refine
**Plain meaning:** Deduplication, enrichment, and validation.

Post-reconciliation polishing where duplicate matches are collapsed, records are enriched with additional metadata or cross-references, and ShEx/quality constraints are applied to ensure the output meets shape and content requirements.

### Proof
**Plain meaning:** Quality scoring and confidence checking.

The validation and scoring layer where each distilled record is measured against quality metrics: completeness, consistency with reference data, internal coherence, confidence scores for matches, and fitness for downstream use.

### Blend
**Plain meaning:** Merging multiple sources into a unified dataset.

The combination layer where separate distilled datasets (e.g., Wikidata + OSM + referenced linkages) are merged, conflicts resolved, and a unified knowledge graph constructed. Analogous to blending spirits from different casks.

### Bottle
**Plain meaning:** Export in specific formats for downstream use.

The output serialization layer where distilled, validated, and blended data is formatted for external consumption (JSON-LD, TSV, RDF, ShEx-labeled exports, human-readable reports).

## Supporting Concepts

### Barrel (Storage)
**Plain meaning:** Cache, snapshot, and provenance storage.

The persistent storage layer for intermediate results, caches, versioned snapshots, and complete provenance trails. Allows reuse, rollback, and audit trails without re-computation. Note: Distinct from "Barrel Schema" (target system specification) – this is the storage container metaphor.

### Cut
**Plain meaning:** Filtering rules and heuristics that select the best data.

A decision criterion or filter that separates high-quality results ("the heart") from noise ("heads and tails"). Applied at multiple stages to trim low-confidence matches or invalid records.

### Spirit Safe
**Plain meaning:** Validation against Barrel Schemas and reference checking.

The quality gate that ensures data meets the shape, structure, and integrity constraints defined by Barrel Schemas before being bottled for delivery. Validates that transformed data conforms to target system schemas (e.g., checking Wikidata items against EntitySchemas, validating OSM features against tagging schemes). Named after the locked cabinet in traditional distilleries where the best product is inspected and held securely.

### Barrel Notes
**Plain meaning:** Metadata about data lineage and transformation.

Explicit provenance records, transformation logs, confidence scores, and source citations attached to each record. Allows traceability and reproducibility of how data was derived.

### Angel's Share
**Plain meaning:** Schema deviations preserved for future use.

Records, values, or details that do not conform to the current schema are preserved rather than discarded. These deviations are retained with notes so they can inform future schema expansion or alternate endpoints in the Global Knowledge Commons.

### Cask Strength
**Plain meaning:** Raw, unmodified source data (full fidelity).

Data presented without transformation, filtering, or qualification; the original form before reconciliation or enrichment. Useful for power users who want to apply their own logic.

### Heart
**Plain meaning:** The best or canonical match/result.

The highest-confidence, most-authoritative result after reconciliation and filtering. The "sweet spot" of quality.

### Reserve Batch (or Reserve Edition)
**Plain meaning:** High-quality, fully referenced, curated output.

A small, hand-checked or specially validated subset of the full distilled dataset, with complete citations and high confidence scores. For high-stakes use or reference.

## Component Layer (Modules/Services, future)

### The Mashery (or Mash Tun)
Ingest and initial parse module.

### The Fermenter
Cleaning and normalization engine.

### The Column Still (or Spirit Engine)
Reconciliation and entity linking engine.

### The Spirit Safe
Validation and constraints engine.

### The Cooperage
Barrel Schema management, property metadata, and reference data repository.

Maintains the collection of Barrel Schemas from various target systems, fetches and caches property definitions and constraints, and manages reference lookups. The cooperage provides the specifications and metadata needed to build Barrel Recipes and validate against target system requirements.

### The Barrel Room (or Rickhouse)
Caching, provenance, and versioning storage.

### The Blender
Dataset merging and conflict resolution.

### The Bottling Line
Export and serialization utilities.

### The Tasting Room
Human-review interface or reporting dashboard (future).

## CLI Verb Mapping

Each CLI verb maps to a core stage:

| Verb | Stage | Function |
|------|-------|----------|
| `gkc mash` | Mash | Ingest and parse raw data |
| `gkc ferment` | Ferment | Clean and normalize |
| `gkc distill` | Distill | Reconcile to canonical entities |
| `gkc refine` | Refine | Validate and enrich |
| `gkc proof` | Proof | Score quality and confidence |
| `gkc blend` | Blend | Merge sources |
| `gkc bottle` | Bottle | Export formatted output |
| `gkc barrel` | Barrel | Manage snapshots and provenance |
| `gkc label` | Metadata | Add documentation/attribution |
| `gkc toast` | Diagnostics | Health checks and debugging |

## Other Concepts

Some concepts are retained as-is:

- **Authentication**: credential and session management (no themed name).
- **ShEx**: Shape Expression validation (named for spec, not distillery).
- **SPARQL**: Query language (named for spec, not distillery).
- **Sitelinks**: Wikipedia/Wikimedia project links (domain term, kept as-is).

---

**Version**: 1.0  
**Established**: 2026-02-12  
**Status**: Foundation for terminology refactoring
