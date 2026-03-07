# Mash Module: Loading and Shaping Source Data

**Plain Meaning:** A comprehensive guide to the mash module's role as the inbound/read layer for GKC workflows, covering how to load data from multiple sources, shape entities into templates, and extend mash with new source adapters.

## Overview

The **mash module** is GKC's unified read layer for ingesting data from diverse sources. The name comes from the distillery metaphor—like grain milled and steeped to extract fermentable sugars, mashed entities extract essential structure from raw source data, preparing them as ingredients for downstream GKC workflows (validation, transformation, packet creation, and curation).

The mash module provides:

- **`MashSourceAdapter` protocol** — A plugin contract for registering new data sources (Wikibase, Wikipedia, CSV, JSON APIs, dataframes, etc.)
- **Pre-built adapters** — Current implementations for Wikidata/Wikibase items, properties, EntitySchemas, and Wikipedia templates
- **Template models** — Dataclass-based structures (`WikibaseItemTemplate`, `WikibasePropertyTemplate`, `WikibaseEntitySchemaTemplate`, `WikipediaTemplate`) that normalize entity shape for downstream processing
- **Utilities** — Helpers for filtering, labeling, transforming, and preparing entities for export

Mash is strictly a **read/load layer**. Write operations (creating, editing, or removing data) belong in the [shipping module](shipping.md)—mash shapes data received; shipper ships data created.

---

## Quick Start

### Load Wikidata items

```python
from gkc.mash import WikibaseLoader

loader = WikibaseLoader()
template = loader.load_item("Q42")
print(template.summary())
```

### Use a source adapter directly

```python
from gkc.mash import WikibaseMashSourceAdapter, WikipediaMashSourceAdapter

# Wikibase adapter dispatches based on ID prefix (Q, P, E)
wb_adapter = WikibaseMashSourceAdapter()
item = wb_adapter.load("Q42")
prop = wb_adapter.load("P31")
schema = wb_adapter.load("E502")

# Wikipedia adapter loads templates
wp_adapter = WikipediaMashSourceAdapter()
infobox = wp_adapter.load("Infobox_settlement")

print(item.summary(), prop.summary(), schema.summary(), infobox.summary())
```

### Batch loading

```python
from gkc.mash import WikibaseMashSourceAdapter

adapter = WikibaseMashSourceAdapter()
results = adapter.load_many(["Q42", "Q5", "Q30"])
print(sorted(results.keys()))
```

---

## Architecture

### Layered Design

The mash module is organized into focused layers:

```
┌─ __init__.py ────────── Stable public API surface
│                         (exports all public names)
│
├─ protocols.py ────────── Plugin contracts
│  └─ MashSourceAdapter  - Protocol defining source loader interface
│  └─ DataTemplate       - Protocol defining template shape contract
│
├─ core.py ──────────────── Implementations (main module)
│  ├─ Clients
│  │  └─ WikibaseApiClient  - HTTP client for Wikibase/Wikidata API
│  ├─ Templates
│  │  ├─ WikibaseItemTemplate
│  │  ├─ WikibasePropertyTemplate
│  │  ├─ WikibaseEntitySchemaTemplate
│  │  └─ WikipediaTemplate
│  ├─ Loaders
│  │  ├─ WikibaseLoader      - Orchestrates Wikibase item/property/schema loading
│  │  └─ WikipediaLoader     - Wikipedia template retrieval
│  ├─ Adapters (plugin implementations)
│  │  ├─ WikibaseMashSourceAdapter    - Wraps WikibaseLoader with protocol
│  │  └─ WikipediaMashSourceAdapter   - Wraps WikipediaLoader with protocol
│  └─ Utilities
│     ├─ apply_template_language_filter()   - Filter entity labels/descriptions/aliases
│     ├─ apply_item_property_filters()      - Include/exclude item claims
│     └─ [other utilities for transformation]
```

### Component Responsibilities

