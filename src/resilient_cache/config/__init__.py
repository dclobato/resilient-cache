"""
Configurações para o sistema de cache.

Define dataclasses para configuração type-safe do sistema de cache.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from resilient_cache.config.utils import (
    validate_boolean,
    validate_host,
    validate_int_min,
    validate_optional_string,
    validate_port_number,
    validate_string_in_choices,
    validate_string_not_empty,
)
from resilient_cache.serializers import CacheSerializer, list_serializers


@dataclass
class CircuitBreakerConfig:
    """
    Configuração do circuit breaker para proteção do L2.

    O circuit breaker monitora falhas no L2 e automaticamente
    desabilita conexões quando o threshold é atingido.
    """

    enabled: bool = True
    """Habilita o circuit breaker"""

    threshold: int = 5
    """Número de falhas consecutivas para abrir o circuit"""

    timeout: int = 60
    """Segundos antes de tentar fechar o circuit (half-open)"""

    def __post_init__(self) -> None:
        """Valida a configuração."""
        validate_boolean(self.enabled, "Circuit breaker enabled")
        validate_int_min(self.threshold, "Circuit breaker threshold", 1)
        validate_int_min(self.timeout, "Circuit breaker timeout", 1)


@dataclass
class L1Config:
    """Configuração do cache L1 (local/memória)."""

    enabled: bool = False
    """Habilita o cache L1"""

    maxsize: int = 1000
    """Número máximo de itens no cache L1"""

    ttl: int = 60
    """Time-to-live em segundos para itens no L1"""

    backend: str = "ttl"
    """Tipo de backend L1: 'ttl' (TTLCache) ou 'lru' (LRUCache)"""

    def __post_init__(self) -> None:
        """Valida a configuração."""
        validate_boolean(self.enabled, "L1 enabled")
        if self.enabled:
            validate_int_min(self.maxsize, "L1 maxsize", 1)
            validate_int_min(self.ttl, "L1 TTL", 1)
            self.backend = validate_string_not_empty(self.backend, "L1 backend").lower()
            validate_string_in_choices(self.backend, "L1 backend", ("ttl", "lru"))


@dataclass
class L2Config:
    """Configuração do cache L2 (distribuído/Redis/Valkey)."""

    enabled: bool = True
    """Habilita o cache L2"""

    key_prefix: str = "cache"
    """Prefixo para todas as chaves no L2"""

    ttl: int = 3600
    """Time-to-live em segundos para itens no L2"""

    backend: str = "redis"
    """Tipo de backend L2: 'redis' ou 'valkey'"""

    host: str = "localhost"
    """Host do servidor Redis/Valkey"""

    port: int = 6379
    """Porta do servidor Redis/Valkey"""

    db: int = 0
    """Número do database Redis/Valkey"""

    password: Optional[str] = None
    """Senha para autenticação (opcional)"""

    connect_timeout: int = 5
    """Timeout de conexão em segundos"""

    socket_timeout: int = 5
    """Timeout de socket em segundos"""

    def __post_init__(self) -> None:
        """Valida a configuração."""
        validate_boolean(self.enabled, "L2 enabled")
        if self.enabled:
            validate_int_min(self.ttl, "L2 TTL", 1)
            validate_string_not_empty(self.key_prefix, "L2 key_prefix")
            self.host = validate_host(self.host, "L2 host")
            validate_port_number(self.port, "L2 port", exclude_zero=True)
            validate_int_min(self.db, "L2 db", 0)
            validate_optional_string(self.password, "L2 password")
            validate_int_min(self.connect_timeout, "L2 connect_timeout", 1)
            validate_int_min(self.socket_timeout, "L2 socket_timeout", 1)
            self.backend = validate_string_not_empty(self.backend, "L2 backend").lower()
            validate_string_in_choices(self.backend, "L2 backend", ("redis", "valkey"))


@dataclass
class CacheConfig:
    """
    Configuração completa de um cache.

    Esta classe agrupa todas as configurações necessárias para
    criar uma instância de cache resiliente.
    """

    l1: L1Config
    """Configuração do cache L1"""

    l2: L2Config
    """Configuração do cache L2"""

    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    """Configuração do circuit breaker"""

    serializer: str | CacheSerializer = "pickle"
    """Serializer a usar: nome registrado ou instancia de CacheSerializer"""

    logger: Optional[logging.Logger] = None
    """Logger customizado (opcional)"""

    # Factories para criar backends (injetadas pela CacheFactory)
    l1_backend_factory: Optional[Callable[[L1Config], Any]] = None
    l2_backend_factory: Optional[Callable[[L2Config], Any]] = None

    def __post_init__(self) -> None:
        """Valida a configuração."""
        if isinstance(self.serializer, CacheSerializer):
            pass
        elif isinstance(self.serializer, str):
            available = list_serializers()
            if self.serializer not in available:
                raise ValueError(
                    f"Serializer must be one of {available} or a CacheSerializer instance"
                )
        else:
            raise TypeError(
                f"Serializer must be a string or CacheSerializer, got {type(self.serializer)}"
            )

        # Se logger não for da classe logging.Logger ou não fornecido, cria um padrão
        if not isinstance(self.logger, logging.Logger) or self.logger is None:
            self.logger = logging.getLogger("resilient_cache")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                )
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)


@dataclass
class CacheFactoryConfig:
    """
    Configuração global da CacheFactory.

    Define defaults que serão aplicados a todos os caches criados
    pela factory, a menos que sejam sobrescritos.
    """

    l2_backend: str = "redis"
    """Backend padrão para L2: 'redis' ou 'valkey'"""

    l2_host: str = "localhost"
    """Host padrão do servidor L2"""

    l2_port: int = 6379
    """Porta padrão do servidor L2"""

    l2_db: int = 0
    """Database padrão do L2"""

    l2_password: Optional[str] = None
    """Senha padrão para L2 (opcional)"""

    l2_connect_timeout: int = 5
    """Timeout de conexão padrão para L2"""

    l2_socket_timeout: int = 5
    """Timeout de socket padrão para L2"""

    l1_backend: str = "ttl"
    """Backend padrão para L1: 'ttl' ou 'lru'"""

    serializer: str | CacheSerializer = "pickle"
    """Serializer padrao: nome registrado ou instancia de CacheSerializer"""

    circuit_breaker_enabled: bool = True
    """Habilita circuit breaker por padrão"""

    circuit_breaker_threshold: int = 5
    """Threshold padrão do circuit breaker"""

    circuit_breaker_timeout: int = 60
    """Timeout padrão do circuit breaker"""

    logger: Optional[logging.Logger] = None
    """Logger padrão para todos os caches"""

    def __post_init__(self) -> None:
        """Valida a configuração."""
        # Validate and normalize backends
        self.l2_backend = validate_string_not_empty(self.l2_backend, "l2_backend").lower()
        validate_string_in_choices(self.l2_backend, "l2_backend", ("redis", "valkey"))

        self.l1_backend = validate_string_not_empty(self.l1_backend, "l1_backend").lower()
        validate_string_in_choices(self.l1_backend, "l1_backend", ("ttl", "lru"))

        # Validate host and port
        self.l2_host = validate_host(self.l2_host, "l2_host")
        validate_port_number(self.l2_port, "l2_port", exclude_zero=True)

        # Validate other L2 settings
        validate_int_min(self.l2_db, "l2_db", 0)
        validate_optional_string(self.l2_password, "l2_password")
        validate_int_min(self.l2_connect_timeout, "l2_connect_timeout", 0)
        validate_int_min(self.l2_socket_timeout, "l2_socket_timeout", 0)

        # Validate serializer
        if isinstance(self.serializer, CacheSerializer):
            pass
        elif isinstance(self.serializer, str):
            available = list_serializers()
            if self.serializer not in available:
                raise ValueError(
                    f"serializer must be one of {available} or a CacheSerializer instance"
                )
        else:
            raise TypeError(
                f"serializer must be a string or CacheSerializer, got {type(self.serializer)}"
            )

        # Validate circuit breaker settings
        validate_boolean(self.circuit_breaker_enabled, "circuit_breaker_enabled")
        validate_int_min(self.circuit_breaker_threshold, "circuit_breaker_threshold", 1)
        validate_int_min(self.circuit_breaker_timeout, "circuit_breaker_timeout", 1)

        # Se logger não for instância de logging.Logger ou não fornecido, cria um padrão
        if self.logger is None or not isinstance(self.logger, logging.Logger):
            self.logger = logging.getLogger("resilient_cache.factory")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(
                    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
                )
                self.logger.addHandler(handler)
                self.logger.setLevel(logging.INFO)

    @classmethod
    def from_flask_config(cls, config: dict) -> "CacheFactoryConfig":
        """
        Cria configuração a partir de um dict de configuração Flask.

        Args:
            config: Dicionário com configurações Flask (app.config)

        Returns:
            Instância de CacheFactoryConfig

        Example:
            >>> from flask import Flask
            >>> app = Flask(__name__)
            >>> app.config['CACHE_REDIS_HOST'] = 'redis.example.com'
            >>> factory_config = CacheFactoryConfig.from_flask_config(app.config)
        """
        return cls(
            l2_backend=config.get("CACHE_L2_BACKEND", "redis"),
            l2_host=config.get("CACHE_REDIS_HOST", "localhost"),
            l2_port=config.get("CACHE_REDIS_PORT", 6379),
            l2_db=config.get("CACHE_REDIS_DB", 0),
            l2_password=config.get("CACHE_REDIS_PASSWORD", None),
            l2_connect_timeout=config.get("CACHE_REDIS_CONNECT_TIMEOUT", 5),
            l2_socket_timeout=config.get("CACHE_REDIS_SOCKET_TIMEOUT", 5),
            l1_backend=config.get("CACHE_L1_BACKEND", "ttl"),
            serializer=config.get("CACHE_SERIALIZER", "pickle"),
            circuit_breaker_enabled=config.get("CACHE_CIRCUIT_BREAKER_ENABLED", True),
            circuit_breaker_threshold=config.get("CACHE_CIRCUIT_BREAKER_THRESHOLD", 5),
            circuit_breaker_timeout=config.get("CACHE_CIRCUIT_BREAKER_TIMEOUT", 60),
        )
