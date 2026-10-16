from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.enums import TeamRole
from app.schemas.work_item import (
    WorkItemCreate,
    WorkItemUpdate,
    WorkItemTransition,
    WorkItemRead,
    PaginatedWorkItems,
)
from app.schemas.activity import ActivityEventRead, CommentCreate, CommentRead
from app.api.deps import (
    get_current_user,
    verify_team_access,
    get_user_team_roles_dict,
    get_idempotency_key,
)
from app.services import item_service
from app.services import idempotency_service

router = APIRouter(prefix="/items", tags=["Work Items"])


@router.get("", response_model=PaginatedWorkItems)
async def list_items(
    team_id: Optional[str] = Query(None, description="Scope query to specific team"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    assignee_id: Optional[str] = Query(None, description="Filter by assignee user ID or 'unassigned'"),
    q: Optional[str] = Query(None, description="Search term in title and description"),
    view: Optional[str] = Query(None, description="Quick view: assigned_to_me, unassigned_urgent, awaiting_my_approval"),
    cursor: Optional[str] = Query(None, description="Keyset pagination cursor"),
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Paginated, filtered list of work items with keyset / cursor pagination.
    Guarantees consistent performance at scale and enforces team isolation.
    """
    roles_map = get_user_team_roles_dict(current_user)
    user_team_ids = list(roles_map.keys())

    if team_id:
        verify_team_access(current_user, team_id)

    # Teams where user is a Lead or Admin (for awaiting_my_approval view)
    user_lead_team_ids = [
        tid for tid, r in roles_map.items()
        if r in (TeamRole.LEAD.value, TeamRole.ADMIN.value)
    ]

    items, next_cursor, has_more, total_count = await item_service.list_work_items(
        db=db,
        team_id=team_id,
        user_team_ids=user_team_ids,
        status_filter=status,
        priority_filter=priority,
        assignee_id=assignee_id,
        search_query=q,
        view=view,
        current_user_id=current_user.id,
        user_lead_team_ids=user_lead_team_ids,
        cursor=cursor,
        limit=limit,
    )

    return PaginatedWorkItems(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total_count=total_count,
    )


@router.post("", response_model=WorkItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_in: WorkItemCreate,
    response: Response,
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new work item with role verification, idempotency protection,
    and guaranteed transactional audit log.
    """
    # Authorization: Viewer cannot create items
    verify_team_access(
        current_user,
        item_in.team_id,
        allowed_roles=[TeamRole.MEMBER, TeamRole.LEAD, TeamRole.ADMIN]
    )

    endpoint = "/api/v1/items"
    request_payload = item_in.model_dump(mode="json")

    # Check idempotency replay
    if idempotency_key:
        cached = await idempotency_service.check_idempotency_key(
            db=db,
            key=idempotency_key,
            user_id=current_user.id,
            endpoint=endpoint,
            body=request_payload
        )
        if cached:
            status_code, cached_body = cached
            response.status_code = status_code
            response.headers["Idempotent-Replay"] = "true"
            return cached_body

    created_item = await item_service.create_work_item(
        db=db,
        data=item_in,
        current_user_id=current_user.id
    )

    item_read = WorkItemRead.model_validate(created_item)
    response_data = item_read.model_dump(mode="json")

    # Record idempotency record in the SAME transaction
    if idempotency_key:
        await idempotency_service.save_idempotency_key(
            db=db,
            key=idempotency_key,
            user_id=current_user.id,
            endpoint=endpoint,
            body=request_payload,
            response_code=status.HTTP_201_CREATED,
            response_body=response_data,
        )

    await db.commit()
    return created_item


@router.get("/{item_id}", response_model=WorkItemRead)
async def get_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    item = await item_service.get_work_item_or_404(db, item_id)
    verify_team_access(current_user, item.team_id)
    return item


@router.patch("/{item_id}", response_model=WorkItemRead)
async def update_item(
    item_id: str,
    update_data: WorkItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    CRITICAL BEHAVIOR: Optimistic Locking update.
    Client supplies version number; fails with 409 Conflict if item was updated by someone else.
    """
    item = await item_service.get_work_item_or_404(db, item_id)
    verify_team_access(
        current_user,
        item.team_id,
        allowed_roles=[TeamRole.MEMBER, TeamRole.LEAD, TeamRole.ADMIN]
    )

    updated_item = await item_service.update_work_item_with_optimistic_lock(
        db=db,
        item_id=item_id,
        update_data=update_data,
        current_user_id=current_user.id,
        current_user_name=current_user.full_name,
    )

    await db.commit()
    return updated_item


@router.post("/{item_id}/claim", response_model=WorkItemRead)
async def claim_item(
    item_id: str,
    response: Response,
    idempotency_key: Optional[str] = Depends(get_idempotency_key),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    CRITICAL BEHAVIOR: Atomic Claim.
    Simultaneous claims on the same item guarantee exactly one winner and 409 Conflict for the rest.
    """
    item = await item_service.get_work_item_or_404(db, item_id)
    verify_team_access(
        current_user,
        item.team_id,
        allowed_roles=[TeamRole.MEMBER, TeamRole.LEAD, TeamRole.ADMIN]
    )

    endpoint = f"/api/v1/items/{item_id}/claim"
    if idempotency_key:
        cached = await idempotency_service.check_idempotency_key(
            db=db,
            key=idempotency_key,
            user_id=current_user.id,
            endpoint=endpoint,
            body={"item_id": item_id}
        )
        if cached:
            status_code, cached_body = cached
            response.status_code = status_code
            response.headers["Idempotent-Replay"] = "true"
            return cached_body

    claimed_item = await item_service.claim_work_item(
        db=db,
        item_id=item_id,
        current_user_id=current_user.id,
        current_user_name=current_user.full_name
    )

    response_data = WorkItemRead.model_validate(claimed_item).model_dump(mode="json")
    if idempotency_key:
        await idempotency_service.save_idempotency_key(
            db=db,
            key=idempotency_key,
            user_id=current_user.id,
            endpoint=endpoint,
            body={"item_id": item_id},
            response_code=status.HTTP_200_OK,
            response_body=response_data,
        )

    await db.commit()
    return claimed_item


@router.post("/{item_id}/transition", response_model=WorkItemRead)
async def transition_item(
    item_id: str,
    transition_data: WorkItemTransition,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    CRITICAL BEHAVIOR: Workflow State Machine & Role Validation.
    Enforces valid sequence and requires Lead/Admin role for approval.
    """
    item = await item_service.get_work_item_or_404(db, item_id)
    user_role = verify_team_access(current_user, item.team_id)

    transitioned_item = await item_service.transition_work_item(
        db=db,
        item_id=item_id,
        transition_data=transition_data,
        current_user_id=current_user.id,
        current_user_name=current_user.full_name,
        user_role=user_role,
    )

    await db.commit()
    return transitioned_item


@router.post("/{item_id}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def add_item_comment(
    item_id: str,
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    item = await item_service.get_work_item_or_404(db, item_id)
    verify_team_access(
        current_user,
        item.team_id,
        allowed_roles=[TeamRole.MEMBER, TeamRole.LEAD, TeamRole.ADMIN]
    )

    new_comment = await item_service.add_comment(
        db=db,
        item_id=item_id,
        content=comment_in.content,
        current_user_id=current_user.id
    )

    await db.commit()
    return new_comment


@router.get("/{item_id}/activity", response_model=List[ActivityEventRead])
async def get_item_activity(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    item = await item_service.get_work_item_or_404(db, item_id)
    verify_team_access(current_user, item.team_id)
    return item.activities
