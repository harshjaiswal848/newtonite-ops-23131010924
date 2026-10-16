import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outbox import OutboxJob
from app.models.enums import OutboxJobStatus
from app.worker.outbox_worker import process_outbox_batch, notification_sink_log


@pytest.mark.asyncio
async def test_outbox_worker_processes_jobs_reliably(db_session: AsyncSession):
    """
    CRITICAL TEST: Reliable Transactional Outbox.
    1. Pending jobs are processed and marked 'completed'.
    2. Repeated execution does not re-process completed jobs (idempotent).
    """
    job_id = str(uuid.uuid4())
    test_payload = {
        "item_id": "item-outbox-test-1",
        "actor_id": "user-test-1",
        "action": "status_changed",
    }

    job = OutboxJob(
        id=job_id,
        job_type="work_item.status_changed",
        payload=test_payload,
        status=OutboxJobStatus.PENDING.value,
        attempts=0,
        max_attempts=3,
        scheduled_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    await db_session.commit()

    initial_log_len = len(notification_sink_log)

    # First batch process
    processed = await process_outbox_batch(db_session, batch_size=10)
    assert processed >= 1

    # Reload job
    updated_job = await db_session.get(OutboxJob, job_id)
    assert updated_job.status == OutboxJobStatus.COMPLETED.value
    assert updated_job.attempts == 1
    assert updated_job.processed_at is not None
    assert len(notification_sink_log) == initial_log_len + 1

    # Second batch process: Nothing should be processed (idempotent)
    second_processed = await process_outbox_batch(db_session, batch_size=10)
    assert second_processed == 0
    assert len(notification_sink_log) == initial_log_len + 1


@pytest.mark.asyncio
async def test_outbox_worker_retries_and_marks_failed_on_max_attempts(db_session: AsyncSession):
    """
    Worker catches failures, applies exponential backoff, and marks job as FAILED
    once max_attempts threshold is reached.
    """
    job_id = str(uuid.uuid4())
    failing_payload = {
        "item_id": "item-fail-test",
        "simulate_failure": True,  # Triggers transient gateway exception in worker handler
    }

    # Job starts with attempts = 2, max_attempts = 3
    job = OutboxJob(
        id=job_id,
        job_type="work_item.assigned",
        payload=failing_payload,
        status=OutboxJobStatus.PENDING.value,
        attempts=2,
        max_attempts=3,
        scheduled_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(job)
    await db_session.commit()

    # Process batch -> attempt 3 should fail and cap attempts to mark as FAILED
    await process_outbox_batch(db_session, batch_size=10)

    updated_job = await db_session.get(OutboxJob, job_id)
    assert updated_job.status == OutboxJobStatus.FAILED.value
    assert updated_job.attempts == 3
    assert "Simulated transient connection failure" in updated_job.last_error
