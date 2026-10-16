import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.work_item import WorkItem
from app.models.activity import ActivityEvent
from app.models.enums import ActivityEventType


@pytest.mark.asyncio
async def test_concurrent_claim_only_one_wins(client: AsyncClient, seed_test_context: dict, db_session: AsyncSession):
    """
    CRITICAL TEST: Two operators click 'Claim' simultaneously on an unassigned item.
    Enforces atomic conditional update: Exactly one claim succeeds (200),
    and the other receives a 409 Conflict.
    """
    token_m1 = seed_test_context["tokens"]["member1"]
    token_m2 = seed_test_context["tokens"]["member2"]
    team_id = seed_test_context["team_alpha_id"]

    # 1. Create unassigned work item
    create_resp = await client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {token_m1}"},
        json={
            "title": "High Priority Gateway Outage",
            "description": "Simultaneous claim target test item",
            "type": "incident",
            "priority": "urgent",
            "team_id": team_id,
        }
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    # 2. Fire two claims concurrently via asyncio.gather
    async def claim_as_user(token: str):
        return await client.post(
            f"/api/v1/items/{item_id}/claim",
            headers={"Authorization": f"Bearer {token}"}
        )

    responses = await asyncio.gather(
        claim_as_user(token_m1),
        claim_as_user(token_m2)
    )

    status_codes = [r.status_code for r in responses]

    # 3. Assertions: Exactly one 200 OK and one 409 Conflict
    assert 200 in status_codes, f"Expected one successful claim, got: {status_codes}"
    assert 409 in status_codes, f"Expected one 409 Conflict, got: {status_codes}"
    assert len(status_codes) == 2

    # 4. Verify database state
    item_query = await db_session.execute(select(WorkItem).where(WorkItem.id == item_id))
    persisted_item = item_query.scalar_one()

    # The assignee must be either member1 or member2, and cannot be null
    assert persisted_item.assignee_id in ("user-member-1", "user-member-2")
    assert persisted_item.status == "In Progress"

    # 5. Check activity events: exactly one assignment event recorded
    act_query = await db_session.execute(
        select(ActivityEvent).where(
            ActivityEvent.work_item_id == item_id,
            ActivityEvent.event_type == ActivityEventType.ASSIGNED.value
        )
    )
    activities = act_query.scalars().all()
    assert len(activities) == 1
    assert activities[0].old_value == "Unassigned"
