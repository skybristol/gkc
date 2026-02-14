# Distillery Terminology Glossary

This document defines the core vocabulary used throughout the GKC package, organized by concept. Each term includes its technical meaning and plain-language explanation.

## Core Processing Stages

### Mash
**Plain meaning:** Initial data ingestion and parsing.

The raw input layer where heterogeneous data sources (CSV, JSON, spreadsheets, API dumps, RDF) are read, validated structurally, and prepared for transformation. Equivalent to the "must" or raw ingredient preparation in traditional distillation.

### Ferment
**Plain meaning:** Cleaning, normalization, and schema alignment.

The transformation layer where data is sanitized (whitespace, type coercion, encoding), normalized to a consistent overarching schema, informed by target ontologies (Wikidata entity schemas, OSM tags). This is where messy becomes workable.

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

### Barrel
**Plain meaning:** Cache, snapshot, and provenance storage.

The persistent storage layer for intermediate results, caches, versioned snapshots, and complete provenance trails. Allows reuse, rollback, and audit trails without re-computation.

### Cut
**Plain meaning:** Filtering rules and heuristics that select the best data.

A decision criterion or filter that separates high-quality results ("the heart") from noise ("heads and tails"). Applied at multiple stages to trim low-confidence matches or invalid records.

### Spirit Safe
**Plain meaning:** Validation and reference checking.

The quality gate that ensures data meets reference and integrity constraints before proceeding downstream. Named after the locked cabinet in traditional distilleries where the best product is held.

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
Schema, property dictionary, and reference management.

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
