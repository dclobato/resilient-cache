"""
Interface base para backends de cache.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class CacheBackend(ABC):
    """
    Interface abstrata para backends de cache.

    Define o contrato que todos os backends (L1 e L2) devem implementar.
    """

    @abstractmethod
    def get(self, key: str) -> Any:
        """
        Busca um valor no backend.

        Args:
            key: Chave para buscar

        Returns:
            O valor armazenado, ou None se não encontrado
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena um valor no backend.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado
            ttl: Time-to-live em segundos (opcional)
        """
        pass

    @abstractmethod
    def set_if_not_exist(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Armazena um valor no backend apenas se ele não existir.

        Args:
            key: Chave para armazenar
            value: Valor a ser armazenado
            ttl: Time-to-live em segundos (opcional)
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Remove um valor do backend.

        Args:
            key: Chave para remover
        """
        pass

    @abstractmethod
    def clear(self) -> int:
        """
        Limpa todo o cache.

        Returns:
            Número de itens removidos
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Verifica se uma chave existe no backend.

        Args:
            key: Chave para verificar

        Returns:
            True se existe, False caso contrário
        """
        pass

    @abstractmethod
    def get_ttl(self, key: str) -> Optional[int]:
        """
        Obtém o TTL restante de uma chave.

        Args:
            key: Chave para verificar

        Returns:
            TTL em segundos, ou None se não existe ou sem TTL
        """
        pass

    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        Lista chaves no backend.

        Args:
            prefix: Prefixo opcional para filtrar

        Returns:
            Lista de chaves
        """
        pass

    @abstractmethod
    def get_size(self) -> int:
        """
        Obtém o número de itens no cache.

        Returns:
            Número de itens
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict:
        """
        Retorna estatísticas do backend.

        Returns:
            Dicionário com estatísticas específicas do backend
        """
        pass

    def __repr__(self) -> str:
        """Representação string do backend."""
        return f"<{self.__class__.__name__}>"
