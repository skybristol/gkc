# Core architectural principles/components
- The **Global Knowledge Commons** (GKC) is an abstract concept for an envisioned improved linkage between Wikidata, Wikimedia Commons, Wikipedia Templates, and OpenStreetMap
- Our project uses the whiskey distillery metaphor for naming and organizing parts of a complex architecture
- gkc is the engine (python package) that does the work
- **SpiritSafe** is a declarative registry hosted in the dedicated `skybristol/SpiritSafe` repository; it contains
  - `profiles/` with YAML Entity Profiles
  - `queries/` with SPARQL files for allowed‑items list hydration
  - `cache/` with the resulting hydrated JSON lists and indexes
- **GKC Entities** are abstract representations of real‑world entities that we want to model and link across platforms
  - GKC Entity Profiles are YAML documents that define entity structure, constraints, references, and SPARQL‑driven allowed‑item lists
  - Entity Profiles are fundamentally based on the Wikibase/Wikidata model but incorporate linkages to other parts of the Global Knowledge Commons; the vision is to get Wikidata right and then share that content out with other platforms
  - Entity Profiles drive both data validation and the presentation of input forms for users

# High‑level rules for reasoning
- Never hallucinate Wikidata JSON structures; always follow the profile.
- Treat YAML profiles as the single source of truth for form generation and validation.
- Keep code modular, atomic, and testable.
- Maintain strict separation between profile definition, modulation, and serialization.
- Never mix UI logic with profile logic.
- Never modify SpiritSafe artifacts without explicit instruction to do so.

# Agent awareness and handoffs
- Custom agents are at work in this workspace with guideline files at `.github/agents`
  - Profile Architect - direct responsibility for the SpiritSafe registry structure, profile schema, documentation, and related functionality in the spirit_safe module
  - Validation Agent - direct responsibility for the validation engine that consumes profiles and performs entity profile validation, entity validation, serialized data validation for shipping, and other related tasks
  - Wizard Engineer - direct responsibility for the user interface components that consume profiles to generate forms, provide user guidance, and perform client‑side validation from the Entity Profiles
- Always be aware of which agent (human or AI) is responsible for the next step in the workflow. When you reach a point where another agent's role begins, produce a concise Handoff Summary that captures only the information that agent needs to proceed. Do not attempt to perform tasks outside your scope. Instead, clearly indicate which agent should take the next step and what inputs they require.

# Interaction expectations
- Prefer small, composable functions.
- Prefer declarative over imperative logic.
- Prefer explicit over inferred behavior.
- Follow the YAML schema strictly. When it doesn't accomplish what's being asked, describe the necessary change and wait for instructions to proceed.

# Documentation guidelines
- Write Markdown for MkDocs (Python-Markdown strict mode), not GitHub-flavored Markdown: always include a blank line before and after bullet/numbered lists, and ensure nested list indentation is consistent.
- Run a final pass to normalize list formatting so all lists render correctly in mkdocs serve.

# Test guidelines
- Always run Python tests from the repo root with poetry run ... so they execute in the project .venv (not the system Python).
- Follow existing test patterns for structure and style; when in doubt, ask for guidance before writing new tests.
- For new features, write tests that cover both expected success cases and edge cases/failure modes