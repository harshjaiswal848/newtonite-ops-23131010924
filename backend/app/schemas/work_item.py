from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import WorkItemType, WorkItemPriority, WorkItemStatus
from app.schemas.auth import UserRead
from app.schemas.team import TeamSummary
from app.schemas.activity import ActivityEventRead, CommentRead


class WorkItemBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: str = Field("", max_length=10000)
    type: WorkItemType = WorkItemType.TASK
    priority: WorkItemPriority = WorkItemPriority.MEDIUM
    due_date: Optional[datetime] = None


class WorkItemCreate(WorkItemBase):
    team_id: str
    assignee_id: Optional[str] = None


class WorkItemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    priority: Optional[WorkItemPriority] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[str] = None
    # Crucial for optimistic locking:
    version: int = Field(..., description="Current version on client to prevent stale updates")


class WorkItemTransition(BaseModel):
    target_status: WorkItemStatus
    comment: Optional[str] = None


class WorkItemClaim(BaseModel):
    pass


class WorkItemRead(BaseModel):
    id: str
    title: str
    description: str
    type: str
    priority: str
    status: str
    team_id: str
    assignee_id: Optional[str] = None
    created_by_id: str
    due_date: Optional[datetime] = None
    version: int
    created_at: datetime
    updated_at: datetime

    team: Optional[TeamSummary] = None
    assignee: Optional[UserRead] = None
    creator: Optional[UserRead] = None
    activities: Optional[List[ActivityEventRead]] = None
    comments: Optional[List[CommentRead]] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedWorkItems(BaseModel):
    items: List[WorkItemRead]
    next_cursor: Optional[str] = None
    has_more: bool
    total_count: Optional[int] = None
