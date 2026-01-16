"""
Cache resiliente em dois níveis (L1 + L2).

Implementa a coordenação entre cache local (L1) e distribuído (L2)
com fallback gracioso e circuit breaker.
"""

import logging
from typing import Any, List, Optional

from .app_cache import AppCache
from .backends.base import CacheBackend
from .circuit_breaker import CircuitBreaker
from .config import CacheConfig
from .exceptions import (
    CacheConnectionError,
    CacheSerializationError,
)


class ResilientTwoLevelCache(AppCache):
    """
    Cache resiliente em dois níveis (L1 + L2).

    Características:
    - Write-through: Escreve em L1 e L2 simultaneamente
    - Cache promotion: Hits em L2 são promovidos para L1
    - Fallback gracioso: Se L2 falhar, continua com L1
    - Circuit breaker: Protege contra falhas repetidas do L2

    Example:
        >>> from resilient_cache import ResilientTwoLevelCache, CacheConfig
        >>> config = CacheConfig(...)
        >>> cache = ResilientTwoLevelCache(config)
        >>>
        >>> # Usar o cache
        >>> value = cache.get("my_key")
        >>> if value is None:
        ...     value = expensive_computation()
        ...     cache.set("my_key", value)
    """

    def __init__(self, config: CacheConfig) -> None:
        """
        Inicializa o cache em dois níveis.

        Args:
            config: Configuração completa do cache
        """
        self.config = config
        self.logger = config.logger or logging.getLogger(__name__)

        # Inicializar backends
        self._l1_backend: Optional[CacheBackend] = None
        self._l2_backend: Optional[CacheBackend] = None

        # Inicializar L1 se habilitado e factory disponível
        if config.l1.enabled and config.l1_backend_factory:
            try:
                self._l1_backend = config.l1_backend_factory(config.l1)
                self.logger.info("L1 cache initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize L1 cache: {e}")
                self._l1_backend = None

        # Inicializar L2 se habilitado e factory disponível
        if config.l2.enabled and config.l2_backend_factory:
            try:
                self._l2_backend = config.l2_backend_factory(config.l2)
                self.logger.info("L2 cache initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize L2 cache: {e}")
                self._l2_backend = None

        # Inicializar circuit breaker
        self._circuit_breaker = CircuitBreaker(
            config=config.circuit_breaker,
            logger=self.logger,
        )

        # Log final do estado
        self.logger.info(
            f"Cache initialized: L1={'enabled' if self._l1_backend else 'disabled'}, "
            f"L2={'enabled' if self._l2_backend else 'disabled'}"
        )

    def get(self, key: str) -> Any:
        """
        Busca valor no cache.

        Ordem de busca:
        1. L1 (cache local) - extremamente rápido
        2. L2 (cache distribuído) - rápido e compartilhado
        3. None (cache miss)

        Se encontrado no L2, promove para L1 automaticamente.

        Args:
            key: Chave para buscar

        Returns:
            Valor armazenado ou None se não encontrado
        """
        # Tentar L1 primeiro
        if self._l1_backend:
            try:
                value = self._l1_backend.get(key)
                if value is not None:
                    self.logger.debug(f"L1 hit: {key}")
                    return value
            except Exception as e:
                self.logger.warning(f"L1 get error for {key}: {e}")

        # Tentar L2 se L1 miss
        if self._l2_backend and not self._circuit_breaker.is_open():
            try:
                value = self._l2_backend.get(key)

                if value is not None:
                    self.logger.debug(f"L2 hit: {key}")

                    # Promover para L1 (cache promotion)
                    if self._l1_backend:
                        try:
                            self._l1_backend.set(key, value)
                            self.logger.debug(f"Promoted {key} to L1")
                        except Exception as e:
                            self.logger.warning(f"Failed to promote {key} to L1: {e}")

                    # Registrar sucesso no circuit breaker
                    self._circuit_breaker.record_success()

                    return value

                # Miss em L2 também é sucesso (não é erro)
                self._circuit_breaker.record_success()

            except (CacheConnectionError, CacheSerializationError) as e:
                self.logger.warning(f"L2 get error for {key}: {e}")
                self._circuit_breaker.record_failure()

            except Exception as e:
                self.logger.error(f"Unexpected L2 error for {key}: {e}")
                self._circuit_breaker.record_failure()

        # Cache miss completo
        self.logger.debug(f"Cache miss: {key}")
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Armazena valor no cache.

        Estratégia write-through: escreve em L1 e L2 simultaneamente.
        Se L2 falhar, continua com apenas L1.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado
        """
        # Armazenar em L1
        if self._l1_backend:
            try:
                self._l1_backend.set(key, value)
                self.logger.debug(f"Stored in L1: {key}")
            except Exception as e:
                self.logger.warning(f"L1 set error for {key}: {e}")

        # Armazenar em L2 (se circuit não estiver aberto)
        if self._l2_backend and not self._circuit_breaker.is_open():
            try:
                self._l2_backend.set(key, value)
                self.logger.debug(f"Stored in L2: {key}")

                # Registrar sucesso no circuit breaker
                self._circuit_breaker.record_success()

            except (CacheConnectionError, CacheSerializationError) as e:
                self.logger.warning(f"L2 set error for {key}: {e}")
                self._circuit_breaker.record_failure()

            except Exception as e:
                self.logger.error(f"Unexpected L2 set error for {key}: {e}")
                self._circuit_breaker.record_failure()

    def set_if_not_exist(self, key: str, value: Any) -> None:
        """
        Armazena valor no cache apenas se ele não existir.

        Estratégia:
        - Tenta L2 primeiro (fonte de verdade).
        - Se L2 aceitar, propaga para L1 (best-effort).
        - Se L2 estiver indisponível, faz fallback para L1.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado
        """
        if self._l2_backend and not self._circuit_breaker.is_open():
            try:
                if self._l2_backend.exists(key):
                    self.logger.debug(f"L2 set_if_not_exist skipped: {key} already exists")
                    self._circuit_breaker.record_success()
                    return

                self._l2_backend.set_if_not_exist(key, value)
                self.logger.debug(f"Stored in L2 if not exist: {key}")
                self._circuit_breaker.record_success()

                if self._l1_backend:
                    try:
                        self._l1_backend.set_if_not_exist(key, value)
                        self.logger.debug(f"Stored in L1 if not exist: {key}")
                    except Exception as e:
                        self.logger.warning(f"L1 set_if_not_exist error for {key}: {e}")
                return

            except (CacheConnectionError, CacheSerializationError) as e:
                self.logger.warning(f"L2 set_if_not_exist error for {key}: {e}")
                self._circuit_breaker.record_failure()

            except Exception as e:
                self.logger.error(f"Unexpected L2 set_if_not_exist error for {key}: {e}")
                self._circuit_breaker.record_failure()

        if self._l1_backend:
            try:
                self._l1_backend.set_if_not_exist(key, value)
                self.logger.debug(f"Stored in L1 if not exist: {key}")
            except Exception as e:
                self.logger.warning(f"L1 set_if_not_exist error for {key}: {e}")

    def delete(self, key: str) -> None:
        """
        Remove valor do cache.

        Remove de L2 e depois L1 (L2 como fonte de verdade).

        Args:
            key: Chave para remover
        """
        # Deletar de L2 (se circuit não estiver aberto)
        if self._l2_backend and not self._circuit_breaker.is_open():
            try:
                self._l2_backend.delete(key)
                self.logger.debug(f"Deleted from L2: {key}")

                # Registrar sucesso no circuit breaker
                self._circuit_breaker.record_success()

            except (CacheConnectionError, CacheSerializationError) as e:
                self.logger.warning(f"L2 delete error for {key}: {e}")
                self._circuit_breaker.record_failure()

            except Exception as e:
                self.logger.error(f"Unexpected L2 delete error for {key}: {e}")
                self._circuit_breaker.record_failure()

        # Deletar de L1
        if self._l1_backend:
            try:
                self._l1_backend.delete(key)
                self.logger.debug(f"Deleted from L1: {key}")
            except Exception as e:
                self.logger.warning(f"L1 delete error for {key}: {e}")

    def clear(self) -> dict:
        """
        Limpa todo o cache (L1 e L2).

        Returns:
            Dicionário com estatísticas antes da limpeza:
            {
                'l1_items_removed': int,
                'l2_items_removed': int,
                'timestamp': float
            }
        """
        import time

        stats = {
            "l1_items_removed": 0,
            "l2_items_removed": 0,
            "timestamp": time.time(),
        }

        # Limpar L1
        if self._l1_backend:
            try:
                stats["l1_items_removed"] = self._l1_backend.clear()
                self.logger.info(f"L1 cleared: {stats['l1_items_removed']} items")
            except Exception as e:
                self.logger.warning(f"L1 clear error: {e}")

        # Limpar L2 (se circuit não estiver aberto)
        if self._l2_backend and not self._circuit_breaker.is_open():
            try:
                stats["l2_items_removed"] = self._l2_backend.clear()
                self.logger.info(f"L2 cleared: {stats['l2_items_removed']} items")

                # Registrar sucesso no circuit breaker
                self._circuit_breaker.record_success()

            except (CacheConnectionError, CacheSerializationError) as e:
                self.logger.warning(f"L2 clear error: {e}")
                self._circuit_breaker.record_failure()

            except Exception as e:
                self.logger.error(f"Unexpected L2 clear error: {e}")
                self._circuit_breaker.record_failure()

        return stats

    def get_stats(self) -> dict:
        """
        Retorna estatísticas detalhadas do cache.

        Returns:
            Dicionário com estatísticas completas de L1, L2 e circuit breaker
        """
        stats = {
            "enabled": True,
            "l1": {"enabled": False},
            "l2": {"enabled": False},
            "circuit_breaker": self._circuit_breaker.get_stats(),
        }

        # Estatísticas do L1
        if self._l1_backend:
            try:
                stats["l1"] = self._l1_backend.get_stats()
            except Exception as e:
                self.logger.warning(f"Failed to get L1 stats: {e}")
                stats["l1"] = {"enabled": True, "error": str(e)}

        # Estatísticas do L2
        if self._l2_backend:
            try:
                stats["l2"] = self._l2_backend.get_stats()
            except Exception as e:
                self.logger.warning(f"Failed to get L2 stats: {e}")
                stats["l2"] = {"enabled": True, "error": str(e)}

        return stats

    def get_ttl(self, key: str) -> Optional[int]:
        """
        Obtém o TTL restante de uma chave.

        Verifica L1 primeiro, depois L2.

        Args:
            key: Chave para verificar

        Returns:
            TTL em segundos ou None se não encontrado
        """
        # Tentar L1 primeiro
        if self._l1_backend:
            try:
                ttl = self._l1_backend.get_ttl(key)
                if ttl is not None:
                    return ttl
            except Exception as e:
                self.logger.warning(f"L1 get_ttl error for {key}: {e}")

        # Tentar L2 se L1 miss
        if self._l2_backend and not self._circuit_breaker.is_open():
            try:
                ttl = self._l2_backend.get_ttl(key)
                self._circuit_breaker.record_success()
                return ttl
            except Exception as e:
                self.logger.warning(f"L2 get_ttl error for {key}: {e}")
                self._circuit_breaker.record_failure()

        return None

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        Lista chaves no cache.

        Retorna união das chaves de L1 e L2.

        Args:
            prefix: Prefixo opcional para filtrar

        Returns:
            Lista de chaves únicas
        """
        keys = set()

        # Listar chaves do L1
        if self._l1_backend:
            try:
                keys.update(self._l1_backend.list_keys(prefix))
            except Exception as e:
                self.logger.warning(f"L1 list_keys error: {e}")

        # Listar chaves do L2
        if self._l2_backend and not self._circuit_breaker.is_open():
            try:
                keys.update(self._l2_backend.list_keys(prefix))
                self._circuit_breaker.record_success()
            except Exception as e:
                self.logger.warning(f"L2 list_keys error: {e}")
                self._circuit_breaker.record_failure()

        return list(keys)

    def is_on_cache(self, key: str) -> bool:
        """
        Verifica se chave existe no cache.

        Verifica L1 primeiro, depois L2.

        Args:
            key: Chave para verificar

        Returns:
            True se existe em L1 ou L2
        """
        # Verificar L1 primeiro
        if self._l1_backend:
            try:
                if self._l1_backend.exists(key):
                    return True
            except Exception as e:
                self.logger.warning(f"L1 exists error for {key}: {e}")

        # Verificar L2 se não está em L1
        if self._l2_backend and not self._circuit_breaker.is_open():
            try:
                exists = self._l2_backend.exists(key)
                self._circuit_breaker.record_success()
                return exists
            except Exception as e:
                self.logger.warning(f"L2 exists error for {key}: {e}")
                self._circuit_breaker.record_failure()

        return False

    def __repr__(self) -> str:
        """Representação string do cache."""
        l1_status = "enabled" if self._l1_backend else "disabled"
        l2_status = "enabled" if self._l2_backend else "disabled"
        return f"<ResilientTwoLevelCache L1={l1_status} L2={l2_status}>"
