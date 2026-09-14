from options_analysis.services.cache import TTLCache


def test_ttl_cache_expires_and_evicts_least_recently_used() -> None:
    now = 0.0

    def clock() -> float:
        return now

    cache = TTLCache[str, int](ttl_seconds=2, max_entries=2, clock=clock)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1

    cache.put("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3

    now = 3
    assert cache.get("a") is None
    assert cache.get("c") is None


def test_zero_ttl_disables_cache() -> None:
    cache = TTLCache[str, int](ttl_seconds=0, max_entries=1)
    cache.put("key", 1)

    assert cache.get("key") is None
    assert len(cache) == 0
