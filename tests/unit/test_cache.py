"""
Testes básicos para o sistema de cache.
"""

from resilient_cache import CacheFactoryConfig, CacheService, FlaskCacheService


class TestCacheService:
    """Testes para CacheService."""

    def test_init_without_app(self):
        """Testa criação sem app."""
        service = CacheService()
        assert service._factory is None

    def test_init_with_config(self):
        """Testa inicialização com config."""
        config = CacheFactoryConfig(l2_host="localhost", l2_port=6379)
        service = CacheService(config)
        assert service._factory is not None

    def test_init_app(self, app):
        """Testa init_app."""
        service = FlaskCacheService()
        service.init_app(app)
        assert service._factory is not None
        assert "cache_service" in app.extensions

    def test_create_cache(self, cache_service):
        """Testa criação de cache."""
        cache = cache_service.create_cache(
            l2_key_prefix="test",
            l2_ttl=300,
            l2_enabled=True,
            l1_enabled=True,
            l1_maxsize=100,
            l1_ttl=30,
        )
        assert cache is not None

    def test_get_stats(self, cache_service):
        """Testa obtenção de estatísticas."""
        stats = cache_service.get_stats()
        assert "dependencies" in stats
        assert "defaults" in stats

    def test_cache_service_repr(self, cache_service):
        """Testa repr."""
        assert "CacheService" in repr(cache_service)


class TestCacheOperations:
    """Testes para operações básicas de cache."""

    def test_set_and_get(self, simple_cache):
        """Testa set e get."""
        simple_cache.set("key1", "value1")
        value = simple_cache.get("key1")
        assert value == "value1"

    def test_get_miss(self, simple_cache):
        """Testa cache miss."""
        value = simple_cache.get("nonexistent")
        assert value is None

    def test_delete(self, simple_cache):
        """Testa delete."""
        simple_cache.set("key1", "value1")
        simple_cache.delete("key1")
        value = simple_cache.get("key1")
        assert value is None

    def test_clear(self, simple_cache):
        """Testa clear."""
        simple_cache.set("key1", "value1")
        simple_cache.set("key2", "value2")
        result = simple_cache.clear()
        assert result["l1_items_removed"] >= 0
        assert simple_cache.get("key1") is None
        assert simple_cache.get("key2") is None

    def test_is_on_cache(self, simple_cache):
        """Testa is_on_cache."""
        assert not simple_cache.is_on_cache("key1")
        simple_cache.set("key1", "value1")
        assert simple_cache.is_on_cache("key1")

    def test_list_keys(self, simple_cache):
        """Testa list_keys."""
        simple_cache.set("prefix_key1", "value1")
        simple_cache.set("prefix_key2", "value2")
        simple_cache.set("other_key", "value3")

        all_keys = simple_cache.list_keys()
        assert len(all_keys) >= 3

        prefix_keys = simple_cache.list_keys(prefix="prefix_")
        assert len(prefix_keys) == 2

    def test_get_stats(self, simple_cache):
        """Testa get_stats."""
        stats = simple_cache.get_stats()
        assert "enabled" in stats
        assert "l1" in stats
        assert "l2" in stats
        assert "circuit_breaker" in stats


class TestCachePromotion:
    """Testes para cache promotion."""

    def test_l2_hit_promotes_to_l1(self, cache_service):
        """Testa que hit em L2 promove para L1."""
        cache = cache_service.create_cache(
            l2_key_prefix="promo_test",
            l2_ttl=300,
            l2_enabled=True,
            l1_enabled=True,
            l1_maxsize=100,
            l1_ttl=30,
        )

        # Armazenar valor
        cache.set("key1", "value1")

        # Limpar L1 (simulando expiração)
        if cache._l1_backend:
            cache._l1_backend.clear()

        # Primeira busca: miss L1, hit L2
        value = cache.get("key1")
        assert value == "value1"

        # Segunda busca: deve ser hit L1 (promovido)
        if cache._l1_backend:
            assert cache._l1_backend.exists("key1")


class TestSerialization:
    """Testes para serialização."""

    def test_pickle_serializer(self, cache_service):
        """Testa serialização com pickle."""
        cache = cache_service.create_cache(
            l2_key_prefix="pickle_test",
            l2_ttl=300,
            l2_enabled=True,
            serializer="pickle",
        )

        # Testar com diferentes tipos
        test_data = {
            "string": "hello",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        cache.set("data", test_data)
        retrieved = cache.get("data")
        assert retrieved == test_data

    def test_json_serializer(self, cache_service):
        """Testa serialização com JSON."""
        cache = cache_service.create_cache(
            l2_key_prefix="json_test",
            l2_ttl=300,
            l2_enabled=True,
            serializer="json",
        )

        # JSON só suporta tipos básicos
        test_data = {
            "string": "hello",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        cache.set("data", test_data)
        retrieved = cache.get("data")
        assert retrieved == test_data
