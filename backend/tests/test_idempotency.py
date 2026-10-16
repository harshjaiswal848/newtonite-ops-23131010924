import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.work_item import WorkItem


@pytest.mark.asyncio
async def test_idempotent_creation_prevents_duplicate_items(
    client: AsyncClient,
    seed_test_context: dict,
    db_session: AsyncSession
):
    """
    CRITICAL TEST: Double-click or network retry protection.
    Submitting the same request with an identical Idempotency-Key
    produces exactly ONE work item and replays the cached response.
    """
    token_m1 = seed_test_context["tokens"]["member1"]
    team_id = seed_test_context["team_alpha_id"]
    idempotency_key = f"idemp-test-{uuid.uuid4()}"

    payload = {
        "title": "Critical Settlement Anomaly",
        "description": "Double-click test payload",
        "type": "payment",
        "priority": "urgent",
        "team_id": team_id,
    }

    # First request
    resp1 = await client.post(
        "/api/v1/items",
        headers={
            "Authorization": f"Bearer {token_m1}",
            "Idempotency-Key": idempotency_key,
        },
        json=payload,
    )
    assert resp1.status_code == 201
    data1 = resp1.json()
    item_id_1 = data1["id"]

    # Second request (immediate duplicate retry with same key)
    resp2 = await client.post(
        "/api/v1/items",
        headers={
            "Authorization": f"Bearer {token_m1}",
            "Idempotency-Key": idempotency_key,
        },
        json=payload,
    )
    assert resp2.status_code == 201
    assert resp2.headers.get("Idempotent-Replay") == "true"
    data2 = resp2.json()

    # Must return the identical item ID
    assert data1["id"] == data2["id"]
    assert data1["title"] == data2["title"]

    # Verify only ONE item was created in the database
    count_query = await db_session.execute(
        select(func.count(WorkItem.id)).where(WorkItem.title == "Critical Settlement Anomaly")
    )
    total_count = count_query.scalar()
    assert total_count == 1


@pytest.mark.asyncio
async def test_idempotency_key_payload_mismatch_rejected(
    client: AsyncClient,
    seed_test_context: dict
):
    """Reusing the same key with different parameters must be rejected."""
    token_m1 = seed_test_context["tokens"]["member1"]
    team_id = seed_test_context["team_alpha_id"]
    shared_key = f"mismatch-key-{uuid.uuid4()}"

    # First request
    r1 = await client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {token_m1}", "Idempotency-Key": shared_key},
        json={"title": "Payload A", "description": "Original", "team_id": team_id},
    )
    assert r1.status_code == 201

    # Second request with altered body using same key
    r2 = await client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {token_m1}", "Idempotency-Key": shared_key},
        json={"title": "Payload B - Tampered", "description": "Modified", "team_id": team_id},
    )
    assert r2.status_code == 422
