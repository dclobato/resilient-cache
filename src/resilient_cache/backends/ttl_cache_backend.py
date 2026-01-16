"""
Backend de cache L1 usando cachetools.TTLCache.
"""

import logging
from threading import RLock
from typing import Any, List, Optional

from ..config import L1Config
from ..exceptions import CacheConfigurationError
from .base import CacheBackend

try:
    from cachetools import TTLCache

    CACHETOOLS_AVAILABLE = True
except ImportError:
    CACHETOOLS_AVAILABLE = False
    TTLCache = None  # type: ignore


class TTLCacheBackend(CacheBackend):
    """
    Backend L1 usando cachetools.TTLCache.

    Implementa cache em memória com Time-To-Live (TTL) por item.
    Extremamente rápido (< 1ms) mas limitado ao processo atual.
    """

    def __init__(self, config: L1Config, logger: Optional[logging.Logger] = None) -> None:
        """
        Inicializa o backend TTLCache.

        Args:
            config: Configuração do L1
            logger: Logger opcional

        Raises:
            CacheConfigurationError: Se cachetools não estiver disponível
        """
        if not CACHETOOLS_AVAILABLE:
            raise CacheConfigurationError(
                "`cachetools` library not available. Please install it to use TTLCacheBackend.",
                config_key="l1_backend",
                config_value="ttl",
            )

        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        # Criar cache com maxsize e ttl configurados
        self._cache: TTLCache = TTLCache(maxsize=config.maxsize, ttl=config.ttl)
        self._hits = 0
        self._misses = 0

        self._lock = RLock()

        self.logger.info(f"TTLCache initialized: maxsize={config.maxsize}, ttl={config.ttl}s")

    def get(self, key: str) -> Any:
        """
        Busca valor no cache.

        Args:
            key: Chave para buscar

        Returns:
            Valor armazenado ou None se não encontrado
        """
        try:
            with self._lock:
                value = self._cache[key]
            self._hits += 1
            self.logger.debug(f"L1 cache hit: {key}")
            return value
        except KeyError:
            self._misses += 1
            self.logger.debug(f"L1 cache miss: {key}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena valor no cache.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado
            ttl: TTL não é usado aqui (TTLCache usa TTL global)

        Note:
            TTLCache usa um TTL global definido na criação.
            O parâmetro ttl é ignorado.
        """
        with self._lock:
            self._cache[key] = value
        self.logger.debug(f"L1 cache set: {key}")

    def delete(self, key: str) -> None:
        """
        Remove valor do cache.

        Args:
            key: Chave para remover
        """
        try:
            with self._lock:
                del self._cache[key]
            self.logger.debug(f"L1 cache delete: {key}")
        except KeyError:
            # Chave não existe, ignorar
            pass

    def clear(self) -> int:
        """
        Limpa todo o cache.

        Returns:
            Número de itens removidos
        """
        size = len(self._cache)
        with self._lock:
            self._cache.clear()
        self.logger.info(f"L1 cache cleared: {size} items removed")
        return size

    def exists(self, key: str) -> bool:
        """
        Verifica se chave existe.

        Args:
            key: Chave para verificar

        Returns:
            True se existe
        """
        with self._lock:
            r = key in self._cache
        return r

    def get_ttl(self, key: str) -> Optional[int]:
        """
        Obtém TTL restante de uma chave.

        Args:
            key: Chave para verificar

        Returns:
            TTL em segundos (aproximado) ou None se não existe

        Note:
            TTLCache não expõe TTL por item diretamente.
            Retorna o TTL global se a chave existe.
        """
        r = None
        with self._lock:
            if key in self._cache:
                # Estimativa: retorna o TTL global
                r = self.config.ttl
        return r

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        Lista chaves no cache.

        Args:
            prefix: Prefixo opcional para filtrar

        Returns:
            Lista de chaves
        """
        with self._lock:
            keys = list(self._cache.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    def get_size(self) -> int:
        """
        Obtém número de itens no cache.

        Returns:
            Número de itens
        """
        with self._lock:
            r = len(self._cache)
        return r

    def get_stats(self) -> dict:
        """
        Retorna estatísticas do backend.

        Returns:
            Dicionário com estatísticas
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0

        return {
            "backend": "TTLCache",
            "enabled": True,
            "size": len(self._cache),
            "maxsize": self.config.maxsize,
            "ttl": self.config.ttl,
            "hits": self._hits,
            "misses": self._misses,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 2),
            "usage_percent": round(len(self._cache) / self.config.maxsize * 100, 2),
        }

    def __repr__(self) -> str:
        """Representação string do backend."""
        return (
            f"<TTLCacheBackend size={len(self._cache)}/{self.config.maxsize} "
            f"ttl={self.config.ttl}s>"
        )
