# SpiritSafe CLI

Plain meaning: Build SpiritSafe-maintained support artifacts from local cache content.

## Overview

The `gkc spiritsafe` command group manages generated artifacts that live alongside the SpiritSafe cache.

Current subcommands:

- `gkc spiritsafe manifest build`
- `gkc spiritsafe sitelinks sync-wikimedia-sites`
- `gkc spiritsafe semantic-anchors build`

These routes are oriented toward local SpiritSafe maintenance workflows.

## `gkc spiritsafe manifest build`

Build `cache/manifest.json` from local SpiritSafe artifacts.

```bash
gkc spiritsafe manifest build --source local --local-root /path/to/SpiritSafe
```

Write the manifest to a specific path:

```bash
gkc spiritsafe manifest build --source local --local-root /path/to/SpiritSafe --output /tmp/manifest.json
```

Common options:

- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.
- `-o`, `--output`: Optional output path for the manifest JSON file.

This command is primarily useful in local maintenance mode, where the generated manifest is written back into the SpiritSafe artifact tree.

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
- `-o`, `--output`: Optional output path. By default this writes to `cache/config/wikimedia_sites.json` under the local SpiritSafe root.

## `gkc spiritsafe semantic-anchors build`

Build the SpiritSafe semantic anchor artifact from local cache entities.

```bash
gkc spiritsafe semantic-anchors build --source local --local-root /path/to/SpiritSafe
```

Common options:

- `--source`: Source override, either `github` or `local`.
- `--local-root`: Local SpiritSafe root when using `--source local`.
- `--repo`: GitHub repository slug when using `--source github`.
- `--ref`: Git ref when using `--source github`.
- `-o`, `--output`: Optional output path. By default this writes to `cache/config/semantic_anchors.json` under the local SpiritSafe root, unless a workflow overrides it.

## Related Commands

- `gkc profile export-json`
- `gkc profile value-lists hydrate`
- `gkc packet build`
