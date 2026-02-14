# CI/CD Configuration

This document describes the continuous integration and deployment setup for the GKC project.

## Overview

The project uses GitHub Actions for CI/CD with two main workflows:
1. **CI Workflow** - Runs tests, linting, and type checking on every PR and push to main
2. **Publish Workflow** - Automatically publishes to PyPI when a GitHub release is created

## Local Pre-Merge Testing

### Quick Check

Before pushing or creating a PR, run the pre-merge check script:

```bash
./scripts/pre-merge-check.sh
```

This script will:
- ✓ Install/sync dependencies
- ✓ Run ruff linting
- ✓ Check code formatting (black)
- ✓ Run type checking (mypy)
- ✓ Execute full test suite
- ✓ Verify package builds

### Manual Testing

You can also run individual checks:

```bash
# Install dependencies
poetry install --sync

# Run linting
poetry run ruff check gkc tests

# Check formatting
poetry run black --check gkc tests

# Auto-fix formatting
poetry run black gkc tests

# Run type checking
poetry run mypy gkc

# Run tests
poetry run pytest -v

# Run tests with coverage
poetry run pytest --cov=gkc --cov-report=html

# Build package
poetry build
```

## CI Workflow (`.github/workflows/ci.yml`)

### Triggers

- Push to `main` branch
- Pull requests targeting `main` branch

### Jobs

#### Test Matrix

Runs tests on multiple Python versions:
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

**Steps:**
1. Checkout code
2. Set up Python
3. Install Poetry
4. Cache dependencies
5. Install dependencies
6. Run linting (ruff)
7. Check formatting (black)
8. Run type checking (mypy) - non-blocking
9. Run tests with coverage
10. Upload coverage to Codecov (optional)

#### Lint Job

Runs on Python 3.12 to verify code quality:
- Ruff linting
- Black formatting check

### Success Criteria

All tests must pass across all Python versions for the workflow to succeed. This ensures:
- Code works on all supported Python versions
- Code style is consistent
- All tests pass
- No import errors

## Publish Workflow (`.github/workflows/publish.yml`)

### Trigger

Automatically runs when you **create and publish a GitHub release**.

### Publishing Method: PyPI Trusted Publishing

The workflow uses **PyPI Trusted Publishing** (OIDC), which is the modern, secure way to publish packages. This method:
- ✅ No API tokens needed
- ✅ More secure (temporary credentials)
- ✅ Automatic rotation
- ✅ Recommended by PyPI

### Setup Required

Before your first release, you must configure Trusted Publishing on PyPI:

