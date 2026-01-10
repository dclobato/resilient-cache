"""
Resilient Cache
===============

Sistema de cache resiliente em dois níveis (L1/L2) para qualquer aplicação,
com integração opcional com Flask.

Características:
- L1 (Cache Local): TTLCache em memória RAM por processo
- L2 (Cache Distribuído): Redis/Valkey compartilhado entre instâncias
- Circuit Breaker: Proteção automática contra falhas do L2
- Fallback Gracioso: Continua funcionando mesmo se L2 estiver indisponível

Exemplo de uso básico (framework-agnostic):

    from resilient_cache import CacheService, CacheFactoryConfig

    config = CacheFactoryConfig(l2_host="localhost")
    cache_service = CacheService(config)

    cache = cache_service.create_cache(
        l2_key_prefix="users",
        l2_ttl=3600,
        l2_enabled=True,
        l1_enabled=True,
        l1_maxsize=1000,
        l1_ttl=60,
    )

    # Usar o cache
    value = cache.get("key")
    cache.set("key", "value")
"""

__version__ = "0.1.0"
__author__ = "dclobato"
__email__ = "daniel@lobato.org"

from .app_cache import AppCache
from .cache_factory import CacheFactory, CacheFactoryConfig
from .cache_service import CacheService
from .exceptions import (
    CacheConfigurationError,
    CacheConnectionError,
    CacheError,
    CacheSerializationError,
)
from .two_level_cache import ResilientTwoLevelCache

__all__ = [
    "CacheService",
    "AppCache",
    "ResilientTwoLevelCache",
    "CacheFactory",
    "CacheFactoryConfig",
    "CacheError",
    "CacheConnectionError",
    "CacheSerializationError",
    "CacheConfigurationError",
]

try:
    from .flask_integration import FlaskCacheService, get_cache_service  # noqa: F401

    __all__.extend(["FlaskCacheService", "get_cache_service"])
except ImportError:
    # Flask is optional; ignore if not available.
    pass
