import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, get_password_hash
from app.database import Base
from app.main import app
from app.models.user import User, UserRole

load_dotenv()

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

test_async_session_maker = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """
    Creates all tables before the test session starts and drops them after.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Deletes all data from tables after each test to ensure test isolation."""
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest_asyncio.fixture
async def db_session():
    async with test_async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    HTTP client for API testing.

    Overrides get_db with the test session via dependency_overrides.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def student_user(db_session: AsyncSession) -> User:
    """Creates a test student user in the database."""
    user = User(
        email="student@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test Student",
        role=UserRole.STUDENT,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def instructor_user(db_session: AsyncSession) -> User:
    """Creates a test instructor user in the database."""
    user = User(
        email="instructor@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test Instructor",
        role=UserRole.INSTRUCTOR,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Creates a test admin user in the database."""
    user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def student_client(db_session: AsyncSession, student_user: User):
    """
    HTTP client authorized as a student.

    Overrides get_current_user so there is no need to perform a real login
    or pass a JWT token in every request.
    """

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return student_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def instructor_client(db_session: AsyncSession, instructor_user: User):
    """HTTP client authorized as an instructor."""

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return instructor_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def student_token(student_user: User) -> str:
    """JWT token for a student user."""
    return create_access_token(data={"sub": student_user.email})


@pytest.fixture
def instructor_token(instructor_user: User) -> str:
    """JWT token for an instructor user."""
    return create_access_token(data={"sub": instructor_user.email})
