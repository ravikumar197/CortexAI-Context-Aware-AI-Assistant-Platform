
from app.services.cache_service import ChatCache


def test_same_context_generates_same_key():
    key1 = ChatCache.make_key(
        "Summarize this page",
        "Redis Tutorial",
        "https://example.com/redis",
        "Redis is an in-memory data store.",
    )

    key2 = ChatCache.make_key(
        "Summarize this page",
        "Redis Tutorial",
        "https://example.com/redis",
        "Redis is an in-memory data store.",
    )

    assert key1 == key2


def test_different_question_generates_different_key():
    key1 = ChatCache.make_key(
        "Summarize this page",
        "Redis Tutorial",
        "https://example.com/redis",
        "Redis is an in-memory data store.",
    )

    key2 = ChatCache.make_key(
        "Explain Redis TTL",
        "Redis Tutorial",
        "https://example.com/redis",
        "Redis is an in-memory data store.",
    )

    assert key1 != key2


def test_different_page_context_generates_different_key():
    key1 = ChatCache.make_key(
        "Summarize this page",
        "Redis Tutorial",
        "https://example.com/redis",
        "Redis is an in-memory data store.",
    )

    key2 = ChatCache.make_key(
        "Summarize this page",
        "Kafka Tutorial",
        "https://example.com/kafka",
        "Kafka is an event streaming platform.",
    )

    assert key1 != key2
