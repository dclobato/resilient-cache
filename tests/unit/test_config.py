import pytest

from resilient_cache.config import CacheConfig, CacheFactoryConfig, CircuitBreakerConfig, L1Config, L2Config


def test_circuit_breaker_config_validation():
    with pytest.raises(ValueError):
        CircuitBreakerConfig(threshold=0)
    with pytest.raises(ValueError):
        CircuitBreakerConfig(timeout=0)


def test_l1_config_validation():
    with pytest.raises(ValueError):
        L1Config(enabled=True, maxsize=0, ttl=10)
    with pytest.raises(ValueError):
        L1Config(enabled=True, maxsize=10, ttl=0)
    with pytest.raises(ValueError):
        L1Config(enabled=True, maxsize=10, ttl=10, backend="bad")


def test_l2_config_validation():
    with pytest.raises(ValueError):
        L2Config(enabled=True, ttl=0)
    with pytest.raises(ValueError):
        L2Config(enabled=True, key_prefix="")
    with pytest.raises(ValueError):
        L2Config(enabled=True, port=0)
    with pytest.raises(ValueError):
        L2Config(enabled=True, db=-1)
    with pytest.raises(ValueError):
        L2Config(enabled=True, backend="bad")


def test_cache_config_validation_and_logger():
    with pytest.raises(ValueError):
        CacheConfig(l1=L1Config(), l2=L2Config(), serializer="xml")

    config = CacheConfig(l1=L1Config(), l2=L2Config())
    assert config.logger is not None


def test_cache_factory_config_validation_and_logger():
    with pytest.raises(ValueError):
        CacheFactoryConfig(l2_backend="bad")
    with pytest.raises(ValueError):
        CacheFactoryConfig(l1_backend="bad")
    with pytest.raises(ValueError):
        CacheFactoryConfig(serializer="bad")
    with pytest.raises(ValueError):
        CacheFactoryConfig(l2_port=0)

    config = CacheFactoryConfig()
    assert config.logger is not None


def test_cache_factory_config_from_flask_config():
    data = {
        "CACHE_L2_BACKEND": "valkey",
        "CACHE_REDIS_HOST": "redis.example.com",
        "CACHE_REDIS_PORT": 6380,
        "CACHE_REDIS_DB": 2,
        "CACHE_REDIS_PASSWORD": "pw",
        "CACHE_REDIS_CONNECT_TIMEOUT": 6,
        "CACHE_REDIS_SOCKET_TIMEOUT": 7,
        "CACHE_L1_BACKEND": "ttl",
        "CACHE_SERIALIZER": "json",
        "CACHE_CIRCUIT_BREAKER_ENABLED": False,
        "CACHE_CIRCUIT_BREAKER_THRESHOLD": 3,
        "CACHE_CIRCUIT_BREAKER_TIMEOUT": 9,
    }
    config = CacheFactoryConfig.from_flask_config(data)
    assert config.l2_backend == "valkey"
    assert config.l2_host == "redis.example.com"
    assert config.l2_port == 6380
    assert config.l2_db == 2
    assert config.l2_password == "pw"
    assert config.l2_connect_timeout == 6
    assert config.l2_socket_timeout == 7
    assert config.l1_backend == "ttl"
    assert config.serializer == "json"
    assert config.circuit_breaker_enabled is False
    assert config.circuit_breaker_threshold == 3
    assert config.circuit_breaker_timeout == 9
