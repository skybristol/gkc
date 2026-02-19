# Project Overview
The GKC python package supports a data integration workflow that transforms raw data from various sources into linked open data distributed across systems like Wikidata, Wikimedia Commons, Wikipedia, and OpenStreetMap. The project uses a distillery metaphor to describe its architecture and processes.

## Who's who
- Architect: Sky
- Engineer: Copilot (with oversight and guidance from Sky)

## Protocol
- The architect will create issues in GitHub to outline specific tasks or features to be developed, along with any necessary context or requirements.
- The architect will start work on an issue by creating a new branch.
- The architect may ask the engineer to evaluate the issue by reading the issue description and any related documentation, and then writing a response comment in the GitHub issue with their understanding of the task and any questions or clarifications needed. (Note: GitHub issues and pull request comments are a primary channel for communication and documentation of design decisions in this project, so it's important to use them consistently and effectively.)
- The architect will review the approach and provide feedback or additional guidance as needed with further comments in the GitHub issue before the engineer begins writing code.
- The architect will ask the engineer to write code for the issue, and the engineer will write code in the branch created for that issue, following the guidance and requirements outlined in the issue description and any related documentation.
- The engineer will write code that is clear, maintainable, and well-documented, following the coding style and architectural patterns established in the project.
- The engineer will write tests for the code they create, ensuring that the code is robust and that functionality is verified.
- The engineer will run tests frequently during development to catch issues early, and will use the provided pre-merge check script to run all CI checks locally to resolve as many issues as possible before handoff to the architect.
- The engineer will include documentation in their workflow with both docstrings in the code and markdown files in the `/docs/gkc/` directory as appropriate.
- The engineer will follow up from work completed with a comment in the GitHub issue describing what was done, any issues encountered, and any questions or concerns that remain.
- The architect will review the code, tests, and documentation written by the engineer, providing feedback in the GitHub issue and requesting changes as needed to ensure that the code meets the project's standards for quality and maintainability.
- Once the code is approved, the architect will merge the branch into the main codebase, and delete the branch.

### Code Quality Standards
- The engineer will use the provided pre-merge check script frequently during development (after each major component, not just at the end)
- The engineer will prioritize mypy type checking and aim for zero type errors in new code
- Type annotations should be included in initial code, not added as an afterthought
- The engineer will verify code imports and runs without syntax errors before committing
- When writing new functions/classes, examine existing patterns in the codebase for consistency in typing and style

### Development Workflow Checkpoint
Before considering work complete:
1. Run `./scripts/pre-merge-check.sh` and ensure all checks pass
2. Do not commit code that produces mypy errors
3. If type errors exist, investigate the root cause

### Escalation Checkpoints
The engineer should escalate to the architect if any of these conditions are met:

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
- Include links to existing code patterns to follow
- Specify which files/components will be modified
- Estimate scope (touching N files suggests scope creep if it grows)

## Software Design Guidelines (for Engineer)
- Always produce both library and CLI compatible infrastructure when implementing new features
- Follow existing code patterns for consistency in style and architecture
- Prioritize type safety and maintainability over quick fixes
- Write tests that are robust and cover edge cases, not just the happy path
- Document code with clear docstrings and maintain up-to-date API documentation in `/docs/gkc`