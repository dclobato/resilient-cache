# Resilient Cache - Installation and First Steps

## Project Structure

```
resilient-cache/
├── src/
│   └── resilient_cache/      # Package source code
│       ├── __init__.py       # Public exports
│       ├── app_cache.py      # Abstract cache interface
│       ├── cache_service.py  # Core service (framework-agnostic)
│       ├── flask_integration.py # Optional Flask integration
│       ├── cache_factory.py  # Cache factory
│       ├── two_level_cache.py # L1+L2 implementation
│       ├── circuit_breaker.py # Circuit breaker pattern
│       ├── exceptions.py     # Custom exceptions
│       ├── config/           # Configuration dataclasses
│       └── backends/         # L1/L2 backends
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── examples/                 # Usage examples
├── pyproject.toml            # Project configuration
├── README.md                 # Main documentation
├── LICENSE                   # MIT license
├── CHANGELOG.md              # Release history
├── CONTRIBUTING.md           # Contributing guide
├── Makefile                  # Task automation (Linux/macOS)
└── Makefile.windows          # Task automation (Windows)
```

## Development Installation

### 1) Sync Dependencies with uv

```bash
cd resilient-cache
```

### 2) Install Dependencies

```bash
# Core install
uv sync

# Flask integration
uv sync --extra flask

# L1 support (cachetools)
uv sync --extra l1

# L2 support (Redis/Valkey)
uv sync --extra l2

# Full install (Flask + L1 + L2)
uv sync --extra full

# Development (pytest, mypy, etc)
uv sync --extra dev
```

### 3) Run Tests

```bash
# Basic tests
uv run pytest

# Coverage
uv run pytest --cov=resilient_cache --cov-report=html

# Or use the Makefile
uv run make test
uv run make test-cov
```

### 4) Code Quality Checks

```bash
# Formatting
uv run make format

# Linting
uv run make lint

# Type checking
uv run make type-check

# All checks
uv run make check
```

## Testing the Package Locally

### Example 1: Non-Flask Usage

Create `test_local.py`:

```python
from resilient_cache import CacheFactoryConfig, CacheService

config = CacheFactoryConfig(
    l2_host="localhost",
    l2_port=6379,
)

cache_service = CacheService(config)

cache = cache_service.create_cache(
    l2_key_prefix="test",
    l2_ttl=300,
    l2_enabled=True,
    l1_enabled=True,
    l1_maxsize=100,
    l1_ttl=30,
)

cache.set("key", "value")
print(cache.get("key"))
print(cache.get_stats())
```

Run:
```bash
uv run python test_local.py
```

### Example 2: Full Flask App

```bash
# Ensure Redis is running
docker run -d -p 6379:6379 redis:7-alpine

# Run the example
uv run python examples/basic_usage.py
```

Test endpoints:
```bash
curl http://localhost:5000/users/1
curl http://localhost:5000/cache/stats
curl http://localhost:5000/health
```

## Publishing to PyPI

### 1) Update Version

Edit `src/resilient_cache/__init__.py` and `pyproject.toml`:

```python
__version__ = "0.1.1"
```

### 2) Update CHANGELOG

Document changes in `CHANGELOG.md`.

### 3) Tag the Release

```bash
git add .
git commit -m "Release v0.1.1"
git tag v0.1.1
git push origin main --tags
```

### 4) Build and Upload

```bash
uv build
uv publish
```

### 5) Installation Test

```bash
# In another environment
uv init
uv add "resilient-cache[flask]"

# Test
uv run python -c "from resilient_cache import FlaskCacheService; print('OK')"
```

## Using in Other Projects

After publishing, other projects can install:

```bash
uv init
uv add "resilient-cache[flask]"

# With L1 + L2
uv add "resilient-cache[full]"
```

And use it like this:

```python
from flask import Flask
from resilient_cache import FlaskCacheService

app = Flask(__name__)
cache_service = FlaskCacheService()
cache_service.init_app(app)

my_cache = cache_service.create_cache(
    l2_key_prefix="my_module",
    l2_ttl=3600,
    l2_enabled=True,
    l1_enabled=True,
    l1_maxsize=1000,
    l1_ttl=60,
)
```

## Next Steps

1. Test thoroughly in local environments.
2. Integrate into the original application with `uv add --editable ../resilient-cache`.
3. Collect feedback.
4. Iterate and improve based on real usage.
5. Publish when stable.

## Support

- Issues: https://github.com/dclobato/resilient-cache/issues
- Email: daniel@lobato.org
- Website: https://sites.lobato.org
