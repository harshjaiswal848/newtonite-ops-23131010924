import hashlib
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.idempotency import IdempotencyKey


def compute_request_hash(user_id: str, endpoint: str, body: Any) -> str:
    raw_str = f"{user_id}:{endpoint}:"
    if body is not None:
        if isinstance(body, dict):
            raw_str += json.dumps(body, sort_keys=True)
        else:
            raw_str += str(body)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


async def check_idempotency_key(
    db: AsyncSession,
    key: Optional[str],
    user_id: str,
    endpoint: str,
    body: Any
) -> Optional[Tuple[int, Dict[str, Any]]]:
    if not key:
        return None

    query = select(IdempotencyKey).where(
        IdempotencyKey.key == key,
        IdempotencyKey.user_id == user_id
    )
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        return None

    # Check if expired
    if record.expires_at and record.expires_at < datetime.now(timezone.utc):
        return None

    # Verify fingerprint
    expected_hash = compute_request_hash(user_id, endpoint, body)
    if record.request_hash != expected_hash:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Idempotency key reused with different request payload or endpoint."
        )

    return record.response_code, record.response_body


async def save_idempotency_key(
    db: AsyncSession,
    key: Optional[str],
    user_id: str,
    endpoint: str,
    body: Any,
    response_code: int,
    response_body: Dict[str, Any],
    ttl_hours: int = 24
) -> None:
    if not key:
        return

    req_hash = compute_request_hash(user_id, endpoint, body)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

    idemp_record = IdempotencyKey(
        key=key,
        user_id=user_id,
        endpoint=endpoint,
        request_hash=req_hash,
        response_code=response_code,
        response_body=response_body,
        expires_at=expires_at
    )
    db.add(idemp_record)
