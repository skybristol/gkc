# Mash: Wikidata Item Sourcing Design

Plain meaning: Load an existing Wikidata item as a template, modify it, and output it in a form ready for creation as a new item or batch processing.

## Context and use case

**The problem:** A user has a Wikidata item (e.g., Q127419548) that serves as a pattern or template for a set of new items they want to create. The template contains:

- Labels in multiple languages
- Descriptions
- A core set of claims (statements) with qualifiers and references
- Instance-of claims, classification data, etc.

**The goal:** Extract the template, allow the user to:
1. View it in a readable format
2. Modify specific values
3. Output it in a form suitable for batch creation (QuickStatements V1) or schema building (ShEx)

**The workflow:** `gkc mash qid Q127419548 --output=qsv1` produces a QS file the user can edit and re-submit for creation of new items.

## Architecture overview

### High-level flow

```
Wikidata API (qid via Cooperage)
    ↓
Mash Loader (fetch + normalize item)
    ↓
Mash Editor (filter/modify fields)
    ↓
Output Formatter (QSV1, ShEx, JSON, etc.)
    ↓
User
```

Plain meaning: Fetch a template, optionally transform it, then emit it in the format the user requests.

### Components

**Cooperage (existing):**
- Already fetches RDF/JSON from Wikidata via `fetch_entity_rdf()`.
- Will be used to load the template item.

**MashLoader:**
- Accepts a QID and optional API URL.
- Fetches the item via Cooperage.
- Normalizes the item to an intermediate format (plain Python dict with labels, descriptions, claims).
- Returns a `MashTemplate` object.

**MashTemplate:**
- Represents a loaded Wikidata item in intermediate form.
- Provides methods to filter/modify claims, labels, descriptions.
- Can be serialized to multiple output formats.

**Output formatters:**
- `QSV1Formatter`: Convert to QuickStatements V1 syntax.
- `ShExFormatter`: Convert to ShEx schema (future).
- `JSONFormatter`: Pretty JSON (for debugging/UI).

**CLIcommand:**
- `gkc mash qid Q... --output=qsv1`
- Orchestrates loader and formatter.

## MashTemplate data model

```python
@dataclass
class MashTemplate:
    """An extracted Wikidata item ready for modification and export."""
    qid: str
    labels: dict[str, str]
    descriptions: dict[str, str]
    aliases: dict[str, list[str]]
    claims: list[ClaimSummary]
```

Where `ClaimSummary` is a simple summary of a claim (not full RDF):

```python
@dataclass
class ClaimSummary:
    """Simplified claim for display and editing."""
    property_id: str
    property_label: str
    value: str  # Human-readable value
    qualifiers: list[dict] = field(default_factory=list)
    references: list[dict] = field(default_factory=list)
    rank: str = "normal"
```

Plain meaning: Hold just enough information to display and modify, without requiring full RDF knowledge from the user.

## Output formats

### QuickStatements V1

The user typically wants bulk-edit-friendly output:

```
Q127419548	P31	Q5
Q127419548	P21	Q6581097
Q127419548	P166	Q123456|S248	Q456789|S854	"http://example.com"
```

For a new item template:

```
CREATE
LAST	P31	Q5
LAST	En	"Label in English"
LAST	Fn	"Français label"
LAST	P21	Q6581097
```

The user edits and re-submits to a QuickStatements UI or a future GKC processor.

### ShEx (future)

Output the item's structure as an EntitySchema template that could be refined and stored as an E-ID. Not in v1.

### JSON (debugging)

Pretty-print the `MashTemplate` for inspection and scripting.

## Mash command in CLI

New subcommand tree:

- `gkc mash qid <QID>` - fetch and display template
- `gkc mash qid <QID> --output=qsv1` - output as QuickStatements V1
- `gkc mash qid <QID> --output=json` - output as JSON
- `gkc mash qid <QID> --api-url=<URL>` - use custom Wikidata API
- `gkc mash qid <QID> --filter-properties=<list>` - include only specific properties

Plain meaning: a set of options to extract, filter, and export template items.

## Implementation phases

### Phase 1: MVP (now)

- `MashLoader` fetches QID via Cooperage.
- `MashTemplate` represents the item.
- `QSV1Formatter` outputs QuickStatements V1 (for new items using LAST syntax).
- `gkc mash qid` CLI command.
- Basic tests.

### Phase 2: Enhancements

- `--filter-properties` option to select a subset of claims.
- `--exclude-qualifiers` / `--exclude-references` for leaner output.
- JSON output format.
- Better error messages for invalid QIDs.

### Phase 3: Future

- `ShExFormatter`.
- QuickStatements processor to consume QS files and write via `wbeditentity`.
- Interactive editing UI (TBD).

## Design decisions

- **Data model:** Use simple dict-based `MashTemplate` rather than full RDF to keep it accessible and testable.
- **Output format default:** Barebones summary - report labels, descriptions, aliases, and total statement count. Avoid expensive SPARQL lookups for property labels in v1.
- **Default language:** Add a package-level default language variable (set to English) for consistent human-readable output.
- **Property filtering:** Use `--exclude-properties` approach (blacklist). Start with support for this; `--filter-properties` can be added later if needed.
- **Qualifier/reference handling:** Include all qualifiers and references by default in QS output. Use `--exclude-qualifiers` and `--exclude-references` to omit them if desired.
- **QID validation:** Try to fetch and report errors gracefully. Use `wbgetentities` API; it returns `error.code = no-such-entity` for missing items.
- **Item size handling:** Emit the full processed item. Monitor for performance issues in practice.
- **API method:** Use Wikidata's `wbgetentities` action to fetch item JSON (not RDF). Allows access to full entity structure without parsing complexity.
