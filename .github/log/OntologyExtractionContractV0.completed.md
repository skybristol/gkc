# Ontology Extraction Contract V0

**Status:** Completed enough for archival handoff. Decision points resolved and Sprint 1 + Sprint 2 scaffolding implemented as of March 13, 2026.

**Update Log:**

- 2026-03-13: Contract status refreshed to reflect implemented profile-aware guidance precedence, legacy API removal, and current verification results.
- 2026-03-13: Sprint 1 profile-to-cache route validated end-to-end and initial SpiritSafe entity cache baseline produced.
- 2026-03-13: Sprint 2 mash-level recentchanges refresh primitives and CLI wrapper implemented and tested.
- 2026-03-13: Document prepared for archival move to `.github/log` and handoff to ProfilesV2 planning.

## Completion Snapshot

This V0 contract has served its purpose as the extraction architecture definition and initial implementation guide.

Completed in scope:

- Ontology index + profile graph extraction architecture implemented.
- Profile-linked per-entity cache export route implemented and validated.
- Metadata-enriched cache artifacts implemented and baseline regenerated.
- Mash-level recentchanges polling and cache refresh route implemented with CLI wrapper and targeted tests.

Remaining for next phase (tracked in ProfilesV2):

- Live revision validation loops in GitHub workflows against evolving gkc main.
- Impacted-profile mapping and incremental next-gen Entity JSON translation pipeline.
- Fermenter-facing translation contract finalization and integration.

**Scope:** Defines what data the gkc ontology module should extract from the Data Distillery Wikibase, how it should fetch that data, and what shape the result should take at runtime.

**Related files:**
- `gkc/wikibase/ontology.py` — current implementation
- `docs/gkc/wikibase_ontology_orientation.md` — shared orientation doc
- `tests/wikibase/test_ontology.py`

---

## What We Need To Extract

At minimum, a usable ontology snapshot must give runtime code and profile consumers the following:

### 1. Profile Items And Their Multilingual Label/Description

For each item that is an instance of Q3 (GKC Entity Profile), we need:

- Item URI (e.g., `wd:Q3`)
- Label in each available language
- Description in each available language

### 2. Guidance Text For Label, Description, and Alias Fields

For each profile item, we need the guidance texts stored in the six guidance/prompt properties:

| Property | Role |
|---|---|
| P188 | Label prompt (instructional text for the label field) |
| P185 | Label guidance (contextual help for the label field) |
| P189 | Description prompt |
| P186 | Description guidance |
| P190 | Alias prompt |
| P187 | Alias guidance |

Each of these is a monolingual text value, so each property may have multiple statements — one per language.

### 3. Property Inventory With Class And Optional Guidance

For each property in the ontology:

- Property URI and PID
- Property label per language
- Ontology class (via P1)
- Class label per language
- Optional: guidance/message texts from P168–P171, P185–P190 as applicable

---

## The SPARQL Problem

The following query collects the full multilingual guidance bundle for profile items:

