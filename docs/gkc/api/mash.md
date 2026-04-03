# Mash Module API

## Overview

The mash module is the read/retrieval layer for source data in GKC workflows.

It includes:

- Generic Wikibase API retrieval via `WikibaseApiClient`
- MediaWiki page wikitext retrieval and SPARQL-block extraction primitives
- `MashSourceAdapter` plugin contract for source loader integrations
- Wikidata loaders and template objects
- Wikipedia template retrieval
- Utility functions for template preparation, raw-to-write payload shaping, and label hydration

Use mash for reads and template shaping. Write operations belong in shipper.

## Quick Start

```python
from gkc.mash import WikibaseApiClient, WikibaseLoader

# Generic Wikibase read (works with Wikidata or Data Distillery API URLs)
api = WikibaseApiClient(api_url="https://www.wikidata.org/w/api.php")
entity = api.get_entity("Q42")

# Wikidata convenience loader
loader = WikibaseLoader()
template = loader.load_item("Q42")
print(template.summary())
```

## Public API Quick Starts

### `WikibaseApiClient`

```python
from gkc.mash import WikibaseApiClient

client = WikibaseApiClient(api_url="https://datadistillery.wikibase.cloud/w/api.php")

results = client.search_entities(
    label="GKC Property Specification",
    entity_type="item",
    language="en",
    limit=5,
)

batch = client.get_entities(["Q1", "Q2"])
single = client.get_entity("Q1")

raw = client.request({"action": "query", "format": "json", "meta": "siteinfo"})
print(len(results), sorted(batch.keys()), single.get("id"), bool(raw))
```

`WikibaseApiClient.get_and_transform_entity()` provides a one-line bridge from
raw entity retrieval to shipper-ready payload preparation for templating
workflows.

`WikibaseApiClient` sends a default `User-Agent` header automatically when one is not provided. You can still pass a custom `user_agent` value in the constructor to override it for your workflow.

### `fetch_mediawiki_page_wikitext()`

```python
from gkc.mash import WikibaseApiClient, fetch_mediawiki_page_wikitext

api_client = WikibaseApiClient(api_url="https://datadistillery.wikibase.cloud/w/api.php")
wikitext = fetch_mediawiki_page_wikitext(api_client, "Item_talk:Q4")
print(wikitext[:200])
```

### `extract_sparql_blocks()` and `extract_first_sparql_block()`

```python
from gkc.mash import extract_first_sparql_block, extract_sparql_blocks

wikitext = """
<sparql>SELECT ?item ?itemLabel WHERE { ?item ?p ?o }</sparql>
<sparql>SELECT ?other WHERE { ?other ?p ?o }</sparql>
"""

all_blocks = extract_sparql_blocks(wikitext)
first_block = extract_first_sparql_block(wikitext)

print(len(all_blocks), first_block[:40])
```

### `DataTemplate` (Protocol)

```python
from dataclasses import dataclass
from gkc.mash import DataTemplate

@dataclass
class MinimalTemplate(DataTemplate):
    value: str

    def summary(self):
        return {"value": self.value}

    def to_dict(self):
        return {"value": self.value}

template = MinimalTemplate("example")
print(template.summary(), template.to_dict())
```

### `MashSourceAdapter` (Protocol)

```python
from gkc.mash import MashSourceAdapter, WikibaseMashSourceAdapter

adapter: MashSourceAdapter = WikibaseMashSourceAdapter()
print(adapter.source_name, adapter.can_load("Q42"))
```

### `WikibaseMashSourceAdapter`

```python
from gkc.mash import WikibaseMashSourceAdapter

adapter = WikibaseMashSourceAdapter()

single = adapter.load("Q42")
batch = adapter.load_many(["Q42", "P31", "E502"])

print(single.summary())
print(sorted(batch.keys()))
```

### `WikipediaMashSourceAdapter`

