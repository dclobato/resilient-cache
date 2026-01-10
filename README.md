# Resilient Cache

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A resilient two-level cache (L1/L2) for any application, with optional Flask integration. It combines local in-memory performance with distributed sharing via Redis/Valkey.

## Features

### Hybrid Architecture

- **L1 (Local Cache)**: per-process in-memory TTL cache
- **L2 (Distributed Cache)**: Redis/Valkey shared across instances
- **Circuit Breaker**: automatic protection against L2 failures
- **Graceful Fallback**: continues operating even if L2 is unavailable

### Benefits

| Aspect | L1 (Memory) | L2 (Redis/Valkey) | Combined (L1+L2) |
|---------|--------------|-------------------|--------------------|
| **Latency** | < 1ms | 5-10ms | < 1ms (L1 hit) |
| **Sharing** | No (per process) | Yes (across instances) | Yes + fast |
| **Persistence** | No (lost on restart) | Yes | Hybrid |
| **Scalability** | Limited | High | Best of both |
| **Resilience** | Always available | Can fail | Automatic fallback |

## Installation

### Makefile (Linux/macOS) vs Windows

- `Makefile` targets Linux/macOS.
- On Windows, use `Makefile.windows`:
  ```bash
  make -f Makefile.windows install-dev
  make -f Makefile.windows test
  make -f Makefile.windows check
  ```

### Core Install

```bash
uv add resilient-cache
```

### Extras Available

- `flask`: Flask integration
- `l1`: in-memory cache (cachetools)
- `l2`: distributed cache (Redis/Valkey)
- `full`: Flask + L1 + L2

### With Flask Integration

```bash
uv add "resilient-cache[flask]"
```

### With L1 (in-memory)

```bash
uv add "resilient-cache[l1]"
```

### With L2 (Redis/Valkey)

```bash
uv add "resilient-cache[l2]"
```

### Full Install (Flask + L1 + L2)

```bash
uv add "resilient-cache[full]"
```

### For Development

```bash
uv sync --extra dev
```

## Quick Start

### Framework-Agnostic Usage

```python
from resilient_cache import CacheFactoryConfig, CacheService

config = CacheFactoryConfig(
    l2_host="localhost",
    l2_port=6379,
    l2_db=0,
)

cache_service = CacheService(config)
```

### Basic Flask Configuration

```python
from flask import Flask
from resilient_cache import FlaskCacheService

app = Flask(__name__)

# Redis/Valkey configuration
app.config.update({
    'CACHE_REDIS_HOST': 'localhost',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 0,
})

# Initialize cache service
cache_service = FlaskCacheService()
cache_service.init_app(app)
```

### Creating a Custom Cache

```python
# Create L1 + L2 cache
cache = cache_service.create_cache(
    l2_key_prefix="users",
    l2_ttl=3600,           # 1 hour in L2
    l2_enabled=True,
    l1_enabled=True,
    l1_maxsize=1000,       # up to 1000 items in L1
    l1_ttl=60,             # 1 minute in L1
)

# Use the cache
@app.route('/user/<int:user_id>')
def get_user(user_id):
    cache_key = f"user_{user_id}"

    user = cache.get(cache_key)

    if user is None:
        user = User.query.get(user_id)
        cache.set(cache_key, user)

    return user
```

### Decorator Example (Future Feature)

```python
from resilient_cache import cached

@cached(
    key_prefix="dashboard",
    ttl=300,
    l1_enabled=True,
    l1_ttl=30,
)
def get_dashboard_data(user_id):
    return expensive_computation(user_id)
```

## Configuration

### Environment Keys

```python
# L2 (Redis/Valkey)
CACHE_REDIS_HOST = "localhost"
CACHE_REDIS_PORT = 6379
CACHE_REDIS_DB = 0
CACHE_REDIS_PASSWORD = None
CACHE_REDIS_CONNECT_TIMEOUT = 5
CACHE_REDIS_SOCKET_TIMEOUT = 5

# Circuit Breaker
CACHE_CIRCUIT_BREAKER_ENABLED = True
CACHE_CIRCUIT_BREAKER_THRESHOLD = 5
CACHE_CIRCUIT_BREAKER_TIMEOUT = 60

# Serialization
CACHE_SERIALIZER = "pickle"  # "pickle" or "json"

# L1 backend (default: TTLCache)
CACHE_L1_BACKEND = "ttl"  # "ttl" or "lru"

# L2 backend (default: Redis)
CACHE_L2_BACKEND = "redis"  # "redis" or "valkey"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Flask Application                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                 ┌──────────▼──────────┐                     │
│                 │ ResilientTwoLevel   │                     │
│                 │ Cache               │                     │
│                 └──────────┬──────────┘                     │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│   ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐       │
│   │ L1: TTL   │     │ L2: Redis │     │ Circuit   │       │
│   │ Cache     │     │ Backend   │     │ Breaker   │       │
│   │ Backend   │     │           │     │           │       │
│   └───────────┘     └─────┬─────┘     └───────────┘       │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  CacheService   │
                    │   (Facade)      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Redis Server    │
                    │ (or Valkey)     │
                    └─────────────────┘
```