```sparql
PREFIX wd: <https://datadistillery.wikibase.cloud/entity/>
PREFIX wdt: <https://datadistillery.wikibase.cloud/prop/direct/>
PREFIX p: <https://datadistillery.wikibase.cloud/prop/>
PREFIX ps: <https://datadistillery.wikibase.cloud/prop/statement/>

SELECT ?profile ?label ?label_lang ?description ?description_lang
?label_prompt ?label_prompt_lang
?label_guidance ?label_guidance_lang
?description_prompt ?description_prompt_lang
?description_guidance ?description_guidance_lang
?alias_prompt ?alias_prompt_lang
?alias_guidance ?alias_guidance_lang
WHERE {
  ?profile wdt:P1 wd:Q3 ;
           rdfs:label ?label ;
           schema:description ?description .

  BIND(LANG(?label) AS ?label_lang)
  BIND(LANG(?description) AS ?description_lang)

  ?profile p:P188 ?label_prompt_statement .
  ?label_prompt_statement ps:P188 ?label_prompt_value .
  BIND(STR(?label_prompt_value) AS ?label_prompt)
  BIND(LANG(?label_prompt_value) AS ?label_prompt_lang)

  ?profile p:P185 ?label_guidance_statement .
  ?label_guidance_statement ps:P185 ?label_guidance_value .
  BIND(STR(?label_guidance_value) AS ?label_guidance)
  BIND(LANG(?label_guidance_value) AS ?label_guidance_lang)

  ?profile p:P189 ?desc_prompt_statement .
  ?desc_prompt_statement ps:P189 ?desc_prompt_value .
  BIND(STR(?desc_prompt_value) AS ?description_prompt)
  BIND(LANG(?desc_prompt_value) AS ?description_prompt_lang)

  ?profile p:P186 ?desc_guidance_statement .
  ?desc_guidance_statement ps:P186 ?desc_guidance_value .
  BIND(STR(?desc_guidance_value) AS ?description_guidance)
  BIND(LANG(?desc_guidance_value) AS ?description_guidance_lang)

  ?profile p:P190 ?alias_prompt_statement .
  ?alias_prompt_statement ps:P190 ?alias_prompt_value .
  BIND(STR(?alias_prompt_value) AS ?alias_prompt)
  BIND(LANG(?alias_prompt_value) AS ?alias_prompt_lang)

  ?profile p:P187 ?alias_guidance_statement .
  ?alias_guidance_statement ps:P187 ?alias_guidance_value .
  BIND(STR(?alias_guidance_value) AS ?alias_guidance)
  BIND(LANG(?alias_guidance_value) AS ?alias_guidance_lang)

  SERVICE wikibase:label { bd:serviceParam wikibase:language "es,mul". }
}
```

### Problem 1: Required Patterns Create Silent Exclusions

All six guidance-property patterns are required (not `OPTIONAL`). A profile item that is missing even one of them will not appear in results at all. As the ontology grows, this makes completeness guarantees fragile and makes it hard to distinguish "this item has no alias guidance" from "this item was silently dropped."

### Problem 2: Cartesian Explosion Across Languages

`rdfs:label` and `schema:description` return one binding per language. Each guidance property also returns one binding per language. Because the query joins these with required patterns, the result set grows as the product of the language counts per variable group — not as a joined record per profile item. This makes the result set wide, noisy, and non-trivial to reassemble into a per-item structure in Python.

### Problem 3: SPARQL Cannot Express All Statement Structure

Qualifier and reference data is not surfaced by this query. If guidance texts carry qualifiers (e.g., applies-to-context qualifiers), those would require further joins or a separate query. Item JSON returns the full statement array including qualifiers and references without additional query complexity.

### Problem 4: Maintenance Surface Area

Each time a new guidance property is added to the ontology, the query must be updated with two new triple patterns and two new BINDs. Item JSON extraction requires no query changes — the consumer code reads whatever keys are present.

---

## Where SPARQL Still Has Value

SPARQL is not the wrong tool for all of this. There are specific extraction goals where SPARQL remains the efficient and maintainable choice:

- **Discovery queries:** Find all items of a given class (e.g., all Q3 instances, all Q6 instances). One triple pattern, no joins.
- **Cross-item indexed lookups:** "Which properties are classified as Q49?" — set membership queries.
- **PID maps and class group summaries:** Batch-fetching the property inventory with its class grouping is naturally a SPARQL join.

The problem is using SPARQL to reconstruct a complex per-item structured record. That is where item JSON is the better primary source.

---

## Proposed Hybrid Extraction Model

```
SPARQL layer                    Item JSON layer
─────────────────               ─────────────────────────────────────
Discover item URIs  ──────────► Fetch full item records (wbgetentities)
(e.g., all Q3s)                 Get all labels, descriptions, aliases
                                Get all statement arrays with all
                                  guidance properties
                                Get qualifiers and references

Build PID map       ──────────► Fetch property records (P-items)
  prop label                    Get full monolingual text arrays
  class grouping                Get property constraints
```

The SPARQL layer answers the question "what exists and how is it classified." The item JSON layer answers the question "what are all the details for these specific items."

---

## Open Decision Points

The following decisions are required before this contract can be finalized and implementation can proceed. These are not defaults or suggestions — they require explicit choices from the project owner.

### Decision 1: Guidance Channel Scope

Which guidance properties should be extracted in a standard ontology snapshot?

Options:
- A: Label/description/alias guidance only (P185–P190): the six basic field-level UX properties.
- B: A + runtime message types (P168–P171): error, guidance, suggestion, consequences.
- C: All documented guidance properties.
- D: Configurable per consumer, with a default set specified here.

