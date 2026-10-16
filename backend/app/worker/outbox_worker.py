import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.outbox import OutboxJob
from app.models.enums import OutboxJobStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [OutboxWorker] %(message)s")
logger = logging.getLogger("OutboxWorker")


# Mock external sink for dispatched notifications
notification_sink_log = []


async def handle_notification_job(job_type: str, payload: Dict[str, Any]) -> None:
    """
    Idempotent job handler.
    Simulates sending notifications, webhooks, or external integrations.
    """
    event_fingerprint = f"{job_type}:{payload.get('item_id')}:{payload.get('actor_id') or payload.get('assignee_id')}"
    
    # Check for test-induced failures
    if payload.get("simulate_failure") is True:
        raise RuntimeError("Simulated transient connection failure to notification gateway.")

    log_entry = {
        "event": job_type,
        "payload": payload,
        "dispatched_at": datetime.now(timezone.utc).isoformat(),
        "fingerprint": event_fingerprint,
    }
    notification_sink_log.append(log_entry)
    logger.info(f"Dispatched async event '{job_type}' for item {payload.get('item_id')}")


async def process_outbox_batch(db: AsyncSession, batch_size: int = 10) -> int:
    now = datetime.now(timezone.utc)

    # SELECT ... FOR UPDATE SKIP LOCKED
    # Guarantees concurrent worker processes will never pick up the same job.
    stmt = (
        select(OutboxJob)
        .where(
            OutboxJob.status == OutboxJobStatus.PENDING.value,
            OutboxJob.scheduled_at <= now
        )
        .order_by(OutboxJob.scheduled_at.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )

    result = await db.execute(stmt)
    jobs = result.scalars().all()

    if not jobs:
        return 0

    for job in jobs:
        job.status = OutboxJobStatus.PROCESSING.value
        job.attempts += 1
        
        try:
            await handle_notification_job(job.job_type, job.payload)
            job.status = OutboxJobStatus.COMPLETED.value
            job.processed_at = datetime.now(timezone.utc)
            job.last_error = None
            logger.info(f"Job {job.id} ({job.job_type}) completed successfully.")
        except Exception as e:
            error_msg = str(e)
            job.last_error = error_msg
            logger.warning(f"Job {job.id} failed attempt {job.attempts}/{job.max_attempts}: {error_msg}")

            if job.attempts >= job.max_attempts:
                job.status = OutboxJobStatus.FAILED.value
                logger.error(f"Job {job.id} reached max attempts. Marked as FAILED.")
            else:
                # Exponential backoff: 2^attempts seconds
                backoff_seconds = 2 ** job.attempts
                job.status = OutboxJobStatus.PENDING.value
                job.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
                logger.info(f"Job {job.id} rescheduled in {backoff_seconds}s for retry.")

    await db.commit()
    return len(jobs)


async def run_worker_loop():
    logger.info("Starting Outbox Worker daemon...")
    while True:
        try:
            async with AsyncSessionLocal() as session:
                processed_count = await process_outbox_batch(session, batch_size=settings.OUTBOX_BATCH_SIZE)
                if processed_count == 0:
                    await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Worker received shutdown signal. Exiting.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
            await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_worker_loop())
