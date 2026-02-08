# GKC - Global Knowledge Commons

[![CI](https://github.com/skybristol/gkc/workflows/CI/badge.svg)](https://github.com/skybristol/gkc/actions)
[![PyPI version](https://badge.fury.io/py/gkc.svg)](https://badge.fury.io/py/gkc)
[![Python Versions](https://img.shields.io/pypi/pyversions/gkc.svg)](https://pypi.org/project/gkc/)

A Python package for working in the Global Knowledge Commons, including Wikidata, Wikipedia, and OpenStreetMap.

## Features

- 🔐 Authentication support for Wikidata, Wikipedia, and OpenStreetMap
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
```

## Usage

### Authentication

The package provides authentication classes for Global Knowledge Commons services. You can provide credentials directly, via environment variables, or through interactive prompts.

#### Wikiverse (Wikidata, Wikipedia, Wikimedia Commons)

The `WikiverseAuth` class provides unified authentication for all Wikimedia projects using **bot passwords**. The same credentials work across Wikidata, Wikipedia, and Wikimedia Commons due to Wikimedia's Single User Login (SUL) system.

**Setting up Bot Passwords:**

1. Go to [Special:BotPasswords](https://www.wikidata.org/wiki/Special:BotPasswords) on Wikidata
2. Create a new bot password with appropriate permissions
3. Your username will be in the format `YourUsername@BotName`
4. Save the generated password (you won't see it again!)

**Using WikiverseAuth:**

```python
from gkc import WikiverseAuth

# Method 1: Using explicit credentials (bot password format)
auth = WikiverseAuth(
    username="YourUsername@BotName",
    password="abc123def456ghi789"
)

# Method 2: Using environment variables (WIKIVERSE_USERNAME, WIKIVERSE_PASSWORD)
auth = WikiverseAuth()

# Method 3: Interactive prompt
auth = WikiverseAuth(interactive=True)

# Check authentication status
if auth.is_authenticated():
    print(f"Authenticated as: {auth.get_account_name()}")
    print(f"Bot name: {auth.get_bot_name()}")
```

**Helper Methods:**

```python
auth = WikiverseAuth(username="Alice@MyBot", password="secret")

# Extract account name
print(auth.get_account_name())  # Output: "Alice"

# Extract bot name
print(auth.get_bot_name())  # Output: "MyBot"
```

#### OpenStreetMap

```python
from gkc import OpenStreetMapAuth

# Method 1: Using explicit credentials
auth = OpenStreetMapAuth(username="your_username", password="your_password")

# Method 2: Using environment variables (OPENSTREETMAP_USERNAME, OPENSTREETMAP_PASSWORD)
auth = OpenStreetMapAuth()

# Method 3: Interactive prompt
auth = OpenStreetMapAuth(interactive=True)

# Check authentication status
if auth.is_authenticated():
    print("Authenticated successfully!")
```

### Environment Variables

You can set the following environment variables for automatic authentication:

- `WIKIVERSE_USERNAME` and `WIKIVERSE_PASSWORD` for Wikimedia projects (Wikidata, Wikipedia, Wikimedia Commons)
- `OPENSTREETMAP_USERNAME` and `OPENSTREETMAP_PASSWORD` for OpenStreetMap

Example:

```bash
# Bot password format: Username@BotName
export WIKIVERSE_USERNAME="Alice@MyBot"
export WIKIVERSE_PASSWORD="abc123def456ghi789"

# OpenStreetMap
export OPENSTREETMAP_USERNAME="your_osm_username"
export OPENSTREETMAP_PASSWORD="your_osm_password"
```

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
  - Publishes to PyPI using trusted publishing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Wikidata community
- Wikipedia community
- OpenStreetMap community
