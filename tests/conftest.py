"""
Configuração de fixtures para testes.
"""

import pytest
from flask import Flask

from resilient_cache import FlaskCacheService


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
