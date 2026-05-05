"""
STDF 파싱 워커 — RabbitMQ 큐에서 작업을 소비해 파싱·DB 저장·Redis 이벤트 발행.
Day 3에 구현 예정. 현재는 연결 확인용 스켈레톤.
"""
import asyncio

import structlog

from app.core.config import settings

logger = structlog.get_logger()


async def main() -> None:
    logger.info("worker.started", rabbitmq_url=settings.RABBITMQ_URL)
    # TODO Day 3: aio-pika로 RabbitMQ 연결 + 큐 소비 루프
    while True:
        await asyncio.sleep(5)
        logger.debug("worker.heartbeat")


if __name__ == "__main__":
    asyncio.run(main())
