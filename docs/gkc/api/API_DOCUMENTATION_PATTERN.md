# API Documentation Pattern Template

This template documents the standard pattern for creating API documentation for GKC modules. Use this as a guide when creating documentation for remaining modules.

## Purpose

Each module should have its own API documentation page that follows this consistent structure, making it easy for users to discover functionality and understand how to use it.

## File Structure

```
docs/gkc/api/
  ├── index.md                 # Overview and quick reference
  ├── module_name.md           # Per-module documentation
  └── ...
```

## Module Documentation Pattern

Each module documentation file (`docs/gkc/api/module_name.md`) should follow this structure:

### 1. Header and Overview (Required)

```markdown
# Module Name API

## Overview

[1-2 sentence description of what the module does]

[Optional: 1-2 sentences about its role in the distillery workflow]

**Current implementations:** [What's supported now]  
**Future implementations:** [What's planned, if applicable]

## Quick Start

```python
[Minimal 3-5 line example showing the most common use case]
```
```

### 2. Core Classes/Functions (Required)

Use mkdocstrings to auto-generate detailed API documentation:

```markdown
## Classes

### ClassName

::: gkc.module_name.ClassName
    options:
      show_root_heading: false
      heading_level: 4

## Functions

### function_name()

::: gkc.module_name.function_name
    options:
      show_root_heading: false
      heading_level: 4
```

**Note:** The `::: gkc.module_name.ClassName` syntax tells mkdocstrings to extract and render the docstring from that class/function.

### 3. Examples Section (Required)

Include 3-5 real-world examples showing common tasks:

```markdown
## Examples

### [Task-oriented example title]

```python
[Complete, runnable example using realistic QIDs, data, etc.]
```

### [Another example]

```python
[Another complete example]
```
```

**Guidelines for examples:**
- Use real Wikidata QIDs (Q42, Q5, etc.) not placeholders
- Show complete, copy-paste-ready code
- Include comments explaining non-obvious steps
- Show error handling where appropriate
- Progress from simple to complex

### 4. Error Handling (Optional but Recommended)

Document common error conditions and how to handle them:

```markdown
## Error Handling

### [Error scenario]

```python
[Example showing how the error occurs and how to handle it]
```
```

### 5. See Also Section (Required)

Cross-link to related documentation:

```markdown
## See Also

- [Related API Module](other_module.md) - Brief description
- [Related CLI](../cli/command.md) - Command-line interface
- [Conceptual Guide](../concept.md) - Background information
```

## Complete Example

See [docs/gkc/api/mash.md](mash.md) and [docs/gkc/api/mash_formatters.md](mash_formatters.md) for complete examples following this pattern.

## Documentation Guidelines

### Docstrings in Code

Every public function/class must have a docstring following this format:

```python
def function_name(param1: str, param2: int = 10) -> dict:
    """One-line summary of what the function does.

    Longer description if needed (2-3 sentences maximum).

    Args:
        param1: Description of param1.
        param2: Description of param2 (default: 10).

    Returns:
        Description of return value.

    Raises:
        ExceptionType: When this error occurs.

    Example:
        >>> result = function_name("Q42")
        >>> print(result)
        {'qid': 'Q42', 'label': 'Douglas Adams'}

    Plain meaning: [Simple explanation in everyday language]
    """
```

**Note:** The "Plain meaning" section is a GKC convention to provide a non-technical explanation.

### Writing Style

- **Be concise**: Keep explanations short and clear
- **Be explicit**: Don't assume the user knows internal details
- **Use examples**: Show, don't just tell
- **Prefer tasks over features**: "Load a Wikidata item" not "WikidataLoader class"
- **Use real data**: Q42, E502, etc., not foo/bar
- **Link generously**: Cross-reference related docs

### What to Include

**Always include:**
- Overview and quick start
- Auto-generated class/function docs
- 3-5 real-world examples
- See also links

**Include when relevant:**
- Error handling examples
- Configuration options
- Performance considerations
- Limitations or caveats

**Never include:**
- Implementation details users don't need
- Duplicate information from docstrings
- Placeholder/toy examples (foo, bar, etc.)

## Updating the Navigation

After creating a new module documentation file, add it to `mkdocs.yml`:

```yaml
nav:
  - GKC Documentation:
    - API Reference:
      - Overview: gkc/api/index.md
      - Module Name: gkc/api/module_name.md
      - ...
```

## Checklist for New Module Documentation

- [ ] Create `docs/gkc/api/module_name.md`
- [ ] Add header with module name
- [ ] Write overview section (1-2 sentences)
- [ ] Add quick start example (3-5 lines)
- [ ] Use mkdocstrings to include class/function docs
- [ ] Write 3-5 real-world examples
- [ ] Add error handling section (if applicable)
- [ ] Add "See also" links
- [ ] Update `mkdocs.yml` navigation
- [ ] Update `docs/gkc/api/index.md` quick reference table
- [ ] Test that documentation builds correctly
- [ ] Verify all code examples are runnable

## Testing Documentation

Build and preview locally:

```bash
mkdocs serve
```

Visit `http://127.0.0.1:8000/` to preview the site.

## Modules Still Needing Documentation

Based on the codebase, these modules need API documentation:

1. **recipe.md** - Recipe builder and entity catalog
2. **cooperage.md** - Barrel schema management
3. **spirit_safe.md** - Validation
4. **bottler.md** - Data transformation
5. **exporter.md** - Wikidata submission
6. **auth.md** - Authentication
7. **sitelinks.md** - Wikipedia sitelinks

Priority: Start with the most commonly used modules (recipe, auth) before less frequently used ones.
