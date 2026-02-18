# Write Operations Architecture Proposal

Plain meaning: This document proposes where and how to add safe, testable write operations for Wikidata, Wikimedia Commons, and OpenStreetMap, while keeping the current distillery workflow intact.

## Prompt that led to this document

We previously removed a capability in the package to run the wbeditentity action in the Wikidata API to write the results of the bottler process of building Wikidata items from source data passed through a Barrel Schema. We need to reintroduce that specific functionality at an appropriate place in the package architecture. Please write up a technical document at temp/WRITE_TO_COMMONS.md on how you would propose architecting this part of the package that will have write operations to Wikidata, Wikimedia Commons, and OpenStreetMap (the latter two to be developed later). I will review, suggest changes, and then you can use that document to guide development of the actual code.

## Context and current flow

The current flow creates Wikidata-ready structures in the Bottler stage. The core pieces to build on are:

- Bottler output (claims, qualifiers, references) is built by `Distillate` in `gkc/bottler.py`.
- Authentication for Wikimedia and OSM already exists in `gkc/auth.py`.
- Validation against Barrel Schemas happens in `gkc/spirit_safe.py`.
- Recipe generation and constraint handling lives in `gkc/recipe.py`.

We previously removed the ability to submit `wbeditentity` writes to Wikidata. The goal is to reintroduce this capability in a place that is consistent with the distillery metaphor and supports future write targets.

## Architectural proposal

### New stage: Cooperage-ready -> Spirit Safe -> Bottler -> Exporter

Introduce a new stage after Bottler that is responsible for *delivery* to external systems. This stage should not exist inside Bottler, so the Bottler remains a pure transformer.

Proposed module and class names (aligned with distillery metaphor):

- `gkc/exporter.py`
  - `Exporter` (base class)
  - `WikidataExporter`
  - `CommonsExporter` (scaffold only)
  - `OpenStreetMapExporter` (scaffold only)

Plain meaning: Exporters take Bottler output and submit it to external APIs.

### Responsibilities

**Bottler** (unchanged):
- Build the structured Wikidata JSON payload (claims, labels, descriptions, aliases).

**Spirit Safe** (unchanged, but used as a gate):
- Provide an optional preflight check for items about to be written.

**Exporter** (new):
- Accept Bottler output and perform write operations using target-specific APIs.
- Own write mode (dry-run, validate-only, submit).
- Own rate limiting, retry strategy, and response parsing.

### Proposed public API

Add a write-focused API that mirrors the existing flow:

```python
from gkc.auth import WikiverseAuth
from gkc.bottler import Distillate
from gkc.exporter import WikidataExporter

# Build bottler output
builder = RecipeBuilder(eid="E502")
distillate = Distillate.from_recipe(builder, entity_type="Q123")
item_payload = distillate.transform(source_record)

# Authenticate
auth = WikiverseAuth()
auth.login()

# Write
exporter = WikidataExporter(auth=auth)
result = exporter.write_item(item_payload, summary="Created via GKC bottler")
```

This separates the pure transformation step (Bottler) from write operations (Exporter).

## Wikidata write architecture details

### Core responsibilities of `WikidataExporter`

- Accept Bottler output and normalize it into the `wbeditentity` input format.
- Create new entities or update existing ones based on input payload.
- Provide clear result objects containing QID, revision ID, and API warnings.

### Proposed data model for write results

```python
@dataclass
class WriteResult:
    entity_id: str
    revision_id: int
    status: str
    warnings: list[str]
    api_response: dict
```

Plain meaning: always capture the full API response, but keep a stable summary for users and tests.

### Write behavior modes

- `dry_run=True`: Build the request payload and return it without sending.
- `validate_only=True`: Run Spirit Safe validation and return validation status.
- `submit=True`: Perform `wbeditentity` write.

Defaults should favor safety: `dry_run=True` unless explicitly set to submit.

### Required inputs for `wbeditentity`

Minimal form:

- `action=wbeditentity`
- `format=json`
- `token` (CSRF)
- `data` (json payload)
- `summary`
- `new=item` or `id=Q...`

The `data` field should be the exact Bottler payload, but needs normalization to ensure MediaWiki accepts the structure.

### Authentication flow

