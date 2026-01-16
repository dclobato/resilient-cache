# Tests

This directory contains the test suite for resilient-cache, organized into unit tests and integration tests.

## Test Structure

```
tests/
├── unit/           # Unit tests (no external dependencies)
├── integration/    # Integration tests (require Valkey/Redis)
├── conftest.py     # Shared pytest fixtures
└── README.md       # This file
```

## Running Tests

### Unit Tests Only (Default)

Unit tests run fast and don't require any external services:

```bash
# Linux/macOS
make test
make test-unit

# Windows
make -f Makefile.windows test
make -f Makefile.windows test-unit
```

### Integration Tests Only

Integration tests require a running Valkey/Redis instance. Set the environment variables:

```bash
# Linux/macOS
make test-integration

# Windows
make -f Makefile.windows test-integration
```

The Makefile automatically sets these default values:
- `VALKEY_HOST=localhost`
- `VALKEY_PORT=6379`
- `VALKEY_DB=0`

### All Tests (Unit + Integration)

To run the complete test suite:

```bash
# Linux/macOS
make test-all

# Windows
make -f Makefile.windows test-all
```

## Test Coverage

### Coverage for Unit Tests

```bash
# Linux/macOS
make test-cov

# Windows
make -f Makefile.windows test-cov
```

### Coverage for Integration Tests

```bash
# Linux/macOS
make test-cov-integration

# Windows
make -f Makefile.windows test-cov-integration
```

### Coverage for All Tests

```bash
# Linux/macOS
make test-cov-all

# Windows
make -f Makefile.windows test-cov-all
```

Coverage reports are generated in:
- Terminal output (summary)
- `htmlcov/index.html` (detailed HTML report)

## Environment Variables

Integration tests use these environment variables to connect to Valkey/Redis:

| Variable | Default | Description |
|----------|---------|-------------|
| `VALKEY_HOST` | `localhost` | Valkey/Redis server hostname or IP |
| `VALKEY_PORT` | `6379` | Valkey/Redis server port |
| `VALKEY_DB` | `0` | Valkey/Redis database number |

### Custom Configuration

You can override the defaults by setting environment variables before running tests:

**Linux/macOS:**
```bash
VALKEY_HOST=redis.example.com VALKEY_PORT=6380 VALKEY_DB=1 make test-integration
```

**Windows (PowerShell):**
```powershell
$env:VALKEY_HOST='redis.example.com'
$env:VALKEY_PORT='6380'
$env:VALKEY_DB='1'
make -f Makefile.windows test-integration
```

## Setting Up Valkey/Redis for Integration Tests

### Using Docker

The easiest way to run integration tests is with Docker:

```bash
# Start Valkey (Redis-compatible)
docker run -d -p 6379:6379 --name valkey valkey/valkey:latest

# Run integration tests
make test-integration

# Stop Valkey when done
docker stop valkey
docker rm valkey
```

### Using Docker Compose

Create a `docker-compose.yml` in the project root:

```yaml
version: '3.8'
services:
  valkey:
    image: valkey/valkey:latest
    ports:
      - "6379:6379"
    environment:
      - VALKEY_MAXMEMORY=128mb
      - VALKEY_MAXMEMORY_POLICY=allkeys-lru
```

Then:

```bash
# Start services
docker-compose up -d

# Run tests
make test-integration

# Stop services
docker-compose down
```

### Local Installation

If you prefer installing Valkey/Redis locally:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**macOS (using Homebrew):**
```bash
brew install redis
brew services start redis
```

**Windows:**
- Download from [Redis for Windows](https://github.com/microsoftarchive/redis/releases)
- Or use WSL2 with Ubuntu

## CI/CD Integration

For continuous integration pipelines, integration tests typically:

1. Start Valkey/Redis as a service
2. Run tests with appropriate environment variables
3. Stop services after tests complete

Example GitHub Actions workflow:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      valkey:
        image: valkey/valkey:latest
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        env:
          VALKEY_HOST: localhost
          VALKEY_PORT: 6379
          VALKEY_DB: 0
        run: make test-all
```

## Writing Tests

### Unit Tests

Place in `tests/unit/`. Should:
- Not require external services
- Use mocks/fakes for dependencies
- Run fast (milliseconds)

Example:
```python
def test_serializer_json():
    serializer = JsonSerializer()
    data = {"key": "value"}
    serialized = serializer.serialize(data)
    assert serializer.deserialize(serialized) == data
```

### Integration Tests

Place in `tests/integration/`. Should:
- Test real interactions with Valkey/Redis
- Use environment variables for configuration
- Clean up after themselves

Example:
```python
import os
from resilient_cache import CacheFactory, CacheFactoryConfig

def test_redis_integration():
    config = CacheFactoryConfig(
        l2_host=os.getenv("VALKEY_HOST", "localhost"),
        l2_port=int(os.getenv("VALKEY_PORT", "6379")),
        l2_db=int(os.getenv("VALKEY_DB", "0")),
    )
    factory = CacheFactory(config)
    cache = factory.create_cache(
        l2_key_prefix="test",
        l2_ttl=60,
        l2_enabled=True,
    )

    # Test operations
    cache.set("key", "value")
    assert cache.get("key") == "value"

    # Cleanup
    cache.clear()
```

## Troubleshooting

### Integration Tests Failing

**Connection Refused:**
- Ensure Valkey/Redis is running: `docker ps` or `systemctl status redis`
- Check port: `telnet localhost 6379`
- Verify environment variables: `echo $VALKEY_HOST`

**Authentication Required:**
If your Valkey/Redis requires a password:
```bash
# Add to your config or export
VALKEY_PASSWORD=your-password make test-integration
```

**Database Not Empty:**
Integration tests should clean up, but you can manually flush:
```bash
redis-cli -n 0 FLUSHDB
```

### Coverage Not Reaching 90%

This is expected:
- Unit tests alone may not cover all code paths
- Integration tests exercise real backend interactions
- Run `make test-cov-all` for complete coverage

## Quick Reference

| Command | Description |
|---------|-------------|
| `make test` | Run unit tests only (fast) |
| `make test-integration` | Run integration tests (requires Valkey) |
| `make test-all` | Run all tests |
| `make test-cov` | Unit tests with coverage |
| `make test-cov-integration` | Integration tests with coverage |
| `make test-cov-all` | All tests with coverage |
| `make check` | Run format, lint, type-check, and all tests |

On Windows, prefix all commands with `-f Makefile.windows`.
