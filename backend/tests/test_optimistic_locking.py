import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.work_item import WorkItem


@pytest.mark.asyncio
async def test_stale_update_rejected_with_409(client: AsyncClient, seed_test_context: dict, db_session: AsyncSession):
    """
    CRITICAL TEST: Optimistic Concurrency Control.
    When a user attempts to update a record using a stale version,
    the server rejects the edit with 409 Conflict and protects data integrity.
    """
    token_m1 = seed_test_context["tokens"]["member1"]
    token_m2 = seed_test_context["tokens"]["member2"]
    team_id = seed_test_context["team_alpha_id"]

    # 1. Create work item (initial version = 1)
    create_resp = await client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {token_m1}"},
        json={
            "title": "Database Connection Pool Saturation",
            "description": "Original description text",
            "type": "incident",
            "priority": "medium",
            "team_id": team_id,
        }
    )
    assert create_resp.status_code == 201
    item = create_resp.json()
    item_id = item["id"]
    assert item["version"] == 1

    # 2. User 1 successfully updates the item with version=1 -> version becomes 2
    update_1 = await client.patch(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {token_m1}"},
        json={
            "title": "Database Pool Saturation [RESOLVING]",
            "description": "Pool size doubled to 50",
            "priority": "high",
            "version": 1,
        }
    )
    assert update_1.status_code == 200
    updated_data = update_1.json()
    assert updated_data["version"] == 2
    assert updated_data["priority"] == "high"

    # 3. User 2 (who still held the stale version=1 snapshot) attempts an edit
    stale_update = await client.patch(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {token_m2}"},
        json={
            "title": "Stale Overwrite Attempt",
            "description": "Should not be saved",
            "priority": "low",
            "version": 1,  # STALE VERSION!
        }
    )

    # 4. Assertions: Must be rejected with 409 Conflict
    assert stale_update.status_code == 409
    error_body = stale_update.json()
    assert "Version conflict" in str(error_body)

    # 5. Verify database data remains the version 2 values (User 1's values untouched)
    item_query = await db_session.execute(select(WorkItem).where(WorkItem.id == item_id))
    db_item = item_query.scalar_one()

    assert db_item.version == 2
    assert db_item.title == "Database Pool Saturation [RESOLVING]"
    assert db_item.priority == "high"
    assert db_item.description == "Pool size doubled to 50"
