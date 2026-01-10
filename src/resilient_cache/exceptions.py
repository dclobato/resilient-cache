"""
Exceções customizadas para o sistema de cache.
"""

from typing import Any, Optional


class CacheError(Exception):
    """Exceção base para erros do sistema de cache."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:  # noqa: B042
        """
        Inicializa a exceção.

        Args:
            message: Mensagem de erro
            details: Detalhes adicionais sobre o erro
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class CacheConnectionError(CacheError):
    """Erro de conexão com o backend de cache (L2)."""

    def __init__(  # noqa: B042
        self,
        message: str = "Failed to connect to cache backend",
        backend: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """
        Inicializa erro de conexão.

        Args:
            message: Mensagem de erro
            backend: Nome do backend que falhou
            original_error: Exceção original que causou o erro
        """
        details = {}
        if backend:
            details["backend"] = backend
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(message, details)
        self.backend = backend
        self.original_error = original_error


class CacheSerializationError(CacheError):
    """Erro de serialização/deserialização de dados."""

    def __init__(  # noqa: B042
        self,
        message: str = "Failed to serialize/deserialize cache data",
        key: Optional[str] = None,
        serializer: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """
        Inicializa erro de serialização.

        Args:
            message: Mensagem de erro
            key: Chave do cache que causou o erro
            serializer: Nome do serializador usado
            original_error: Exceção original que causou o erro
        """
        details = {}
        if key:
            details["key"] = key
        if serializer:
            details["serializer"] = serializer
        if original_error:
            details["original_error"] = str(original_error)
            details["error_type"] = type(original_error).__name__

        super().__init__(message, details)
        self.key = key
        self.serializer = serializer
        self.original_error = original_error


class CacheConfigurationError(CacheError):
    """Erro de configuração do cache."""

    def __init__(  # noqa: B042
        self,
        message: str = "Invalid cache configuration",
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
    ) -> None:
        """
        Inicializa erro de configuração.

        Args:
            message: Mensagem de erro
            config_key: Chave de configuração inválida
            config_value: Valor de configuração inválido
        """
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_value:
            details["config_value"] = str(config_value)

        super().__init__(message, details)
        self.config_key = config_key
        self.config_value = config_value


class CircuitBreakerOpenError(CacheError):
    """Erro quando o circuit breaker está aberto."""

    def __init__(  # noqa: B042
        self,
        message: str = "Circuit breaker is open",
        backend: Optional[str] = None,
        failure_count: Optional[int] = None,
    ) -> None:
        """
        Inicializa erro de circuit breaker.

        Args:
            message: Mensagem de erro
            backend: Nome do backend afetado
            failure_count: Número de falhas consecutivas
        """
        details: dict[str, Any] = {}
        if backend:
            details["backend"] = backend
        if failure_count is not None:
            details["failure_count"] = failure_count

        super().__init__(message, details)
        self.backend = backend
        self.failure_count = failure_count
