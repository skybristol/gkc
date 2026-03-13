# Ontology API

## Overview

The ontology module in `gkc.wikibase.ontology` provides a two-layer extraction model for Data Distillery Wikibase.

- `DDOntologyIndex`: SPARQL-derived discovery for item/property classification and profile discovery.

- `DDProfileGraph`: authoritative item JSON traversal from profile roots, preserving labels, descriptions, aliases, claims, qualifiers, references, and rank metadata exactly as stored.

Use the index layer to discover relevant IDs and the graph layer to retrieve complete semantic content.

## Public API

### `build_discovery_sparql_query(...)`

Builds the union SPARQL query used by `fetch_ontology_index()`.

### `build_profile_ids_sparql_query(...)`

Builds the SPARQL query used by `fetch_profile_ids()` to find items with `P1 -> Q3`.

### `fetch_ontology_index(...)`

Runs SPARQL discovery and returns an immutable `DDOntologyIndex`.

```python
from gkc.wikibase.ontology import fetch_ontology_index

index = fetch_ontology_index(
    sparql_endpoint="https://datadistillery.wikibase.cloud/query/sparql",
    wikibase_base_uri="https://datadistillery.wikibase.cloud",
)

print(index.fetched_at)
print(len(index.items), len(index.properties), len(index.class_index))
```

### `fetch_profile_ids(...)`

Returns profile item IDs (`Q...`) discovered from live Wikibase.

```python
from gkc.wikibase.ontology import fetch_profile_ids

profile_ids = fetch_profile_ids(
    sparql_endpoint="https://datadistillery.wikibase.cloud/query/sparql",
    wikibase_base_uri="https://datadistillery.wikibase.cloud",
    profile_class_id="Q3",
)

print(profile_ids)
```

### `fetch_profile_graph(...)`

Traverses internal `wikibase-entityid` links breadth-first and fetches full JSON records through `WikibaseApiClient.get_entities(...)`.

```python
from gkc.mash import WikibaseApiClient
from gkc.wikibase.ontology import fetch_profile_graph

api_client = WikibaseApiClient(
    api_url="https://datadistillery.wikibase.cloud/w/api.php"
)

graph = fetch_profile_graph(
    profile_ids=["Q10"],
    api_client=api_client,
    max_hops=8,
)

print(graph.fetched_at)
print(len(graph.profile_ids))
print(len(graph.raw_items))
print(graph.traversal_log)
```

### `get_label_for_language(item, language="en")`

Reads an item label for a requested language key, with fallback to first available label.

```python
from gkc.wikibase.ontology import get_label_for_language

item = graph.raw_items["Q10"]
print(get_label_for_language(item, language="en"))
```

### `get_monolingualtext_for_language(claims, language="en")`

Extracts monolingual text values for one property in the requested language.

```python
from gkc.wikibase.ontology import get_monolingualtext_for_language

statement_item = graph.raw_items["Q123"]
claims = statement_item.get("claims", {}).get("P171", [])
texts = get_monolingualtext_for_language(
    claims,
    language="en",
)
print(texts)
```

### `resolve_statement_guidance(...)`

Resolves guidance text with fallback precedence:

1. Statement item guidance.
2. Primitive property guidance fallback.

```python
from gkc.wikibase.ontology import resolve_statement_guidance

guidance = resolve_statement_guidance(
    graph=graph,
    statement_item_id="Q123",
    primitive_item_id="Q456",
    language="en",
    guidance_prop_id="P171",
)
print(guidance)
```

### `resolve_profile_statement_guidance(...)`

Resolves statement guidance with profile-aware precedence:

1. Profile-level qualifier text on matching `P157` claim.
2. Statement item claim fallback.
3. Primitive/template item claim fallback.

This is the preferred resolver for statement channels such as:

- `P171` statement prompt
- `P170` consequences message text
- `P169` statement guidance
- `P168` error message text

```python
from gkc.wikibase.ontology import resolve_profile_statement_guidance

text = resolve_profile_statement_guidance(
    graph=graph,
    profile_item_id="Q10",
    statement_item_id="Q123",
    guidance_prop_id="P171",
    language="en",
    primitive_item_id="Q456",  # optional
)
print(text)
```

