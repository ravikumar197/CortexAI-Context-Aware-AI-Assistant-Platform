
import hashlib
import json
import logging
import os

import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class ChatCache:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        self.ttl_seconds = int(os.getenv("CHAT_CACHE_TTL", "300"))

    @staticmethod
    def make_key(
        question: str,
        page_title: str,
        page_url: str,
        page_text: str,
    ) -> str:
        payload = json.dumps(
            {
                "question": question,
                "page_title": page_title,
                "page_url": page_url,
                "page_text": page_text,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"copilot:chat:{digest}"

    def get(self, key: str) -> str | None:
        try:
            return self.client.get(key)
        except RedisError:
            logger.warning("Redis cache read failed", exc_info=True)
            return None

    def set(self, key: str, answer: str) -> None:
        try:
            self.client.set(key, answer, ex=self.ttl_seconds)
        except RedisError:
            logger.warning("Redis cache write failed", exc_info=True)

    def close(self) -> None:
        self.client.close()


chat_cache = ChatCache()
