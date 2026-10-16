import base64
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import select, update, func, or_, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.work_item import WorkItem
from app.models.activity import ActivityEvent, Comment
from app.models.outbox import OutboxJob
from app.models.team import Membership
from app.models.enums import (
    WorkItemStatus,
    WorkItemPriority,
    TeamRole,
    ActivityEventType,
    OutboxJobStatus,
)
from app.schemas.work_item import WorkItemCreate, WorkItemUpdate, WorkItemTransition
from app.services.state_machine import validate_transition


def encode_cursor(created_at: datetime, item_id: str) -> str:
    payload = {"t": created_at.isoformat(), "id": item_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def decode_cursor(cursor_str: str) -> Optional[Tuple[datetime, str]]:
    try:
        raw = base64.urlsafe_b64decode(cursor_str.encode("utf-8")).decode("utf-8")
        data = json.loads(raw)
        dt = datetime.fromisoformat(data["t"])
        return dt, data["id"]
    except Exception:
        return None


async def get_work_item_or_404(db: AsyncSession, item_id: str) -> WorkItem:
    query = (
        select(WorkItem)
        .where(WorkItem.id == item_id)
        .options(
            selectinload(WorkItem.team),
            selectinload(WorkItem.assignee),
            selectinload(WorkItem.creator),
            selectinload(WorkItem.activities).selectinload(ActivityEvent.user),
            selectinload(WorkItem.comments).selectinload(Comment.user),
        )
    )
    res = await db.execute(query)
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work item with ID '{item_id}' not found."
        )
    return item


async def list_work_items(
    db: AsyncSession,
    team_id: Optional[str] = None,
    user_team_ids: Optional[List[str]] = None,
    status_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    assignee_id: Optional[str] = None,
    search_query: Optional[str] = None,
    view: Optional[str] = None,
    current_user_id: Optional[str] = None,
    user_lead_team_ids: Optional[List[str]] = None,
    cursor: Optional[str] = None,
    limit: int = 25,
) -> Tuple[List[WorkItem], Optional[str], bool, int]:
    limit = max(1, min(limit, 100))

    conditions = []

    # Scoped team authorization
    if team_id:
        conditions.append(WorkItem.team_id == team_id)
    elif user_team_ids is not None:
        if not user_team_ids:
            return [], None, False, 0
        conditions.append(WorkItem.team_id.in_(user_team_ids))

    # Standard filters
    if status_filter:
        conditions.append(WorkItem.status == status_filter)
    if priority_filter:
        conditions.append(WorkItem.priority == priority_filter)
    if assignee_id:
        if assignee_id.lower() == "unassigned":
            conditions.append(WorkItem.assignee_id.is_(None))
        else:
            conditions.append(WorkItem.assignee_id == assignee_id)

    # Search filter (title / description)
    if search_query:
        search_pattern = f"%{search_query.strip()}%"
        conditions.append(
            or_(
                WorkItem.title.ilike(search_pattern),
                WorkItem.description.ilike(search_pattern),
            )
        )

    # Quick Attention Dashboard Views
    if view == "assigned_to_me" and current_user_id:
        conditions.append(WorkItem.assignee_id == current_user_id)
    elif view == "unassigned_urgent":
        conditions.append(WorkItem.assignee_id.is_(None))
        conditions.append(WorkItem.priority.in_([WorkItemPriority.HIGH.value, WorkItemPriority.URGENT.value]))
    elif view == "awaiting_my_approval":
        conditions.append(WorkItem.status == WorkItemStatus.AWAITING_APPROVAL.value)
        if user_lead_team_ids:
            conditions.append(WorkItem.team_id.in_(user_lead_team_ids))
        else:
            return [], None, False, 0

    # Total count calculation
    count_stmt = select(func.count(WorkItem.id)).where(and_(*conditions))
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar() or 0

    # Keyset / Cursor Pagination filter
    query_conditions = list(conditions)
    if cursor:
        decoded = decode_cursor(cursor)
        if decoded:
            c_time, c_id = decoded
            query_conditions.append(
                or_(
                    WorkItem.created_at < c_time,
                    and_(WorkItem.created_at == c_time, WorkItem.id < c_id)
                )
            )

    # Fetch 1 extra to determine has_more
    fetch_limit = limit + 1
    stmt = (
        select(WorkItem)
        .where(and_(*query_conditions))
        .options(
            selectinload(WorkItem.team),
            selectinload(WorkItem.assignee),
            selectinload(WorkItem.creator),
        )
        .order_by(desc(WorkItem.created_at), desc(WorkItem.id))
        .limit(fetch_limit)
    )

    result = await db.execute(stmt)
    items = list(result.scalars().all())

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = None
    if items and has_more:
        last_item = items[-1]
        next_cursor = encode_cursor(last_item.created_at, last_item.id)

    return items, next_cursor, has_more, total_count


