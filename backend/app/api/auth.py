from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.team import Membership
from app.schemas.auth import LoginRequest, Token, UserRead, TeamRoleInfo
from app.services.auth_service import verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(User)
        .where(User.email == login_data.email.lower().strip())
        .options(selectinload(User.memberships))
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    return Token(access_token=access_token, expires_in=86400)


@router.post("/token", response_model=Token)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """OAuth2 compatible token endpoint for swagger docs."""
    stmt = (
        select(User)
        .where(User.email == form_data.username.lower().strip())
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    return Token(access_token=access_token, expires_in=86400)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    roles_info = [
        TeamRoleInfo(
            team_id=m.team_id,
            team_name=m.team.name if m.team else m.team_id,
            role=m.role
        )
        for m in current_user.memberships
    ]
    return UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        roles=roles_info,
        created_at=current_user.created_at
    )


@router.get("/demo-users")
async def list_demo_users(db: AsyncSession = Depends(get_db)):
    """Convenience endpoint returning pre-seeded accounts for 1-click login on reviewer's UI."""
    stmt = (
        select(User)
        .options(selectinload(User.memberships).selectinload(Membership.team))
        .order_by(User.email)
    )
    res = await db.execute(stmt)
    users = res.scalars().all()
    
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "teams": [
                {"team_id": m.team_id, "team_name": m.team.name if m.team else m.team_id, "role": m.role}
                for m in u.memberships
            ]
        }
        for u in users
    ]
