# Wikimedia Commons Architecture

## Purpose

This document defines how `gkc` treats Wikimedia Commons as an extension layer on top of the Wikidata-centered GKC foundation.

The current architecture does not attempt to model Wikimedia Commons as a separate semantic universe. Instead, it treats Commons structured data as a specialized execution context that still relies on Wikibase statements, Wikidata items, and the same profile-driven runtime used elsewhere in `gkc`.

The practical outcome is a single package-owned GKC Entity Profile, `commons_media_object`, that can be attached implicitly whenever a workflow encounters a statement whose datatype points at a Wikimedia Commons-hosted object.

## Architectural Position

Wikidata remains the semantic foundation.

Wikimedia Commons extends that foundation in two complementary ways.

1. File pages can carry structured data through MediaInfo, backed by Wikibase and Wikidata properties and items.

2. Commons-hosted data assets in the `Data:` namespace can carry reusable geographic and tabular resources that are referenced from Wikibase statements.

In `gkc`, these are not modeled as unrelated resource classes. They are treated as Commons-side realizations of the same cross-system entity model.

That keeps the operating pattern consistent:

1. Author semantic contracts in the Meta-Wikibase.

2. Materialize them in SpiritSafe.

3. Execute curation, validation, packet assembly, bottling, and shipping in `gkc`.

## Why An Implicit Profile Exists

The Wikibase datatype alone is not enough to drive a useful Commons workflow.

For example, knowing that a statement has datatype `commonsMedia`, `geo-shape`, or `tabular-data` tells runtime code the primitive value form, but it does not tell the system:

- which additional Commons-facing metadata should be gathered

- which statements commonly travel together on a media object

- which qualifiers are needed for valid Wikibase serialization

- which value lists and format constraints should be offered in the UI

- which downstream destinations are file pages versus `Data:` namespace pages

The `commons_media_object` profile fills that gap.

It acts as the profile-level contract that sits above the primitive datatype and gives `gkc` a stable, reusable semantic bundle for Wikimedia Commons structured content.

## Datatype Trigger Rule

`gkc` treats the following Wikibase datatypes as Commons triggers:

- `commonsMedia`

- `geo-shape`

- `tabular-data`

When any statement in a profile or packet uses one of these datatypes, runtime workflows may resolve an implicit relationship to the `commons_media_object` profile.

The intent of that relationship is architectural, not magical.

It means the runtime can infer that the value being curated is not just an opaque string or file name. It is a Commons-hosted object that should be handled with the Commons-specific semantic contract.

This pattern avoids forcing every profile author to redundantly declare a second explicit profile link every time a Commons value appears, while still letting the runtime load a well-defined profile contract.

## Scope Of The Commons Profile

The current baseline Commons profile covers the metadata needed for Wikimedia Commons structured data on media objects and for closely related Commons-hosted assets.

The seeded statement set is:

1. `depicts`

2. `copyright_status`

3. `copyright_license`

4. `inception`

5. `media_type`

6. `height`

7. `width`

8. `data_size`

9. `checksum`

10. `coordinates_of_the_point_of_view`

These statements provide a practical baseline for describing media files and related Commons resources without overcommitting the ontology before more packet, wizard, and shipper workflows are exercised.

## Statement Design Within The Profile

The ten seeded statements are not arbitrary.

They fall into four functional groups.

### Discovery And Meaning

- `depicts`
- `inception`
- `coordinates_of_the_point_of_view`

These statements improve findability, chronological interpretation, and spatial interpretation of Commons-hosted content.

They align closely with how Structured Data on Commons improves search, multilingual reuse, and cross-collection exploration.

### Rights And Reuse

- `copyright_status`
- `copyright_license`

These statements clarify the legal status of a file or related data object and support safer downstream use.

### Technical Description

- `media_type`
- `height`
- `width`
- `data_size`
- `checksum`

These statements describe the technical shape of the object being referenced or shipped.

This is especially important for bottling, shipping, and later validation and presentation work because a Commons target is not only semantically meaningful, it is also a concrete file or data artifact with format expectations.

### Modifier Support

Some Commons-oriented statements require helper qualifier or value entities rather than a bare primitive datatype.

The current contract includes support for:

- datetime precision
- coordinate precision
- IANA media type format constraints
- checksum format constraints
- value lists for rights and measurement units

This keeps the semantic layer explicit and reusable instead of hardcoding every Commons-specific rule into runtime code.

## MediaInfo Relationship

Structured Data on Commons is implemented on Wikimedia Commons through WikibaseMediaInfo.

That matters for `gkc` because Commons file pages are not treated as ad hoc metadata blobs. They are Wikibase-backed entities with:

- multilingual captions
- statements
- qualifiers
- references

From the perspective of `gkc`, this means a Commons file can participate in the same broad statement, qualifier, and reference model used elsewhere in the stack, even though the storage target is a Commons file page rather than a Wikidata item page.

