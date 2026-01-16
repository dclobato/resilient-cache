"""Estratégias de serialização para cache distribuído.

Este módulo fornece diferentes estratégias de serialização para armazenar
objetos Python no cache distribuído (Valkey/Redis).
"""
import json
import pickle
from abc import ABC, abstractmethod
from typing import Any


class CacheSerializer(ABC):
    """Interface abstrata para estratégias de serialização de cache."""

    @abstractmethod
    def serialize(self, value: Any) -> bytes:
        """Serializa um valor Python para bytes.

        Args:
            value: Valor a ser serializado.

        Returns:
            bytes: Valor serializado.

        Raises:
            Exception: Se a serialização falhar.
        """
        pass

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Desserializa bytes de volta para um valor Python.

        Args:
            data (bytes): Dados serializados.

        Returns:
            Any: Valor Python desserializado.

        Raises:
            Exception: Se a desserialização falhar.
        """
        pass


class PickleSerializer(CacheSerializer):
    """Serialização com pickle.

    Pickle suporta qualquer objeto Python (dataclasses, tuplas, bytes, etc.)
    mas não é human-readable.

    **Uso recomendado:** Objetos complexos como ImageProcessingResult,
    StaticMapResponse, bytes base64, etc.

    **Segurança:** Pickle pode executar código arbitrário durante desserialização.
    Use apenas com dados confiáveis.
    """
    def __repr__(self) -> str:
        return "PickleSerializer()"

    def serialize(self, value: Any) -> bytes:
        """Serializa usando pickle com protocolo mais recente.

        Args:
            value: Valor a ser serializado.

        Returns:
            bytes: Valor serializado com pickle.
        """
        try:
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        except pickle.PicklingError as e:
            raise ValueError(f"Erro ao serializar com pickle: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        """Desserializa bytes pickle de volta para objeto Python.

        Args:
            data (bytes): Dados serializados com pickle.

        Returns:
            Any: Objeto Python desserializado.
        """
        try:
            return pickle.loads(data)
        except pickle.UnpicklingError as e:
            raise ValueError(f"Erro ao desserializar com pickle: {e}") from e


class JsonSerializer(CacheSerializer):
    """Serialização com JSON.

    JSON é human-readable e seguro, mas suporta apenas tipos JSON-safe
    (dict, list, str, int, float, bool, None).

    **Uso recomendado:** Dicionários simples, listas, dados estatísticos.

    **Limitações:** Não suporta dataclasses, bytes, tuplas nativas, etc.
    """
    def __repr__(self) -> str:
        return "JsonSerializer()"

    def serialize(self, value: Any) -> bytes:
        """Serializa usando JSON.

        Args:
            value: Valor a ser serializado (deve ser JSON-safe).

        Returns:
            bytes: Valor serializado em JSON (UTF-8).

        Raises:
            TypeError: Se o valor não for JSON-safe.
        """
        try:
            return json.dumps(value, ensure_ascii=False).encode('utf-8')
        except Exception as e:
            raise ValueError(f"Erro ao serializar com JSON: {e}") from e

    def deserialize(self, data: bytes) -> Any:
        """Desserializa bytes JSON de volta para objeto Python.

        Args:
            data (bytes): Dados JSON em UTF-8.

        Returns:
            Any: Objeto Python (dict, list, str, int, float, bool, None).
        """
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise ValueError(f"Erro ao desserializar com JSON: {e}") from e


# Registro global de serializers disponíveis
_SERIALIZER_REGISTRY: dict[str, type[CacheSerializer]] = {
    'pickle': PickleSerializer,
    'json': JsonSerializer,
}


def register_serializer(name: str, serializer_class: type[CacheSerializer]) -> None:
    """
    Registra um serializer customizado.

    Args:
        name: Nome identificador do serializer
        serializer_class: Classe que implementa CacheSerializer

    Raises:
        TypeError: Se serializer_class não for subclasse de CacheSerializer

    Example:
        >>> class MsgPackSerializer(CacheSerializer):
        ...     def serialize(self, value): ...
        ...     def deserialize(self, data): ...
        >>>
        >>> register_serializer('msgpack', MsgPackSerializer)
    """
    if not issubclass(serializer_class, CacheSerializer):
        raise TypeError(
            f"serializer_class must be a subclass of CacheSerializer, "
            f"got {serializer_class}"
        )
    _SERIALIZER_REGISTRY[name] = serializer_class


def get_serializer(name: str) -> CacheSerializer:
    """
    Obtém uma instância de serializer pelo nome.

    Args:
        name: Nome do serializer registrado

    Returns:
        Instância do serializer

    Raises:
        ValueError: Se o serializer não estiver registrado

    Example:
        >>> serializer = get_serializer('json')
        >>> serializer = get_serializer('pickle')
    """
    if name not in _SERIALIZER_REGISTRY:
        available = ', '.join(_SERIALIZER_REGISTRY.keys())
        raise ValueError(
            f"Unknown serializer '{name}'. "
            f"Available serializers: {available}"
        )

    serializer_class = _SERIALIZER_REGISTRY[name]
    return serializer_class()


def list_serializers() -> list[str]:
    """
    Lista todos os serializers registrados.

    Returns:
        Lista de nomes de serializers disponíveis

    Example:
        >>> list_serializers()
        ['pickle', 'json']
    """
    return list(_SERIALIZER_REGISTRY.keys())