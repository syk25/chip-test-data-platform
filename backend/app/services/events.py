"""Redis Pub/Sub 이벤트 발행 — ADR-007."""
import json
from datetime import datetime, timezone

from redis.asyncio import Redis

from app.core.config import settings

CHANNEL = "events:global"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def publish_stdf_parsed(redis: Redis, lot_id: int, file_id: int, status: str) -> None:
    payload = json.dumps({
        "type": "stdf.parsed",
        "lot_id": lot_id,
        "file_id": file_id,
        "status": status,
        "timestamp": _now(),
    })
    await redis.publish(CHANNEL, payload)


async def publish_fail_rate_exceeded(redis: Redis, lot_id: int, fail_rate: float) -> None:
    payload = json.dumps({
        "type": "lot.fail_rate_exceeded",
        "lot_id": lot_id,
        "fail_rate": round(fail_rate, 4),
        "threshold": settings.FAIL_RATE_THRESHOLD,
        "timestamp": _now(),
    })
    await redis.publish(CHANNEL, payload)
