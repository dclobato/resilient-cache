"""
Serviço de cache independente de framework.

Fornece uma fachada simples para inicialização e uso
do sistema de cache em qualquer contexto de aplicação.
"""

import logging
from typing import Optional

from .app_cache import AppCache
from .cache_factory import CacheFactory
from .config import CacheFactoryConfig


class CacheService:
    """
    Serviço principal de cache independente de framework.

    Fornece uma interface simples para:
    - Inicialização com configuração própria
    - Criação de caches personalizados
    - Acesso à factory de caches

    Example:
        >>> from resilient_cache import CacheService
        >>> from resilient_cache import CacheFactoryConfig
        >>>
        >>> config = CacheFactoryConfig(
        ...     l2_host="localhost",
        ...     l2_port=6379,
        ... )
        >>> cache_service = CacheService(config)
        >>>
        >>> # Criar cache personalizado
        >>> user_cache = cache_service.create_cache(
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
        config: Optional[CacheFactoryConfig] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Inicializa o serviço de cache.

        Args:
            config: Configuração global da factory (opcional)
            logger: Logger opcional
        """
        self._factory: Optional[CacheFactory] = None
        self._logger: Optional[logging.Logger] = logger

        if config is not None:
            self.init_config(config, logger=logger)

    def init_config(
        self,
        config: CacheFactoryConfig,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Inicializa o serviço com uma configuração de factory.

        Args:
            config: Configuração global da CacheFactory
            logger: Logger opcional

        Example:
            >>> cache_service = CacheService()
            >>> cache_service.init_config(CacheFactoryConfig())
        """
        # Configurar logger
        self._logger = logger or self._logger or config.logger or logging.getLogger(__name__)
        config.logger = self._logger

        # Criar factory
        self._factory = CacheFactory(config, self._logger)

        self._logger.info("CacheService initialized")

    @property
    def factory(self) -> CacheFactory:
        """
        Acesso à factory de caches.

        Returns:
            Instância da CacheFactory

        Raises:
            RuntimeError: Se não foi inicializado com init_config
        """
        if self._factory is None:
            raise RuntimeError("CacheService not initialized. Call init_config(config) first.")
        return self._factory

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
        Cria um cache personalizado.

        Wrapper conveniente para factory.create_cache().

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
            >>> cache = cache_service.create_cache(
            ...     l2_key_prefix="sessions",
            ...     l2_ttl=1800,
            ...     l2_enabled=True,
            ...     l1_enabled=True,
            ...     l1_maxsize=500,
            ...     l1_ttl=300,
            ... )
        """
        return self.factory.create_cache(
            l2_key_prefix=l2_key_prefix,
            l2_ttl=l2_ttl,
            l2_enabled=l2_enabled,
            l1_enabled=l1_enabled,
            l1_maxsize=l1_maxsize,
            l1_ttl=l1_ttl,
            serializer=serializer,
            circuit_breaker_enabled=circuit_breaker_enabled,
            circuit_breaker_threshold=circuit_breaker_threshold,
            circuit_breaker_timeout=circuit_breaker_timeout,
        )

    def get_stats(self) -> dict:
        """
        Retorna estatísticas do serviço.

        Returns:
            Dicionário com estatísticas da factory

        Example:
            >>> stats = cache_service.get_stats()
            >>> print(stats['dependencies'])
            {'cachetools': True, 'redis': True}
        """
        return self.factory.get_stats()

    def __repr__(self) -> str:
        """Representação string do serviço."""
        initialized = self._factory is not None
        return f"<CacheService initialized={initialized}>"
