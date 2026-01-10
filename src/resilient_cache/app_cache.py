"""
Interface abstrata para caches da aplicação.

Define o contrato que todos os caches devem implementar,
permitindo trocar implementações sem afetar o código cliente.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class AppCache(ABC):
    """
    Interface comum para caches da aplicação.

    Esta classe abstrata define todos os métodos que qualquer implementação
    de cache deve fornecer, garantindo consistência e permitindo substituição
    transparente de implementações.
    """

    @abstractmethod
    def get(self, key: str) -> Any:
        """
        Busca um valor no cache.

        Para caches em dois níveis, a busca segue a ordem:
        1. L1 (cache local)
        2. L2 (cache distribuído)
        3. None (cache miss)

        Args:
            key: Chave para buscar no cache

        Returns:
            O valor armazenado, ou None se não encontrado

        Example:
            >>> value = cache.get("user_123")
            >>> if value is None:
            ...     value = fetch_from_database("user_123")
            ...     cache.set("user_123", value)
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Armazena um valor no cache.

        Para caches em dois níveis, usa estratégia write-through:
        armazena em L1 e L2 simultaneamente.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado

        Raises:
            CacheSerializationError: Se falhar ao serializar o valor
            CacheConnectionError: Se falhar ao conectar com L2 (mas continua com L1)

        Example:
            >>> cache.set("user_123", {"name": "João", "age": 30})
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Remove um valor do cache.

        Remove a chave tanto de L1 quanto de L2.

        Args:
            key: Chave para remover

        Example:
            >>> cache.delete("user_123")
        """
        pass

    @abstractmethod
    def clear(self) -> dict:
        """
        Limpa todo o cache e retorna estatísticas.

        Remove todas as chaves de L1 e L2.

        Returns:
            Dicionário com estatísticas antes da limpeza:
            - l1_size: Número de itens em L1
            - l2_size: Número de itens em L2 (se disponível)
            - timestamp: Timestamp da operação

        Example:
            >>> stats = cache.clear()
            >>> print(f"Removed {stats['l1_size']} items from L1")
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do cache.

        Returns:
            Dicionário com estatísticas detalhadas:
            {
                'enabled': bool,
                'l1': {
                    'enabled': bool,
                    'size': int,
                    'maxsize': int,
                    'ttl': int,
                    'backend': str
                },
                'l2': {
                    'enabled': bool,
                    'ttl': int,
                    'circuit_breaker': {
                        'state': str,  # 'closed', 'open', 'half_open'
                        'failure_count': int
                    }
                }
            }

        Example:
            >>> stats = cache.get_stats()
            >>> if stats['l1']['size'] / stats['l1']['maxsize'] > 0.9:
            ...     print("Warning: L1 cache is 90% full!")
        """
        pass

    @abstractmethod
    def get_ttl(self, key: str) -> Optional[int]:
        """
        Obtém o tempo de vida (TTL) restante de uma chave.

        Args:
            key: Chave para verificar

        Returns:
            TTL em segundos, ou None se a chave não existe ou não tem TTL

        Example:
            >>> ttl = cache.get_ttl("user_123")
            >>> if ttl and ttl < 60:
            ...     print("Key expires in less than 1 minute!")
        """
        pass

    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        Lista as chaves presentes no cache.

        Args:
            prefix: Prefixo opcional para filtrar chaves

        Returns:
            Lista de chaves encontradas

        Example:
            >>> # Listar todas as chaves
            >>> all_keys = cache.list_keys()
            >>> print(f"Total keys: {len(all_keys)}")
            >>>
            >>> # Listar apenas chaves de usuários
            >>> user_keys = cache.list_keys(prefix="user_")
            >>> print(f"User keys: {user_keys}")
        """
        pass

    @abstractmethod
    def is_on_cache(self, key: str) -> bool:
        """
        Verifica se uma chave existe no cache.

        Args:
            key: Chave para verificar

        Returns:
            True se a chave existe, False caso contrário

        Example:
            >>> if cache.is_on_cache("user_123"):
            ...     print("Cache hit!")
            ... else:
            ...     print("Cache miss - will fetch from database")
        """
        pass

    def __repr__(self) -> str:
        """Representação string do cache."""
        stats = self.get_stats()
        return f"<{self.__class__.__name__} enabled={stats.get('enabled', False)}>"
