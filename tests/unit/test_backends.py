import types
from typing import Optional

import pytest

from resilient_cache.backends import redis_backend as redis_module
from resilient_cache.backends import ttl_cache_backend as ttl_module
from resilient_cache.config import L1Config, L2Config
from resilient_cache.exceptions import (
    CacheConfigurationError,
    CacheConnectionError,
    CacheSerializationError,
)
from resilient_cache.serializers import JsonSerializer, PickleSerializer


class FakeTTLCache:
    def __init__(self, maxsize: int, ttl: int) -> None:
        self._data = {}

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def clear(self):
        self._data.clear()

    def keys(self):
        return self._data.keys()

    def __contains__(self, key):
        return key in self._data

    def __len__(self):
        return len(self._data)


def test_ttl_cache_backend_raises_when_cachetools_missing(monkeypatch):
    monkeypatch.setattr(ttl_module, "CACHETOOLS_AVAILABLE", False)
    config = L1Config(enabled=True, maxsize=10, ttl=5)

    with pytest.raises(CacheConfigurationError):
        ttl_module.TTLCacheBackend(config)


def test_ttl_cache_backend_basic_operations(monkeypatch):
    monkeypatch.setattr(ttl_module, "CACHETOOLS_AVAILABLE", True)
    monkeypatch.setattr(ttl_module, "TTLCache", FakeTTLCache)

    config = L1Config(enabled=True, maxsize=2, ttl=10)
    backend = ttl_module.TTLCacheBackend(config)

    assert backend.get("missing") is None
    backend.set("k1", "v1")
    assert backend.get("k1") == "v1"
    assert backend.exists("k1")
    assert backend.get_ttl("k1") == 10
    assert backend.list_keys(prefix="k") == ["k1"]
    assert backend.get_size() == 1

    stats = backend.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1

    backend.delete("k1")
    assert backend.get("k1") is None

    backend.set("k2", "v2")
    removed = backend.clear()
    assert removed == 1
    assert backend.get_size() == 0
    assert "TTLCacheBackend" in repr(backend)


class FakeRedisClient:
    def __init__(self, *args, **kwargs) -> None:
        self._data = {}
        self._closed = False

    def ping(self) -> bool:
        return True

    def get(self, key: str) -> Optional[bytes]:
        return self._data.get(key)

    def setex(
        self, key: str, ttl: Optional[int] = None, value: Optional[bytes] = None, **kwargs
    ) -> None:
        if ttl is None and "time" in kwargs:
            ttl = kwargs["time"]
        if value is None and "value" in kwargs:
            value = kwargs["value"]
        self._data[key] = value

    def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            normalized = key.decode("utf-8") if isinstance(key, bytes) else key
            if normalized in self._data:
                del self._data[normalized]
                removed += 1
        return removed

    def keys(self, pattern: str):
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [k.encode("utf-8") for k in self._data if k.startswith(prefix)]
        return []

    def scan(self, cursor: int = 0, match: Optional[str] = None, count: int = 10):
        keys = self.keys(match or "*")
        return 0, keys

    def exists(self, key: str) -> int:
        return 1 if key in self._data else 0

    def ttl(self, key: str) -> int:
        return -2 if key not in self._data else 5

    def info(self, section: str):
        return {
            "total_connections_received": 1,
            "total_commands_processed": 2,
            "keyspace_hits": 3,
            "keyspace_misses": 4,
        }

    def close(self) -> None:
        self._closed = True


class FakeRedisFailClient(FakeRedisClient):
    def ping(self) -> bool:
        raise RuntimeError("no redis")


def _setup_fake_redis(monkeypatch, client_cls):
    fake_module = types.SimpleNamespace(Valkey=client_cls)
    monkeypatch.setattr(redis_module, "valkey", fake_module)
    monkeypatch.setattr(redis_module, "VALKEY_AVAILABLE", True)


def test_redis_backend_connection_error(monkeypatch):
    _setup_fake_redis(monkeypatch, FakeRedisFailClient)
    config = L2Config(enabled=True, host="localhost", port=6379, db=0, key_prefix="p")

    with pytest.raises(CacheConnectionError):
        redis_module.RedisBackend(config, JsonSerializer())


