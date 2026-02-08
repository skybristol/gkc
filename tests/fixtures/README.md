# Test Fixtures

This directory contains test data files used by the test suite.

## Structure

- `shex/` - ShEx schema files (EntitySchemas)
- `rdf/` - RDF data files in Turtle format

## Files to Add

### ShEx Schemas (`shex/`)

Place EntitySchema files here with naming convention:
- `tribe_<EID>.shex` (e.g., `tribe_E502.shex`)

To fetch from Wikidata:
```bash
curl https://www.wikidata.org/wiki/Special:EntitySchemaText/E502 > tests/fixtures/shex/tribe_E502.shex
```

### RDF Data (`rdf/`)

Place RDF Turtle files here with naming convention:
- `valid_<QID>.ttl` - Data that passes validation
- `invalid_<QID>.ttl` - Data that fails validation

To fetch from Wikidata:
```bash
# Valid example
curl https://www.wikidata.org/wiki/Special:EntityData/valid_Q14708404.ttl > tests/fixtures/rdf/valid_Q14708404.ttl

# Invalid example (adjust QID as needed)
curl https://www.wikidata.org/wiki/Special:EntityData/invalid_Q736809.ttl > tests/fixtures/rdf/invalid_Q736809.ttl
```

## Usage in Tests

Fixtures are automatically available via pytest fixtures defined in `conftest.py`:

```python
def test_with_fixtures(schema_file, valid_rdf_file):
    """Test using fixture file paths."""
    validator = ShExValidator(
        schema_file=str(schema_file),
        rdf_file=str(valid_rdf_file)
    )
    validator.validate()
    assert validator.is_valid()

def test_with_loaded_data(schema_text, valid_rdf_text):
    """Test using loaded fixture content."""
    validator = ShExValidator(
        schema_text=schema_text,
        rdf_text=valid_rdf_text
    )
    validator.validate()
    assert validator.is_valid()
```
