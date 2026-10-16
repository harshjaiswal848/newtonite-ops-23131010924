from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.team import Team, Membership
from app.models.user import User
from app.schemas.team import TeamRead
from app.api.deps import get_current_user, verify_team_access

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=List[TeamRead])
async def get_my_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all teams that the authenticated user is a member of."""
    stmt = (
        select(Team)
        .join(Membership, Membership.team_id == Team.id)
        .where(Membership.user_id == current_user.id)
        .options(
            selectinload(Team.memberships).selectinload(Membership.user)
        )
        .order_by(Team.name)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/all", response_model=List[TeamRead])
async def list_all_teams(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all teams in the organization for discovery."""
    stmt = (
        select(Team)
        .options(
            selectinload(Team.memberships).selectinload(Membership.user)
        )
        .order_by(Team.name)
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(
    team_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    verify_team_access(current_user, team_id)

    stmt = (
        select(Team)
        .where(Team.id == team_id)
        .options(
            selectinload(Team.memberships).selectinload(Membership.user)
        )
    )
    res = await db.execute(stmt)
    team = res.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")
    return team
