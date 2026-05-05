"""STDF 파일 업로드 비즈니스 로직."""
import hashlib
import json
import uuid

import aio_pika
import structlog
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connections import STDF_QUEUE
from app.models.domain import FileProcessingJob, StdfFile
from app.schemas.stdf import StdfUploadResponse
from app.storage.local import LocalStorage

logger = structlog.get_logger()


async def receive_stdf_file(
    file: UploadFile,
    osat_id: int,
    uploaded_by: int | None,
    db: AsyncSession,
    channel: aio_pika.abc.AbstractChannel,
) -> StdfUploadResponse:
    data = await file.read()
    checksum = hashlib.sha256(data).hexdigest()
    file_id_str = f"{uuid.uuid4().hex[:16]}_{file.filename}"

    # 로컬 스토리지 저장
    storage = LocalStorage()
    file_path = await storage.save(file_id_str, data)

    # DB: StdfFile 생성
    stdf_record = StdfFile(
        osat_id=osat_id,
        filename=file.filename or "unknown.stdf",
        file_path=file_path,
        file_size=len(data),
        checksum=checksum,
        uploaded_by=uploaded_by,
    )
    db.add(stdf_record)
    await db.flush()  # id 확보

    # DB: FileProcessingJob 생성
    job = FileProcessingJob(stdf_file_id=stdf_record.id)
    db.add(job)
    await db.flush()

    await db.commit()
    await db.refresh(job)

    # RabbitMQ 발행
    message_body = json.dumps({
        "job_id": job.id,
        "file_id": stdf_record.id,
        "file_path": file_path,
        "osat_id": osat_id,
    }).encode()

    await channel.default_exchange.publish(
        aio_pika.Message(body=message_body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key=STDF_QUEUE,
    )

    logger.info("stdf.uploaded", file_id=stdf_record.id, job_id=job.id, size=len(data))

    return StdfUploadResponse(
        file_id=stdf_record.id,
        job_id=job.id,
        filename=stdf_record.filename,
    )
