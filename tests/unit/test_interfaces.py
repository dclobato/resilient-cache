import builtins
import importlib
import sys

import resilient_cache
from resilient_cache.app_cache import AppCache
from resilient_cache.backends.base import CacheBackend


class DummyAppCache(AppCache):
    def get(self, key):
        return AppCache.get(self, key)

    def set(self, key, value):
        return AppCache.set(self, key, value)

    def set_if_not_exist(self, key, value):
        return AppCache.set_if_not_exist(self, key, value)

    def delete(self, key):
        return AppCache.delete(self, key)

    def clear(self):
        return AppCache.clear(self)

    def get_stats(self):
        return {"enabled": True}

    def get_ttl(self, key):
        return AppCache.get_ttl(self, key)

    def list_keys(self, prefix=None):
        return AppCache.list_keys(self, prefix)

    def is_on_cache(self, key):
        return AppCache.is_on_cache(self, key)


class DummyBackend(CacheBackend):
    def get(self, key):
        return CacheBackend.get(self, key)

    def set(self, key, value, ttl=None):
        return CacheBackend.set(self, key, value, ttl)

    def set_if_not_exist(self, key, value, ttl=None):
        return CacheBackend.set_if_not_exist(self, key, value, ttl)

    def delete(self, key):
        return CacheBackend.delete(self, key)

    def clear(self):
        return CacheBackend.clear(self)

    def exists(self, key):
        return CacheBackend.exists(self, key)

    def get_ttl(self, key):
        return CacheBackend.get_ttl(self, key)

    def list_keys(self, prefix=None):
        return CacheBackend.list_keys(self, prefix)

    def get_size(self):
        return CacheBackend.get_size(self)

    def get_stats(self):
        return CacheBackend.get_stats(self)


def test_app_cache_repr_executes_base():
    cache = DummyAppCache()
    assert "DummyAppCache" in repr(cache)


def test_cache_backend_repr_executes_base():
    backend = DummyBackend()
    assert "DummyBackend" in repr(backend)


def test_app_cache_base_methods_execute():
    cache = DummyAppCache()
    assert cache.get("k") is None
    assert cache.set("k", "v") is None
    assert cache.delete("k") is None
    assert cache.clear() is None
    assert cache.get_ttl("k") is None
    assert cache.list_keys(prefix="p") is None
    assert cache.is_on_cache("k") is None


def test_cache_backend_base_methods_execute():
    backend = DummyBackend()
    assert backend.get("k") is None
    assert backend.set("k", "v") is None
    assert backend.delete("k") is None
    assert backend.clear() is None
    assert backend.exists("k") is None
    assert backend.get_ttl("k") is None
    assert backend.list_keys(prefix="p") is None
    assert backend.get_size() is None
    assert backend.get_stats() is None


def test_init_without_flask(monkeypatch):
    original_module = sys.modules.get("resilient_cache")
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "flask":
            raise ImportError("no flask")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.modules.pop("resilient_cache.flask_integration", None)
    reloaded = importlib.reload(resilient_cache)
    assert "FlaskCacheService" not in reloaded.__all__

    if original_module is not None:
        importlib.reload(original_module)
