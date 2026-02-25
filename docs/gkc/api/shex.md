# ShEx Validation API

## Overview

The ShEx validation module provides RDF data validation against ShEx (Shape Expression) schemas. It's designed primarily for validating Wikidata entities against EntitySchemas but supports any RDF data and ShEx schema combination.

**Current implementations:** Wikidata EntitySchema validation, local file validation  
**Future implementations:** Additional RDF graph sources, streaming validation

## Quick Start

```python
from gkc import ShexValidator

# Validate Wikidata item against EntitySchema
validator = ShexValidator(qid='Q14708404', eid='E502')
result = validator.check()

if result.is_valid():
    print("✓ Validation passed")
else:
    print("✗ Validation failed")
```

## Classes

### ShexValidator

::: gkc.shex.ShexValidator
    options:
      show_root_heading: false
      heading_level: 4

## Exceptions

### ShexValidationError

::: gkc.shex.ShexValidationError
    options:
      show_root_heading: false
      heading_level: 4

## Examples

### Validating Wikidata Entities

Validate a Wikidata item against a published EntitySchema:

```python
from gkc import ShexValidator

# Validate federally recognized tribe (Q14708404) against tribe schema (E502)
validator = ShexValidator(qid='Q14708404', eid='E502')
result = validator.check()

if result.is_valid():
    print("✓ Item conforms to EntitySchema E502")
else:
    print("✗ Item does not conform:")
    for res in result.results:
        print(f"  - {res.reason}")
```

### Validating Local Files

Validate local RDF data against a local ShEx schema:

```python
from gkc import ShexValidator

validator = ShexValidator(
    rdf_file='path/to/entity.ttl',
    schema_file='path/to/schema.shex'
)

result = validator.check()
print(f"Valid: {result.is_valid()}")
```

### Mixed Sources

You can mix Wikidata and local sources:

```python
# Wikidata entity with local schema
validator = ShexValidator(
    qid='Q42',
    schema_file='custom_schema.shex'
)
result = validator.check()

# Local RDF data with Wikidata EntitySchema
validator = ShexValidator(
    rdf_file='new_entity.ttl',
    eid='E502'
)
result = validator.check()
```

### Using Text Strings

For programmatically generated RDF or schemas:

```python
from gkc import ShexValidator

my_rdf = """
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix wdt: <http://www.wikidata.org/prop/direct/> .

wd:Q42 wdt:P31 wd:Q5 .
"""

my_schema = """
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>

<Human> {
  wdt:P31 [ wd:Q5 ]
}
"""

validator = ShexValidator(
    rdf_text=my_rdf,
    schema_text=my_schema
)

result = validator.check()
```

### Fluent API Pattern

Load and validate step-by-step:

```python
from gkc import ShexValidator

validator = ShexValidator(qid='Q42', eid='E502')

# Load schema
validator.load_specification()
print(f"Schema loaded: {len(validator._schema)} characters")

# Load RDF data
validator.load_rdf()
print(f"RDF loaded: {len(validator._rdf)} characters")

# Perform validation
validator.evaluate()

# Check result
if validator.passes_inspection():
    print("✓ Validation passed!")
```

### Custom User Agent

When fetching from Wikidata, use a custom user agent:

```python
from gkc import ShexValidator

validator = ShexValidator(
    qid='Q42',
    eid='E502',
    user_agent='MyBot/1.0 (https://example.com; bot@example.com)'
)

result = validator.check()
```

### Pre-Upload Quality Check

Validate data before uploading to Wikidata:

```python
from gkc import ShexValidator, ShexValidationError

def validate_before_upload(rdf_data: str, target_schema: str) -> bool:
    """Validate RDF data against target EntitySchema."""
    try:
        validator = ShexValidator(
            rdf_text=rdf_data,
            eid=target_schema
        )
        
        result = validator.check()
        
        if result.is_valid():
            return True
        else:
            # Log validation errors
            for res in result.results:
                print(f"Validation error: {res.reason}")
            return False
            
    except ShexValidationError as e:
        print(f"Validation failed: {e}")
        return False

# Use in upload workflow
if validate_before_upload(my_data, 'E502'):
    upload_to_wikidata(my_data)
else:
    print("Fix validation errors before uploading")
```

### Batch Validation

Validate multiple entities:

```python
from gkc import ShexValidator

entities_to_validate = [
    ('Q14708404', 'Wanapum'),
    ('Q3551781', 'Umatilla'),
    ('Q1948829', 'Muckleshoot')
]

schema_id = 'E502'  # Federally recognized tribe schema

results = {}
for qid, name in entities_to_validate:
    validator = ShexValidator(qid=qid, eid=schema_id)
    validator.check()
    results[name] = validator.is_valid()

# Report
for name, valid in results.items():
    status = "✓" if valid else "✗"
    print(f"{status} {name}")
```

## Error Handling

### Common Error Patterns

```python
from gkc.shex import ShexValidationError, ShexValidator

try:
    validator = ShexValidator(qid='Q42', eid='E502')
    result = validator.check()
    
    if not result.is_valid():
        # Parse validation errors
        for res in result.results:
            reason = res.reason or ""
            
            if "not in value set" in reason:
                print(f"Value constraint violation: {reason}")
            elif "does not match" in reason:
                print(f"Format/type mismatch: {reason}")
            elif "Constraint violation" in reason:
                print(f"Cardinality or requirement error: {reason}")
                
except ShexValidationError as e:
    print(f"Validation process failed: {e}")
```

### Handling Missing Sources

```python
from gkc.shex import ShexValidationError, ShexValidator

try:
    validator = ShexValidator()  # No sources provided
    validator.check()
except ShexValidationError as e:
    print(f"Error: {e}")
    # Output: "No schema source provided. Specify eid, schema_text, or schema_file."
```

## See Also

- [ShEx CLI Documentation](../cli/shex.md) - Command-line interface
- [Utilities Guide](../utilities.md) - General ShEx validation guide
- [Wikidata EntitySchemas](https://www.wikidata.org/wiki/Wikidata:EntitySchema) - Wikidata's schema namespace
- [ShEx Primer](http://shex.io/shex-primer/) - Learn ShEx syntax
