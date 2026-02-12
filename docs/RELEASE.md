# Release Process

This document describes how to plan, version, and publish releases for GKC.

## Versioning Policy

GKC follows semantic versioning.

- Patch ($0.1.x$): bug fixes, small improvements, doc-only changes when publishing a release
- Minor ($0.x.0$): new features, non-breaking API additions
- Major ($1.0.0$): breaking changes or redesigns

Notes:
- Do not bump the version for every commit. Bump only when you are about to publish a release.
- Doc-only changes do not require a PyPI release unless you want a new package build.

## Release Checklist

1) Verify clean working tree
- `git status`

2) Run local checks
- `./scripts/pre-merge-check.sh`

3) Decide version bump
- Update the version in `pyproject.toml`

4) Update release notes
- Add a short summary of changes in the GitHub release notes

5) Commit the version bump
- `git add pyproject.toml`
- `git commit -m "Bump version to X.Y.Z"`

6) Tag the release
- `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- `git push origin vX.Y.Z`

7) Create GitHub release
- Use the GitHub UI or CLI
- Publishing the release triggers PyPI publishing via GitHub Actions

8) Verify PyPI
- `pip install --upgrade gkc`
- Check https://pypi.org/project/gkc/

## Example

```bash
# Update version in pyproject.toml
# version = "0.1.1"

git add pyproject.toml
git commit -m "Bump version to 0.1.1"

# Tag and push
git tag -a v0.1.1 -m "Release v0.1.1"
git push origin v0.1.1

# Create GitHub release (if you have gh CLI installed)
gh release create v0.1.1 \
  --title "v0.1.1" \
  --notes "Short summary of changes"
```

## Notes on Documentation-Only Changes

If you only update documentation and you do not need a new package build:
- Skip the version bump
- Skip tagging and release
- Let GitHub Pages publish documentation updates

If you want a new package release for documentation updates:
- Follow the standard checklist and bump the patch version

## Troubleshooting

- If `poetry lock` fails, run `poetry lock --no-update` to sync the lockfile
- If `gh` is not installed, create the release in the GitHub web UI
- If PyPI publish fails, check the GitHub Actions logs and PyPI Trusted Publishing settings
