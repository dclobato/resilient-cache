from resilient_cache.circuit_breaker import CircuitState
from resilient_cache.config import CacheConfig, CircuitBreakerConfig, L1Config, L2Config
from resilient_cache.exceptions import CacheConnectionError
from resilient_cache.two_level_cache import ResilientTwoLevelCache


class FakeBackend:
    def __init__(self, fail_on=None):
        self._data = {}
        self.fail_on = fail_on or set()

    def _maybe_fail(self, op):
        if op in self.fail_on:
            raise CacheConnectionError(f"fail {op}", backend="fake")

    def get(self, key):
        self._maybe_fail("get")
        return self._data.get(key)

    def set(self, key, value, ttl=None):
        self._maybe_fail("set")
        self._data[key] = value

    def delete(self, key):
        self._maybe_fail("delete")
        self._data.pop(key, None)

    def clear(self):
        self._maybe_fail("clear")
        count = len(self._data)
        self._data.clear()
        return count

    def exists(self, key):
        self._maybe_fail("exists")
        return key in self._data

    def get_ttl(self, key):
        self._maybe_fail("get_ttl")
        return 5 if key in self._data else None

    def list_keys(self, prefix=None):
        self._maybe_fail("list_keys")
        keys = list(self._data.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys

    def get_size(self):
        return len(self._data)

    def get_stats(self):
        self._maybe_fail("get_stats")
        return {"enabled": True, "size": len(self._data)}


def _make_cache(l1_backend=None, l2_backend=None, breaker=None):
    l1_config = L1Config(enabled=bool(l1_backend), maxsize=10, ttl=10)
    l2_config = L2Config(enabled=bool(l2_backend), key_prefix="p", ttl=10)
    cb = breaker or CircuitBreakerConfig(threshold=1, timeout=1)
    config = CacheConfig(l1=l1_config, l2=l2_config, circuit_breaker=cb)
    config.l1_backend_factory = lambda _: l1_backend
    config.l2_backend_factory = lambda _: l2_backend
    return ResilientTwoLevelCache(config)


def test_get_promotes_from_l2_to_l1():
    l1 = FakeBackend()
    l2 = FakeBackend()
    l2.set("k1", "v1")
    cache = _make_cache(l1, l2)

    assert cache.get("k1") == "v1"
    assert l1.get("k1") == "v1"


def test_get_handles_l1_error_and_l2_failure_opens_circuit():
    l1 = FakeBackend(fail_on={"get"})
    l2 = FakeBackend(fail_on={"get"})
    cache = _make_cache(l1, l2)

    assert cache.get("k1") is None
    assert cache._circuit_breaker.state == CircuitState.OPEN


def test_l2_error_on_set_delete_clear():
    l1 = FakeBackend()
    l2 = FakeBackend(fail_on={"set", "delete", "clear"})
    cache = _make_cache(l1, l2)

    cache.set("k1", "v1")
    cache.delete("k1")
    stats = cache.clear()
    assert "timestamp" in stats


def test_set_write_through_and_skip_l2_when_open():
    l1 = FakeBackend()
    l2 = FakeBackend(fail_on={"set"})
    cache = _make_cache(l1, l2)

    cache.set("k1", "v1")
    assert l1.get("k1") == "v1"
    assert cache._circuit_breaker.state == CircuitState.OPEN

    # circuito aberto evita chamadas L2
    l2._data.clear()
    cache.set("k2", "v2")
    assert l1.get("k2") == "v2"
    assert l2.get("k2") is None


def test_delete_and_clear_collect_stats():
    l1 = FakeBackend()
    l2 = FakeBackend()
    cache = _make_cache(l1, l2)

    cache.set("k1", "v1")
    cache.delete("k1")
    assert cache.is_on_cache("k1") is False

    cache.set("k2", "v2")
    stats = cache.clear()
    assert stats["l1_items_removed"] >= 0
    assert stats["l2_items_removed"] >= 0


def test_get_stats_handles_backend_errors():
    l1 = FakeBackend(fail_on={"get_stats"})
    l2 = FakeBackend(fail_on={"get_stats"})
    cache = _make_cache(l1, l2)

    stats = cache.get_stats()
    assert stats["l1"]["enabled"] is True
    assert "error" in stats["l1"]
    assert stats["l2"]["enabled"] is True
    assert "error" in stats["l2"]


def test_get_ttl_list_keys_and_exists():
    l1 = FakeBackend()
    l2 = FakeBackend()
    cache = _make_cache(l1, l2)

    cache.set("prefix_a", 1)
    cache.set("b", 2)

    # Forcar L1 miss para cobrir L2 get_ttl
    l1._data.clear()
    assert cache.get_ttl("prefix_a") == 5
    assert sorted(cache.list_keys(prefix="prefix_")) == ["prefix_a"]
    assert cache.is_on_cache("b") is True


def test_init_with_backend_factory_errors():
    def bad_factory(_):
        raise RuntimeError("boom")

    l1_config = L1Config(enabled=True, maxsize=10, ttl=10)
    l2_config = L2Config(enabled=True, key_prefix="p", ttl=10)
    config = CacheConfig(l1=l1_config, l2=l2_config)
    config.l1_backend_factory = bad_factory
    config.l2_backend_factory = bad_factory

    cache = ResilientTwoLevelCache(config)
    assert cache._l1_backend is None
    assert cache._l2_backend is None


def test_l2_errors_on_delete_clear_list_keys_exists():
    l1 = FakeBackend()
    l2 = FakeBackend(fail_on={"delete", "clear", "list_keys", "exists"})
    cache = _make_cache(l1, l2)

    cache.delete("k1")
    stats = cache.clear()
    assert "timestamp" in stats
    assert cache.list_keys(prefix="k") == []
    assert cache.is_on_cache("k1") is False


def test_l2_error_on_get_stats():
    l1 = FakeBackend()
    l2 = FakeBackend(fail_on={"get_stats"})
    cache = _make_cache(l1, l2)

    stats = cache.get_stats()
    assert stats["l2"]["enabled"] is True
    assert "error" in stats["l2"]


def test_l2_error_on_get_ttl_and_list_keys():
    l1 = FakeBackend(fail_on={"get_ttl"})
    l2 = FakeBackend(fail_on={"get_ttl", "list_keys"})
    breaker = CircuitBreakerConfig(threshold=10, timeout=1)
    cache = _make_cache(l1, l2, breaker=breaker)

    assert cache.get_ttl("k") is None
    assert cache.list_keys(prefix="k") == []


def test_list_keys_deduplicates_from_l1_l2():
    l1 = FakeBackend()
    l2 = FakeBackend()
    cache = _make_cache(l1, l2)

    l1.set("k1", 1)
    l2.set("k1", 2)
    l2.set("k2", 3)

    keys = sorted(cache.list_keys())
    assert keys == ["k1", "k2"]


def test_repr_includes_backend_status():
    cache = _make_cache(None, None)
    assert "ResilientTwoLevelCache" in repr(cache)


def test_get_l2_success_does_not_set_l1():
    l1 = FakeBackend(fail_on={"set"})
    l2 = FakeBackend()
    l2.set("k1", "v1")
    cache = _make_cache(l1, l2)

    assert cache.get("k1") == "v1"


def test_l2_unexpected_errors_record_failure():
    class BoomBackend(FakeBackend):
        def get(self, key):
            raise RuntimeError("boom")

        def set(self, key, value, ttl=None):
            raise RuntimeError("boom")

        def delete(self, key):
            raise RuntimeError("boom")

    l1 = FakeBackend()
    l2 = BoomBackend()
    cache = _make_cache(l1, l2)

    assert cache.get("k1") is None
    cache.set("k1", "v1")
    cache.delete("k1")
    assert cache._circuit_breaker.state == CircuitState.OPEN


def test_l1_operation_errors():
    l1 = FakeBackend(fail_on={"set", "delete", "clear", "list_keys", "exists", "get_ttl"})
    cache = _make_cache(l1, None)

    cache.set("k1", "v1")
    cache.delete("k1")
    stats = cache.clear()
    assert "timestamp" in stats
    assert cache.list_keys(prefix="k") == []
    assert cache.is_on_cache("k1") is False
    assert cache.get_ttl("k1") is None


def test_l1_get_ttl_short_circuit():
    l1 = FakeBackend()
    cache = _make_cache(l1, None)
    l1.set("k1", "v1")
    assert cache.get_ttl("k1") == 5


def test_l2_unexpected_set_delete_clear_errors():
    class BoomBackend(FakeBackend):
        def set(self, key, value, ttl=None):
            raise RuntimeError("boom")

        def delete(self, key):
            raise RuntimeError("boom")

        def clear(self):
            raise RuntimeError("boom")

    l1 = FakeBackend()
    l2 = BoomBackend()
    cache = _make_cache(l1, l2)

    cache.set("k1", "v1")
    cache.delete("k1")
    stats = cache.clear()
    assert "timestamp" in stats


def test_l2_list_keys_and_exists_errors():
    l1 = FakeBackend()
    l2 = FakeBackend(fail_on={"list_keys", "exists"})
    breaker = CircuitBreakerConfig(threshold=10, timeout=1)
    cache = _make_cache(l1, l2, breaker=breaker)

    assert cache.list_keys(prefix="k") == []
    assert cache.is_on_cache("k1") is False
