from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict
from app.schemas.auth import UserRead


class ActivityEventRead(BaseModel):
    id: str
    work_item_id: str
    user_id: Optional[str] = None
    event_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    user: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    content: str


class CommentRead(BaseModel):
    id: str
    work_item_id: str
    user_id: str
    content: str
    created_at: datetime
    user: Optional[UserRead] = None

    model_config = ConfigDict(from_attributes=True)
