import os

import pytest

from resilient_cache.backends.redis_backend import RedisBackend
from resilient_cache.config import L2Config
from resilient_cache.serializers import JsonSerializer, PickleSerializer


def _get_env_settings():
    host = os.getenv("VALKEY_HOST")
    port = os.getenv("VALKEY_PORT")
    db = os.getenv("VALKEY_DB")
    password = os.getenv("VALKEY_PASSWORD")

    if not host or not port or not db:
        pytest.skip("VALKEY_HOST/VALKEY_PORT/VALKEY_DB not set")

    try:
        port_value = int(port)
        db_value = int(db)
    except ValueError:
        pytest.skip("VALKEY_PORT/VALKEY_DB must be integers")

    return host, port_value, db_value, password


def _require_valkey_client():
    try:
        import valkey  # noqa: F401
    except ImportError:
        pytest.skip("valkey client not installed")


@pytest.fixture(params=[JsonSerializer(), PickleSerializer()])
def backend(request):
    _require_valkey_client()
    host, port, db, password = _get_env_settings()
    prefix = "resilient-cache-test"

    config = L2Config(
        enabled=True,
        host=host,
        port=port,
        db=db,
        password=password,
        key_prefix=prefix,
        ttl=10,
    )
    instance = RedisBackend(config, request.param)

    try:
        instance.clear()
        yield instance
    finally:
        instance.clear()
        instance.close()


def test_valkey_backend_get_set(backend):
    assert backend.get("missing") is None
    backend.set("k1", {"a": 1})
    assert backend.get("k1") == {"a": 1}


def test_valkey_backend_exists(backend):
    backend.set("k2", {"b": 2})
    assert backend.exists("k2") is True


def test_valkey_backend_list_keys(backend):
    backend.set("k1", {"a": 1})
    backend.set("k2", {"b": 2})
    assert set(backend.list_keys(prefix="k")) == {"k1", "k2"}


def test_valkey_backend_get_size(backend):
    backend.set("k1", {"a": 1})
    backend.set("k2", {"b": 2})
    assert backend.get_size() >= 2


def test_valkey_backend_get_ttl(backend):
    backend.set("k1", {"a": 1})
    ttl = backend.get_ttl("k1")
    assert ttl is None or ttl > 0


def test_valkey_backend_delete(backend):
    backend.set("k2", {"b": 2})
    backend.delete("k2")
    assert backend.get("k2") is None
    assert backend.exists("k2") is False


def test_valkey_backend_get_stats(backend):
    backend.set("k1", {"a": 1})
    stats = backend.get_stats()
    assert stats["enabled"] is True
    assert "redis_stats" in stats
