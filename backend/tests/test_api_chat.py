
from unittest.mock import Mock

from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.main import app, chat_cache


client = TestClient(app)

PAYLOAD = {
    "question": "Explain Redis caching",
    "page_title": "Redis Tutorial",
    "page_url": "https://example.com/redis",
    "page_text": "Redis is an in-memory data store used for caching.",
}


def test_cache_miss_calls_ai_and_stores_answer(monkeypatch):
    monkeypatch.setattr(chat_cache, "get", Mock(return_value=None))
    cache_set = Mock()
    monkeypatch.setattr(chat_cache, "set", cache_set)

    provider = Mock()
    provider.generate.return_value = "Redis speeds up data access."
    monkeypatch.setattr("app.main.get_ai_provider", lambda: provider)

    response = client.post("/api/chat", json=PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Redis speeds up data access.",
        "cached": False,
    }
    provider.generate.assert_called_once()
    cache_set.assert_called_once()


def test_cache_hit_does_not_call_ai(monkeypatch):
    monkeypatch.setattr(
        chat_cache, "get", Mock(return_value="Previously cached answer")
    )
    provider_factory = Mock()
    monkeypatch.setattr(
        "app.main.get_ai_provider", provider_factory
    )

    response = client.post("/api/chat", json=PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Previously cached answer",
        "cached": True,
    }
    provider_factory.assert_not_called()


def test_redis_failure_does_not_prevent_chat(monkeypatch):
    # Exercise the real ChatCache error handling.
    monkeypatch.setattr(
        chat_cache.client,
        "get",
        Mock(side_effect=RedisError("Redis unavailable")),
    )
    monkeypatch.setattr(
        chat_cache.client,
        "set",
        Mock(side_effect=RedisError("Redis unavailable")),
    )

    provider = Mock()
    provider.generate.return_value = "Generated without Redis."
    monkeypatch.setattr("app.main.get_ai_provider", lambda: provider)

    response = client.post("/api/chat", json=PAYLOAD)

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Generated without Redis.",
        "cached": False,
    }
    provider.generate.assert_called_once()


def test_ai_failure_returns_503(monkeypatch):
    monkeypatch.setattr(chat_cache, "get", Mock(return_value=None))

    provider = Mock()
    provider.generate.side_effect = RuntimeError("AI provider unavailable")
    monkeypatch.setattr("app.main.get_ai_provider", lambda: provider)

    response = client.post("/api/chat", json=PAYLOAD)

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "The local AI model is unavailable. Check that Ollama is running."
    )
