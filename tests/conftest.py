"""
Configuração de fixtures para testes.
"""

import sys
import types

import pytest
from flask import Flask

from resilient_cache import FlaskCacheService


class FakeValkeyClient:
    def __init__(self, *args, **kwargs) -> None:
        self._data = {}

    def ping(self) -> bool:
        return True

    def get(self, key):
        return self._data.get(key)

    def setex(self, key, ttl=None, value=None, **kwargs) -> None:
        if ttl is None and "time" in kwargs:
            ttl = kwargs["time"]
        if value is None and "value" in kwargs:
            value = kwargs["value"]
        self._data[key] = value

    def delete(self, *keys):
        removed = 0
        for key in keys:
            normalized = key.decode("utf-8") if isinstance(key, bytes) else key
            if normalized in self._data:
                del self._data[normalized]
                removed += 1
        return removed

    def scan(self, cursor=0, match=None, count=10):
        pattern = match or "*"
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            keys = [k.encode("utf-8") for k in self._data if k.startswith(prefix)]
        else:
            keys = []
        return 0, keys

    def exists(self, key):
        return 1 if key in self._data else 0

    def ttl(self, key):
        return -2 if key not in self._data else 5

    def info(self, section):
        return {
            "total_connections_received": 1,
            "total_commands_processed": 2,
            "keyspace_hits": 3,
            "keyspace_misses": 4,
        }

    def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def fake_valkey_client(monkeypatch):
    fake_module = types.SimpleNamespace(Valkey=FakeValkeyClient)
    sys.modules.setdefault("valkey", fake_module)

    import resilient_cache.backends.redis_backend as redis_module

    monkeypatch.setattr(redis_module, "valkey", fake_module)
    monkeypatch.setattr(redis_module, "VALKEY_AVAILABLE", True)
    yield


@pytest.fixture
def app():
    """Fixture para aplicação Flask de teste."""
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        CACHE_REDIS_HOST="10.0.1.17",
        CACHE_REDIS_PORT=6379,
        CACHE_REDIS_DB=15,  # Usar DB diferente para testes
        CACHE_SERIALIZER="pickle",
    )
    return app


@pytest.fixture
def cache_service(app):
    """Fixture para FlaskCacheService."""
    service = FlaskCacheService()
    service.init_app(app)
    return service


@pytest.fixture
def simple_cache(cache_service):
    """Fixture para cache simples de teste."""
    return cache_service.create_cache(
        l2_key_prefix="test",
        l2_ttl=300,
        l2_enabled=True,
        l1_enabled=True,
        l1_maxsize=100,
        l1_ttl=30,
    )


@pytest.fixture(autouse=True)
def cleanup_cache(simple_cache):
    """Limpa cache antes e depois de cada teste."""
    simple_cache.clear()
    yield
    simple_cache.clear()
