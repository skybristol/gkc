# Collaboration Guidelines for GKC Development

This document establishes conventions for AI-assisted development of the GKC (Geoscience Knowledge Commons) project. These guidelines ensure consistency, maintain code quality, and align with open science principles of transparency and reproducibility.

## Core Principles

### Open Science & Transparency
- All development decisions, implementation notes, and rationale should be documented
- Code and documentation changes should be traceable and well-explained
- Examples and test data should be representative and reusable
- Documentation should be accessible to both technical and non-technical audiences

### Quality Standards
- All code must pass CI/CD checks (Black, Ruff, pytest)
- Test coverage should be comprehensive (aim for 80%+)
- Changes should include both implementation and documentation updates
- Examples should demonstrate real-world usage patterns

## Project Structure

### Source Code (`gkc/`)
- Core library modules with clear, focused responsibilities
- Each module should have corresponding tests and documentation
- Follow existing patterns: authentication, item creation, SPARQL queries, etc.

### Tests (`tests/`)
- All test files use `test_*.py` naming convention
- Tests should be comprehensive, not just happy-path
- Use pytest fixtures for reusable test data (see `conftest.py`)
- Mock external API calls to ensure deterministic testing
- Each new feature should include test coverage before merging

### Documentation (`docs/`)

#### User Documentation
- `docs/*.md`: End-user guides and tutorials
- `docs/api/`: API reference documentation
- Keep guides practical with working examples
- Use relative links for internal docs: `../other_doc.md`
- Link to code on GitHub, not local paths: `https://github.com/skybristol/gkc/blob/main/gkc/module.py`

#### Development Notes (`docs/copilot/`)
- Implementation notes documenting development decisions
- Include context, alternatives considered, and rationale
- Use descriptive filenames: `FEATURE_IMPLEMENTATION.md`, `BUG_FIX_APPROACH.md`
- Reference relevant issues, PRs, and commits
- **These notes are preserved for transparency and future reference**

### Examples (`examples/`)
- Working examples including Python scripts and Jupyter notebooks
- Each example should be self-contained and runnable
- Examples are part of the documentation suite (docs dependency group), not included in PyPI distribution
- Self-contained notebooks eliminate need for separate configuration/data files
- Include descriptive comments/markdown cells explaining what examples demonstrate
- Use realistic but anonymized/public data (e.g., public Wikidata records)

### Temporary Files
- Test-related temporary files: Use pytest's `tmp_path` fixture
- Notebook exploration/scratch work: Store locally with `.gitignore` rules if not committing
- Integration tests: Clean up after completion or document persistence reason

## Code Standards

### Formatting
- **Black**: Primary code formatter, no negotiation
- **Ruff**: Linter for code quality and style
- Line length: 88 characters (Black default)
- Both must pass before merging

### Style Conventions
- Clear, descriptive variable and function names
- Type hints for public APIs
- Docstrings for all public functions/classes (Google style)
- Prefer explicit over implicit
- Handle errors gracefully with custom exceptions

### Dependencies
- Managed via Poetry (`pyproject.toml`)
- Keep dependencies minimal and intentional
- Optional dependencies for specialized features (e.g., pandas for SPARQL)
- Document why each dependency is needed

## Development Workflow

### Making Changes
1. **Understand context**: Review relevant code, tests, and documentation
2. **Plan approach**: For complex changes, create a todo list to track progress
3. **Implement incrementally**: Code + tests + docs together
4. **Verify quality**: Run tests and linters locally
5. **Document rationale**: Add implementation notes if decisions were non-obvious

### Testing Strategy
- Unit tests for individual functions/methods
- Integration tests for component interactions
- Test error conditions, not just success cases
- Use parametrized tests for multiple similar scenarios
- Mock external services when warranted (Wikidata, OpenStreetMap, etc.) but follow up with real world testing and documentation in notebooks

### Documentation Updates
- Update relevant user docs when behavior changes
- Keep API reference in sync with code
- Add examples for new features
- Update navigation in `mkdocs.yml` when adding new docs