| Component | Responsibility | Typical Use |
|-----------|-----------------|-------------|
| **WikibaseApiClient** | Raw HTTP communication with Wikibase instances | Direct queries, batch entity retrieval, search |
| **WikibaseLoader** | High-level orchestration: fetch, parse entity data, build templates | CLI bulk loads, programmatic entity shaping |
| **MashSourceAdapter** | Plugin interface: `can_load()`, `load()`, `load_many()` | Extension point for CSV/JSON/dataframe sources |
| **Adapter Implementations** | Concrete adapters wrapping loaders | Auto-dispatch to correct loader based on source ref format |
| **Templates** | Normalized entity shape with export methods | Downstream filtering, validation, transformation, shipper input |
| **Utilities** | Reusable transforms and helpers | Language filtering, property filtering, label hydration |

---

## Core Concepts

### MashSourceAdapter Protocol

The `MashSourceAdapter` is the plugin contract for extending mash with new source types. Every source (Wikibase, Wikipedia, CSV, JSON, dataframe, etc.) should implement this protocol.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class MashSourceAdapter(Protocol):
    """
    Plugin interface for loading data from any source into mash templates.
    
    Attributes:
        source_name (str): Human-readable identifier of the source (e.g., "wikibase", "csv")
    
    Methods:
        can_load(source_ref: str) -> bool
            Check if this adapter can load a given source reference.
            
        load(source_ref: str) -> DataTemplate
            Load a single entity and return a template.
            Raises MashLoadError if the reference is not found or is malformed.
            
        load_many(source_refs: list[str]) -> dict[str, DataTemplate]
            Load multiple entities. Returns dict of source_ref -> template.
            Silently skips references that cannot be loaded or returns error stubs.
    """
    source_name: str
    
    def can_load(self, source_ref: str) -> bool:
        ...
    
    def load(self, source_ref: str) -> DataTemplate:
        ...
    
    def load_many(self, source_refs: list[str]) -> dict[str, DataTemplate]:
        ...
```

**Key design principles:**

- Adapters are **stateless** — each call to `load()` or `load_many()` is independent; no session state expected
- Source references are **opaque strings** — each adapter interprets the format (e.g., `"Q42"` vs. `"products-2024-01.csv"` vs. `"SELECT * FROM users"`)
- Templates are **normalized outputs** — all adapters return objects implementing the `DataTemplate` protocol, regardless of source
- Graceful degradation — `load_many()` should attempt partial loading rather than failing on first error

### DataTemplate Protocol

Every template returned by any adapter must implement the `DataTemplate` protocol:

```python
@runtime_checkable
class DataTemplate(Protocol):
    """Minimal contract for shaped entity data."""
    
    def summary(self) -> dict:
        """Return a human-readable summary (labels, descriptions, key properties)."""
        ...
    
    def to_dict(self) -> dict:
        """Return full normalized representation."""
        ...
```

---

## Current Source Adapters

### Wikibase Adapter: `WikibaseMashSourceAdapter`

**Source references:** Wikibase entity IDs formatted as `Q<number>` (items), `P<number>` (properties), `E<number>` (EntitySchemas)

**Example:**
```python
from gkc.mash import WikibaseMashSourceAdapter

adapter = WikibaseMashSourceAdapter()

# All three dispatch automatically based on prefix
item = adapter.load("Q42")           # Item
prop = adapter.load("P31")           # Property
schema = adapter.load("E502")        # EntitySchema

# Batch loading
batch = adapter.load_many(["Q42", "P31", "E502"])
```

**Configuration:**
- By default, connects to public Wikidata (`https://www.wikidata.org/w/api.php`)
- Can be reconfigured to point to any Wikibase instance via the underlying `WikibaseLoader`

**Output:** `WikibaseItemTemplate`, `WikibasePropertyTemplate`, or `WikibaseEntitySchemaTemplate`

### Wikipedia Adapter: `WikipediaMashSourceAdapter`

**Source references:** Wikipedia (or Wikimedia) template names with optional `Template:` prefix normalization

