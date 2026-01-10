import pytest
from flask import Flask

from resilient_cache.flask_integration import FlaskCacheService, get_cache_service


def test_flask_cache_service_registers_extension():
    app = Flask(__name__)
    app.config.update(CACHE_REDIS_HOST="localhost", CACHE_REDIS_PORT=6379, CACHE_REDIS_DB=0)

    service = FlaskCacheService()
    service.init_app(app)

    assert "cache_service" in app.extensions
    assert get_cache_service(app) is service


def test_get_cache_service_raises_when_missing():
    app = Flask(__name__)
    with pytest.raises(RuntimeError):
        get_cache_service(app)


def test_flask_cache_service_init_with_app():
    app = Flask(__name__)
    app.config.update(CACHE_REDIS_HOST="localhost", CACHE_REDIS_PORT=6379, CACHE_REDIS_DB=0)
    service = FlaskCacheService(app)
    assert service is not None
    assert "cache_service" in app.extensions


def test_get_cache_service_uses_current_app():
    app = Flask(__name__)
    app.config.update(CACHE_REDIS_HOST="localhost", CACHE_REDIS_PORT=6379, CACHE_REDIS_DB=0)
    service = FlaskCacheService()
    service.init_app(app)

    with app.app_context():
        assert get_cache_service() is service
