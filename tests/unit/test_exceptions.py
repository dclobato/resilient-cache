from resilient_cache.exceptions import (
    CacheConfigurationError,
    CacheConnectionError,
    CacheError,
    CacheSerializationError,
    CircuitBreakerOpenError,
)


def test_cache_error_string_without_details():
    err = CacheError("boom")
    assert str(err) == "boom"
    assert err.details == {}


def test_cache_error_string_with_details():
    err = CacheError("boom", {"key": "value"})
    assert "boom" in str(err)
    assert "key" in str(err)


def test_cache_connection_error_details():
    original = ValueError("nope")
    err = CacheConnectionError(backend="redis", original_error=original)
    assert err.backend == "redis"
    assert "redis" in str(err)
    assert "ValueError" in str(err)


def test_cache_serialization_error_details():
    original = TypeError("bad")
    err = CacheSerializationError(key="k1", serializer="json", original_error=original)
    assert err.key == "k1"
    assert err.serializer == "json"
    assert "json" in str(err)


def test_cache_configuration_error_details():
    err = CacheConfigurationError(config_key="l1_backend", config_value="foo")
    assert err.config_key == "l1_backend"
    assert "l1_backend" in str(err)


def test_circuit_breaker_open_error_details():
    err = CircuitBreakerOpenError(backend="L2", failure_count=3)
    assert err.backend == "L2"
    assert err.failure_count == 3
    assert "failure_count" in str(err)