async def create_work_item(
    db: AsyncSession,
    data: WorkItemCreate,
    current_user_id: str
) -> WorkItem:
    item_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    item = WorkItem(
        id=item_id,
        title=data.title,
        description=data.description,
        type=data.type.value,
        priority=data.priority.value,
        status=WorkItemStatus.OPEN.value,
        team_id=data.team_id,
        assignee_id=data.assignee_id,
        created_by_id=current_user_id,
        due_date=data.due_date,
        version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(item)

    # Activity Event: Created (in same transaction)
    activity = ActivityEvent(
        id=str(uuid.uuid4()),
        work_item_id=item_id,
        user_id=current_user_id,
        event_type=ActivityEventType.CREATED.value,
        new_value=f"Created work item '{data.title}'",
        extra_data={"initial_priority": data.priority.value, "initial_status": WorkItemStatus.OPEN.value},
        created_at=now,
    )
    db.add(activity)

    # Transactional Outbox Job (e.g. notify if assigned on creation)
    if data.assignee_id:
        outbox_job = OutboxJob(
            id=str(uuid.uuid4()),
            job_type="work_item.assigned",
            payload={
                "item_id": item_id,
                "title": data.title,
                "assignee_id": data.assignee_id,
                "actor_id": current_user_id,
                "team_id": data.team_id,
            },
            status=OutboxJobStatus.PENDING.value,
            scheduled_at=now,
            created_at=now,
        )
        db.add(outbox_job)

    await db.flush()
    return await get_work_item_or_404(db, item_id)


async def claim_work_item(
    db: AsyncSession,
    item_id: str,
    current_user_id: str,
    current_user_name: str
) -> WorkItem:
    """
    CRITICAL BEHAVIOR: Atomic conditional update for concurrency safety.
    Guarantees that if two operators click 'Claim' simultaneously,
    exactly one succeeds, and the other receives a 409 Conflict.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        update(WorkItem)
        .where(
            WorkItem.id == item_id,
            WorkItem.assignee_id.is_(None)
        )
        .values(
            assignee_id=current_user_id,
            status=WorkItemStatus.IN_PROGRESS.value,
            version=WorkItem.version + 1,
            updated_at=now
        )
    )

    result = await db.execute(stmt)

    if result.rowcount == 0:
        # Check why 0 rows updated
        item_check = await db.execute(select(WorkItem).where(WorkItem.id == item_id))
        existing = item_check.scalar_one_or_none()
        if not existing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work item not found.")
        
        if existing.assignee_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already claimed this work item."
            )
        
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: This work item has already been claimed by another team member."
        )

    # Activity log recorded in the SAME transaction
    activity = ActivityEvent(
        id=str(uuid.uuid4()),
        work_item_id=item_id,
        user_id=current_user_id,
        event_type=ActivityEventType.ASSIGNED.value,
        old_value="Unassigned",
        new_value=current_user_name,
        extra_data={"action": "atomic_claim", "status_moved_to": WorkItemStatus.IN_PROGRESS.value},
        created_at=now,
    )
    db.add(activity)

    # Transactional outbox job
    outbox = OutboxJob(
        id=str(uuid.uuid4()),
        job_type="work_item.claimed",
        payload={
            "item_id": item_id,
            "claimant_id": current_user_id,
            "claimant_name": current_user_name,
        },
        status=OutboxJobStatus.PENDING.value,
        scheduled_at=now,
        created_at=now,
    )
    db.add(outbox)

    await db.flush()
    return await get_work_item_or_404(db, item_id)


async def update_work_item_with_optimistic_lock(
    db: AsyncSession,
    item_id: str,
    update_data: WorkItemUpdate,
    current_user_id: str,
    current_user_name: str
) -> WorkItem:
    """
    CRITICAL BEHAVIOR: Optimistic Concurrency Control.
    Ensures that stale edits are rejected with a 409 Conflict.
    """
    now = datetime.now(timezone.utc)
    current_item = await get_work_item_or_404(db, item_id)

    # Build values dictionary
    values: Dict[str, Any] = {
        "version": WorkItem.version + 1,
        "updated_at": now
    }
    changes = []

    if update_data.title is not None and update_data.title != current_item.title:
        values["title"] = update_data.title
        changes.append(f"Title changed from '{current_item.title}' to '{update_data.title}'")

    if update_data.description is not None and update_data.description != current_item.description:
        values["description"] = update_data.description
        changes.append("Description updated")

    if update_data.priority is not None and update_data.priority.value != current_item.priority:
        values["priority"] = update_data.priority.value
        changes.append(f"Priority changed from '{current_item.priority}' to '{update_data.priority.value}'")

    if update_data.due_date is not None and update_data.due_date != current_item.due_date:
        values["due_date"] = update_data.due_date
        changes.append("Due date updated")

    if update_data.assignee_id is not None and update_data.assignee_id != current_item.assignee_id:
        values["assignee_id"] = update_data.assignee_id
        changes.append("Assignee updated")

    # Atomic conditional update targeting specific version
    stmt = (
        update(WorkItem)
        .where(
            WorkItem.id == item_id,
            WorkItem.version == update_data.version
        )
        .values(**values)
    )

    result = await db.execute(stmt)
    if result.rowcount == 0:
        # Check current DB version to prove conflict
        fresh = await get_work_item_or_404(db, item_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Version conflict: This work item has been modified by another operator.",
                "client_version": update_data.version,
                "current_version": fresh.version,
                "latest_item": {
                    "id": fresh.id,
                    "title": fresh.title,
                    "status": fresh.status,
                    "priority": fresh.priority,
                    "version": fresh.version,
                    "updated_at": fresh.updated_at.isoformat(),
                }
            }
        )

    # Record activity log in the same transaction
    if changes:
        activity = ActivityEvent(
            id=str(uuid.uuid4()),
            work_item_id=item_id,
            user_id=current_user_id,
            event_type=ActivityEventType.UPDATED.value,
            new_value="; ".join(changes),
            extra_data={"client_version": update_data.version, "new_version": update_data.version + 1},
            created_at=now,
        )
        db.add(activity)

    await db.flush()
    return await get_work_item_or_404(db, item_id)


async def transition_work_item(
    db: AsyncSession,
    item_id: str,
    transition_data: WorkItemTransition,
    current_user_id: str,
    current_user_name: str,
    user_role: str
) -> WorkItem:
    """
    CRITICAL BEHAVIOR: Server-Enforced Workflow State Machine.
    Validates legal transitions and restricts approvals strictly to Leads/Admins.
    """
    item = await get_work_item_or_404(db, item_id)
    target_status = transition_data.target_status.value

    # Validate against state machine rules
    validate_transition(item.status, target_status, user_role)

    now = datetime.now(timezone.utc)
    old_status = item.status

    # Update item status atomically
    stmt = (
        update(WorkItem)
        .where(
            WorkItem.id == item_id,
            WorkItem.status == old_status
        )
        .values(
            status=target_status,
            version=WorkItem.version + 1,
            updated_at=now
        )
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: Work item status was modified concurrently by another operator."
        )

    # Append activity event in the same transaction
    activity = ActivityEvent(
        id=str(uuid.uuid4()),
        work_item_id=item_id,
        user_id=current_user_id,
        event_type=ActivityEventType.STATUS_CHANGED.value,
        old_value=old_status,
        new_value=target_status,
        extra_data={"comment": transition_data.comment, "role_at_transition": user_role},
        created_at=now,
    )
    db.add(activity)

    # Optional comment
    if transition_data.comment:
        comment = Comment(
            id=str(uuid.uuid4()),
            work_item_id=item_id,
            user_id=current_user_id,
            content=transition_data.comment,
            created_at=now,
        )
        db.add(comment)

    # Enqueue Outbox Notification
    outbox = OutboxJob(
        id=str(uuid.uuid4()),
        job_type="work_item.status_changed",
        payload={
            "item_id": item_id,
            "old_status": old_status,
            "new_status": target_status,
            "actor_id": current_user_id,
            "actor_name": current_user_name,
        },
        status=OutboxJobStatus.PENDING.value,
        scheduled_at=now,
        created_at=now,
    )
    db.add(outbox)

    await db.flush()
    return await get_work_item_or_404(db, item_id)


async def add_comment(
    db: AsyncSession,
    item_id: str,
    content: str,
    current_user_id: str
) -> Comment:
    item = await get_work_item_or_404(db, item_id)
    now = datetime.now(timezone.utc)

    comment = Comment(
        id=str(uuid.uuid4()),
        work_item_id=item.id,
        user_id=current_user_id,
        content=content.strip(),
        created_at=now,
    )
    db.add(comment)

    activity = ActivityEvent(
        id=str(uuid.uuid4()),
        work_item_id=item.id,
        user_id=current_user_id,
        event_type=ActivityEventType.COMMENTED.value,
        new_value="Added a comment",
        created_at=now,
    )
    db.add(activity)

    await db.flush()
    
    # Reload comment with user relationship
    c_query = (
        select(Comment)
        .where(Comment.id == comment.id)
        .options(selectinload(Comment.user))
    )
    res = await db.execute(c_query)
    return res.scalar_one()
