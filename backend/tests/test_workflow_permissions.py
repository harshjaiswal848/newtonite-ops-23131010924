import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workflow_state_machine_and_lead_approval(
    client: AsyncClient,
    seed_test_context: dict
):
    """
    CRITICAL TEST: Server-enforced state machine & Lead-only approval gate.
    1. Direct invalid transition (Open -> Closed) is rejected with 400.
    2. Member moves Open -> In Progress -> Awaiting Approval (allowed).
    3. Member attempts to approve to Resolved -> REJECTED with 403 Forbidden.
    4. Lead approves to Resolved -> SUCCEEDS with 200 OK.
    """
    token_lead = seed_test_context["tokens"]["lead"]
    token_member = seed_test_context["tokens"]["member1"]
    team_id = seed_test_context["team_alpha_id"]

    # 1. Create item (starts in 'Open')
    create_resp = await client.post(
        "/api/v1/items",
        headers={"Authorization": f"Bearer {token_member}"},
        json={"title": "Compliance Audit Item", "description": "Workflow test", "team_id": team_id},
    )
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    # 2. Attempt illegal jump: Open -> Closed
    bad_jump = await client.post(
        f"/api/v1/items/{item_id}/transition",
        headers={"Authorization": f"Bearer {token_member}"},
        json={"target_status": "Closed"},
    )
    assert bad_jump.status_code == 400
    assert "Forbidden workflow transition" in bad_jump.json()["detail"]

    # 3. Legitimate transition: Open -> In Progress
    t1 = await client.post(
        f"/api/v1/items/{item_id}/transition",
        headers={"Authorization": f"Bearer {token_member}"},
        json={"target_status": "In Progress"},
    )
    assert t1.status_code == 200
    assert t1.json()["status"] == "In Progress"

    # 4. Legitimate transition: In Progress -> Awaiting Approval
    t2 = await client.post(
        f"/api/v1/items/{item_id}/transition",
        headers={"Authorization": f"Bearer {token_member}"},
        json={"target_status": "Awaiting Approval", "comment": "Ready for Lead review"},
    )
    assert t2.status_code == 200
    assert t2.json()["status"] == "Awaiting Approval"

    # 5. Non-Lead tries to approve: Awaiting Approval -> Resolved
    unauthorized_approval = await client.post(
        f"/api/v1/items/{item_id}/transition",
        headers={"Authorization": f"Bearer {token_member}"},
        json={"target_status": "Resolved"},
    )
    # Must be 403 Forbidden!
    assert unauthorized_approval.status_code == 403
    assert "Only a team Lead or Admin can approve" in unauthorized_approval.json()["detail"]

    # 6. Team Lead approves: Awaiting Approval -> Resolved
    lead_approval = await client.post(
        f"/api/v1/items/{item_id}/transition",
        headers={"Authorization": f"Bearer {token_lead}"},
        json={"target_status": "Resolved", "comment": "Approved and verified by Lead"},
    )
    assert lead_approval.status_code == 200
    assert lead_approval.json()["status"] == "Resolved"

    # 7. Lead closes item: Resolved -> Closed
    lead_close = await client.post(
        f"/api/v1/items/{item_id}/transition",
        headers={"Authorization": f"Bearer {token_lead}"},
        json={"target_status": "Closed"},
    )
    assert lead_close.status_code == 200
    assert lead_close.json()["status"] == "Closed"
