"""GET /api/v1/events — SSE 실시간 이벤트 스트림 (ADR-007)."""
import asyncio

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.connections import get_redis
from app.services.events import CHANNEL

router = APIRouter(prefix="/events", tags=["events"])
logger = structlog.get_logger()


@router.get(
    "",
    summary="실시간 이벤트 스트림 (SSE)",
    description="Redis Pub/Sub을 SSE로 브릿지. 파싱 완료·FAIL률 초과 이벤트를 실시간 수신.",
    response_class=StreamingResponse,
)
async def event_stream() -> StreamingResponse:
    redis = get_redis()

    async def generate():
        pubsub = redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        logger.info("sse.client_connected")
        try:
            # keepalive: 30초마다 빈 comment 전송 (nginx proxy_read_timeout 대응)
            async def listen():
                async for message in pubsub.listen():
                    if message["type"] == "message":
                        yield f"data: {message['data']}\n\n"

            keepalive_interval = 30
            elapsed = 0
            async for chunk in listen():
                yield chunk
                elapsed = 0

            while True:
                await asyncio.sleep(1)
                elapsed += 1
                if elapsed >= keepalive_interval:
                    yield ": keepalive\n\n"
                    elapsed = 0
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(CHANNEL)
            logger.info("sse.client_disconnected")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx 버퍼링 비활성화
        },
    )
