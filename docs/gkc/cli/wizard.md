# Wizard Commands

Plain meaning: Launch the interactive Streamlit curation wizard from the CLI.

## Overview

Use the top-level wizard command to open the guided curation interface for a selected profile.

```bash
gkc wizard --profile Q4 --source local --local-root /path/to/SpiritSafe
```

## Command Reference

### gkc wizard

Launch the interactive wizard.

Required arguments:

- --profile: Profile reference (QID or full profile entity URI)

Optional arguments:

- --qid: Wikidata item ID to edit an existing item
- --packet: Path to a curation packet JSON file for multi-entity workflow
- --depth: Related profile traversal depth when creating a packet on-the-fly (default: 1)
- --source: SpiritSafe source mode (github or local)
- --repo: GitHub repository in owner/name format when using --source github
- --github-ref: Git ref to use with --source github (default: main)
- --local-root: Local SpiritSafe root when using --source local

Examples:

```bash
# Launch from a local SpiritSafe mirror
gkc wizard --profile Q4 --source local --local-root /path/to/SpiritSafe
```

```bash
# Launch and edit an existing item
gkc wizard --profile Q4 --qid Q123 --source local --local-root /path/to/SpiritSafe
```

```bash
# Launch from a prepared packet file
gkc wizard --profile Q4 --packet /tmp/curation_packet.json --source local --local-root /path/to/SpiritSafe
```

## Notes

- The wizard starts a local Streamlit app, typically at http://localhost:8501.
- The command exits when the Streamlit process exits.
- If Streamlit is not installed, install wizard UI dependencies before running this command.

## Related CLI Docs

- [CLI Overview](index.md)
- [Profiles Commands](profiles.md)