**Example:**
```python
from gkc.mash import WikipediaMashSourceAdapter

adapter = WikipediaMashSourceAdapter()

# Both are equivalent (prefix normalization handled)
template1 = adapter.load("Infobox_settlement")
template2 = adapter.load("Template:Infobox_settlement")
assert template1.title == template2.title
```

**Configuration:**
- Connects to `en.wikipedia.org` by default
- Language/wiki selection configurable via the underlying `WikipediaLoader`

**Output:** `WikipediaTemplate`

---

## Extending Mash: Building New Source Adapters

To add a new source type (CSV, JSON API, database query, dataframe, etc.), follow this pattern:

### 1. Create a new adapter module

Create a module in the mash package (or in your own package):

```python
# Example: gkc/mash/csv_adapter.py
from gkc.mash import MashSourceAdapter, DataTemplate
from pathlib import Path
import csv

class CSVMashSourceAdapter:
    """Load rows from CSV files as templates."""
    
    source_name = "csv"
    
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
    
    def can_load(self, source_ref: str) -> bool:
        """Check if row ID exists in the CSV."""
        # source_ref format: "row_id" or "row_index"
        try:
            with open(self.file_path) as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if source_ref == row.get("id") or source_ref == str(i):
                        return True
            return False
        except Exception:
            return False
    
    def load(self, source_ref: str) -> DataTemplate:
        """Load a single CSV row as a template."""
        with open(self.file_path) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if source_ref == row.get("id") or source_ref == str(i):
                    return CSVRowTemplate(source_ref, row)
        raise MashLoadError(f"Row {source_ref} not found in CSV")
    
    def load_many(self, source_refs: list[str]) -> dict[str, DataTemplate]:
        """Load multiple CSV rows."""
        results = {}
        for ref in source_refs:
            try:
                results[ref] = self.load(ref)
            except MashLoadError:
                pass  # Skip missing rows
        return results


class CSVRowTemplate:
    """Minimal template wrapper for CSV row data."""
    
    def __init__(self, source_ref: str, row_data: dict):
        self.source_ref = source_ref
        self.row_data = row_data
    
    def summary(self) -> dict:
        return {
            "source_ref": self.source_ref,
            "row_data": self.row_data,
            "field_count": len(self.row_data),
        }
    
    def to_dict(self) -> dict:
        return {
            "source_ref": self.source_ref,
            "row_data": self.row_data,
        }
```

### 2. Register the adapter

Once created, the adapter can be used directly:

```python
from gkc.mash.csv_adapter import CSVMashSourceAdapter

csv_adapter = CSVMashSourceAdapter(Path("data/records.csv"))

# The adapter automatically satisfies the MashSourceAdapter protocol
if csv_adapter.can_load("record_123"):
    template = csv_adapter.load("record_123")
    print(template.summary())
```

Or register it in your own code for polymorphic dispatch:

```python
def load_from_source(source_ref: str, sources: dict[str, MashSourceAdapter]):
    """Try each adapter until one can load the reference."""
    for adapter in sources.values():
        if adapter.can_load(source_ref):
            return adapter.load(source_ref)
    raise MashLoadError(f"No adapter can load {source_ref}")
```

### 3. Adapter skeleton template

Use this as a starting point for new adapters:

