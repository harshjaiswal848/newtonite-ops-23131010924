from typing import Optional, List, Dict
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.team import Membership, Team
from app.models.work_item import WorkItem
from app.models.enums import TeamRole
from app.services.auth_service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session expired.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise credentials_exception

    query = (
        select(User)
        .where(User.id == user_id, User.is_active == True)
        .options(
            selectinload(User.memberships).selectinload(Membership.team)
        )
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception

    return user


def get_user_team_roles_dict(user: User) -> Dict[str, str]:
    """Returns a dict mapping team_id -> role string for fast lookup."""
    return {m.team_id: m.role for m in user.memberships}


def verify_team_access(
    user: User,
    team_id: str,
    allowed_roles: Optional[List[TeamRole]] = None
) -> str:
    """
    CRITICAL BEHAVIOR: Real Resource-level Server Authorization.
    Enforces per-team permissions. Rejects users with 403 Forbidden.
    """
    roles_map = get_user_team_roles_dict(user)
    
    # Check if user has an Admin membership in any team for emergency oversight,
    # or specifically check within the given team
    user_role = roles_map.get(team_id)

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You are not a member of team '{team_id}'."
        )

    if allowed_roles:
        allowed_values = [r.value for r in allowed_roles]
        if user_role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user_role}' has insufficient permissions for this operation."
            )

    return user_role


def get_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
) -> Optional[str]:
    return idempotency_key
