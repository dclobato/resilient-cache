"""
Exemplo básico de uso do Resilient Cache (Flask).

Este exemplo demonstra:
 - Inicialização do FlaskCacheService
- Criação de cache personalizado
- Operações básicas de cache
- Monitoramento de estatísticas
"""

from flask import Flask, jsonify

from resilient_cache import FlaskCacheService

# Criar aplicação Flask
app = Flask(__name__)

# Configurar Redis/Valkey
app.config.update(
    CACHE_REDIS_HOST="localhost",
    CACHE_REDIS_PORT=6379,
    CACHE_REDIS_DB=0,
    CACHE_SERIALIZER="pickle",
    CACHE_CIRCUIT_BREAKER_ENABLED=True,
)

# Inicializar FlaskCacheService
cache_service = FlaskCacheService()
cache_service.init_app(app)

# Criar cache para usuários
user_cache = cache_service.create_cache(
    l2_key_prefix="users",
    l2_ttl=3600,  # 1 hora
    l2_enabled=True,
    l1_enabled=True,
    l1_maxsize=1000,
    l1_ttl=60,  # 1 minuto
)


# Simulação de banco de dados
fake_db = {
    "1": {"id": 1, "name": "João Silva", "email": "joao@example.com"},
    "2": {"id": 2, "name": "Maria Santos", "email": "maria@example.com"},
    "3": {"id": 3, "name": "Pedro Costa", "email": "pedro@example.com"},
}


@app.route("/users/<user_id>")
def get_user(user_id: str):
    """
    Busca usuário com cache.

    Primeiro tenta buscar do cache (L1 -> L2).
    Se não encontrar, busca do "banco de dados" e armazena no cache.
    """
    cache_key = f"user_{user_id}"

    # Tentar obter do cache
    user = user_cache.get(cache_key)

    if user is not None:
        return jsonify({"user": user, "source": "cache"})

    # Cache miss - buscar do "banco de dados"
    user = fake_db.get(user_id)

    if user is None:
        return jsonify({"error": "User not found"}), 404

    # Armazenar no cache
    user_cache.set(cache_key, user)

    return jsonify({"user": user, "source": "database"})


@app.route("/users/<user_id>/clear")
def clear_user(user_id: str):
    """Limpa cache de um usuário específico."""
    cache_key = f"user_{user_id}"
    user_cache.delete(cache_key)
    return jsonify({"message": f"Cache cleared for user {user_id}"})


@app.route("/cache/stats")
def cache_stats():
    """Retorna estatísticas do cache."""
    stats = user_cache.get_stats()
    return jsonify(stats)


@app.route("/cache/clear")
def clear_all_cache():
    """Limpa todo o cache."""
    result = user_cache.clear()
    return jsonify(
        {
            "message": "Cache cleared",
            "l1_items_removed": result["l1_items_removed"],
            "l2_items_removed": result["l2_items_removed"],
        }
    )


@app.route("/cache/keys")
def list_cache_keys():
    """Lista todas as chaves no cache."""
    keys = user_cache.list_keys()
    return jsonify({"keys": keys, "total": len(keys)})


@app.route("/health")
def health_check():
    """
    Verifica saúde do sistema de cache.

    Retorna 503 se o circuit breaker estiver aberto.
    """
    stats = user_cache.get_stats()

    # Verificar estado do circuit breaker
    cb_state = stats.get("circuit_breaker", {}).get("state", "unknown")

    if cb_state == "open":
        return (
            jsonify(
                {
                    "status": "degraded",
                    "reason": "L2 cache unavailable",
                    "circuit_breaker": cb_state,
                }
            ),
            503,
        )

    return jsonify(
        {
            "status": "healthy",
            "l1_enabled": stats.get("l1", {}).get("enabled", False),
            "l2_enabled": stats.get("l2", {}).get("enabled", False),
            "circuit_breaker": cb_state,
        }
    )


if __name__ == "__main__":
    print("=" * 60)
    print("Resilient Cache - Flask Example Application")
    print("=" * 60)
    print("\nEndpoints disponíveis:")
    print("  GET  /users/<user_id>         - Buscar usuário (com cache)")
    print("  GET  /users/<user_id>/clear   - Limpar cache do usuário")
    print("  GET  /cache/stats             - Estatísticas do cache")
    print("  GET  /cache/clear             - Limpar todo o cache")
    print("  GET  /cache/keys              - Listar chaves do cache")
    print("  GET  /health                  - Verificar saúde do cache")
    print("\nExemplos:")
    print("  curl http://localhost:5000/users/1")
    print("  curl http://localhost:5000/cache/stats")
    print("  curl http://localhost:5000/health")
    print("\n" + "=" * 60)

    app.run(debug=True, port=5000)
