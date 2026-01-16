# Adding a New Cache Backend (L1 or L2)

This document is for maintainers. End users can only choose from the built-in backends; they cannot plug in custom backends without modifying the package.

## Overview

Backends implement the `CacheBackend` interface in `src/resilient_cache/backends/base.py`.
The factory (`src/resilient_cache/cache_factory.py`) selects which backend to build based on config.

## L1 Backend: Step-by-step

1) Create a backend class under `src/resilient_cache/backends/`.

Example skeleton:
```python
from typing import Any, List, Optional

from resilient_cache.backends.base import CacheBackend
from resilient_cache.config import L1Config


class MyL1Backend(CacheBackend):
    def __init__(self, config: L1Config):
        self.config = config

    def get(self, key: str) -> Any:
        ...

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ...

    def set_if_not_exist(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ...

    def delete(self, key: str) -> None:
        ...

    def clear(self) -> int:
        ...

    def exists(self, key: str) -> bool:
        ...

    def get_ttl(self, key: str) -> Optional[int]:
        ...

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        ...

    def get_size(self) -> int:
        ...

    def get_stats(self) -> dict:
        ...
```

2) Wire it into the factory:
- Update `CacheFactory._create_l1_backend` to recognize the new backend name.
- Update `L1Config.backend` validation in `src/resilient_cache/config/__init__.py`.

Example factory change:
```python
if config.backend == "my_l1":
    from .backends.my_l1_backend import MyL1Backend
    return MyL1Backend(config)
```

3) Add optional dependency (if needed) in `pyproject.toml`, usually under `project.optional-dependencies`.

4) Add tests:
- Unit tests for the backend itself.
- Factory selection test in `tests/unit/test_cache_factory.py`.

## L2 Backend: Step-by-step

1) Implement `CacheBackend` in `src/resilient_cache/backends/`.
2) Update `CacheFactory._create_l2_backend` to support the new backend name.
3) Update `L2Config.backend` validation in `src/resilient_cache/config/__init__.py`.
4) Add optional dependency in `pyproject.toml`.
5) Add tests to cover:
   - Serializer handling
   - Connection errors
   - Key prefixing and TTL behavior

Example factory change:
```python
if config.backend == "my_l2":
    from .backends.my_l2_backend import MyL2Backend
    return MyL2Backend(config, serializer, self.logger)
```

## Config Keys and Naming

- L1 backend key: `CACHE_L1_BACKEND` (values like `ttl`, `my_l1`)
- L2 backend key: `CACHE_L2_BACKEND` (values like `redis`, `my_l2`)

Keep names lowercase and stable, because they become part of the public configuration surface.

## Documentation Updates

If you add a backend:
- Update `README.md` and `INSTALLATION_GUIDE.md` with the new option and extras.
- Mention any new dependencies and configuration keys.

## Non-Goal: User-Defined Backends

This package does not currently support user-supplied backend plugins.
Adding a new backend requires changes in the source tree and a package release.
