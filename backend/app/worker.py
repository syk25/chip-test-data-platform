"""
STDF 파싱 워커 — RabbitMQ 큐에서 작업을 소비해 파싱·DB 저장·Redis 이벤트 발행.
진입점: python -m app.worker
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone

import aio_pika
import structlog
from redis.asyncio import Redis
from sqlalchemy import func, select

from app.core.config import settings
from app.core.connections import STDF_QUEUE
from app.db.session import AsyncSessionLocal
from app.models.domain import FileProcessingJob, Measurement, Part, Wafer
from app.services.events import publish_fail_rate_exceeded, publish_stdf_parsed
from app.services.stdf_parser import parse_and_save
from app.storage.local import LocalStorage

logger = structlog.get_logger()
WORKER_ID = str(uuid.uuid4())[:8]


async def check_fail_rate(lot_id: int, db) -> float:
    """Lot의 전체 FAIL률 계산."""
    result = await db.execute(
        select(
            func.count(Part.id).label("total"),
            func.sum(func.cast(~Part.is_pass, type_=aio_pika.abc.AbstractIncomingMessage.__class__)).label("fail"),
        )
        .join(Wafer, Part.wafer_id == Wafer.id)
        .where(Wafer.lot_id == lot_id)
    )
    # 간단히 scalar로 계산
    from sqlalchemy import Integer, case
    total_result = await db.execute(
        select(func.count(Part.id))
        .join(Wafer, Part.wafer_id == Wafer.id)
        .where(Wafer.lot_id == lot_id)
    )
    fail_result = await db.execute(
        select(func.count(Part.id))
        .join(Wafer, Part.wafer_id == Wafer.id)
        .where(Wafer.lot_id == lot_id, Part.is_pass == False)  # noqa: E712
    )
    total = total_result.scalar_one_or_none() or 0
    fail = fail_result.scalar_one_or_none() or 0
    return fail / total if total > 0 else 0.0


async def process_message(message: aio_pika.abc.AbstractIncomingMessage, redis: Redis) -> None:
    async with message.process(requeue=True):
        body = json.loads(message.body.decode())
        job_id: int = body["job_id"]
        file_id: int = body["file_id"]
        file_path: str = body["file_path"]
        osat_id: int = body.get("osat_id", 1)

        logger.info("worker.job_start", job_id=job_id, file_id=file_id, worker=WORKER_ID)

        async with AsyncSessionLocal() as db:
            job = await db.get(FileProcessingJob, job_id)
            if not job:
                logger.warning("worker.job_not_found", job_id=job_id)
                return

            # 처리 중으로 상태 변경
            job.status = "processing"
            job.started_at = datetime.now(timezone.utc)
            job.worker_id = WORKER_ID
            await db.commit()

            try:
                storage = LocalStorage()
                file_data = await storage.load(file_path)

                lot_id = await parse_and_save(file_data, file_id, osat_id, db)

                job.status = "success"
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()

                logger.info("worker.job_done", job_id=job_id, lot_id=lot_id)

                # Redis: 파싱 완료 이벤트
                await publish_stdf_parsed(redis, lot_id, file_id, "success")

                # Redis: FAIL률 초과 확인
                fail_rate = await check_fail_rate(lot_id, db)
                if fail_rate > settings.FAIL_RATE_THRESHOLD:
                    await publish_fail_rate_exceeded(redis, lot_id, fail_rate)
                    logger.warning("worker.fail_rate_exceeded", lot_id=lot_id, rate=fail_rate)

            except Exception as exc:
                logger.error("worker.job_failed", job_id=job_id, error=str(exc))
                await db.rollback()

                async with AsyncSessionLocal() as db2:
                    job2 = await db2.get(FileProcessingJob, job_id)
                    if job2:
                        job2.status = "failure"
                        job2.error_message = str(exc)
                        job2.finished_at = datetime.now(timezone.utc)
                        await db2.commit()

                await publish_stdf_parsed(redis, 0, file_id, "failure")


async def main() -> None:
    logger.info("worker.starting", worker_id=WORKER_ID, rabbitmq=settings.RABBITMQ_URL)

    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)  # 한 번에 1개씩 처리

    queue = await channel.declare_queue(STDF_QUEUE, durable=True)
    logger.info("worker.ready", queue=STDF_QUEUE)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            await process_message(message, redis)


if __name__ == "__main__":
    asyncio.run(main())