@pytest.mark.parametrize(
    ("serializer", "value"),
    [
        (JsonSerializer(), {"a": 1}),
        (PickleSerializer(), {"a": 1}),
    ],
)
def test_redis_backend_basic_operations(monkeypatch, serializer, value):
    _setup_fake_redis(monkeypatch, FakeRedisClient)
    config = L2Config(enabled=True, host="localhost", port=6379, db=0, key_prefix="p", ttl=10)
    backend = redis_module.RedisBackend(config, serializer)

    assert backend.get("missing") is None
    backend.set("k1", value)
    assert backend.get("k1") == value
    assert backend.exists("k1") is True
    assert backend.get_ttl("k1") == 5
    assert backend.list_keys(prefix="k") == ["k1"]
    assert backend.get_size() == 1
    assert backend.ping() is True

    stats = backend.get_stats()
    assert stats["enabled"] is True
    assert stats["redis_stats"]["keyspace_hits"] == 3

    backend.delete("k1")
    assert backend.get("k1") is None

    backend.set("k2", {"b": 2})
    assert backend.clear() == 1
    backend.close()
    assert "RedisBackend" in repr(backend)


@pytest.mark.parametrize(
    ("serializer", "bad_value"),
    [
        (JsonSerializer(), {"value": object()}),
        (PickleSerializer(), lambda x: x),
    ],
)
def test_redis_backend_serialization_error(monkeypatch, serializer, bad_value):
    _setup_fake_redis(monkeypatch, FakeRedisClient)
    config = L2Config(enabled=True, host="localhost", port=6379, db=0, key_prefix="p", ttl=10)
    backend = redis_module.RedisBackend(config, serializer)

    with pytest.raises(CacheSerializationError):
        backend.set("bad", bad_value)


def test_redis_backend_missing_dependency(monkeypatch):
    monkeypatch.setattr(redis_module, "VALKEY_AVAILABLE", False)
    monkeypatch.setattr(redis_module, "valkey", None)
    config = L2Config(enabled=True, host="localhost", port=6379, db=0, key_prefix="p")

    with pytest.raises(CacheConfigurationError):
        redis_module.RedisBackend(config, JsonSerializer())


@pytest.mark.parametrize(
    ("serializer", "bad_bytes"),
    [
        (JsonSerializer(), b"not-json"),
        (PickleSerializer(), b"not-pickle"),
    ],
)
def test_redis_backend_deserialize_error(monkeypatch, serializer, bad_bytes):
    _setup_fake_redis(monkeypatch, FakeRedisClient)
    config = L2Config(enabled=True, host="localhost", port=6379, db=0, key_prefix="p", ttl=10)
    backend = redis_module.RedisBackend(config, serializer)

    with pytest.raises(CacheSerializationError):
        backend._client.setex("p:bad", 10, bad_bytes)
        backend.get("bad")


def test_redis_backend_operations_raise_connection_error(monkeypatch):
    class ErrorRedisClient(FakeRedisClient):
        def get(self, key):
            raise RuntimeError("boom")

        def setex(self, key, ttl=None, value=None, **kwargs):
            raise RuntimeError("boom")

        def delete(self, *keys):
            raise RuntimeError("boom")

        def keys(self, pattern):
            raise RuntimeError("boom")

        def exists(self, key):
            raise RuntimeError("boom")

        def ttl(self, key):
            raise RuntimeError("boom")

        def info(self, section):
            raise RuntimeError("boom")

        def close(self):
            raise RuntimeError("boom")

    _setup_fake_redis(monkeypatch, ErrorRedisClient)
    config = L2Config(enabled=True, host="localhost", port=6379, db=0, key_prefix="p", ttl=10)
    backend = redis_module.RedisBackend(config, PickleSerializer())

    with pytest.raises(CacheConnectionError):
        backend.get("k1")

    with pytest.raises(CacheConnectionError):
        backend.set("k1", "v1")

    with pytest.raises(CacheConnectionError):
        backend.delete("k1")

    with pytest.raises(CacheConnectionError):
        backend.clear()

    with pytest.raises(CacheConnectionError):
        backend.exists("k1")

    with pytest.raises(CacheConnectionError):
        backend.get_ttl("k1")

    with pytest.raises(CacheConnectionError):
        backend.list_keys(prefix="k")

    with pytest.raises(CacheConnectionError):
        backend.get_size()

    stats = backend.get_stats()
    assert stats["enabled"] is False

    def _boom():
        raise RuntimeError("boom")

    backend._client.ping = _boom  # type: ignore[assignment]
    backend._is_connected = lambda: True  # type: ignore[assignment]
    with pytest.raises(CacheConnectionError):
        backend.ping()

    backend.close()
