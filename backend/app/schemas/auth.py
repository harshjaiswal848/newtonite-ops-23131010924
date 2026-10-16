from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr, ConfigDict


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TeamRoleInfo(BaseModel):
    team_id: str
    team_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    roles: List[TeamRoleInfo] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
