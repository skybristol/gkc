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

# Run pre-merge checks (recommended before PRs)
./scripts/pre-merge-check.sh
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

**Basic Usage:**

```python
from gkc import WikiverseAuth, AuthenticationError

# Method 1: Using environment variables (recommended)
auth = WikiverseAuth()
auth.login()

# Method 2: Using explicit credentials
auth = WikiverseAuth(
    username="YourUsername@BotName",
    password="abc123def456ghi789"
)
auth.login()

# Method 3: Interactive prompt
auth = WikiverseAuth(interactive=True)
auth.login()

# Check login status
if auth.is_logged_in():
    print(f"Logged in as: {auth.get_account_name()}")
    print(f"Bot name: {auth.get_bot_name()}")
```

**Targeting Different Wikimedia Projects:**

```python
# Wikidata (default)
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="wikidata"  # or just omit for default
)
auth.login()

# English Wikipedia
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="wikipedia"
)
auth.login()

# Wikimedia Commons
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="commons"
)
auth.login()

# Custom MediaWiki instance (e.g., enterprise wiki)
auth = WikiverseAuth(
    username="User@Bot",
    password="secret",
    api_url="https://wiki.mycompany.com/w/api.php"
)
auth.login()
```

**Making Authenticated API Requests:**

```python
# After login, use the session for API requests
auth = WikiverseAuth()
auth.login()

# Example: Query user information
response = auth.session.get(auth.api_url, params={
    "action": "query",
    "meta": "userinfo",
    "format": "json"
})
print(response.json())

# For editing, get a CSRF token
try:
    csrf_token = auth.get_csrf_token()
    print(f"CSRF Token: {csrf_token}")
except AuthenticationError as e:
    print(f"Error: {e}")

# When done, logout
auth.logout()
```

**Helper Methods:**

```python
auth = WikiverseAuth(username="Alice@MyBot", password="secret")

# Extract account name
print(auth.get_account_name())  # Output: "Alice"

# Extract bot name
print(auth.get_bot_name())  # Output: "MyBot"

# Check authentication state
print(auth.is_authenticated())  # Has credentials
print(auth.is_logged_in())      # Successfully logged in to API
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

**Wikimedia Projects:**
- `WIKIVERSE_USERNAME` - Bot password username (format: Username@BotName)
- `WIKIVERSE_PASSWORD` - Bot password
- `WIKIVERSE_API_URL` - (Optional) MediaWiki API endpoint. Defaults to Wikidata. Can use shortcuts: "wikidata", "wikipedia", "commons"

**OpenStreetMap:**
- `OPENSTREETMAP_USERNAME` - OpenStreetMap username
- `OPENSTREETMAP_PASSWORD` - OpenStreetMap password

Example:

```bash
# Wikidata (default)
export WIKIVERSE_USERNAME="Alice@MyBot"
export WIKIVERSE_PASSWORD="abc123def456ghi789"

# Wikipedia
export WIKIVERSE_USERNAME="Alice@MyBot"
export WIKIVERSE_PASSWORD="abc123def456ghi789"
export WIKIVERSE_API_URL="wikipedia"

# Custom MediaWiki instance
export WIKIVERSE_USERNAME="Alice@MyBot"
export WIKIVERSE_PASSWORD="abc123def456ghi789"
export WIKIVERSE_API_URL="https://wiki.mycompany.com/w/api.php"

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
