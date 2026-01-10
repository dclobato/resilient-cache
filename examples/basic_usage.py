"""
Exemplo básico de uso do Resilient Cache (sem Flask).

Este exemplo demonstra:
- Inicialização do CacheService
- Criação de cache personalizado
- Operações básicas de cache
"""

from resilient_cache import CacheFactoryConfig, CacheService


def main() -> None:
    config = CacheFactoryConfig(
        l2_host="localhost",
        l2_port=6379,
        l2_db=0,
        serializer="pickle",
        circuit_breaker_enabled=True,
    )

    cache_service = CacheService(config)

    cache = cache_service.create_cache(
        l2_key_prefix="example",
        l2_ttl=300,
        l2_enabled=True,
        l1_enabled=True,
        l1_maxsize=100,
        l1_ttl=60,
    )

    cache.set("user:1", {"id": 1, "name": "Joao"})
    value = cache.get("user:1")

    print("value:", value)
    print("stats:", cache.get_stats())


if __name__ == "__main__":
    main()