## Cache Operations

### Basic Operations

```python
value = cache.get("my_key")
cache.set("my_key", {"data": "value"})
cache.delete("my_key")
stats = cache.clear()
exists = cache.is_on_cache("my_key")
```

### Advanced Operations

```python
ttl = cache.get_ttl("my_key")
keys = cache.list_keys()
user_keys = cache.list_keys(prefix="user_")
stats = cache.get_stats()
```

## Cache Strategies

### Write-Through

By default, write-through writes to L1 and L2.

```python
cache.set("key", "value")
```

### Cache Promotion

L2 hits are promoted into L1 automatically.

```python
value = cache.get("key")  # L2 hit promotes to L1
value = cache.get("key")  # L1 hit (< 1ms)
```

### Selective Invalidation

```python
def update_user(user_id, new_data):
    user = User.query.get(user_id)
    user.update(new_data)
    db.session.commit()

    cache.delete(f"user_{user_id}")
```

## Monitoring and Troubleshooting

### Cache Health Check

```python
@app.route('/health/cache')
def cache_health():
    stats = cache.get_stats()

    if stats['l2']['circuit_breaker']['state'] == 'open':
        return {"status": "degraded", "reason": "L2 unavailable"}, 503

    return {"status": "healthy", "stats": stats}, 200
```

### Key Metrics

```python
stats = cache.get_stats()

l1_usage = stats['l1']['size'] / stats['l1']['maxsize'] * 100
if l1_usage > 90:
    print("Warning: L1 cache nearly full")

cb_state = stats['l2']['circuit_breaker']['state']
if cb_state != 'closed':
    print(f"Warning: Circuit breaker state is {cb_state}")
```

## Real-World Examples

### Session Cache

```python
session_cache = cache_service.create_cache(
    l2_key_prefix="session",
    l2_ttl=1800,
    l2_enabled=True,
    l1_enabled=True,
    l1_maxsize=500,
    l1_ttl=300,
)
```

### Expensive Computation Cache

```python
computation_cache = cache_service.create_cache(
    l2_key_prefix="computation",
    l2_ttl=86400,
    l2_enabled=True,
    l1_enabled=True,
    l1_maxsize=100,
    l1_ttl=3600,
)
```

### Generated Images Cache

```python
image_cache = cache_service.create_cache(
    l2_key_prefix="images",
    l2_ttl=604800,
    l2_enabled=True,
    l1_enabled=True,
    l1_maxsize=2000,
    l1_ttl=1800,
    serializer="pickle",
)
```

## Performance

### Typical Benchmarks

| Operation | Latency | Throughput |
|----------|----------|------------|
| L1 hit | < 1ms | > 100k ops/s |
| L2 hit (local) | 2-5ms | > 20k ops/s |
| L2 hit (network) | 5-10ms | > 10k ops/s |
| L1 set | < 1ms | > 100k ops/s |
| L2 set (local) | 3-8ms | > 15k ops/s |

### Optimization Tips

1. Keep L1 TTL shorter than L2 TTL.
2. Size L1 using monitoring (`l1_maxsize`).
3. Choose serializer based on data type (`json` vs `pickle`).
4. Use L2 for shared data across instances.
5. Use L1 for per-process computations.

## Contributing

Contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to your branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

For maintainers: see `BACKEND_GUIDE.md` if you need to add a new L1/L2 backend.

### Running Tests

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Coverage
uv run pytest --cov=resilient_cache --cov-report=html

# Format code
uv run black src/
uv run isort src/

# Type checks
uv run mypy src/
```

## License

This project is licensed under the MIT License. See `LICENSE`.

## Author

**Daniel Correa Lobato**
- Website: [sites.lobato.org](https://sites.lobato.org)
- Email: daniel@lobato.org

## Acknowledgements

- Inspired by production-grade caching patterns used in large Flask applications
- Architecture based on industry multi-level cache practices