## Quick Start: End-To-End Discovery To Guidance

```python
from gkc.mash import WikibaseApiClient
from gkc.wikibase.ontology import (
    fetch_ontology_index,
    fetch_profile_ids,
    fetch_profile_graph,
    get_label_for_language,
    resolve_profile_statement_guidance,
)

SPARQL_ENDPOINT = "https://datadistillery.wikibase.cloud/query/sparql"
API_ENDPOINT = "https://datadistillery.wikibase.cloud/w/api.php"
WIKIBASE_BASE = "https://datadistillery.wikibase.cloud"

index = fetch_ontology_index(
    sparql_endpoint=SPARQL_ENDPOINT,
    wikibase_base_uri=WIKIBASE_BASE,
)

profile_ids = fetch_profile_ids(
    sparql_endpoint=SPARQL_ENDPOINT,
    wikibase_base_uri=WIKIBASE_BASE,
    profile_class_id="Q3",
)

api_client = WikibaseApiClient(api_url=API_ENDPOINT)
profile_graph = fetch_profile_graph(profile_ids=profile_ids, api_client=api_client)

print(f"profiles: {len(profile_ids)}")
print(f"graph items: {len(profile_graph.raw_items)}")

sample_qid = profile_ids[0]
sample_item = profile_graph.raw_items[sample_qid]
print(get_label_for_language(sample_item, language="en"))
```

## Quick Start: Inspect P157 Qualifier Dynamic

Use this flow to inspect qualifier-level overrides and resolve prompt text through the full precedence model.

```python
profile_qid = profile_ids[0]
profile_item = profile_graph.raw_items[profile_qid]

p157_claims = profile_item.get("claims", {}).get("P157", [])
print(f"P157 claims on {profile_qid}: {len(p157_claims)}")

for i, claim in enumerate(p157_claims, start=1):
    mainsnak = claim.get("mainsnak", {})
    dv = mainsnak.get("datavalue", {})
    value = dv.get("value", {}) if isinstance(dv, dict) else {}
    statement_qid = value.get("id")

    qualifiers = claim.get("qualifiers", {})
    qualifier_pids = sorted(qualifiers.keys())

    print(f"{i}. statement={statement_qid} qualifiers={qualifier_pids}")

    if statement_qid and statement_qid in profile_graph.raw_items:
        resolved = resolve_profile_statement_guidance(
            graph=profile_graph,
            profile_item_id=profile_qid,
            statement_item_id=statement_qid,
            primitive_item_id=None,
            language="en",
            guidance_prop_id="P171",
        )
        print(f"   resolved statement prompt P171: {resolved}")
```

Interpretation checklist:

- If `qualifiers` includes `P171`/`P170`/`P169`/`P168`, those values override statement-item claims for that statement.

- If qualifier-level values are absent, resolver falls back to statement-item claims and then primitive/template claims.

## Guidance Semantics (Current)

Profile-level label and description channels are resolved directly from profile item claims:

- `P188` label prompt
- `P185` label guidance
- `P189` description prompt
- `P186` description guidance
- `P190` alias prompt
- `P187` alias guidance

Statement-level channels should use `resolve_profile_statement_guidance(...)` with profile-level qualifiers preferred:

- `P171` statement prompt (primary statement prompt channel)
- `P170` consequences message text
- `P169` statement guidance
- `P168` error message text

`P168` currently appears primarily on `Wikibase Property Template` items, so primitive/template fallback is common when profile-level or statement-item values are absent.

## Notes

- SPARQL is used for discovery; item JSON is authoritative for details.

- All language variants are preserved exactly as stored in `DDProfileGraph.raw_items`.

- Traversal only follows internal `wikibase-entityid` links and records unresolved IDs in `traversal_log`.

## Theoretical Design Notes

Potential future extension: add explicit validation that every `GKC Entity Statement` used by `P157` provides required prompt channels (for example, enforcing `P171` presence at qualifier or statement-item level).
