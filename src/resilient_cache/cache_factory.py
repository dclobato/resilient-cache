"""
Factory para criação de caches configurados.

Centraliza a criação de instâncias de cache com configuração
padronizada e detecção automática de dependências disponíveis.
"""

import logging
from typing import Optional

from .app_cache import AppCache
from .backends.base import CacheBackend
from .config import (
    CacheConfig,
    CacheFactoryConfig,
    CircuitBreakerConfig,
    L1Config,
    L2Config,
)
from .two_level_cache import ResilientTwoLevelCache


class CacheFactory:
    """
    Factory para criar caches com configuração padronizada.

    Centraliza:
    - Defaults globais de configuração
    - Detecção automática de dependências (cachetools, redis)
    - Validação de configuração
    - Criação de backends apropriados

    Example:
        >>> from resilient_cache import CacheFactory, CacheFactoryConfig
        >>>
        >>> factory_config = CacheFactoryConfig(l2_host="localhost", l2_port=6379)
        >>> factory = CacheFactory(factory_config)
        >>>
        >>> # Criar cache personalizado
        >>> cache = factory.create_cache(
        ...     l2_key_prefix="users",
        ...     l2_ttl=3600,
        ...     l2_enabled=True,
        ...     l1_enabled=True,
        ...     l1_maxsize=1000,
        ...     l1_ttl=60,
        ... )
    """

    def __init__(
        self,
        config: CacheFactoryConfig,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Inicializa a factory com configuração global.

        Args:
            config: Configuração global da factory
            logger: Logger opcional
        """
        self.config = config
        self.logger = logger or config.logger or logging.getLogger(__name__)

        # Detectar disponibilidade de dependências
        self._check_dependencies()

        self.logger.info("CacheFactory initialized")

    def _check_dependencies(self) -> None:
        """
        Verifica disponibilidade de dependências opcionais.

        Registra warnings se dependências não estiverem disponíveis.
        """
        # Verificar cachetools (L1)
        try:
            import cachetools  # noqa: F401

            self._cachetools_available = True
            self.logger.debug("cachetools available for L1 cache")
        except ImportError:
            self._cachetools_available = False
            self.logger.warning(
                "cachetools not available - L1 cache will be disabled. "
                'Install with: uv add "resilient-cache[l1]"'
            )

        # Verificar redis (L2)
        try:
            import redis  # noqa: F401

            self._redis_available = True
            self.logger.debug("redis available for L2 cache")
        except ImportError:
            self._redis_available = False
            self.logger.warning(
                "redis not available - L2 cache will be disabled. "
                'Install with: uv add "resilient-cache[l2]"'
            )

    def _create_l1_backend(self, config: L1Config) -> Optional[CacheBackend]:
        """
        Cria backend L1 se possível.

        Args:
            config: Configuração do L1

        Returns:
            Backend L1 ou None se não disponível
        """
        if not config.enabled:
            return None

        if not self._cachetools_available:
            self.logger.warning("Cannot create L1: cachetools not available")
            return None

        # Validar configuração
        if config.maxsize < 1 or config.ttl < 1:
            self.logger.warning(
                f"Invalid L1 config: maxsize={config.maxsize}, ttl={config.ttl}. "
                "L1 will be disabled."
            )
            return None

        # Criar backend apropriado
        try:
            if config.backend == "ttl":
                from .backends.ttl_cache_backend import TTLCacheBackend

                return TTLCacheBackend(config, self.logger)
            else:
                self.logger.error(f"Unknown L1 backend: {config.backend}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to create L1 backend: {e}")
            return None

    def _create_l2_backend(self, config: L2Config, serializer: str) -> Optional[CacheBackend]:
        """
        Cria backend L2 se possível.

        Args:
            config: Configuração do L2
            serializer: Tipo de serialização

        Returns:
            Backend L2 ou None se não disponível
        """
        if not config.enabled:
            return None

        if not self._redis_available:
            self.logger.warning("Cannot create L2: redis not available")
            return None

        # Criar backend apropriado
        try:
            if config.backend in ("redis", "valkey"):
                from .backends.redis_backend import RedisBackend

                return RedisBackend(config, serializer, self.logger)
            else:
                self.logger.error(f"Unknown L2 backend: {config.backend}")
                return None

        except Exception as e:
            self.logger.warning(f"Failed to create L2 backend: {e}")
            return None

    def create_cache(
        self,
        l2_key_prefix: str,
        l2_ttl: int,
        l2_enabled: bool,
        l1_enabled: bool = False,
        l1_maxsize: int = 0,
        l1_ttl: int = 0,
        serializer: Optional[str] = None,
        circuit_breaker_enabled: Optional[bool] = None,
        circuit_breaker_threshold: Optional[int] = None,
        circuit_breaker_timeout: Optional[int] = None,
    ) -> AppCache:
        """
        Cria uma instância de cache com configuração específica.

        Args:
            l2_key_prefix: Prefixo para chaves no L2 (obrigatório)
            l2_ttl: TTL em segundos para L2 (obrigatório)
            l2_enabled: Habilitar L2
            l1_enabled: Habilitar L1
            l1_maxsize: Tamanho máximo do L1
            l1_ttl: TTL em segundos para L1
            serializer: Tipo de serialização ('pickle' ou 'json')
            circuit_breaker_enabled: Habilitar circuit breaker
            circuit_breaker_threshold: Falhas para abrir circuit
            circuit_breaker_timeout: Timeout antes de tentar fechar

        Returns:
            Instância de AppCache configurada

        Example:
            >>> cache = factory.create_cache(
            ...     l2_key_prefix="users",
            ...     l2_ttl=3600,
            ...     l2_enabled=True,
            ...     l1_enabled=True,
            ...     l1_maxsize=1000,
            ...     l1_ttl=60,
            ... )
        """
        # Usar defaults da factory se não especificado
        serializer = serializer or self.config.serializer

        # Configuração do L1
        l1_config = L1Config(
            enabled=l1_enabled,
            maxsize=l1_maxsize if l1_maxsize > 0 else 1000,
            ttl=l1_ttl if l1_ttl > 0 else 60,
            backend=self.config.l1_backend,
        )

        # Configuração do L2
        l2_config = L2Config(
            enabled=l2_enabled,
            key_prefix=l2_key_prefix,
            ttl=l2_ttl,
            backend=self.config.l2_backend,
            host=self.config.l2_host,
            port=self.config.l2_port,
            db=self.config.l2_db,
            password=self.config.l2_password,
            connect_timeout=self.config.l2_connect_timeout,
            socket_timeout=self.config.l2_socket_timeout,
        )

        # Configuração do Circuit Breaker
        cb_config = CircuitBreakerConfig(
            enabled=(
                circuit_breaker_enabled
                if circuit_breaker_enabled is not None
                else self.config.circuit_breaker_enabled
            ),
            threshold=(
                circuit_breaker_threshold
                if circuit_breaker_threshold is not None
                else self.config.circuit_breaker_threshold
            ),
            timeout=(
                circuit_breaker_timeout
                if circuit_breaker_timeout is not None
                else self.config.circuit_breaker_timeout
            ),
        )

        # Criar configuração completa do cache
        cache_config = CacheConfig(
            l1=l1_config,
            l2=l2_config,
            circuit_breaker=cb_config,
            serializer=serializer,
            logger=self.logger,
        )

        # Adicionar factories de backend
        cache_config.l1_backend_factory = self._create_l1_backend
        cache_config.l2_backend_factory = lambda config: self._create_l2_backend(config, serializer)

        # Criar e retornar cache
        cache = ResilientTwoLevelCache(cache_config)

        self.logger.info(
            f"Cache created: prefix={l2_key_prefix}, "
            f"L1={'enabled' if l1_enabled else 'disabled'}, "
            f"L2={'enabled' if l2_enabled else 'disabled'}"
        )

        return cache

    def get_stats(self) -> dict:
        """
        Retorna estatísticas da factory.

        Returns:
            Dicionário com informações sobre dependências e configuração
        """
        return {
            "dependencies": {
                "cachetools": self._cachetools_available,
                "redis": self._redis_available,
            },
            "defaults": {
                "l1_backend": self.config.l1_backend,
                "l2_backend": self.config.l2_backend,
                "l2_host": self.config.l2_host,
                "l2_port": self.config.l2_port,
                "serializer": self.config.serializer,
                "circuit_breaker_enabled": self.config.circuit_breaker_enabled,
                "circuit_breaker_threshold": self.config.circuit_breaker_threshold,
                "circuit_breaker_timeout": self.config.circuit_breaker_timeout,
            },
        }

    def __repr__(self) -> str:
        """Representação string da factory."""
        return (
            f"<CacheFactory "
            f"cachetools={'✓' if self._cachetools_available else '✗'} "
            f"redis={'✓' if self._redis_available else '✗'}>"
        )
