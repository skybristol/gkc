# Project Overview
The GKC python package supports a data integration workflow that transforms raw data from various sources into linked open data distributed across systems like Wikidata, Wikimedia Commons, Wikipedia, and OpenStreetMap. The project uses a distillery metaphor to describe its architecture and processes.

## Who's who
- Architect: Sky
- Engineer: Copilot (with oversight and guidance from the Architect)

## Protocol
1. The Architect will start work toward a new feature by creating a collaborative design document under `.dev`.
2. Before getting started on code, the Architect will ask the Engineer to collaborate on building out the design document under `.dev` that follows a basic template.
3. The Architect and Engineer will track their work and design decisions made in the working development file.
4. The Architect will respond to specific questions on the plans submitted by the Engineer in the dev document, create a branch for the work, and direct the Engineer on when they can proceed with writing code.
5. The Engineer will write code in the development branch following the guidance and requirements outlined in the working development document and any related documentation.
6. The Engineer will follow up from work completed with a summary of what was done, any issues encountered, any questions or concerns that remain, and a reasonable commit message all written to the dev document.
7. The Architect will review the code, tests, and documentation written by the Engineer, providing feedback on the dev document and requesting changes as needed to ensure that the code meets the project's standards for quality and maintainability.
8. Once the code is approved, the Architect will post the documentation from the dev document in a pull request, review CI workflow status, and merge the branch into the main codebase, and delete the branch.

### Code Quality Standards
- The Engineer will use the provided pre-merge check script frequently during development (after each major component, not just at the end)
- The Engineer will prioritize mypy type checking and aim for zero type errors in new code
- Type annotations should be included in initial code, not added as an afterthought
- The Engineer will verify code imports and runs without syntax errors before committing
- When writing new functions/classes, examine existing patterns in the codebase for consistency in typing and style

### Documentation Guidelines

- Use the standard Python package documentation structure: Overview → Examples → API Reference → CLI Reference → Notes.
- Every public function/class must include: purpose, parameters, return values, side effects, error conditions, and at least one real-world example.
- Every CLI command must include: description, usage block, flags/options, and two examples (minimal + realistic).
- Document the Python API first, then the CLI as a thin wrapper.
- Each module should begin with a high-level description and a list of its main functions.
- Prefer task-oriented examples using realistic Wikidata data.
- All public functionality must be documented; no undocumented parameters or return types.
- Keep documentation concise, explicit, and example-driven.
- Add “See also” links between related modules and commands.

### Development Workflow Checkpoint
Before considering work complete:
1. Run `./scripts/pre-merge-check.sh` and ensure all checks pass
2. Do not commit code that produces mypy errors
3. If type errors exist, investigate the root cause

### Escalation Checkpoints
The Engineer should escalate to the Architect if any of these conditions are met:

**1. Pre-Merge Check Failures (after each component):**
- More than 10 mypy errors in new/modified code
- More than 5 consecutive failed test runs on the same component
- Ruff/Black failures that can't be resolved with auto-fix
- *Action:* Stop, commit current state, and describe the issue in GitHub

**2. Complexity Growth:**
- A task that was estimated as "small" is now touching >5 files
- Need to refactor existing code extensively to support new code (suggests wrong approach)
- Generated code is >1.5x the size of existing analogous code in the project
- *Action:* Pause and review approach with architect before continuing

**3. Iterative Failure Pattern:**
- The same test fails for >3 attempts with different fixes
- Same mypy error re-appears after being "fixed" in a different way
- Fix for one issue creates errors in previously passing code
- *Action:* This signals fundamental misunderstanding; escalate before proceeding

**4. Type Safety Regression:**
- Adding new code reduces the mypy pass rate of the module
- Spreading `Any` types instead of improving specificity
- Adding `# type: ignore` comments as a workaround
- *Action:* Do not commit; investigate root cause with architect

**5. Testing Coverage:**
- New code has <60% test coverage
- Tests pass but don't actually exercise new code paths
- *Action:* Expand tests or escalate if coverage is legitimately difficult

**6. Documentation Debt:**
- New functions lack docstrings or have minimal ones
- No API documentation added to `/docs/gkc/`
- Type hints are unclear or use `Any` without explanation
- *Action:* Complete documentation before marking as ready

## Issue Design Guidelines (for Architect)
Each issue should:
- Have a single, clearly defined goal
- List explicit success criteria (X tests pass, Y mypy errors resolved, etc.)
- Include notional usage patterns for API and or CLI commands
- Include links to existing code patterns to follow
- Specify which files/components will be modified
- Estimate scope (touching N files suggests scope creep if it grows)

## Software Design Guidelines (for Engineer)
- Always produce both library and CLI compatible infrastructure when implementing new features
- Follow existing code patterns for consistency in style and architecture
- Prioritize type safety and maintainability over quick fixes
- Write tests that are robust and cover edge cases, not just the happy path
- Document code with clear docstrings and maintain up-to-date API documentation in `/docs/gkc/api` along with CLI documentation in `/docs/gkc/cli`
- Use GitHub issues and comments to document design decisions and questions, rather than relying on external communication channels