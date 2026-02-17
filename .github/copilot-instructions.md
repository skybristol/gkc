# Project Overview
The GKC python package supports a data integration workflow that transforms raw data from various sources into linked open data distributed across systems like Wikidata, Wikimedia Commons, Wikipedia, and OpenStreetMap. The project uses a distillery metaphor to describe its architecture and processes.

## Coding Style

- Use clear, descriptive names for classes, functions, and variables that reflect their purpose in the distillery workflow (e.g., Cooperage, RecipeBuilder, SpiritSafeValidator)
- Write docstrings for all public classes and functions, including a "Plain meaning:" section to explain complex concepts in simple terms
- Maintain consistency in terminology across code and documentation, especially regarding the Barrel Schema/Recipe metaphor
- When refactoring or renaming, maintain backwards compatibility with old names as aliases and update tests to ensure both paths work
- Use type hints for function signatures to improve readability and catch type-related issues early
- Follow PEP 8 style guidelines for Python code formatting, and use Black for automatic formatting
- Write modular code with single responsibility functions and classes to improve maintainability and testability
- Include comments for any non-obvious logic or decisions, especially when implementing complex transformations or handling edge cases in data processing

## File + Module Structure
- Core package: `/gkc/` - Contains main modules for cooperage, recipe building, validation, and property catalog
- Documentation: `/docs/gkc/` - MkDocs documentation with sections for pipeline overview, glossary, barrel schemas, and examples
- Tests: `/tests/` - pytest test suite covering all public APIs and key functionality
- Examples: `/docs/gkc/examples/` - Canonical user-facing examples in Jupyter notebooks, using real-world data to demonstrate package functionality
- Temp directory: `/temp/` - Staging area for development artifacts, iterative examples, and draft documentation before moving to permanent locations

## How Copilot should assist
- When generating code, prioritize clarity and maintainability over cleverness or brevity
- When writing documentation, focus on providing actionable instructions and concrete examples rather than generic advice
- When refactoring, ensure that changes are well-documented and that backwards compatibility is maintained where appropriate
- When working with structured data (e.g., RDF), use appropriate libraries and techniques rather than resorting to text parsing or regex, unless specifically instructed to do so
- When generating examples, prefer Jupyter notebooks that set things up for the user to leverage real-world data to exercise the full functionality of the package

## Documentation rules
- Write draft documentation for large architectural directions or complex concepts in the `/temp/` directory for review before moving to permanent locations
- Use markdown formatting for all documentation, including docstrings and MkDocs content
- Link to specific examples from the codebase when describing patterns or conventions rather than making something up that doesn't yet exist
- Reference key files or directories that exemplify important patterns (e.g., `gkc/cooperage.py` for Barrel Schema management)
- Avoid generic advice and focus on documenting the specific approaches and patterns used in this project
- List build and test commands explicitly in the documentation, as agents will attempt to run these automatically

## Testing expectations
- Use pytest for all testing, with a focus on testing public APIs and key functionality
- Run tests frequently during development to catch issues early
- Use the provided pre-merge check script to run all CI checks locally before committing or creating a pull request
- Write tests for both new code and any refactored code to ensure that functionality is maintained and that backwards compatibility is preserved where appropriate
- Generate coverage reports to identify untested areas and improve test coverage over time

## Things copilot should avoid
- Avoid making assumptions about project conventions or patterns that haven't been explicitly documented or exemplified in the codebase
- Avoid making changes to Ipython notebooks in `docs/gkc/examples/` unless specifically instructed to do so, as these are being used by the lead developer to work through real-world data and provide examples for users
- Avoid worrying about maintaining backwards compatibility with old names for classes and functions unless specifically instructed to do so, as the code is still highly experimental and we want to avoid cluttering it with legacy names
- Avoid using rudimentary techniques like text parsing and regex when working with structured data formats like RDF, unless specifically instructed to do so, as there are appropriate libraries and techniques that should be used for these tasks to ensure robustness and maintainability