1. **Create PyPI account** (if you don't have one):
   - Go to https://pypi.org/account/register/

2. **Configure Trusted Publishing**:
   - Go to https://pypi.org/manage/account/publishing/
   - Click "Add a new pending publisher"
   - Fill in:
     - **PyPI Project Name**: `gkc`
     - **Owner**: `skybristol`
     - **Repository name**: `gkc`
     - **Workflow name**: `publish.yml`
     - **Environment name**: (leave blank)
   - Click "Add"

3. **Important**: You must do this **before** creating your first release. PyPI will reserve the project name for your GitHub repository.

### Alternative: Token-Based Publishing

If you prefer using a token (though Trusted Publishing is recommended), modify `.github/workflows/publish.yml`:

```yaml
- name: Publish package distributions to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    password: ${{ secrets.PYPI_TOKEN }}
```

And remove the `permissions: id-token: write` line.

## Creating a Release

### 1. Prepare the Release

```bash
# Ensure you're on main with latest changes
git checkout main
git pull origin main

# Run pre-merge checks
./scripts/pre-merge-check.sh

# Update version in pyproject.toml
# Edit: version = "0.1.1"  (or whatever the new version is)

# Commit version bump
git add pyproject.toml
git commit -m "Bump version to 0.1.1"
git push origin main
```

### 2. Create Git Tag

```bash
# Create and push tag
git tag -a v0.1.1 -m "Release version 0.1.1"
git push origin v0.1.1
```

### 3. Create GitHub Release

**Option A: GitHub Web UI**
1. Go to https://github.com/skybristol/gkc/releases/new
2. Choose the tag you just created (`v0.1.1`)
3. Set release title (e.g., "v0.1.1")
4. Add release notes describing changes
5. Click "Publish release"

**Option B: GitHub CLI**
```bash
gh release create v0.1.1 \
  --title "v0.1.1" \
  --notes "Release notes here"
```

### 4. Automated Publishing

Once you publish the release:
1. GitHub Actions automatically triggers the publish workflow
2. Workflow builds the package
3. Package is published to PyPI
4. Within minutes, available via `pip install gkc`

### 5. Verify Publication

Check that the package is available:
```bash
# Wait a few minutes after release
pip install --upgrade gkc

# Or check PyPI directly
open https://pypi.org/project/gkc/
```

## Monitoring Workflows

### View Workflow Runs

- **All workflows**: https://github.com/skybristol/gkc/actions
- **CI runs**: https://github.com/skybristol/gkc/actions/workflows/ci.yml
- **Publish runs**: https://github.com/skybristol/gkc/actions/workflows/publish.yml

### Debugging Failed Workflows

If a workflow fails:

1. **Click on the failed run** in GitHub Actions
2. **Expand the failed step** to see error details
3. **Common issues**:
   - Test failures: Check test output
   - Linting errors: Run `poetry run ruff check gkc tests`
   - Formatting issues: Run `poetry run black gkc tests`
   - Build errors: Run `poetry build` locally
   - PyPI publish errors: Check Trusted Publishing configuration

4. **Fix locally and re-push**:
   ```bash
   # Fix the issue
   ./scripts/pre-merge-check.sh  # Verify fix
   git add .
   git commit -m "Fix CI issue"
   git push
   ```

## Version Management

### Semantic Versioning

Follow semantic versioning (semver):
- **MAJOR** (1.0.0): Breaking changes
- **MINOR** (0.1.0): New features, backwards compatible
- **PATCH** (0.0.1): Bug fixes, backwards compatible

### Pre-releases

For testing releases before official publication:

```bash
# Update version to pre-release
# version = "0.2.0-alpha.1"

# Create pre-release tag
git tag -a v0.2.0-alpha.1 -m "Alpha release"
git push origin v0.2.0-alpha.1

# Create GitHub pre-release
gh release create v0.2.0-alpha.1 \
  --title "v0.2.0-alpha.1" \
  --notes "Alpha release for testing" \
  --prerelease
```

Pre-releases won't be installed by default with `pip install gkc`, users must specify:
```bash
pip install gkc==0.2.0-alpha.1
```

## Security

### Secrets

Current repository secrets:
- `PYPI_TOKEN` - Not needed if using Trusted Publishing, but kept as backup

### Permissions

The publish workflow requires:
- `id-token: write` - For Trusted Publishing authentication

## Troubleshooting

### "Package already exists on PyPI"

If you try to publish a version that already exists:
1. Delete the GitHub release
2. Delete the git tag: `git tag -d v0.1.0 && git push origin :refs/tags/v0.1.0`
3. Bump version in pyproject.toml
4. Create new tag and release

### "Trusted Publisher not configured"

Error: `403: The user 'xxx' isn't allowed to upload to project 'gkc'`

**Solution**: Configure Trusted Publishing on PyPI (see "Setup Required" above)

### "Tests pass locally but fail in CI"

Common causes:
- Python version differences (CI tests on 3.9-3.12)
- Missing dependencies in pyproject.toml
- Environment-specific code

**Debug**:
```bash
# Test on specific Python version
poetry env use 3.9
poetry install
poetry run pytest
```

## Best Practices

1. **Always run pre-merge checks** before pushing
2. **Never commit directly to main** - use PRs for review
3. **Write meaningful commit messages** following conventional commits
4. **Update CHANGELOG** for each release
5. **Test the package** after publishing: `pip install --upgrade gkc`
6. **Monitor CI results** - fix failures immediately
7. **Keep dependencies updated** - run `poetry update` regularly

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [PyPI Trusted Publishing Guide](https://docs.pypi.org/trusted-publishers/)
- [Poetry Publishing Documentation](https://python-poetry.org/docs/libraries/#publishing-to-pypi)
- [Semantic Versioning](https://semver.org/)
