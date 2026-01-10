import time

import pytest

from resilient_cache.circuit_breaker import CircuitBreaker, CircuitState
from resilient_cache.config import CircuitBreakerConfig
from resilient_cache.exceptions import CircuitBreakerOpenError


def test_circuit_breaker_opens_on_threshold():
    config = CircuitBreakerConfig(threshold=2, timeout=1)
    breaker = CircuitBreaker(config)

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED

    breaker.record_failure()
    assert breaker.is_open()


def test_circuit_breaker_half_open_then_closed():
    config = CircuitBreakerConfig(threshold=1, timeout=1)
    breaker = CircuitBreaker(config)

    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    breaker._last_failure_time = time.time() - 2
    assert breaker.state == CircuitState.HALF_OPEN

    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.get_stats()["failure_count"] == 0


def test_circuit_breaker_disabled_always_closed():
    config = CircuitBreakerConfig(enabled=False, threshold=1, timeout=1)
    breaker = CircuitBreaker(config)

    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    assert not breaker.is_open()


def test_protected_raises_when_open():
    config = CircuitBreakerConfig(threshold=1, timeout=1)
    breaker = CircuitBreaker(config)
    breaker._state = CircuitState.OPEN
    breaker._failure_count = 3

    @breaker.protected
    def call():
        return "ok"

    with pytest.raises(CircuitBreakerOpenError):
        call()


def test_protected_records_failure_and_reraises():
    config = CircuitBreakerConfig(threshold=1, timeout=1)
    breaker = CircuitBreaker(config)

    @breaker.protected
    def call():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        call()

    assert breaker.is_open()


def test_reset_clears_state():
    config = CircuitBreakerConfig(threshold=1, timeout=1)
    breaker = CircuitBreaker(config)
    breaker.record_failure()
    assert breaker.is_open()

    breaker.reset()
    assert breaker.state == CircuitState.CLOSED
    stats = breaker.get_stats()
    assert stats["failure_count"] == 0
    assert stats["last_failure_time"] is None
