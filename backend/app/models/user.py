from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base

if TYPE_CHECKING:
    from app.models.team import Membership
    from app.models.work_item import WorkItem
    from app.models.activity import ActivityEvent, Comment


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    memberships: Mapped[List["Membership"]] = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    assigned_items: Mapped[List["WorkItem"]] = relationship("WorkItem", back_populates="assignee", foreign_keys="WorkItem.assignee_id")
    created_items: Mapped[List["WorkItem"]] = relationship("WorkItem", back_populates="creator", foreign_keys="WorkItem.created_by_id")
    activities: Mapped[List["ActivityEvent"]] = relationship("ActivityEvent", back_populates="user")
    comments: Mapped[List["Comment"]] = relationship("Comment", back_populates="user")
