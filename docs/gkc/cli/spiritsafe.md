# SpiritSafe CLI

Plain meaning: Build SpiritSafe-maintained support artifacts from local cache content.

## Overview

The `gkc spiritsafe` command group manages generated artifacts that live alongside the SpiritSafe cache.

If you need the concept before the commands, see [Semantic Anchors](../../architecture/meta-wikibase/semantic-anchors.md).

Current subcommands:

- `gkc spiritsafe sitelinks sync-wikimedia-sites`
- `gkc spiritsafe semantic-anchors build`
- `gkc spiritsafe semantic-anchors validate`

These routes are oriented toward local SpiritSafe maintenance workflows.

## `gkc spiritsafe sitelinks sync-wikimedia-sites`

Fetch the Wikimedia sitematrix and write the SpiritSafe sitelink source artifact.

```bash
gkc spiritsafe sitelinks sync-wikimedia-sites --source local --local-root /path/to/SpiritSafe
```

Common options:

- `--source-url`: Wikimedia sitematrix URL.
- `--timeout`: HTTP timeout in seconds.
- `--user-agent`: User-Agent string for the sitematrix request.
- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.
- `-o`, `--output`: Optional output path. By default this writes to `partners/wikimedia_sites.json` under the local SpiritSafe root.

## `gkc spiritsafe semantic-anchors build`

Build the SpiritSafe semantic anchor artifact from local cache entities.

This command materializes the runtime lookup document that binds internal ontology names such as `_entity_profile` or `_has_statement` to the concrete IDs currently present in the SpiritSafe-backed Meta-Wikibase cache.

```bash
gkc spiritsafe semantic-anchors build --source local --local-root /path/to/SpiritSafe
```

Common options:

- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.
- `-o`, `--output`: Optional output path. By default this writes to `config/semantic_anchors.json` under the local SpiritSafe root, unless a workflow overrides it.

## `gkc spiritsafe semantic-anchors validate`

Validate a semantic-anchor artifact against the package-owned Meta-Wikibase contract.

Use this when you need to confirm that the generated artifact still matches the ontology backbone expected by `gkc` runtime consumers.

Validate a specific artifact file:

```bash
gkc spiritsafe semantic-anchors validate --artifact-file /path/to/semantic_anchors.json
```

Validate the default artifact in a local SpiritSafe checkout and compare it to a freshly rebuilt cache-derived document:

```bash
gkc spiritsafe semantic-anchors validate --local-root /path/to/SpiritSafe --check-current-cache
```

Common options:

- `--artifact-file`: Path to an existing semantic-anchor JSON artifact.
- `--local-root`: Local SpiritSafe root. When `--artifact-file` is omitted, the command defaults to `config/semantic_anchors.json` under this root.
- `--check-current-cache`: Rebuild the current semantic-anchor document from `still/entities` and compare it to the artifact being validated.

This command checks the runtime contract only:

- required internal semantic anchors are present
- property anchors resolve to property IDs and carry the expected datatype
- item anchors resolve to item IDs
- the artifact shape is valid

When `--check-current-cache` is used, stale-artifact drift against current cache-derived anchors is also reported.

## Related Commands

- `gkc profile export-json`
- `gkc profile value-lists hydrate`
- `gkc packet build`
