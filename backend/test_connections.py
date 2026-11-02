
import os

import redis
import psycopg
from kafka import KafkaProducer


def test_redis():
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        decode_responses=True,
    )
    client.set("copilot:test", "connected", ex=60)
    result = client.get("copilot:test")
    assert result == "connected"
    print("Redis: connected successfully")
    client.close()


def test_postgres():
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError(
            "POSTGRES_PASSWORD is not set. Load it from your project .env."
        )

    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="copilot",
        user="copilot",
        password=password,
        connect_timeout=5,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone() == (1,)

    print("PostgreSQL: connected successfully")


def test_kafka():
    producer = KafkaProducer(
        bootstrap_servers=["127.0.0.1:9092"],
        request_timeout_ms=10000,
        api_version_auto_timeout_ms=10000,
    )
    producer.close()
    print("Kafka: connected successfully")


if __name__ == "__main__":
    test_redis()
    test_postgres()
    test_kafka()
    print("All infrastructure connection tests passed.")