```python
from gkc.mash import WikipediaMashSourceAdapter

adapter = WikipediaMashSourceAdapter()
template = adapter.load("Template:Infobox settlement")

print(template.summary())
```

### `fetch_property_labels()`

```python
from gkc.mash import fetch_property_labels

labels = fetch_property_labels(["P31", "P279"], language="en")
print(labels)
```

### `strip_entity_identifiers()`

```python
from gkc.mash import strip_entity_identifiers

entity_data = {
    "id": "Q42",
    "lastrevid": 123,
    "claims": {"P31": [{"id": "Q42$abc", "mainsnak": {"hash": "h1"}}]},
}

shell = strip_entity_identifiers(entity_data)
print(shell)
```

### `flatten_entity_claims_for_write()`

```python
from gkc.mash import flatten_entity_claims_for_write

raw_claims = {
    "P31": [{"mainsnak": {"property": "P31"}}],
    "P279": [{"mainsnak": {"property": "P279"}}],
}

claims = flatten_entity_claims_for_write(raw_claims)
print(len(claims), claims[0]["mainsnak"]["property"])
```

Use this when you already have a stripped entity shell and only need to convert
read-side claims mapping into the flat statement list accepted by shipper.

### `transform_entity_for_write()`

```python
from gkc.mash import transform_entity_for_write

raw_entity = api.get_entity("P31")

item_payload = transform_entity_for_write(
    raw_entity,
    target_entity_type="item",
)

property_payload = transform_entity_for_write(
    raw_entity,
    target_entity_type="property",
    property_datatype="wikibase-item",
)

print(item_payload.keys())
print(property_payload.keys())
```

This helper performs the full raw-to-write conversion for one entity:

- strips create-blocking identifiers and hashes
- removes top-level read-side fields like `type`, `datatype`, and `sitelinks`
- converts raw claims dicts into the flat statement list expected by shipper
- preserves labels, descriptions, aliases, statement rank, qualifiers, and references

When targeting a property payload, `property_datatype` is required unless the
source entity is already a property and has a datatype that can be reused.

### `WikibaseApiClient.get_and_transform_entity()`

```python
from gkc.mash import WikibaseApiClient

api = WikibaseApiClient(api_url="https://datadistillery.wikibase.cloud/w/api.php")

payload = api.get_and_transform_entity(
    "P31",
    target_entity_type="item",
)

print(payload["labels"]["en"]["value"])
```

Use this convenience method when you want to fetch and convert in one step.

### `ClaimSummary`

```python
from gkc.mash import ClaimSummary

claim = ClaimSummary(property_id="P31", value="Q5", rank="normal")
print(claim.property_id, claim.value, claim.rank)
```

### `WikibaseItemTemplate`

```python
from gkc.mash import (
    WikibaseLoader,
    apply_item_property_filters,
    apply_template_language_filter,
)

loader = WikibaseLoader()
template = loader.load_item("Q42")

apply_item_property_filters(template, include_properties=["P31", "P21"])
template.filter_qualifiers()
template.filter_references()
apply_template_language_filter(template, ["en"])

print(template.summary())
print(template.to_dict().keys())
print(template.to_simple_dict().keys())
print(template.to_shell().keys())
print(template.to_qsv1(for_new_item=False)[:120])

try:
    template.to_gkc_entity_profile()
except NotImplementedError:
    pass
```

### `WikibasePropertyTemplate`

```python
from gkc.mash import WikibaseLoader, apply_template_language_filter

loader = WikibaseLoader()
prop = loader.load_property("P31")

apply_template_language_filter(prop, ["en"])
print(prop.summary())
print(prop.to_dict().keys())
print(prop.to_shell().keys())

try:
    prop.to_gkc_entity_profile()
except NotImplementedError:
    pass
```

### `WikibaseEntitySchemaTemplate`

