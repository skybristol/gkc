# High‑level rules for reasoning
- Never hallucinate Wikidata JSON structures; always follow the profile.
- Keep code modular, atomic, and testable.
- Maintain strict separation between profile definition, modulation, and serialization.
- Never modify SpiritSafe artifacts directly. These are built with `gkc` code and GitHub CI.
- Do not build code for backwards compatibility unless explicitly instructed to do so; we are in a greenfield development phase and can iterate quickly without maintaining legacy support.
- Do not edit or create code in Python notebooks unless explicitly instructed to do so; notebooks are for experimentation and prototyping, not for production code.
- Always document your reasoning and design decisions in GitHub issues and PRs to maintain a clear record of the development process and facilitate future contributions.
- When we head down a major refactor path that is going to impact things throughout the codebase, do a thorough review to identify all those areas and document in the GitHub issue(s) we are working on so that we can keep track of the scope and ensure we are updating all relevant parts of the codebase. We might clean up immediately or in the next PR, but we want to make sure we have a clear record of all the areas that are impacted by the refactor and that we are not leaving any loose ends behind.

# Curation philosophy (Wikidata-first, enablement-first)
- We are fundamentally aligned with Wikidata modality and the Freebase-inspired model: curators use judgment in modeling choices while the system provides strong guidance.
- Product intent is enablement over constraint. Design profile and wizard behavior to make better choices obvious and fast, not to over-restrict valid expert workflows.
- Wizard UX exists to reduce friction versus open-ended manual item/claim creation across multiple interfaces; it should accelerate high-quality curation without hiding model expressiveness.
- Focused lookup lists and pre-hydrated allowed-item sets are guidance tools for speed and consistency, not hard-coded conceptual limits unless explicitly required by profile semantics.

# Communication Style and Output Density
- Default to concise responses. Target brief, decision-oriented summaries unless the user explicitly asks for deep detail.
- Use this response pattern by default:
1. Outcome in one to three lines.
2. Key points in up to five bullets.
3. Optional next actions in up to three numbered items.
- Avoid long narrative explanations, repeated context, and broad restatements of prior decisions.
- If a response exceeds roughly 12 lines, include a one-line summary first.
- Ask before expanding: if additional design depth would materially help, ask whether to provide a deep dive instead of sending it automatically.
- Prefer concrete deltas over full rewrites of plans.
- When discussing architecture or process, separate now versus later:
  - Now: what is actionable this sprint.
  - Later: park as a short backlog note.

# Module Contracts
- Pay close attention to and regularly update the module contracts in the documentation. These are the source of truth for how different parts of the system interact and what assumptions they can make about each other. If you find yourself needing to know internal details of another module to do your work, that's a sign that the contract needs to be updated to expose the necessary information or functionality.
- When updating module contracts, consider the impact on all modules that interact with it and ensure that the new contract still allows for modularity and separation of concerns. Avoid creating tight coupling between modules through the contract; instead, aim for clear interfaces that allow for independent development and testing.
- This is a complicated codebase with a lot of moving parts, so the module boundaries should be clear and apply to both public code and internal utilities so that future contributors know where to go to deal with an issue or introduce a new feature. If you find that the module boundaries are not clear or that there is a lot of cross-module interaction that is not well-documented, that's a sign that the module structure may need to be re-evaluated.

# Interaction expectations
- Prefer small, composable functions.
- Prefer declarative over imperative logic.
- Prefer explicit over inferred behavior.

# Documentation guidelines
- Write Markdown for MkDocs (Python-Markdown strict mode), not GitHub-flavored Markdown: always include a blank line before and after bullet/numbered lists, and ensure nested list indentation is consistent.
- Run a final pass to normalize list formatting so all lists render correctly in mkdocs serve.
- When writing official documentation during development work, do not reference things like "Phase 1" or other internal process terms that are not relevant to the end user. Instead, write documentation as if the final product is already complete and these internal phases never existed.
- We're at a point in documentation where things are pretty good and comprehensive, so we need to be vigilant about keeping this up to date as we introduce new functionality or change things so we don't drift off course. If you find that the documentation is not clear or is missing important information, that's a sign that it needs to be updated to reflect the current state of the codebase and the intended usage of the system.

# Test guidelines
- Always run Python tests from the repo root with poetry run ... so they execute in the project .venv (not the system Python).
- Follow existing test patterns for structure and style; when in doubt, ask for guidance before writing new tests.
- For new features, write tests that cover both expected success cases and edge cases/failure modes
- Write testing and other temporary output to /tmp or other non‑repo locations to avoid cluttering the project directory. Do not write test output to the repo unless explicitly instructed to do so.

# GitHub CLI reliability guidelines
- Never use heredocs (`<<EOF`, `<<'EOF'`, etc.) in any terminal command. Never generate multi‑line shell input blocks. These fail in VS Code terminals and break GitHub CLI commands.
- Instead use file-based bodies for `gh` commands such as commit messages that include multi-line content. Example pattern: write content to `/tmp/<name>.md` and use `--body-file`.
- Keep shell command text ASCII-only when possible; put Unicode content in files passed via `--body-file`.
- Prefer one command per terminal invocation for GitHub actions; avoid chaining long `gh` calls in a single command.
- If terminal parsing looks corrupted, stop and retry with a fresh, minimal command using `--body-file`.