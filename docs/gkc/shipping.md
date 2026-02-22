# Shipping: Submission & Receipt

## Overview

**Shipping** is the stage that handles submission of bottled and packaged data to components of the Global Knowledge Commons - Wikidata, OpenStreetMap, Wikimedia Commons, etc. Not all data gets shipped; some of it relies on hand delivery such as the infoboxes in Wikipedia.

| Aspect | Details |
|--------|---------|
| **Input** | Bottled data transformed into the proper formats for target systems |
| **What Happens** | Interaction with write APIs, transmission of data, receipt of delivery |
| **Output** | Receipt notices suitable for annotation for source systems and users |
| **Best For** | Final distribution of finished products (until the next distillation) |
| **Typical Duration** | Minutes to hours, depending on receiving capacity |

---

## The Problem Shipping Solves

Delivery to consumers:

- **Shipping docks are all different** High variability in write APIs
- **Final distribution varies** Wikimedia and OSM and others all have different write APIs
- **API rate limits** must be respected
- **Receipts document point in time state** successful placement of content recorded

**The cost of skipping Shipping**: Data isn't available in the Global Knowledge Commons until this happens

---

## Input Contract

Records entering Shipping should:

1. **Be bottled into the appropriate format** — Only records that pass structure/content validation
2. **Distinguish new or updates** — QIDs, OSM IDs, etc.
3. **Include provenance** — References and source metadata
4. **Be validated** — No known schema errors or conflicts

---

## Supporting Systems

### Barrel (Provenance)
Stores:
- History of actions suitable for annotation on shipped product

### Spirit Safe (Validation)
Provides:
- Final output models to verify the shippable product

---

## Relationship to Other Stages

**After**: Data are available across components of the Commons

---

## Common Patterns

### Pattern 1: "I need a dry-run first"
Generate export files and reports without uploading. Use diff or review to confirm before pushing to target systems.

### Pattern 2: "I need multiple outputs"
Configure Bottling to output in multiple formats at once (Wikidata JSON + Wikipedia infobox + OSM tags).

### Pattern 3: "I want to export only high-confidence records"
Filter by `_proofing_status == "pass"` or a minimum quality threshold.

---

## Reference

- **API Reference**: [Shipper API](api/shipper.md)
- **Target API Specs**:
-- [MediaWiki Action API](https://www.mediawiki.org/wiki/API:Action_API); overall framework for interacting with any MediaWiki instance
-- [MediaWiki Wikibase extension API documentation](https://www.mediawiki.org/wiki/Wikibase/API); includes several actions such as wbeditentity, wbsetclaim, etc.
-- [OpenStreetMap API](https://wiki.openstreetmap.org/wiki/API)
-- [OpenStreetMap API v0.6 Specifications](https://wiki.openstreetmap.org/wiki/API_v0.6)

---

## GitHub Issues & Development

Work on the Shipping stage is tracked under the [`ship` label](https://github.com/skybristol/gkc/issues?q=label%3Aship).

**Other Workflow Stages:**
- [`mash`](https://github.com/skybristol/gkc/issues?q=label%3Amash) — Data Ingestion
- [`ferment`](https://github.com/skybristol/gkc/issues?q=label%3Aferment) — Cleaning & Normalization
- [`distill`](https://github.com/skybristol/gkc/issues?q=label%3Adistill) — Reconciliation & Linking
- [`refine`](https://github.com/skybristol/gkc/issues?q=label%3Arefine) — Deduplication & Enrichment
- [`proof`](https://github.com/skybristol/gkc/issues?q=label%3Aproof) — Quality Assurance
- [`blend`](https://github.com/skybristol/gkc/issues?q=label%3Ablend) — Multi-Source Merging
- [`bottle`](https://github.com/skybristol/gkc/issues?q=label%3Abottle) — Bottling & packaging