```python
"""
<SourceType>MashSourceAdapter

Loads <SourceType> data and shapes it into DataTemplate objects.

Configuration:
  - <config option 1>
  - <config option 2>

Source reference format:
  - <description of how source_ref strings are interpreted>

Output template:
  - <class name implementing DataTemplate>
"""

from gkc.mash import MashSourceAdapter, DataTemplate, MashLoadError


class <SourceType>MashSourceAdapter:
    """Load <source type> data as mash templates."""
    
    source_name = "<lowercase_source_name>"
    
    def __init__(self, **config):
        """
        Initialize the adapter with source-specific configuration.
        
        Args:
            <arg1>: <description>
            <arg2>: <description>
        """
        pass
    
    def can_load(self, source_ref: str) -> bool:
        """
        Check if this adapter can load the given source reference.
        
        Args:
            source_ref: Source-specific reference format
        
        Returns:
            True if the reference exists and is loadable, False otherwise
        """
        pass
    
    def load(self, source_ref: str) -> DataTemplate:
        """
        Load a single entity from the source.
        
        Args:
            source_ref: Source-specific reference
        
        Returns:
            DataTemplate: Normalized template object
        
        Raises:
            MashLoadError: If the reference is not found or is malformed
        """
        pass
    
    def load_many(self, source_refs: list[str]) -> dict[str, DataTemplate]:
        """
        Load multiple entities from the source.
        
        Args:
            source_refs: List of source-specific references
        
        Returns:
            dict: Mapping of source_ref -> DataTemplate for successfully loaded refs
                  (silently omits references that cannot be loaded)
        """
        pass


class <SourceType>Template:
    """Template wrapper for <source type> data."""
    
    def __init__(self, source_ref: str, data: dict):
        """
        Initialize template with source reference and normalized data.
        
        Args:
            source_ref: Original source reference identifier
            data: Normalized/extracted data structure
        """
        pass
    
    def summary(self) -> dict:
        """Return human-readable summary of the entity."""
        pass
    
    def to_dict(self) -> dict:
        """Return full normalized representation."""
        pass
```

### 4. Tips for implementation

- **Lazy loading**: Consider deferring expensive I/O until `load()` is actually called, not during `__init__()`
- **Error handling**: Use `MashLoadError` for user-facing errors; let infrastructure errors propagate for debugging
- **Reference format**: Document your reference format clearly — users need to know what strings are valid (`can_load()` exists for validation)
- **Batch optimization**: Override `load_many()` if your source supports efficient batch retrieval (e.g., SQL `WHERE id IN (...)` vs. loops)
- **Template normalization**: Keep template outputs simple; complex transformations belong in downstream modules (profiles validation, shipper, etc.)
- **Testing**: Use `isinstance(adapter, MashSourceAdapter)` to verify your implementation satisfies the protocol

---

## Common Patterns

### Filtering and shaping entities

```python
from gkc.mash import (
    WikibaseLoader,
    apply_template_language_filter,
    apply_item_property_filters,
)

loader = WikibaseLoader()
item = loader.load_item("Q42")

# Filter to specific properties only
apply_item_property_filters(item, include_properties=["P31", "P21", "P569"])

# Keep only English labels/descriptions/aliases
apply_template_language_filter(item, ["en"])

# Export as clean template for new item creation
shell_data = item.to_shell()

# Or transform for QuickStatements bulk editing
qs_lines = item.to_qsv1(for_new_item=False)
```

### Batch loading with caching

```python
from gkc.mash import WikibaseMashSourceAdapter

adapter = WikibaseMashSourceAdapter()

# Load items, caching successful results
cache = {}
for qid in large_qid_list:
    if qid not in cache:
        try:
            cache[qid] = adapter.load(qid)
        except Exception as e:
            print(f"Failed to load {qid}: {e}")

# Reuse without reloading
for qid, template in cache.items():
    print(template.summary())
```

### Polymorphic source dispatch

```python
from gkc.mash import WikibaseMashSourceAdapter, WikipediaMashSourceAdapter

# Store available adapters
adapters = {
    "wikibase": WikibaseMashSourceAdapter(),
    "wikipedia": WikipediaMashSourceAdapter(),
}

def load_from_any_source(source_ref: str) -> DataTemplate:
    """Try each adapter until one succeeds."""
    for adapter in adapters.values():
        if adapter.can_load(source_ref):
            return adapter.load(source_ref)
    raise ValueError(f"No adapter can load {source_ref}")
```

---

## See Also

- [Mash API Reference](api/mash.md) — Full Python API documentation with mkdocstrings
- [Mash CLI Commands](cli/mash.md) — Command-line interface for bulk loading and transformation
- [Shipping Module](shipping.md) — Write layer for creating/editing entities
- [Profiles Module](profiles.md) — Entity validation and curation packets built from mash data
