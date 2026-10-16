from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.enums import WorkItemType, WorkItemPriority, WorkItemStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.team import Team
    from app.models.activity import ActivityEvent, Comment


class WorkItem(Base):
    __tablename__ = "work_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    type: Mapped[str] = mapped_column(String(50), default=WorkItemType.TASK.value, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default=WorkItemPriority.MEDIUM.value, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default=WorkItemStatus.OPEN.value, nullable=False, index=True)
    
    team_id: Mapped[str] = mapped_column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    team: Mapped["Team"] = relationship("Team", back_populates="work_items")
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_items")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by_id], back_populates="created_items")
    activities: Mapped[List["ActivityEvent"]] = relationship("ActivityEvent", back_populates="work_item", cascade="all, delete-orphan", order_by="ActivityEvent.created_at.desc()")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="work_item", cascade="all, delete-orphan", order_by="Comment.created_at.desc()")

    __table_args__ = (
        # Composite indexes for high performance team-scoped queries and cursor pagination
        Index("ix_work_items_team_status", "team_id", "status"),
        Index("ix_work_items_team_priority", "team_id", "priority"),
        Index("ix_work_items_team_assignee", "team_id", "assignee_id"),
        Index("ix_work_items_team_cursor", "team_id", "created_at", "id"),
    )
