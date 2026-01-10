"""
Integração opcional com Flask.

Fornece uma fachada para inicialização via app.config e
registro em app.extensions.
"""

from typing import Optional, cast

from flask import Flask

from .cache_service import CacheService
from .config import CacheFactoryConfig


class FlaskCacheService(CacheService):
    """
    Fachada de cache para aplicações Flask.

    Example:
        >>> from flask import Flask
        >>> from resilient_cache.flask_integration import FlaskCacheService
        >>>
        >>> app = Flask(__name__)
        >>> app.config['CACHE_REDIS_HOST'] = 'localhost'
        >>>
        >>> cache_service = FlaskCacheService()
        >>> cache_service.init_app(app)
    """

    def __init__(self, app: Optional[Flask] = None) -> None:
        super().__init__()
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """
        Inicializa o serviço com uma aplicação Flask.

        Lê configurações do app.config e cria a factory.
        """
        logger = app.logger

        factory_config = CacheFactoryConfig.from_flask_config(app.config)
        factory_config.logger = logger

        self.init_config(factory_config, logger=logger)

        if not hasattr(app, "extensions"):
            app.extensions = {}  # type: ignore

        app.extensions["cache_service"] = self

        logger.info("FlaskCacheService initialized with Flask app")


def get_cache_service(app: Optional[Flask] = None) -> FlaskCacheService:
    """
    Helper para obter a instância do FlaskCacheService.

    Args:
        app: Aplicação Flask (usa current_app se None)
    """
    if app is None:
        from flask import current_app

        app = current_app

    if "cache_service" not in app.extensions:
        raise RuntimeError(
            "CacheService not found in app.extensions. "
            "Make sure to call cache_service.init_app(app) first."
        )

    return cast(FlaskCacheService, app.extensions["cache_service"])