### Jupyter Notebook Development
- Notebooks part of `examples/` are for demonstration and exploration
- Keep notebooks self-contained with all necessary setup in cells
- Use `nbstripout` to strip execution output before committing (automatic with `nbstripout --install`)
- Notebooks should only depend on the `gkc` package plus common tools (pandas, etc.)
- Include markdown cells explaining example goals and usage patterns
- Notebooks are not part of PyPI distribution; they're part of the documentation suite
- For reproducibility, document any environment or data setup requirements in notebook markdown

### Git Practices
- Descriptive commit messages explaining "why", not just "what"
- Keep commits focused and logical
- Reference issues/PRs when relevant
- Clean up branches after merging

## MkDocs Documentation

### Navigation Structure (`mkdocs.yml`)
```yaml
nav:
  - Getting Started
  - Core Features (by user workflow)
  - Advanced Topics
  - API Reference
  - Development
    - Implementation Notes (copilot docs)
```

### Link Formatting
- **Internal docs**: Relative paths `../other_doc.md`
- **Code files**: GitHub URLs with line numbers
  - `https://github.com/skybristol/gkc/blob/main/gkc/module.py#L42`
- **External resources**: Full URLs with descriptive text

### Building & Validation
- Build locally before committing: `poetry run mkdocs build --clean`
- No warnings allowed (except known dependency deprecations)
- Test serve locally: `poetry run mkdocs serve`

## CI/CD Pipeline

### GitHub Actions
- Runs on: Push to main, pull requests
- Checks: Black formatting, Ruff linting, pytest with coverage
- All checks must pass before merging
- Coverage report uploaded to Codecov

### Local Verification
Before pushing, run:
```bash
poetry run black gkc/ tests/
poetry run ruff check gkc/ tests/
poetry run pytest
poetry run mkdocs build --clean
```

Or use the pre-merge check script:
```bash
./scripts/pre-merge-check.sh
```

## Communication Style

### When AI is Assisting
- Provide clear, factual responses
- Show work through tool usage (don't just describe)
- Update progress transparently for multi-step tasks
- Ask clarifying questions when intent is ambiguous
- Cite sources (files, line numbers, documentation)

### Documentation Writing
- Clear, concise, action-oriented
- Assume reader familiarity with Python but not Wikidata
- Provide working examples early
- Explain "why" for non-obvious decisions
- Use proper Markdown formatting (links, code blocks, etc.)

## Special Considerations

### Wikidata Interaction
- Always use bot passwords, never main account credentials
- Test against Wikidata test instance when possible
- Be mindful of rate limits and API etiquette
- Document SPARQL queries with comments

### Authentication & Secrets
- Never commit credentials or tokens
- Use environment variables for sensitive data
- Document required environment variables in README
- Provide example `.env.example` files

### Data Privacy
- Use only public or synthetic data in examples
- Anonymize any real-world data if used for testing
- Be transparent about data sources and licensing

## Future Enhancements

### Areas for Improvement
- Expand test coverage for edge cases
- Add more real-world examples
- Performance optimization for large datasets
- Additional output format support

### Documentation Needs
- Video tutorials for complex workflows
- Troubleshooting guide for common issues
- Contributing guide for external developers
- Architectural decision records (ADRs)

## Reference Materials

### Project Resources
- [Main Documentation](https://skybristol.github.io/gkc/)
- [GitHub Repository](https://github.com/skybristol/gkc)
- [PyPI Package](https://pypi.org/project/gkc/)

### External Standards
- [PEP 8](https://peps.python.org/pep-0008/) - Python style guide
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) - Docstrings
- [Semantic Versioning](https://semver.org/) - Version management
- [Keep a Changelog](https://keepachangelog.com/) - Changelog format

---

**Document Status**: Living document, updated as practices evolve  
**Last Updated**: February 12, 2026  
**Maintained By**: Project collaborators and AI assistants
