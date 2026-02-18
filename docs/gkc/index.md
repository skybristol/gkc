# GKC Documentation

Welcome to the documentation for GKC (Global Knowledge Commons), a Python package for managing data and information contributions to Wikidata and related Wikimedia projects along with OpenStreetMap. This site covers the background, mapping formats, item creation workflow, sitelinks usage, and API reference.

## Getting Started

- [Installation and setup](setup.md) - setting up to operate the software (aka make whiskey)
- [Authentication](authentication.md) - set up credentials for Wikimedia apps and OpenStreetMap
- [Background](background.md) - read about where the project came from and its motivations
- [Distillery glossary](distillery_glossary.md) - terminology for stages, components, and key concepts

## Schema Architecture

GKC uses a two-schema architecture to enable multi-system data distribution:

- [Pipeline Overview](pipeline_overview.md) — Understand the end-to-end workflow with visual diagram and stage descriptions
- [Barrel Schemas](barrel_schemas/index.md) — Target system schemas and constraints
  - [Wikidata EntitySchemas](barrel_schemas/wikidata_entityschemas.md) — ShEx schemas and Barrel Recipe Builder ✅
  - [Wikimedia Commons](barrel_schemas/commons_schemas.md) — Commons structured data schemas 🚧
  - [Wikipedia Infoboxes](barrel_schemas/wikipedia_infoboxes.md) — Infobox template parameters 🚧
  - [OpenStreetMap Tagging](barrel_schemas/osm_tagging.md) — OSM tagging schemes 🚧

## Data Distillery Workflow

The following sections lay out the extract, transform and load (ETL) workflow the GKC package is designed to support - messy and disconnected data in to refined and linked open data out.

### Data Ingestion (mash tun)

- Schema building - present a list of properties or existing Wikidata item to get the start to an entity schema
- Data source annotation - review and enhance annotation on data sources
- Mystery data sniffer - evaluating source data to produce a best-guess data map

### Data Integration (ferment, distill, refine, proof and blend)

- [Fermentation](fermentation.md) - organize the ingredients and examine gaps between source data and target knowledge systems
- [Distillation](distillation.md) - record choices on how to handle gaps and necessary transformations
- [Refinement](refinement.md) - identify and confirm interconnections within and beyond the source dataset
- [Proofing](proofing.md) - examine the integrity of each component entity and their characteristics
- [Blending](blending.md) - examine and confirm the combination of entities that tell the larger story

### Data Delivery (bottling)

- Wikidata item maintainer - create new items and make claims on existing items in Wikidata
- Infobox template builder - output one or more filled infobox templates for Wikipedia
- Commons contributor - create new items and add properties on existing items in Wikimedia Commons
- OSM mapping & tagging - create new features or add to existing features with OSM tags

## Development Notes

- [Implementation Notes](copilot/index.md) - Detailed technical documentation from feature development sessions

## CI/CD

- [CI/CD](CI_CD.md)
- [Release Process](RELEASE.md)

## API Reference

- [API Reference](api/index.md)