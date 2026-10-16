from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.enums import TeamRole


class MembershipUserRead(BaseModel):
    id: str
    email: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class MembershipRead(BaseModel):
    id: str
    user_id: str
    team_id: str
    role: str
    user: Optional[MembershipUserRead] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamSummary(BaseModel):
    id: str
    name: str
    slug: str
    description: str

    model_config = ConfigDict(from_attributes=True)


class TeamRead(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    created_at: datetime
    memberships: List[MembershipRead] = []

    model_config = ConfigDict(from_attributes=True)
