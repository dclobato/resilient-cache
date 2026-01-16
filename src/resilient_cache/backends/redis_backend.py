"""
Backend de cache L2 usando Redis/Valkey.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Protocol, cast

from ..config import L2Config
from ..exceptions import (
    CacheConfigurationError,
    CacheConnectionError,
    CacheSerializationError,
)
from ..serializers import CacheSerializer
from .base import CacheBackend

try:
    import valkey

    VALKEY_AVAILABLE = True
except ImportError:
    VALKEY_AVAILABLE = False
    valkey = None  # type: ignore


class SyncValkeyClient(Protocol):
    # NOTE: valkey typing stubs return ResponseT = Union[Awaitable[Any], Any],
    # which makes mypy treat sync calls as possibly async. We define a local
    # sync protocol to keep this backend fully synchronous and avoid Awaitable
    # propagation in type checking.
    def get(self, key: str) -> bytes | None: ...
    def setex(self, key: str, time: int, value: bytes) -> Any: ...
    def set(self, key: str, value: bytes, nx: bool = False, ex: int | None = None) -> Any: ...
    def delete(self, *keys: str | bytes) -> int: ...

    def scan(
        self, cursor: int = 0, match: str | None = None, count: int = 10
    ) -> tuple[int, list[bytes]]: ...
    def exists(self, key: str) -> int: ...
    def ttl(self, key: str) -> int: ...
    def info(self, section: str) -> dict: ...
    def ping(self) -> bool: ...
    def close(self) -> None: ...


class RedisBackend(CacheBackend):
    """
    Backend L2 usando Valkey/Redis.

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
        Inicializa o backend Valkey.

        Args:
            config: Configuração do L2
            serializer: Instância de CacheSerializer para serialização de dados
            logger: Logger opcional
        """
        self.config = config
        self.serializer = serializer
        self.logger = logger or logging.getLogger(__name__)
        self._client: Optional[SyncValkeyClient] = None

        self._connect()

    def _connect(self) -> None:
        """Conecta ao servidor Redis/Valkey.

        Raises:
            CacheConfigurationError: Se valkey library não estiver disponível
            CacheConnectionError: Se falhar ao conectar com Valkey
        """
        if not VALKEY_AVAILABLE:
            raise CacheConfigurationError(
                "`valkey` library not available. Please install it to use RedisBackend.",
                config_key="l2_backend",
                config_value="redis",
            )

        # Criar conexão Valkey
        try:
            client = cast(
                SyncValkeyClient,
                valkey.Valkey(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    password=self.config.password,
                    socket_connect_timeout=self.config.connect_timeout,
                    socket_timeout=self.config.socket_timeout,
                    decode_responses=False,  # Trabalha com bytes
                ),
            )

            # Testar conexão
            client.ping()
            self._client = client
        except Exception as e:
            raise CacheConnectionError(
                f"Failed to connect to Valkey at {self.config.host}:{self.config.port}",
                backend="redis",
                original_error=e,
            )

    def _is_connected(self) -> bool:
        """Verifica se ha conexao ativa com o Valkey."""
        if self._client is None:
            return False
        try:
            self._client.ping()
            return True
        except Exception:
            return False

    def _ensure_connected(self) -> None:
        """Garante que ha conexao ativa (reconecta se necessario)."""
        if self._is_connected():
            return

        try:
            self._connect()
        except (CacheConnectionError, CacheConfigurationError):
            self._client = None
            raise

    def _get_client(self) -> SyncValkeyClient:
        """Obtém cliente Valkey.

        Returns:
            SyncValkeyClient: Cliente Valkey pronto para uso.
        """
        if not VALKEY_AVAILABLE:
            raise CacheConfigurationError(
                "`valkey` library not available. Please install it to use RedisBackend.",
                config_key="l2_backend",
                config_value="redis",
            )

        try:
            self._ensure_connected()
            if self._client is None:
                raise CacheConnectionError(
                    f"Failed to connect to Valkey/Redis at {self.config.host}:{self.config.port}",
                    backend="redis",
                )
            return self._client
        except Exception as exc:
            raise CacheConnectionError(
                f"Failed to connect to Valkey/Redis at {self.config.host}:{self.config.port}",
                backend="redis",
                original_error=exc,
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
        Busca valor no Valkey.

        Args:
            key: Chave para buscar

        Returns:
            Valor armazenado ou None se não encontrado

        Raises:
            CacheConnectionError: Se falhar ao conectar com Valkey
        """
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            data = client.get(full_key)

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
                f"Failed to get key from Valkey: {key}",
                backend="redis",
                original_error=e,
            )

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena valor no Valkey.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado
            ttl: Time-to-live em segundos (usa config.ttl se None)

        Raises:
            CacheConnectionError: Se falhar ao conectar com Valkey
            CacheSerializationError: Se falhar ao serializar
        """
        try:
            client = self._get_client()
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

            client.setex(full_key, time=ttl_seconds, value=data)
            self.logger.debug(f"L2 cache set: {key} (ttl={ttl_seconds}s)")

        except CacheSerializationError:
            raise
        except Exception as e:
            self.logger.error(f"L2 cache set error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to set key in Valkey: {key}",
                backend="redis",
                original_error=e,
            )

    def set_if_not_exist(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena valor no Valkey apenas se não existir.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado
            ttl: Time-to-live em segundos (usa config.ttl se None)

        Raises:
            CacheConnectionError: Se falhar ao conectar com Valkey
            CacheSerializationError: Se falhar ao serializar
        """
        try:
            client = self._get_client()
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

            client.set(full_key, data, nx=True, ex=ttl_seconds)
            self.logger.debug(f"L2 cache set: {key} (ttl={ttl_seconds}s)")

        except CacheSerializationError:
            raise
        except Exception as e:
            self.logger.error(f"L2 cache set error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to set key in Valkey: {key}",
                backend="redis",
                original_error=e,
            )

    def delete(self, key: str) -> None:
        """
        Remove valor do Valkey.

        Args:
            key: Chave para remover

        Raises:
            CacheConnectionError: Se falhar ao conectar com Valkey
        """
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            client.delete(full_key)
            self.logger.debug(f"L2 cache delete: {key}")

        except Exception as e:
            self.logger.error(f"L2 cache delete error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to delete key from Valkey: {key}",
                backend="redis",
                original_error=e,
            )

    def clear(self) -> int:
        """
        Limpa todas as chaves com o prefixo configurado.

        Returns:
            Número de itens removidos

        Raises:
            CacheConnectionError: Se falhar ao conectar com Valkey
        """
        try:
            client = self._get_client()
            pattern = f"{self.config.key_prefix}:*"

            # Usa SCAN para não bloquear Valkey
            cursor = 0
            total_deleted = 0

            while True:
                cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)

                if keys:
                    deleted = client.delete(*keys)
                    total_deleted += deleted

                if cursor == 0:
                    break

            self.logger.info(f"L2 cache cleared: {total_deleted} items removed")
            return total_deleted

        except Exception as e:
            self.logger.error(f"L2 cache clear error: {e}")
            raise CacheConnectionError(
                "Failed to clear Valkey cache",
                backend="redis",
                original_error=e,
            )

    def exists(self, key: str) -> bool:
        """
        Verifica se chave existe no Valkey.

        Args:
            key: Chave para verificar

        Returns:
            True se existe

        Raises:
            CacheConnectionError: Se falhar ao conectar com Valkey
        """
        try:
            client = self._get_client()
            valkey_key = self._make_key(key)
            return bool(client.exists(valkey_key))

        except Exception as e:
            self.logger.error(f"L2 cache exists error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to check key existence in Valkey: {key}",
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
            CacheConnectionError: Se falhar ao conectar com Valkey
        """
        try:
            client = self._get_client()
            full_key = self._make_key(key)
            ttl = client.ttl(full_key)

            # Valkey retorna -2 se chave não existe, -1 se sem TTL
            if ttl < 0:
                return None

            return ttl

        except Exception as e:
            self.logger.error(f"L2 cache ttl error for key {key}: {e}")
            raise CacheConnectionError(
                f"Failed to get TTL from Valkey: {key}",
                backend="redis",
                original_error=e,
            )

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        Lista chaves no Valkey.

        Args:
            prefix: Prefixo adicional para filtrar (além do key_prefix)

        Returns:
            Lista de chaves (sem o prefixo do config)

        Raises:
            CacheConnectionError: Se falhar ao conectar com Valkey
        """
        try:
            if prefix:
                pattern = f"{self.config.key_prefix}:{prefix}*"
            else:
                pattern = f"{self.config.key_prefix}:*"
            client = self._get_client()
            results = []
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)

                for key in keys:
                    if isinstance(key, bytes):
                        key_str = key.decode("utf-8")
                    else:
                        key_str = key
                    raw_key = key_str.split(f"{self.config.key_prefix}:", 1)[-1]
                    results.append(raw_key)

                if cursor == 0:
                    break
            return results

        except Exception as e:
            self.logger.error(f"L2 cache list_keys error: {e}")
            raise CacheConnectionError(
                "Failed to list keys from Valkey",
                backend="redis",
                original_error=e,
            )

    def get_size(self) -> int:
        """
        Obtém número de itens no cache.

        Returns:
            Número de itens com o prefixo configurado

        Raises:
            CacheConnectionError: Se falhar ao conectar com Valkey
        """
        try:
            client = self._get_client()
            pattern = f"{self.config.key_prefix}:*"

            # Usa SCAN para não bloquear Valkey
            cursor = 0
            total = 0

            while True:
                cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)

                if keys:
                    total += len(keys)

                if cursor == 0:
                    break

            return total

        except Exception as e:
            self.logger.error(f"L2 cache get_size error: {e}")
            raise CacheConnectionError(
                "Failed to get size from Valkey",
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
            client = self._get_client()
            info = client.info("stats")
            size = self.get_size()

            return {
                "backend": "Valkey",
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
                "backend": "Valkey",
                "enabled": False,
                "error": str(e),
            }

    def ping(self) -> bool:
        """
        Testa conexão com Valkey.

        Returns:
            True se conectado

        Raises:
            CacheConnectionError: Se falhar ao conectar
        """
        try:
            client = self._get_client()
            return client.ping()

        except Exception as e:
            raise CacheConnectionError(
                f"Failed to ping Valkey at {self.config.host}:{self.config.port}",
                backend="redis",
                original_error=e,
            )

    def close(self) -> None:
        """Fecha a conexão com Valkey."""
        if self._client is None:
            return

        try:
            if hasattr(self._client, "close"):
                self._client.close()
            if hasattr(self._client, "connection_pool"):
                self._client.connection_pool.disconnect()
        except Exception as e:
            self.logger.error(f"Error closing Valkey connection: {e}")
        finally:
            self._client = None

    def __repr__(self) -> str:
        """Representação string do backend."""
        return (
            f"<RedisBackend {self.config.host}:{self.config.port} "
            f"db={self.config.db} prefix={self.config.key_prefix}>"
        )
