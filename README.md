# GKC - Global Knowledge Commons

[![CI](https://github.com/skybristol/gkc/workflows/CI/badge.svg)](https://github.com/skybristol/gkc/actions)
[![PyPI version](https://img.shields.io/pypi/v/gkc.svg)](https://pypi.org/project/gkc/)
[![Python Versions](https://img.shields.io/pypi/pyversions/gkc.svg)](https://pypi.org/project/gkc/)

The "Global Knowledge Commons" is a term of art describing the de facto confederation of community built and maintained data, information and knowledge assets freely available online for anyone to use and contribute to. These include Wikipedia, Wikidata, Wikimedia Commons (and other parts of the "Wikiverse") along with OpenStreetMap for mapping data and services. This project is motivated by a desire to make the process of contributing accurate and usable data and information to these assets as seamless and error free as possible. This Python package is designed to provide a full working suite of capabilities for contributing to the Commons in a robust and documented fashion. Read more in the [deployed documentation](https://skybristol.github.io/gkc).

## Features

- 🔐 Authentication support for Wikidata (and other Wikimedia projects) and OpenStreetMap
- 🌍 Easy-to-use interface for Global Knowledge Commons services
- 📦 Built with Poetry for modern Python development
- ✅ Comprehensive test coverage
- 🚀 CI/CD with GitHub Actions

## Installation

### Using pip

```bash
pip install gkc
```

### Using Poetry

```bash
poetry add gkc
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/skybristol/gkc.git
cd gkc

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Run pre-merge checks (recommended before PRs)
./scripts/pre-merge-check.sh
```

## Quick Start

For detailed usage instructions, see the [full documentation](https://skybristol.github.io/gkc).

### Authentication

GKC provides authentication for Wikidata (and other Wikimedia projects) and OpenStreetMap:

```python
from gkc import WikiverseAuth

# Using environment variables (recommended)
auth = WikiverseAuth()
auth.login()

# Check login status
if auth.is_logged_in():
    print(f"Logged in as: {auth.get_account_name()}")
```

See the [Authentication Guide](https://skybristol.github.io/gkc/authentication/) for complete setup instructions, including:

- Setting up bot passwords for Wikimedia projects
- Targeting different Wikimedia sites (Wikidata, Wikipedia, Commons)
- OpenStreetMap authentication
- Using environment variables
- Security best practices

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=gkc --cov-report=html

# Run specific test file
poetry run pytest tests/test_auth.py
```

### Code Quality

```bash
# Format code with Black
poetry run black gkc tests

# Lint with Ruff
poetry run ruff check gkc tests

# Type checking with mypy
poetry run mypy gkc
```

### Building the Package

```bash
# Build distribution packages
poetry build

# The built packages will be in the dist/ directory
```

## Publishing to PyPI

The package is configured to automatically publish to PyPI when a new release is created on GitHub. The workflow uses PyPI's trusted publisher feature for secure authentication.

### Manual Publishing (if needed)

```bash
# Build the package
poetry build

# Publish to PyPI
poetry publish
```

## CI/CD

The project uses GitHub Actions for continuous integration and deployment:

- **CI Workflow**: Runs on every push and pull request
  - Tests on Python 3.9, 3.10, 3.11, and 3.12
  - Runs linting (Ruff), formatting (Black), and type checking (mypy)
  - Runs test suite with coverage reporting
  
- **Publish Workflow**: Runs on release creation
  - Builds the package
  - Publishes to PyPI using PyPI Trusted Publishing (OIDC)

**Before merging or creating a PR**, run the pre-merge checks:
```bash
./scripts/pre-merge-check.sh
```

See [CI/CD Documentation](docs/CI_CD.md) for detailed setup instructions and release process.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. **Run pre-merge checks**: `./scripts/pre-merge-check.sh`
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Wikidata community
- Wikipedia community
- OpenStreetMap community
