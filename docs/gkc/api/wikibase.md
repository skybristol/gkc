# Wikibase Module API

## Overview

The `gkc.wikibase` module is the package-facing access layer for package-owned Wikibase runtime contracts.

In the current slice, it exposes the canonical datatype registry used to normalize datatype semantics across validation, payload shaping, and future ontology initialization flows.

## Quick Start

```python
from gkc.wikibase import (
	build_meta_wikibase_init_index,
	get_wikibase_datatype_spec,
	list_wikibase_datatypes,
)

spec = get_wikibase_datatype_spec("wikibase-item")
init_index = build_meta_wikibase_init_index()

print(spec.ontology_uri)
print(spec.datavalue_type)
print(spec.entity_value_kind)
print(list_wikibase_datatypes())
print(init_index.properties["instance_of"].datatype)
print(init_index.items["entity_profile"].subclass_of)
```

The module now exposes both package-owned datatype registry helpers and package-owned Meta-Wikibase init helpers.

## API Reference

::: gkc.wikibase