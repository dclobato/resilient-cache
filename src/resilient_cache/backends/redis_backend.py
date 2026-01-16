"""
Backend de cache L2 usando Redis/Valkey.
"""

import logging
from typing import Any, List, Optional

from ..config import L2Config
from ..exceptions import (
    CacheConfigurationError,
    CacheConnectionError,
    CacheSerializationError,
)
from .base import CacheBackend
from ..serializers import CacheSerializer

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore


class RedisBackend(CacheBackend):
    """
    Backend L2 usando Redis/Valkey.

    Implementa cache distribuído com suporte a serialização
    pickle ou JSON. Compartilhado entre processos e máquinas.
    """

    def __init__(
        self,
        config: L2Config,
        serializer: CacheSerializer,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Inicializa o backend Redis.

        Args:
            config: Configuração do L2
            serializer: Instância de CacheSerializer para serialização de dados
            logger: Logger opcional

        Raises:
            CacheConfigurationError: Se redis library não estiver disponível
            CacheConnectionError: Se falhar ao conectar com Redis
        """
        if not REDIS_AVAILABLE:
            raise CacheConfigurationError(
                "redis library not available. Install with: pip install redis",
                config_key="l2_backend",
                config_value="redis",
            )

        self.config = config
        self.serializer = serializer
        self.logger = logger or logging.getLogger(__name__)

        # Criar conexão Redis
        try:
            self._client = redis.Redis(
                host=config.host,
                port=config.port,
                db=config.db,
                password=config.password,
                socket_connect_timeout=config.connect_timeout,
                socket_timeout=config.socket_timeout,
                decode_responses=False,  # Trabalha com bytes
            )

            # Testar conexão
            self._client.ping()

            self.logger.info(
                f"Redis connected: {config.host}:{config.port} "
                f"db={config.db} prefix={config.key_prefix}"
            )

        except Exception as e:
            raise CacheConnectionError(
                f"Failed to connect to Redis at {config.host}:{config.port}",
                backend="redis",
                original_error=e,
            )

    def _make_key(self, key: str) -> str:
        """
        Adiciona prefixo à chave.

        Args:
            key: Chave original

        Returns:
            Chave com prefixo
        """
        return f"{self.config.key_prefix}:{key}"

    def get(self, key: str) -> Any:
        """
        Busca valor no Redis.

        Args:
            key: Chave para buscar

        Returns:
            Valor armazenado ou None se não encontrado

        Raises:
            CacheConnectionError: Se falhar ao conectar com Redis
        """
        try:
            full_key = self._make_key(key)
            data = self._client.get(full_key)

            if data is None:
                self.logger.debug(f"L2 cache miss: {key}")
                return None

            try:
                value = self.serializer.deserialize(data)
                self.logger.debug(f"L2 cache hit: {key}")
                return value
            except Exception as e:
                raise CacheSerializationError(
                    "Failed to deserialize cache data",
                    key=key,
                    serializer=type(self.serializer).__name__,
                    original_error=e,
                )

        except CacheSerializationError:
            raise
        except Exception as e:
            self.logger.error(f"L2 cache get error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to get key from Redis: {key}",
                backend="redis",
                original_error=e,
            )

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena valor no Redis.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado
            ttl: Time-to-live em segundos (usa config.ttl se None)

        Raises:
            CacheConnectionError: Se falhar ao conectar com Redis
            CacheSerializationError: Se falhar ao serializar
        """
        try:
            full_key = self._make_key(key)
            try:
                data = self.serializer.serialize(value)
            except Exception as e:
                raise CacheSerializationError(
                    "Failed to serialize cache data",
                    key=key,
                    serializer=type(self.serializer).__name__,
                    original_error=e,
                )
            ttl_seconds = ttl if ttl is not None else self.config.ttl

            self._client.setex(full_key, ttl_seconds, data)
            self.logger.debug(f"L2 cache set: {key} (ttl={ttl_seconds}s)")

        except CacheSerializationError:
            raise
        except Exception as e:
            self.logger.error(f"L2 cache set error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to set key in Redis: {key}",
                backend="redis",
                original_error=e,
            )

    def delete(self, key: str) -> None:
        """
        Remove valor do Redis.

        Args:
            key: Chave para remover

        Raises:
            CacheConnectionError: Se falhar ao conectar com Redis
        """
        try:
            full_key = self._make_key(key)
            self._client.delete(full_key)
            self.logger.debug(f"L2 cache delete: {key}")

        except Exception as e:
            self.logger.error(f"L2 cache delete error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to delete key from Redis: {key}",
                backend="redis",
                original_error=e,
            )

    def clear(self) -> int:
        """
        Limpa todas as chaves com o prefixo configurado.

        Returns:
            Número de itens removidos

        Raises:
            CacheConnectionError: Se falhar ao conectar com Redis
        """
        try:
            pattern = f"{self.config.key_prefix}:*"
            keys = self._client.keys(pattern)

            if keys:
                deleted = self._client.delete(*keys)
                self.logger.info(f"L2 cache cleared: {deleted} items removed")
                return deleted

            return 0

        except Exception as e:
            self.logger.error(f"L2 cache clear error: {e}")
            raise CacheConnectionError(
                "Failed to clear Redis cache",
                backend="redis",
                original_error=e,
            )

    def exists(self, key: str) -> bool:
        """
        Verifica se chave existe no Redis.

        Args:
            key: Chave para verificar

        Returns:
            True se existe

        Raises:
            CacheConnectionError: Se falhar ao conectar com Redis
        """
        try:
            full_key = self._make_key(key)
            return bool(self._client.exists(full_key))

        except Exception as e:
            self.logger.error(f"L2 cache exists error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to check key existence in Redis: {key}",
                backend="redis",
                original_error=e,
            )

    def get_ttl(self, key: str) -> Optional[int]:
        """
        Obtém TTL restante de uma chave.

        Args:
            key: Chave para verificar

        Returns:
            TTL em segundos ou None se não existe

        Raises:
            CacheConnectionError: Se falhar ao conectar com Redis
        """
        try:
            full_key = self._make_key(key)
            ttl = self._client.ttl(full_key)

            # Redis retorna -2 se chave não existe, -1 se sem TTL
            if ttl < 0:
                return None

            return ttl

        except Exception as e:
            self.logger.error(f"L2 cache ttl error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to get TTL from Redis: {key}",
                backend="redis",
                original_error=e,
            )

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        Lista chaves no Redis.

        Args:
            prefix: Prefixo adicional para filtrar (além do key_prefix)

        Returns:
            Lista de chaves (sem o prefixo do config)

        Raises:
            CacheConnectionError: Se falhar ao conectar com Redis
        """
        try:
            if prefix:
                pattern = f"{self.config.key_prefix}:{prefix}*"
            else:
                pattern = f"{self.config.key_prefix}:*"

            keys = self._client.keys(pattern)

            # Remover prefixo das chaves retornadas
            prefix_len = len(self.config.key_prefix) + 1  # +1 para o ':'
            return [k.decode("utf-8")[prefix_len:] for k in keys]

        except Exception as e:
            self.logger.error(f"L2 cache list_keys error: {e}")
            raise CacheConnectionError(
                "Failed to list keys from Redis",
                backend="redis",
                original_error=e,
            )

    def get_size(self) -> int:
        """
        Obtém número de itens no cache.

        Returns:
            Número de itens com o prefixo configurado

        Raises:
            CacheConnectionError: Se falhar ao conectar com Redis
        """
        try:
            pattern = f"{self.config.key_prefix}:*"
            return len(self._client.keys(pattern))

        except Exception as e:
            self.logger.error(f"L2 cache get_size error: {e}")
            raise CacheConnectionError(
                "Failed to get size from Redis",
                backend="redis",
                original_error=e,
            )

    def get_stats(self) -> dict:
        """
        Retorna estatísticas do backend.

        Returns:
            Dicionário com estatísticas
        """
        try:
            info = self._client.info("stats")
            size = self.get_size()

            return {
                "backend": "Redis",
                "enabled": True,
                "host": self.config.host,
                "port": self.config.port,
                "db": self.config.db,
                "key_prefix": self.config.key_prefix,
                "ttl": self.config.ttl,
                "serializer": str(self.serializer),
                "size": size,
                "redis_stats": {
                    "total_connections_received": info.get("total_connections_received"),
                    "total_commands_processed": info.get("total_commands_processed"),
                    "keyspace_hits": info.get("keyspace_hits"),
                    "keyspace_misses": info.get("keyspace_misses"),
                },
            }

        except Exception as e:
            self.logger.error(f"L2 cache get_stats error: {e}")
            return {
                "backend": "Redis",
                "enabled": False,
                "error": str(e),
            }

    def ping(self) -> bool:
        """
        Testa conexão com Redis.

        Returns:
            True se conectado

        Raises:
            CacheConnectionError: Se falhar ao conectar
        """
        try:
            return self._client.ping()
        except Exception as e:
            raise CacheConnectionError(
                f"Failed to ping Redis at {self.config.host}:{self.config.port}",
                backend="redis",
                original_error=e,
            )

    def close(self) -> None:
        """Fecha a conexão com Redis."""
        try:
            self._client.close()
            self.logger.info("Redis connection closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis connection: {e}")

    def __repr__(self) -> str:
        """Representação string do backend."""
        return (
            f"<RedisBackend {self.config.host}:{self.config.port} "
            f"db={self.config.db} prefix={self.config.key_prefix}>"
        )
