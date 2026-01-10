"""
Backends de cache para L1 e L2.

Este módulo contém as implementações concretas dos backends
de cache usado pelo sistema.
"""

from .base import CacheBackend
from .redis_backend import RedisBackend
from .ttl_cache_backend import TTLCacheBackend

__all__ = [
    "CacheBackend",
    "TTLCacheBackend",
    "RedisBackend",
]