> The important thing is to get everything associated with a profile. This will include the prompt/guidance for label/description/alias. There is also guidance on statements at the profile level, falling back to guidance at the statement items themselves (default if a profile doesn't override). Statement type properties (e.g., wikibase-item, etc.) also have error statements for cases when basic datatype validation fails.

**Current state:** P170 was in the prior implementation for historical reasons. That is not an intentional choice and should be replaced with an explicit decision here.

### Decision 2: Language Policy

How should the extraction handle multilingual content?

- Should the snapshot fetch all available languages and return a language-keyed map?
- Should it fetch a specific requested language with a defined fallback chain?
- Where should fallback resolution happen: SPARQL query time, item JSON post-processing, or caller responsibility?
- Is `mul` (multilingual) a valid fallback or should it be treated as a distinct language code?

> Fundamentally, we should fetch and process all languages present in the Wikibase being used. It's then up to a profile consumer on what they want to do with the content.

> Since we have it supported, let's use `mul` as a the default language setting for all monolingual texts in this architecture. This helped me solve the pesky problem where I was not able to set `en` and had to use `en-us` for a number of statements. I set `mul` for the language on all statements. Labels are in `mul` and `en` for items we care about. I have one example in Spanish so far, and I'll do some more translation work so that we have Spanish translations to test.

> We set a default language for the package. One thing that this part of the code should do is pop a warning if a user has a default language set that is not present in the Wikibase it is processing.

### Decision 3: Traversal Boundary

For one extraction pass, what counts as "in scope"?

- Only the profile items themselves (Q3 instances)?
- Profile items plus their directly referenced property specs (via P157/P158/P161)?
- The full linked profile graph (following P162/P205)?

> For a profile to be fully represented, we need to get the profile itself, all of its labels/descriptions/aliases prompts/guidance statements along with all statements and their qualifiers. We need to follow the statements because those have "default" guidance texts (suggestion message text and consequences message text) along with linkages to Wikidata (and eventually other systems). From the statements, we also need to follow the `statement type` claims to the linked properties that give us property datatype along with error texts used on validation errors at the "primitives." The `reference specification` and `value specification` qualifiers on the statements in a profile link to their own items that essentially serve as representations of what future gkc code will do. They also provide statements that we can adjust and add languages to as needed. Right now, these use the `GKC Validation/Coercion Action Directive` property with a `mul` statement stating what the action should do logically.

This determines whether one snapshot fetch is sufficient for a consumer to build a complete profile form, or whether additional fetches are expected.

### Decision 4: SPARQL vs. Item JSON Boundary

Given the analysis above, where exactly does each method take responsibility?

Proposed split (requires confirmation):
- SPARQL: discovery (find all Q3/Q6 items), PID map (all properties with class labels), cross-item set lookups.
- Item JSON: per-item full record extraction including all guidance texts, all languages, all qualifiers.

> The split approach could work. I think that the following could be used as an initial SPARQL query to retrieve all items that are classified below entity and all properties together in one query operation, yielding all of the QID/PID identifiers we need to pull data for using `mash` functionality.

```sparql
PREFIX wd: <https://datadistillery.wikibase.cloud/entity/>
PREFIX wdt: <https://datadistillery.wikibase.cloud/prop/direct/>

SELECT ?item ?itemLabel ?class ?classLabel
WHERE {
  {
    ?class wdt:P2* wd:Q1 .
    ?item wdt:P1 ?class .
  }
  UNION
  {
    ?item wikibase:directClaim ?x ;
          wdt:P1 ?class .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

Is this split correct? Are there cases where SPARQL should still be used for detail extraction?

### Decision 5: Output Contract Shape

What should `DDOntologySnapshot` look like when this is fully implemented?

The current dataclass has:
- `property_map`: PID string → property URI
- `entity_map`: class label → URI
- `class_groups`: class label → list of property PIDs
- `guidance_map`: PID → guidance text (currently P170-only, language unresolved)
- `fetched_at`: datetime

What needs to change? For example:
- Should `guidance_map` become a nested structure keyed by PID → property → language → text?
- Should a separate `profile_map` hold per-profile-item guidance distinct from per-property guidance?
- Should `DDOntologySnapshot` be split into a property snapshot and a profile snapshot?

> Fundamentally, I think that the YAML+JSON structure we had built in the previous iteration was basically functional though not complete. It was able to a) enable Pydantic models for validation/coercion and b) enable the wizard builder to generate a basic working form system. That's what we need here as well. But we do need to pay attention to the primitives so we have functionality, based at the fermenter, that can evaluate the shape of data statement by statement within the context of a profile.

---

## Resolved Decisions

The following decisions are normative. They distill the inline answers in the Open Decision Points section into implementation rules.

**1. Guidance Channel Scope:** Get everything associated with a profile. The full extraction includes label/description/alias prompt and guidance texts (P185-P190), statement-level guidance (P169, P171), and primitive property validation texts (P168) in that precedence order. No hard-coded channel list in code — fetch from Wikibase.

**2. Language Policy:** Fetch and preserve all languages exactly as stored. `mul` is the architectural default for monolingual text statements. All language keys are returned as-is from Wikibase (no normalization). When a configured default language is absent from an item's labels, emit a warning and fall back to `mul`. It is the consumer's responsibility to select which language to display.

**3. Traversal Boundary:** Start from Q3 profile items (P1 → Q3). From each profile, traverse all internal wikibase-entityid links in claims and qualifiers breadth-first until closure. This includes statement items, primitive property items, reference spec items, and value spec items. The traversal is bounded by detected closure (no new internal IDs) and a safety hop limit.

**4. SPARQL vs. Item JSON Boundary:**
- SPARQL: discovery only — find QIDs/PIDs using the combined items+properties union query (all subclasses of Q1 and all properties). Returns the ontology index.
- Item JSON (wbgetentities): authoritative detail for all traversed nodes — full claim arrays, all languages, qualifiers, references, ranks.
- SPARQL is never used to reconstruct per-item structured records.

**5. Output Contract Shape:** Two distinct payloads:
- `DDOntologyIndex`: SPARQL-derived, lightweight, QID/PID + class assignments.
- `DDProfileGraph`: item JSON-derived, full graph payload, all languages, all statement structure as-is.
- These are designed to compose: use SPARQL index to get a starting set of IDs, then use `fetch_profile_graph()` for full detail.

**6. Statement Rank and Reference Handling:** All ranks and all references/qualifiers are preserved as-is in `raw_items`. No pre-filtering. Ranking and ordering are managed from Wikibase configuration, not in Python code.

**7. Profile Completeness on Missing Links:** Take what is documented and encode it. Missing reference/value specifications are not failures — they are structural gaps that the code logs diagnostically. Extraction does not fail hard on missing items.

**8. Guidance Precedence:** Profile-level qualifier guidance wins when present (for profile-scoped statement configuration). Falls back to statement item guidance, then primitive property item guidance when absent. This precedence is implemented in the profile-aware resolver and preserves per-language monolingual text selection behavior.

**9. Primitive Validation Message Scope:** All guidance channels present on primitive property items are captured (not limited to datatype errors). Messaging is fully configurable from Wikibase.

**10. Language Warning Trigger:** Warning + automatic fallback to `mul`. Not a hard failure. Logged in `DDProfileGraph.traversal_log`.

**11. Cache Granularity:** SpiritSafe cache artifacts are stored at individual entity level (item/property), keyed by entity ID. The cache must avoid duplicate storage across profile workflows.

**12. Cache Scope and Layout:** Cache is scoped to the entire Wikibase, not to profile or run containers.

**13. Refresh Modality:** Two operating modes are in scope:
- Workflow mode: profile-entry refresh that pulls a core profile and linked profile-statement-qualifier-type chain.
- Background mode: Wikibase-wide change detection refresh that updates cache and then triggers profile JSON transformation.
For this phase, manual execution is the primary trigger path.

**14. Provenance Requirements:** Cache artifacts include provenance metadata (source endpoint, extraction timestamp, extractor version, source commit/branch context). Metadata must support both profile-entry and background-refresh workflows.

**15. Retention Policy:** Keep only current cache artifacts in-tree; use Git history for historical recovery rather than in-cache snapshot retention.

**16. Partial Failure Policy:** Publish successful entity updates and retain diagnostics for failed entities; reruns should continue from partial completion toward full completion.

**17. Mirror Scope Boundary:** Use a Wikibase-wide cache strategy with a fixed internal denylist and MediaWiki Action API-driven change detection.

**18. Essential Payload Shape:** Start with raw JSON mirror fidelity for required entity content. Payload compaction/normalization is recognized as a future optimization and should not block initial cache implementation.

**19. Deletion/Retirement Handling:** Hard-delete cache entries for entities that are deleted/retired/out-of-scope.

**20. Change Detection Source:** Use MediaWiki Action API `list=recentchanges` as the authoritative background refresh trigger, coupled with an ignore-ID list.

**21. Transformation Triggering:** After cache refresh, run JSON Entity Profile transformation incrementally for impacted profiles, based on maintained profile-impact metadata.

**22. Cache File Naming:** Use deterministic filenames keyed on entity ID (`Q...`/`P...`) in a unified namespace (no separate item/property directory split required).

---

Implementation has moved beyond the initial snapshot-only scope and now tracks the hybrid ontology-index plus profile-graph model in code.

---

## Implementation Status

`gkc/wikibase/ontology.py` has been updated to implement this contract.

New public API:
- `DDOntologyIndex` — SPARQL-derived index dataclass.
- `DDProfileGraph` — item JSON graph payload dataclass.
- `fetch_ontology_index()` — runs the discovery SPARQL query.
- `fetch_profile_ids()` — targeted SPARQL to get Q3 profile QIDs only.
- `fetch_profile_graph()` — breadth-first item JSON traversal.
- `build_discovery_sparql_query()` — the combined items+properties union query.
- `build_profile_ids_sparql_query()` — simple P1→Q3 query.
- `get_label_for_language()` — multilingual label lookup with fallback.
- `get_monolingualtext_for_language()` — guidance text lookup with fallback.
- `resolve_statement_guidance()` — guidance with precedence: statement item → primitive.
- `resolve_profile_statement_guidance()` — profile-aware guidance with precedence: profile qualifier override → statement item → primitive.
- `export_profile_graph_to_entity_cache()` — profile-entry export to per-entity cache files keyed by entity ID.
- `fetch_recent_entity_changes()` — reusable MediaWiki `recentchanges` polling utility in mash.
- `refresh_entity_cache_from_recentchanges()` — reusable per-entity cache refresh utility in mash with overwrite/delete behavior.

Legacy compatibility API has been removed from the ontology public surface and tests.

Current verification status:
- `poetry run pytest tests/wikibase/test_ontology.py -q`: 34 passed.
- `poetry run mkdocs build --strict`: succeeded.
- Current coverage report for `gkc/wikibase/ontology.py`: 88% in the latest targeted ontology test run.
- `poetry run pytest tests/wikibase/test_ontology.py tests/test_cli.py -q`: 71 passed (includes new profile-to-cache API/CLI tests).

New CLI surface:
- `gkc wikibase profile-to-cache` — profile-entry cache export command for seeding SpiritSafe cache from one or more root profiles.
- `gkc wikibase check-for-revisions` — recentchanges-driven cache refresh command built as a thin wrapper over mash refresh primitives.

---

## Pending Work

### Sprint 1 (Profile-to-Cache Seed)

- Run profile-entry cache export for the two-profile chain (start at Tribal Government profile and include linked profile graph) using `gkc wikibase profile-to-cache`.
- Seed SpiritSafe cache with exported entity-ID keyed JSON artifacts.
- Open and merge SpiritSafe cache-seed PR.

### Sprint 2 (Revision Detection + CI)

- Build this as a reusable, higher-level capability in the mash module (not SpiritSafe-specific glue code) so it can be reused for other Wikibase cache/mirror workflows.
- Implement fixed denylist + ignore-ID handling in background refresh pipeline.
- Implement MediaWiki Action API (`list=recentchanges`) change-detection process.
- Use a persisted refresh watermark from the current cache state/run state to set `rcstart` for polling.
- Implement pagination/continuation handling and an overlap window with deduplication to avoid boundary misses across runs.
- Extract changed entity IDs from recentchanges, filter through ignore-ID rules, and refresh only changed entities via `wbgetentities`.
- Implement partial-success refresh behavior with diagnostics and resumable reruns.
- Implement hard-delete handling for deleted/retired/out-of-scope entities.
- Implement impacted-profile detection metadata and incremental JSON Entity Profile transformation.
- Wire revision check + refresh process into CI and validate with a controlled Wikibase revision.

Sprint 2 current status:

- Mash-layer recentchanges polling and cache refresh primitives are implemented.
- CLI wrapper for revision checks is implemented.
- Targeted tests cover watermark derivation, ignore filtering, changed-entity refresh, and hard-delete handling.
- Remaining work is live-run validation against a controlled Wikibase revision, impacted-profile transformation wiring, and CI automation.

Sprint 2 implementation notes:

- Keep refresh logic API-first in mash and expose CLI entry points from gkc as thin wrappers.
- Maintain deterministic cache writes (one file per entity ID) and stable summary artifacts for CI observability.
- Treat update detection and profile transformation as distinct phases with explicit handoff metadata between phases.

### Follow-on Integration

- Integrate ontology index/profile graph replacement into `foundation.py`.
- Delete `gkc/wikibase/foundation_profiles/` after `foundation.py` migration is complete.

## Deferred / Theoretical Design Notes

- Additional profile-driven validation and reporting profile work remains intentionally deferred per current direction. Treat this as future design and implementation work for follow-on updates with the Validation Agent and Wizard Engineer.

---

## Open Questions For Inline Answers

Please answer these directly in this section so we can finalize Contract V0 without assumptions.

1. Root class boundary for SPARQL discovery:
Do you want only descendants of Q1, or a fixed allowlist of roots (for example Q1, Q3, Q6, statement-spec classes), so we avoid pulling unrelated ontologies that might later be subclassed under Q1?

> Q1 for right now. We have total control and will pay attention to anything that might deviate from this.

2. Property discovery in the union query:
For the property side, should we include all properties that have a directClaim plus P1 class, or only properties reachable from discovered profiles/statements in the same extraction run?

> There are only a couple properties there that may not directly influence the instantiation of JSON profiles - instance of, subclass of. I'd say, pull them all.

3. Graph traversal policy:
Should traversal be recursive until closure (follow links repeatedly until no new nodes), or bounded by relationship types and hop limits?
If recursive, do you want cycle detection with deterministic ordering?

> The SPARQL query I laid out should give us a comprehensive list of the QID/PID values we need to pull. The alternative is to simply get all items classed as GKC Entity Profile (P1 -> Q3) and then follow the graph from there. That's bulletproof, so perhaps we should do that instead?

4. Required vs optional links in profile completeness:
If a profile references a statement item that is missing its reference specification or value specification, should extraction fail hard, warn and continue, or mark profile as partial with structured diagnostics?

> Not every statement will have a value specification. In fact, most do not. Their only value spec may come from the linked property primitive spec. This will change a bit in practice after we get the kinks worked out. Fundamentally, any statement that is linking to other things (wikidata-item) really does need to have some type of select list behind it to be fully functional. But some of those are functionally hard to achieve. Bottom line: take what's in the documentation and encode it.

5. Guidance precedence model:
When both profile-level statement guidance and statement-item default guidance exist, do you want strict override (profile always wins), merge (profile plus fallback fields), or per-guidance-channel override rules?

> The profile guidance always rules. Fall back to generalized statement guidance when it's not present.

6. Primitive validation message scope:
For statement type linked properties, should we include only datatype validation errors, or all guidance channels present on those properties (P168-P171, P185-P190 when available)?

> I want to make all validation/coercion messaging configurable from the Wikibase vs. having any of that in code. If we're missing something that should be built into the Wikibase model, we'll add it. Again, the statement level guidance rules as that provides the most specific context. Any one statement item will be reused many times over many profiles. Any one property item will be reused even more times.

7. Language warning behavior:
If package default language is absent in a target Wikibase, should this be:
warning only,
warning plus automatic fallback to mul,
or configuration error that blocks extraction?

> Warning plus automative fallback to mul.

8. Language normalization:
Should language keys be preserved exactly as stored (for example en-us vs en), or normalized to canonical forms with an alias map?
A safe default is preserve raw plus optional normalized index.

> Let's present them as stored for now. Wikibase rules the process.

9. Statement rank/reference handling:
In item JSON claims, should we keep all ranks and all references/qualifiers as-is, or pre-filter to preferred/normal ranks for runtime consumers?

> Keep them as is. We'll also treat ranking/order as a config managed from the Wikibase.

10. Output contract shape split:
Do you want one combined snapshot object, or two explicit payloads:
ontology index payload (SPARQL-derived),
profile graph payload (item JSON-derived)?

> If the SPARQL query ends up working as a starting point, that's really just giving us the identifiers to go after. Otherwise, we need to design a SPARQL query that will pull all kinds of other stuff, which I think will put us in a whole other realm of complexity. In my view, the raw JSON pull is the payload to operate from. I don't know how that will scale ('n' number of profiles with 's' number of statements), but I can see dropping that payload into a folder within the SpiritSafe repo to be processed from there. We can later decide on a GH action of some kind to check for updates and refresh with a manual trigger.

11. Cache file granularity:
Do you want one cache artifact per profile QID, or one bundle artifact per extraction run?

> I would think we want the cache to contain files at an individual item/property level. Any given profile will reference some of the same statements. When processing multiple profiles, we don't want to repeat items/properties in the cache. 

12. SpiritSafe cache path layout:
Should cache artifacts be stored as profile-scoped paths (for example, cache/profiles/<ProfileId>/...), or run-scoped paths (for example, cache/runs/<timestamp>/...)?

> The cache should be scoped to the entire Wikibase; not profiles or runs.

13. Refresh strategy:
For this phase, should cache export be manual-only, or manual with optional scheduled workflow added now?

> Manual only at this point. Given my notes above about this being a cache scoped to the entire Wikibase, we will likely build a refresh strategy based on checking the Wikibase for updates. It's reasonable to have a manual run process based on a given profile and its linked profiles because that's how we will conduct workflows. However, we need the caching functionality at an atomic enough level that we can operate background refresh from a global context.

14. Provenance metadata contract:
Should each cache artifact include source endpoint, extraction timestamp, extractor version, and source commit/branch metadata?

> Yes, with the understanding that sometimes that metadata will be associated with a Profile-based entry point to the workflow and other times based on a change detection auto refresh process.

15. Retention policy:
Should we keep only the latest cache artifacts, or keep historical snapshots for diffing and rollback?

> Couldn't we use git history to get back to previous artifacts? I don't envision the need for diff and rollback in general.

16. Partial failure behavior:
If extraction fails for a subset of profiles, should export publish partial artifacts with diagnostics, or fail the full export run?

> Since the basis of the cache is essentially a JSON doc mirror of the essential parts of the live Wikibase, I would think we would hold on to anything that made it through and then restart to completion.

17. Mirror scope boundary:
For the Wikibase-wide mirror, what is the explicit inclusion/exclusion rule?
For example: include all items/properties except a fixed internal denylist (`Q1`, `P1`, `P2`, etc.), or include only entities reachable from curated root classes and properties.

> Ideally, we could combine an ontology-based query with revision history, but I do not believe that is possible with the Blazegraph store. So, it probably makes sense to store a fixed denylist and use the action API to drive the routine change detection/re-cache workflow.

18. "Essential parts" definition:
When you say mirror of essential parts of live Wikibase, do we store full `wbgetentities` payloads as-is, or a normalized subset (for example labels/descriptions/aliases/claims/references/qualifiers/ranks only)?

> There is kruft in the raw Wikibase JSON content that we don't necessarily need in the cache. The question though - is it worth running them through a transformation to strip the docs down to what we will actually use? It would buy us some efficiency in storage and increase scalability somewhat. 

19. Deletion and retirement handling:
How should the cache represent entities that are deleted, merged/redirected, or moved out of scope?
Options could include tombstone marker files, hard delete from cache, or retaining last-known content with stale status.

> Let's hard delete from cache at this point.

20. Change detection source for background refresh:
What should be the authoritative trigger source for Wikibase-wide updates (for example recent changes feed/API polling, periodic full scan, or checksum comparison against current cache)?

> We'll use `list=recentchanges` through the Mediawiki action API coupled with a list of entity IDs to ignore.

21. Transformation trigger semantics:
When background refresh updates only a subset of mirrored entities, should JSON Entity Profile transformation run incrementally for impacted profiles only, or always run full rebuild?

> It seems like we should have enough metadata content somewhere (perhaps a revised manifest idea) to run a cache refresh, detect which profiles are impacts, and target those profiles for refresh.

22. Cache key and file naming contract:
Should cache artifacts be keyed strictly by entity ID (`Q...`/`P...`) with deterministic filenames, and should we keep item/property namespaces separated in directory layout?

> I would keep filenames keyed on entity ID, and I see no reason to separate item/property namespaces.