import builtins

from resilient_cache.cache_factory import CacheFactory
from resilient_cache.config import CacheFactoryConfig, L1Config, L2Config


def test_cache_factory_dependency_checks(monkeypatch):
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("cachetools", "redis"):
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    factory = CacheFactory(CacheFactoryConfig())
    assert factory._cachetools_available is False
    assert factory._redis_available is False


def test_cache_factory_l1_backend_unavailable():
    factory = CacheFactory(CacheFactoryConfig())
    factory._cachetools_available = False
    l1 = L1Config(enabled=True, maxsize=10, ttl=10)
    assert factory._create_l1_backend(l1) is None


def test_cache_factory_l1_backend_invalid_config():
    factory = CacheFactory(CacheFactoryConfig())
    factory._cachetools_available = True
    l1 = L1Config(enabled=True, maxsize=1, ttl=1)

    l1.maxsize = 0
    assert factory._create_l1_backend(l1) is None

    l1.maxsize = 1
    l1.ttl = 0
    assert factory._create_l1_backend(l1) is None


def test_cache_factory_l1_backend_unknown_backend():
    factory = CacheFactory(CacheFactoryConfig())
    factory._cachetools_available = True
    l1 = L1Config(enabled=True, maxsize=10, ttl=10)
    l1.backend = "unknown"
    assert factory._create_l1_backend(l1) is None


def test_cache_factory_l2_backend_unavailable():
    factory = CacheFactory(CacheFactoryConfig())
    factory._redis_available = False
    l2 = L2Config(enabled=True, key_prefix="p", ttl=10)
    assert factory._create_l2_backend(l2, serializer="pickle") is None


def test_cache_factory_l2_backend_unknown_backend():
    factory = CacheFactory(CacheFactoryConfig())
    factory._redis_available = True
    l2 = L2Config(enabled=True, key_prefix="p", ttl=10)
    l2.backend = "unknown"
    assert factory._create_l2_backend(l2, serializer="pickle") is None


def test_cache_factory_backend_creation_exception(monkeypatch):
    from resilient_cache.backends import redis_backend as redis_module
    from resilient_cache.backends import ttl_cache_backend as ttl_module

    factory = CacheFactory(CacheFactoryConfig())
    factory._cachetools_available = True
    factory._redis_available = True

    l1 = L1Config(enabled=True, maxsize=10, ttl=10)
    l2 = L2Config(enabled=True, key_prefix="p", ttl=10)

    class BadTTLCacheBackend:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    class BadRedisBackend:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(ttl_module, "TTLCacheBackend", BadTTLCacheBackend)
    monkeypatch.setattr(redis_module, "RedisBackend", BadRedisBackend)

    assert factory._create_l1_backend(l1) is None
    assert factory._create_l2_backend(l2, serializer="pickle") is None


def test_cache_factory_create_cache_serializer_override():
    config = CacheFactoryConfig(serializer="json")
    factory = CacheFactory(config)
    cache = factory.create_cache(
        l2_key_prefix="k",
        l2_ttl=10,
        l2_enabled=False,
        l1_enabled=False,
        serializer="pickle",
    )
    assert cache is not None


def test_cache_factory_repr():
    factory = CacheFactory(CacheFactoryConfig())
    assert "CacheFactory" in repr(factory)
