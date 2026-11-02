
from unittest.mock import Mock

from redis.exceptions import RedisError

from app.services.cache_service import ChatCache


def make_cache():
    cache = ChatCache()
    cache.client = Mock()
    return cache


def test_get_returns_cached_answer():
    cache = make_cache()
    cache.client.get.return_value = "Cached answer"

    result = cache.get("copilot:chat:test")

    assert result == "Cached answer"
    cache.client.get.assert_called_once_with("copilot:chat:test")


def test_get_returns_none_when_key_is_missing():
    cache = make_cache()
    cache.client.get.return_value = None

    result = cache.get("copilot:chat:missing")

    assert result is None


def test_get_handles_redis_failure():
    cache = make_cache()
    cache.client.get.side_effect = RedisError("Redis unavailable")

    result = cache.get("copilot:chat:test")

    assert result is None


def test_set_stores_answer_with_ttl():
    cache = make_cache()
    cache.ttl_seconds = 300

    cache.set("copilot:chat:test", "Answer")

    cache.client.set.assert_called_once_with(
        "copilot:chat:test",
        "Answer",
        ex=300,
    )


def test_set_handles_redis_failure():
    cache = make_cache()
    cache.client.set.side_effect = RedisError("Redis unavailable")

    # Should not raise an exception.
    cache.set("copilot:chat:test", "Answer")
