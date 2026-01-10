# Roadmap: User-Defined Backends (Next Step)

This roadmap documents a potential next step: enabling users to add their own L1/L2 backends. It is **not implemented** today.

## Goal

Allow end users to register custom cache backends without modifying this repository, while keeping compatibility, safety, and observability.

## Proposed Public API (Minimal)

### 1) Backend Contract

Backends must implement the existing `CacheBackend` interface and obey the error contract:
- Raise `CacheConnectionError` for connectivity failures.
- Raise `CacheSerializationError` for serialization issues.
- Provide `get_stats()` with at least `{ "enabled": bool, "backend": str }`.

### 2) Registration API (Core)

Introduce a small plugin registry:

```python
# resilient_cache/plugins.py
def register_l1_backend(name: str, factory: Callable[[L1Config, Logger], CacheBackend]) -> None: ...
def register_l2_backend(name: str, factory: Callable[[L2Config, str, Logger], CacheBackend]) -> None: ...
def list_backends() -> dict:  # {"l1": [...], "l2": [...]}
```

### 3) Config Selection

Allow custom names:
- `CACHE_L1_BACKEND = "my_l1"`
- `CACHE_L2_BACKEND = "my_l2"`

Factory resolution should consult the registry before built-ins.

## Example: User Registration (Runtime)

```python
from resilient_cache.plugins import register_l2_backend
from my_pkg.backends import MyL2Backend

def factory(config, serializer, logger):
    return MyL2Backend(config, serializer, logger)

register_l2_backend("my_l2", factory)
```

## Tasks

1) Add plugin registry module and tests.
2) Refactor `CacheFactory` to resolve registered backends.
3) Document the public API and compatibility guarantees.
4) Add compliance tests for third-party backends.

## Next Step (Recommended)

Adopt this roadmap as the next feature milestone after the current release, with a major/minor bump and clear documentation of the new extension API.