The `commons_media_object` profile is therefore the `gkc` side of that bridge.

It does not replace MediaInfo. It tells `gkc` how to prepare, validate, and later ship data into the MediaInfo-oriented environment.

## Relationship To The Three Commons Datatypes

### `commonsMedia`

This datatype points to a Wikimedia Commons file name.

In isolation, that is only a primitive pointer to a file page. In `gkc`, it is also a signal that a file-centered structured data context may need to be assembled, validated, or shipped.

That is the most direct use of the `commons_media_object` profile.

### `geo-shape`

This datatype points to Commons map data, typically a `.map` page in the `Data:` namespace backed by GeoJSON.

Although the storage format differs from a media file, the object is still Commons-hosted and often participates in the same cross-system pattern: Wikidata anchors meaning, Commons stores reusable media and data artifacts, and downstream presentation layers consume the result.

For `gkc`, `geo-shape` therefore triggers the same Commons-profile context, while later runtime code decides which fields are applicable for a specific object subtype.

### `tabular-data`

This datatype points to Commons tabular datasets, typically `.tab` pages in the `Data:` namespace.

As with `geo-shape`, the Commons-hosted object is not a generic string. It is a structured data artifact with its own Commons-side lifecycle, licensing expectations, and downstream rendering uses.

The same implicit-profile rule lets packet assembly and validation treat the object as part of the Commons architecture instead of as a detached external identifier.

## Packet And Workflow Implications

This architecture is meant to support later runtime work in four places.

### Packet Assembly

When a source profile contains one of the three Commons datatypes, packet assembly can introduce a Commons-side sub-entity or linked entity context without requiring the source profile author to restate the full Commons metadata bundle each time.

### Validation And Coercion

Datatype validation still belongs to `fermenter`, but the Commons profile gives it the higher-order statement set, value lists, and helper constraints needed to validate a Commons object meaningfully.

### Bottling And Shipping

The profile provides the semantic material needed to move from packet content to Commons-facing payload construction, whether that means MediaInfo statements on a file page or later support for `Data:` namespace resources.

### Wizard And Presentation

The wizard layer can use the implicit profile to expose Commons-oriented guidance, grouped metadata prompts, and future specialized widgets without forcing every caller to hand-assemble those fields.

## Deliberate Boundaries

This baseline intentionally does not yet model:

- MediaWiki templates
- OpenStreetMap entity contracts
- the full Commons community modeling surface
- every Structured Data on Commons property in active use
- every possible distinction between file-page objects and `Data:` namespace objects

Those are deferred until the runtime paths for packet assembly, bottling, shipping, and wizard presentation are exercised through real use cases.

The current decision is to stabilize one clean Commons baseline first.

## Relationship To The Seed Ontology

The package-owned `meta_wb_init.yaml` seed now carries the Commons baseline contract in authored form.

That includes:

- the `commons_media_object` entity profile
- the ten baseline Commons statements
- helper items for precision and format specification
- value-list items for rights and unit selection
- SPARQL query fixtures for value-list hydration

This is the ontology-level commitment that lets later init, validation, and runtime work proceed from a stable baseline instead of rediscovering the Commons contract in code.

## Upstream References

The current architecture is aligned to Wikimedia’s published model and user-facing behavior, especially the following references:

- [Commons:Structured data](https://commons.wikimedia.org/wiki/Commons:Structured_data) for the overall Structured Data on Commons model, file captions, depicts statements, and Commons-side workflows.

- [Extension:WikibaseMediaInfo](https://www.mediawiki.org/wiki/Special:MyLanguage/Extension:WikibaseMediaInfo) for the MediaInfo entity model used on Commons file pages.

- [Wikibase/DataModel](https://www.mediawiki.org/wiki/Wikibase/DataModel) for the underlying statement, qualifier, reference, datatype, and entity model that Commons structured data still relies on.

- [Help:Map data](https://www.mediawiki.org/wiki/Help:Map_data) for `.map` resources in the Commons `Data:` namespace and their GeoJSON-based structure.

- [Help:Extension:Kartographer](https://www.mediawiki.org/wiki/Help:Extension:Kartographer) for how geoshape-backed Commons data are rendered and combined in Wikimedia map workflows.

- [Help:Tabular data](https://www.mediawiki.org/wiki/Help:Tabular_data) for `.tab` resources in the Commons `Data:` namespace and their JSON-backed table structure.

These references are not a substitute for the `gkc` contract, but they define the upstream execution environment that the `commons_media_object` profile is designed to serve.

## Summary

Wikimedia Commons is currently modeled in `gkc` as a Wikibase-compatible extension layer anchored in Wikidata semantics.

The package baseline is one implicit Commons profile trigger tied to three Commons-oriented datatypes and one seeded profile carrying ten baseline statements.

That is enough to give packet assembly, validation, bottling, shipping, and wizard work a stable architectural target while keeping broader Commons, template, and OSM modeling deliberately out of scope for now.