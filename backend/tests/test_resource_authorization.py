import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cross_team_access_rejected_with_403(
    client: AsyncClient,
    seed_test_context: dict
):
    """
    CRITICAL TEST: Resource-level Authorization.
    Users from Team Beta cannot view, claim, or mutate Team Alpha work items.
    """
    token_m1 = seed_test_context["tokens"]["member1"]
    token_outsider = seed_test_context["tokens"]["outsider"]  # Member of Team Beta only
    team_alpha_id = seed_test_context["team_alpha_id"]

    # 1. Create item in Team Alpha
    create_resp = await client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {token_m1}"},
        json={
            "title": "Alpha Confidential Payroll Sync",
            "description": "Internal alpha team data",
            "team_id": team_alpha_id,
        }
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    # 2. Team Beta outsider tries to GET the item
    get_attempt = await client.get(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {token_outsider}"}
    )
    assert get_attempt.status_code == 403
    assert "Access denied: You are not a member of team" in get_attempt.json()["detail"]

    # 3. Team Beta outsider tries to CLAIM the item
    claim_attempt = await client.post(
        f"/api/v1/items/{item_id}/claim",
        headers={"Authorization": f"Bearer {token_outsider}"}
    )
    assert claim_attempt.status_code == 403

    # 4. Team Beta outsider tries to PATCH the item
    patch_attempt = await client.patch(
        f"/api/v1/items/{item_id}",
        headers={"Authorization": f"Bearer {token_outsider}"},
        json={"title": "Hacked Title", "version": 1}
    )
    assert patch_attempt.status_code == 403


@pytest.mark.asyncio
async def test_viewer_role_cannot_mutate_or_create(
    client: AsyncClient,
    seed_test_context: dict
):
    """Viewers have read-only access and cannot create or claim items."""
    token_viewer = seed_test_context["tokens"]["viewer"]
    team_alpha_id = seed_test_context["team_alpha_id"]

    # Attempt to create an item
    create_attempt = await client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {token_viewer}"},
        json={"title": "Viewer unauthorized creation", "team_id": team_alpha_id}
    )
    assert create_attempt.status_code == 403
    assert "insufficient permissions" in create_attempt.json()["detail"]
