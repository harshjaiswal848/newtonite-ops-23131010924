import os
import sys
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, delete
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.main import app
from app.config import settings
from app.database import Base, get_db
from app.models.user import User
from app.models.team import Team, Membership
from app.models.enums import TeamRole
from app.services.auth_service import get_password_hash, create_access_token


TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    settings.async_database_url
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_test_context(db_session: AsyncSession) -> Dict[str, any]:
    """Sets up clean test teams and personas with clean state per test."""
    test_user_ids = ["user-lead", "user-member-1", "user-member-2", "user-viewer", "user-outsider"]
    test_team_ids = ["team-alpha", "team-beta"]

    # Clean previous test records if any exist
    await db_session.execute(delete(Membership).where(Membership.team_id.in_(test_team_ids)))
    await db_session.execute(delete(Team).where(Team.id.in_(test_team_ids)))
    await db_session.execute(delete(User).where(User.id.in_(test_user_ids)))
    await db_session.commit()

    # Team Alpha (Payments)
    team_alpha = Team(
        id="team-alpha",
        name="Team Alpha (Payments)",
        slug="team-alpha",
        description="Testing Team Alpha"
    )
    # Team Beta (Compliance - Isolated)
    team_beta = Team(
        id="team-beta",
        name="Team Beta (Compliance)",
        slug="team-beta",
        description="Testing Team Beta"
    )
    db_session.add_all([team_alpha, team_beta])

    # Test Personas
    lead_user = User(
        id="user-lead",
        email="lead@alpha.internal",
        full_name="Alpha Lead User",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    member_user_1 = User(
        id="user-member-1",
        email="member1@alpha.internal",
        full_name="Alpha Member One",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    member_user_2 = User(
        id="user-member-2",
        email="member2@alpha.internal",
        full_name="Alpha Member Two",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    viewer_user = User(
        id="user-viewer",
        email="viewer@alpha.internal",
        full_name="Alpha Viewer User",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    outsider_user = User(
        id="user-outsider",
        email="lead@beta.internal",
        full_name="Beta Lead User",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )

    db_session.add_all([lead_user, member_user_1, member_user_2, viewer_user, outsider_user])

    # Memberships
    m_lead = Membership(id="m-lead", user_id="user-lead", team_id="team-alpha", role=TeamRole.LEAD.value)
    m_m1 = Membership(id="m-m1", user_id="user-member-1", team_id="team-alpha", role=TeamRole.MEMBER.value)
    m_m2 = Membership(id="m-m2", user_id="user-member-2", team_id="team-alpha", role=TeamRole.MEMBER.value)
    m_viewer = Membership(id="m-v", user_id="user-viewer", team_id="team-alpha", role=TeamRole.VIEWER.value)
    m_outsider = Membership(id="m-out", user_id="user-outsider", team_id="team-beta", role=TeamRole.LEAD.value)

    db_session.add_all([m_lead, m_m1, m_m2, m_viewer, m_outsider])
    await db_session.commit()

    return {
        "team_alpha_id": "team-alpha",
        "team_beta_id": "team-beta",
        "tokens": {
            "lead": create_access_token({"sub": "user-lead", "email": "lead@alpha.internal"}),
            "member1": create_access_token({"sub": "user-member-1", "email": "member1@alpha.internal"}),
            "member2": create_access_token({"sub": "user-member-2", "email": "member2@alpha.internal"}),
            "viewer": create_access_token({"sub": "user-viewer", "email": "viewer@alpha.internal"}),
            "outsider": create_access_token({"sub": "user-outsider", "email": "lead@beta.internal"}),
        }
    }
