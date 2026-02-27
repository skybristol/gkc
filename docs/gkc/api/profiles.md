# Profiles API

## Overview

The profiles module provides YAML-first entity profiles that drive validation, form schema generation, and profile-aware data workflows.

**Current implementations:** YAML loading, JSON Schema validation, Pydantic model generation, form schema generation, Wikidata validation  
**Future implementations:** profile registry, code generation, broader datatype support

## Quick Start

```python
from gkc.profiles import ProfileLoader, ProfileValidator

profile = ProfileLoader().load_from_file(".dev/TribalGovernmentUS.yaml")
validator = ProfileValidator(profile)
result = validator.validate_item(item_json, policy="lenient")
```

## Classes

### ProfileLoader

::: gkc.profiles.loaders.yaml_loader.ProfileLoader
    options:
      show_root_heading: false
      heading_level: 4

### ProfileDefinition

::: gkc.profiles.models.ProfileDefinition
    options:
      show_root_heading: false
      heading_level: 4

### ProfileValidator

::: gkc.profiles.validation.validator.ProfileValidator
    options:
      show_root_heading: false
      heading_level: 4

### ValidationResult

::: gkc.profiles.validation.validator.ValidationResult
    options:
      show_root_heading: false
      heading_level: 4

### FormSchemaGenerator

::: gkc.profiles.generators.form_generator.FormSchemaGenerator
    options:
      show_root_heading: false
      heading_level: 4

## Examples

### Load a YAML Profile

```python
from gkc.profiles import ProfileLoader

loader = ProfileLoader()
profile = loader.load_from_file(".dev/TribalGovernmentUS.yaml")
print(profile.name)
```

### Generate a Form Schema

```python
from gkc.profiles import FormSchemaGenerator, ProfileLoader

profile = ProfileLoader().load_from_file(".dev/TribalGovernmentUS.yaml")
form_schema = FormSchemaGenerator(profile).build_schema()
print(form_schema["fields"][0]["label"])
```

### Validate a Wikidata Item (Lenient)

```python
from gkc.profiles import ProfileLoader, ProfileValidator

profile = ProfileLoader().load_from_file(".dev/TribalGovernmentUS.yaml")
validator = ProfileValidator(profile)
result = validator.validate_item(item_json, policy="lenient")

if result.ok:
    print("Valid (lenient)")
    for warning in result.warnings:
        print(warning.message)
```

### Validate a Wikidata Item (Strict)

```python
from gkc.profiles import ProfileLoader, ProfileValidator

profile = ProfileLoader().load_from_file(".dev/TribalGovernmentUS.yaml")
validator = ProfileValidator(profile)
result = validator.validate_item(item_json, policy="strict")

if not result.ok:
    for error in result.errors:
        print(error.message)
```

## Error Handling

### Profile Schema Validation Errors

```python
from gkc.profiles import ProfileLoader

loader = ProfileLoader()
try:
    loader.load_from_file("bad_profile.yaml")
except ValueError as exc:
    print(f"Schema error: {exc}")
```

## See Also

- [Mash](mash.md) - Load Wikidata items for validation
- [ShEx](shex.md) - Schema validation against EntitySchemas
- [CLI Profiles](../cli/profiles.md) - Profile commands