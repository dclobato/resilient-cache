import pytest

from resilient_cache.cache_service import CacheService
from resilient_cache.config import CacheFactoryConfig


def test_cache_service_requires_init_config():
    service = CacheService()
    with pytest.raises(RuntimeError):
        _ = service.factory


def test_cache_service_init_config_creates_factory():
    config = CacheFactoryConfig(l2_host="localhost", l2_port=6379)
    service = CacheService(config)
    assert service.factory is not None
    stats = service.get_stats()
    assert "dependencies" in stats
    assert "defaults" in stats
    assert "CacheService" in repr(service)
