import asyncio
import os
import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Dict
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.config import settings
from app.database import Base, get_db
from app.models.user import User
from app.models.team import Team, Membership
from app.models.enums import TeamRole
from app.services.auth_service import get_password_hash, create_access_token


# Use SQLite in-memory or PostgreSQL from environment for testing
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    settings.async_database_url
)

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup after all tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_test_context(db_session: AsyncSession) -> Dict[str, any]:
    """Sets up standard teams and users for tests."""
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

    # Users
    lead_user = User(
        id="user-lead",
        email="lead@alpha.test",
        full_name="Alpha Lead User",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    member_user_1 = User(
        id="user-member-1",
        email="member1@alpha.test",
        full_name="Alpha Member One",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    member_user_2 = User(
        id="user-member-2",
        email="member2@alpha.test",
        full_name="Alpha Member Two",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    viewer_user = User(
        id="user-viewer",
        email="viewer@alpha.test",
        full_name="Alpha Viewer User",
        hashed_password=get_password_hash("password123"),
        is_active=True
    )
    outsider_user = User(
        id="user-outsider",
        email="lead@beta.test",
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
            "lead": create_access_token({"sub": "user-lead", "email": "lead@alpha.test"}),
            "member1": create_access_token({"sub": "user-member-1", "email": "member1@alpha.test"}),
            "member2": create_access_token({"sub": "user-member-2", "email": "member2@alpha.test"}),
            "viewer": create_access_token({"sub": "user-viewer", "email": "viewer@alpha.test"}),
            "outsider": create_access_token({"sub": "user-outsider", "email": "lead@beta.test"}),
        }
    }
