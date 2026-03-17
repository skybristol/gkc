# GKC Documentation

Welcome to the documentation for GKC (Global Knowledge Commons), a Python package for managing data and information contributions to Wikidata and related Wikimedia projects along with OpenStreetMap. This site covers the background, mapping formats, item creation workflow, sitelinks usage, and API reference.

## Getting Started

- [Installation and setup](setup.md) - setting up to operate the software (aka make whiskey)
- [Authentication](authentication.md) - set up credentials for Wikimedia apps and OpenStreetMap
- [Background](background.md) - read about where the project came from and its motivations
- [Architecture Overview](../architecture/index.md) - comprehensive guide to GKC components, data flow, and design principles
- [Profiles](profiles.md) - comprehensive guide to profile structure, semantics, and SpiritSafe artifacts
- [Entity JSON Schema](entity-json-schema.md) - GKC Entity JSON format and multi-entity curation packets
- [Wizard Documentation](wizard.md) - profile-driven UI generation and multi-step curation workflows

## Advanced Architecture

- [Implementation Architecture](../architecture/index.md) - detailed architecture documents for profile loading, SpiritSafe infrastructure, and validation

## Data Distillery Workflow

The following sections lay out the extract, transform and load (ETL) workflow the GKC package is designed to support - messy and disconnected data in to refined and linked open data out.

### Profile Development

- [SpiritSafe Profile Artifacts](profiles.md) - Complete reference for defining and consuming profile artifacts with constraints and mappings

### Data Ingestion (mash tun)

- Schema building - present a list of properties or existing Wikidata item to get the start to an entity schema
- Data source annotation - review and enhance annotation on data sources
- Mystery data sniffer - evaluating source data to produce a best-guess data map

## Development Notes

The GitHub repo for the project maintains a wealth of background on architectural decisions and code design in [issues](https://github.com/skybristol/gkc/issues) and [pull requests](https://github.com/skybristol/gkc/pulls).

## CI/CD

- [CI/CD](CI_CD.md)
- [Release Process](RELEASE.md)

## API Reference

- [API Reference](api/index.md)