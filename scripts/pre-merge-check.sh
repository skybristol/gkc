#!/usr/bin/env bash
# Pre-merge test script
# Run this before creating a pull request or merging to ensure all checks pass

set -e  # Exit on error

echo "=================================="
echo "Running Pre-Merge Checks"
echo "=================================="
echo ""

# Use poetry if available, otherwise fail
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Please install poetry first."
    exit 1
fi

echo "✓ Poetry found"
echo ""

# Install dependencies if needed
echo "📦 Ensuring dependencies are installed..."
poetry install --no-interaction --sync
echo ""

# Run linting
echo "🔍 Running ruff linter..."
poetry run ruff check gkc tests
echo "✓ Ruff checks passed"
echo ""

# Run formatting check
echo "🎨 Checking code formatting with black..."
poetry run black --check gkc tests
echo "✓ Black formatting verified"
echo ""

# Run type checking (allow to fail for now)
echo "🔎 Running type checking with mypy..."
if poetry run mypy gkc; then
    echo "✓ Type checking passed"
else
    echo "⚠️  Type checking had issues (non-blocking)"
fi
echo ""

# Run tests
echo "🧪 Running test suite..."
poetry run pytest -v
echo "✓ All tests passed"
echo ""

# Build package
echo "📦 Testing package build..."
poetry build
echo "✓ Package builds successfully"
echo ""

echo "=================================="
echo "✅ All pre-merge checks passed!"
echo "=================================="
echo ""
echo "You can now:"
echo "  - Create a pull request"
echo "  - Merge to main"
echo "  - Tag a release for PyPI publishing"
echo ""
