"""RabbitMQ + Redis 연결 관리 — lifespan에서 초기화, Depends로 주입."""
import aio_pika
import structlog
from redis.asyncio import Redis

from app.core.config import settings

logger = structlog.get_logger()

STDF_QUEUE = "stdf.processing"

# 모듈 레벨 싱글턴 (lifespan에서 설정)
_rabbitmq_connection: aio_pika.abc.AbstractRobustConnection | None = None
_rabbitmq_channel: aio_pika.abc.AbstractChannel | None = None
_redis: Redis | None = None


async def init_connections() -> None:
    global _rabbitmq_connection, _rabbitmq_channel, _redis

    _rabbitmq_connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    _rabbitmq_channel = await _rabbitmq_connection.channel()
    await _rabbitmq_channel.declare_queue(STDF_QUEUE, durable=True)

    _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("connections.ready")


async def close_connections() -> None:
    if _rabbitmq_channel:
        await _rabbitmq_channel.close()
    if _rabbitmq_connection:
        await _rabbitmq_connection.close()
    if _redis:
        await _redis.aclose()
    logger.info("connections.closed")


def get_channel() -> aio_pika.abc.AbstractChannel:
    assert _rabbitmq_channel, "RabbitMQ not initialised"
    return _rabbitmq_channel


def get_redis() -> Redis:
    assert _redis, "Redis not initialised"
    return _redis