`WikiverseAuth` already supports login and CSRF tokens in `gkc/auth.py`. `WikidataExporter` should depend on:

- `auth.login()`
- `auth.get_csrf_token()`

No auth logic should live in the exporter beyond these calls.

### Safety and quality gates

Before submission, `WikidataExporter` should optionally:

- Validate payload against Barrel Schemas via `SpiritSafeValidator` in `gkc/spirit_safe.py`.
- Validate required labels and descriptions are present.
- Ensure any property constraints collected in recipes are respected.

If validation fails, the exporter returns a `WriteResult` with `status="blocked"` and includes error details in `warnings`.

### Logging and audit trail

Write requests should include a descriptive edit summary. The exporter should also optionally accept:

- `batch_id` or `run_id` to associate a set of edits
- `source_url` for provenance
- `tags` for Wikimedia edit tags when supported

These should be stored in the `WriteResult` to support later reporting.

## Commons and OpenStreetMap roadmap

We should design `Exporter` as a base class with target-specific subclasses. For now:

- `CommonsExporter`: scaffold for MediaWiki `upload` + `wbeditentity` on Structured Data on Commons (SDC). It can reuse `WikiverseAuth` but must point to the Commons API URL.
- `OpenStreetMapExporter`: scaffold for OAuth and changeset creation. It should use `OpenStreetMapAuth` in `gkc/auth.py`, but no write logic yet.

The base class should define a stable interface (`write`, `dry_run`, `validate_only`) so future exporters align with the Wikidata implementation.

## Package layout proposal

- New module: `gkc/exporter.py`
- New tests: `tests/test_exporter.py` and `tests/test_wikidata_exporter.py`
- Optional docs draft: `temp/WRITE_TO_COMMONS.md` (this file)

## Implementation sketch (non-final)

```python
class Exporter:
    def write(self, payload: dict, **kwargs) -> WriteResult:
        raise NotImplementedError


class WikidataExporter(Exporter):
    def __init__(self, auth: WikiverseAuth, api_url: str | None = None):
        self.auth = auth
        self.api_url = api_url or auth.api_url

    def write_item(
        self,
        payload: dict,
        summary: str,
        entity_id: str | None = None,
        dry_run: bool = True,
        validate_only: bool = False,
    ) -> WriteResult:
        ...
```

The implementation should keep a strict boundary between transformation logic (Bottler) and network logic (Exporter).

## Tests and verification

Initial tests should cover:

- Payload normalization (does not mutate the Bottler output).
- Dry-run behavior (returns payload and no network call).
- CSRF token usage and error handling.
- Validation-only mode uses Spirit Safe and blocks writes if validation fails.
- Minimal `wbeditentity` request construction.

## Design decisions

- Should the exporter automatically assign labels/descriptions from Barrel Schema metadata if missing, or block writes?
    - Labels and descriptions for item writes in WikidataExporter should always be populated in source from the Bottler and never assumed.
- Should the default be `dry_run=True` for all exporters, or only for Wikidata?
    - Let's use the dry_run concept for every time we are going to build data and write to a target system so that we have an opportunity to examine the exact package that will be sent before it is sent.
- How should we store and serialize write results for downstream reporting (JSONL, CSV, or other)?
    - Hold write operation results as serialized JSON

- The summary for Wikidata write operations is important provenance metadata. Make it a required property for the write operation. For now, this can be a fixed value supplied for multiple writes if multiple records are presented.

### Followup questions

- For “validation-only,” do you want to validate the Bottler JSON directly, or should we convert it to RDF first and run Spirit Safe on the RDF? (Spirit Safe currently expects RDF.)
    - For now, we can validate the Bottler JSON directly. We'll come back to RDF later.
- Where should JSON write results live by default (in-memory only, user-provided path, or a standard run log folder under temp/ or output/)?
    - Keep write results in memory for now. We'll look to other options in future.
- For Wikidata writes, do you want the exporter to support both create and update in one call (e.g., entity_id optional), or split into create_item() and update_item() methods?
    - Since wbeditentity is a single API operation that accepts Wikidata JSON containing both new item and update "instructions", I would stick with the same approach in our Python API. We just need to make sure that our code and process understands the difference.