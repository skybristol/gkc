# Wikibase Module API

## Overview

The `gkc.wikibase` module is the package-facing access layer for package-owned Wikibase runtime contracts.

In the current slice, it exposes the canonical datatype registry used to normalize datatype semantics across validation, payload shaping, and future ontology initialization flows.

## Quick Start

```python
from gkc.wikibase import get_wikibase_datatype_spec, list_wikibase_datatypes

spec = get_wikibase_datatype_spec("wikibase-item")

print(spec.ontology_uri)
print(spec.datavalue_type)
print(spec.entity_value_kind)
print(list_wikibase_datatypes())
```

## API Reference

::: gkc.wikibase