```python
from gkc.mash import WikibaseLoader, apply_template_language_filter

loader = WikibaseLoader()
schema = loader.load_entity_schema("E502")

apply_template_language_filter(schema, ["en"])
print(schema.summary())
print(schema.to_dict().keys())
print(schema.to_shell().keys())

try:
    schema.to_gkc_entity_profile()
except NotImplementedError:
    pass
```

### `WikibaseLoader`

```python
from gkc.mash import WikibaseLoader

loader = WikibaseLoader(api_url="https://www.wikidata.org/w/api.php")

item = loader.load_item("Q42")
legacy = loader.load("Q42")  # Deprecated alias
batch = loader.load_items(["Q42", "Q5"])
prop = loader.load_property("P31")
schema = loader.load_entity_schema("E502")
raw_entity = loader.load_entity_data("Q42")

print(item.qid, legacy.qid, sorted(batch.keys()), prop.pid, schema.eid, raw_entity.get("id"))
```

### `WikipediaTemplate` and `WikipediaLoader`

```python
from gkc.mash import WikipediaLoader

loader = WikipediaLoader()
template = loader.load_template("Infobox settlement")

print(template.summary())
print(template.to_dict().keys())
```

## API Reference (mkdocstrings)

### `WikibaseApiClient`

::: gkc.mash.WikibaseApiClient
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_mediawiki_page_wikitext()`

::: gkc.mash.fetch_mediawiki_page_wikitext
        options:
            show_root_heading: false
            heading_level: 4

### `extract_sparql_blocks()`

::: gkc.mash.extract_sparql_blocks
        options:
            show_root_heading: false
            heading_level: 4

### `extract_first_sparql_block()`

::: gkc.mash.extract_first_sparql_block
        options:
            show_root_heading: false
            heading_level: 4

### `DataTemplate`

::: gkc.mash.DataTemplate
    options:
      show_root_heading: false
      heading_level: 4

### `MashSourceAdapter`

::: gkc.mash.MashSourceAdapter
    options:
      show_root_heading: false
      heading_level: 4

### `WikibaseMashSourceAdapter`

::: gkc.mash.WikibaseMashSourceAdapter
    options:
      show_root_heading: false
      heading_level: 4

### `WikipediaMashSourceAdapter`

::: gkc.mash.WikipediaMashSourceAdapter
    options:
      show_root_heading: false
      heading_level: 4

### `fetch_property_labels()`

::: gkc.mash.fetch_property_labels
    options:
      show_root_heading: false
      heading_level: 4

### `strip_entity_identifiers()`

::: gkc.mash.strip_entity_identifiers
    options:
      show_root_heading: false
      heading_level: 4

### `flatten_entity_claims_for_write()`

::: gkc.mash.flatten_entity_claims_for_write
        options:
            show_root_heading: false
            heading_level: 4

### `transform_entity_for_write()`

::: gkc.mash.transform_entity_for_write
        options:
            show_root_heading: false
            heading_level: 4

### `ClaimSummary`

::: gkc.mash.ClaimSummary
    options:
      show_root_heading: false
      heading_level: 4

### `WikibaseItemTemplate`

::: gkc.mash.WikibaseItemTemplate
    options:
      show_root_heading: false
      heading_level: 4

### `WikibasePropertyTemplate`

::: gkc.mash.WikibasePropertyTemplate
    options:
      show_root_heading: false
      heading_level: 4

### `WikibaseEntitySchemaTemplate`

::: gkc.mash.WikibaseEntitySchemaTemplate
    options:
      show_root_heading: false
      heading_level: 4

### `WikibaseLoader`

::: gkc.mash.WikibaseLoader
    options:
      show_root_heading: false
      heading_level: 4

### `WikipediaTemplate`

::: gkc.mash.WikipediaTemplate
    options:
      show_root_heading: false
      heading_level: 4

### `WikipediaLoader`

::: gkc.mash.WikipediaLoader
    options:
      show_root_heading: false
      heading_level: 4

## See Also

- [Shipper API](shipper.md)
- [SpiritSafe API](spirit_safe.md)
- [SPARQL API](sparql.md)