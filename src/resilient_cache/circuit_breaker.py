"""
Circuit Breaker para proteção do backend L2.

Implementa o padrão Circuit Breaker para proteger a aplicação
de falhas repetidas no backend L2 (Redis/Valkey).
"""

import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

from .config import CircuitBreakerConfig
from .exceptions import CircuitBreakerOpenError


class CircuitState(Enum):
    """Estados possíveis do circuit breaker."""

    CLOSED = "closed"  # Operação normal
    OPEN = "open"  # Circuit aberto, não tenta operações
    HALF_OPEN = "half_open"  # Testando se pode fechar


class CircuitBreaker:
    """
    Circuit Breaker para proteção contra falhas do L2.

    O circuit breaker monitora falhas consecutivas e:
    - CLOSED: Opera normalmente
    - OPEN: Após threshold falhas, abre e não tenta L2
    - HALF_OPEN: Após timeout, testa uma requisição

    Example:
        >>> config = CircuitBreakerConfig(threshold=5, timeout=60)
        >>> breaker = CircuitBreaker(config)
        >>>
        >>> @breaker.protected
        ... def call_redis():
        ...     return redis_client.get("key")
        >>>
        >>> try:
        ...     value = call_redis()
        ... except CircuitBreakerOpenError:
        ...     print("Circuit is open, using fallback")
    """

    def __init__(
        self,
        config: CircuitBreakerConfig,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Inicializa o circuit breaker.

        Args:
            config: Configuração do circuit breaker
            logger: Logger opcional
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None

    @property
    def state(self) -> CircuitState:
        """
        Estado atual do circuit breaker.

        Automaticamente transita de OPEN para HALF_OPEN após timeout.
        """
        if not self.config.enabled:
            return CircuitState.CLOSED

        # Se está OPEN, verificar se deve ir para HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker entering HALF_OPEN state")

        return self._state

    def _should_attempt_reset(self) -> bool:
        """
        Verifica se deve tentar reset (OPEN -> HALF_OPEN).

        Returns:
            True se passou tempo suficiente desde última falha
        """
        if self._last_failure_time is None:
            return False

        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.config.timeout

    def record_success(self) -> None:
        """
        Registra uma operação bem-sucedida.

        Se estava em HALF_OPEN, fecha o circuit.
        """
        if not self.config.enabled:
            return

        self._last_success_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self.logger.info("Circuit breaker CLOSED after successful test")

        elif self._state == CircuitState.CLOSED:
            # Reset failure count em caso de sucesso
            if self._failure_count > 0:
                self.logger.debug(f"Resetting failure count from {self._failure_count} to 0")
                self._failure_count = 0

    def record_failure(self) -> None:
        """
        Registra uma falha.

        Se atingir threshold, abre o circuit.
        """
        if not self.config.enabled:
            return

        self._failure_count += 1
        self._last_failure_time = time.time()

        self.logger.warning(
            f"Circuit breaker failure {self._failure_count}/{self.config.threshold}"
        )

        # Se estava em HALF_OPEN, volta para OPEN imediatamente
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self.logger.error("Circuit breaker OPEN after failed test in HALF_OPEN")

        # Se atingiu threshold, abre o circuit
        elif self._failure_count >= self.config.threshold:
            self._state = CircuitState.OPEN
            self.logger.error(
                f"Circuit breaker OPEN after {self._failure_count} failures "
                f"(threshold={self.config.threshold})"
            )

    def is_open(self) -> bool:
        """
        Verifica se o circuit está aberto.

        Returns:
            True se o circuit está OPEN (não deve tentar operação)
        """
        return self.state == CircuitState.OPEN

    def protected(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator para proteger uma função com circuit breaker.

        Args:
            func: Função a ser protegida

        Returns:
            Função decorada

        Raises:
            CircuitBreakerOpenError: Se o circuit está aberto
            Exception: Qualquer exceção da função original

        Example:
            >>> @breaker.protected
            ... def risky_operation():
            ...     return redis_client.get("key")
        """

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Se circuit está aberto, não tenta
            if self.is_open():
                raise CircuitBreakerOpenError(
                    backend="L2",
                    failure_count=self._failure_count,
                )

            try:
                # Tenta executar a operação
                result = func(*args, **kwargs)

                # Sucesso - registra
                self.record_success()

                return result

            except Exception as e:
                # Falha - registra
                self.record_failure()

                # Re-raise a exceção original
                raise e

        return wrapper

    def get_stats(self) -> dict:
        """
        Retorna estatísticas do circuit breaker.

        Returns:
            Dicionário com estatísticas
        """
        return {
            "enabled": self.config.enabled,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "threshold": self.config.threshold,
            "timeout": self.config.timeout,
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
        }

    def reset(self) -> None:
        """
        Reseta o circuit breaker para estado inicial.

        Útil para testes ou após manutenção manual.
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._last_success_time = None
        self.logger.info("Circuit breaker manually reset to CLOSED")

    def __repr__(self) -> str:
        """Representação string do circuit breaker."""
        return (
            f"<CircuitBreaker state={self.state.value} "
            f"failures={self._failure_count}/{self.config.threshold}>"
        )
