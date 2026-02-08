# Example Data Files

This directory contains sample data files used in documentation examples and tutorials.

## Structure

Example data files for demonstrating GKC functionality, particularly ShEx validation.

## Files to Add

### Example 1: Tribe Validation

Files for demonstrating EntitySchema validation of tribe data:

1. **`tribe_E502.shex`** - EntitySchema E502 for tribes
   ```bash
   curl https://www.wikidata.org/wiki/Special:EntitySchemaText/E502 > examples/data/tribe_E502.shex
   ```

2. **`valid_Q14708404.ttl`** - Example of a valid tribe (Q14708404 - Wanapum)
   ```bash
   curl https://www.wikidata.org/wiki/Special:EntityData/Q14708404.ttl > examples/data/valid_Q14708404.ttl
   ```

3. **`invalid_Q736809.ttl`** - Example that fails validation
   ```bash
   # Entity that doesn't conform to tribe schema
   curl https://www.wikidata.org/wiki/Special:EntityData/Q736809.ttl > examples/data/invalid_Q736809.ttl
   ```

## Usage in Documentation

Reference these files in README examples:

```python
from gkc import ShExValidator

# Validate using local files
validator = ShExValidator(
    schema_file='examples/data/tribe_E502.shex',
    rdf_file='examples/data/valid_Q14708404.ttl'
)

result = validator.validate()
if result.is_valid():
    print("Validation passed!")
```

## Usage in Example Scripts

See `examples/shex_validation_example.py` for a complete working example using these files.

## Note on Git

These files should be committed to the repository as they're part of the documentation and user-facing examples.
