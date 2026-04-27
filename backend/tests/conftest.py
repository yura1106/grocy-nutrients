"""
Shared pytest fixtures for all tests.
"""

import os
import sys
from pathlib import Path

# ── Must be set before all app imports ────────────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-tests-only-32chars!!")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import MagicMock

# ── App imports (safe after environment variables are set) ─────────────────────
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

# Import all models so that SQLModel.metadata contains all tables
import app.db.base
from app.core.auth import get_current_user
from app.core.security import create_access_token, get_password_hash
from app.db.base import get_db
from app.main import app
from app.models.currency import CurrencyRate  # noqa: F401
from app.models.household import Household, HouseholdUser, Role

# Explicit import of models not registered via app.db.base
from app.models.product import ConsumedProduct, MealPlanConsumption, NoteNutrients  # noqa: F401
from app.models.recipe import RecipeConsumedProduct  # noqa: F401
from app.models.user import User
from app.services.grocy_api import GrocyAPI

# Default household_id used in tests that require it as a query param
TEST_HOUSEHOLD_ID = 1

# ── SQLite in-memory engine ────────────────────────────────────────────────────
# StaticPool ensures the same in-memory connection is reused.
# check_same_thread=False is required for SQLite + threading.
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """
    Session-scoped SQLite engine. Created once for the entire test session.
    All SQLModel tables are created here.
    """
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture()
def db(engine) -> Generator[Session, None, None]:
    """
    Function-scoped database session with rollback after each test.
    Ensures complete isolation — no shared state between tests.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def test_user(db: Session) -> User:
    """Creates a standard test user in the database."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        # SQLite does not execute server_default=func.now(), so we set it explicitly
        # to prevent UserRead(created_at: datetime) from failing with ValidationError
        created_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def test_household(db: Session, test_user: User) -> Household:
    """Creates a test household with the test user as admin."""
    role = db.exec(select(Role).where(Role.name == "admin")).first()
    if not role:
        role = Role(name="admin")
        db.add(role)
        db.commit()
        db.refresh(role)

    household = Household(
        id=TEST_HOUSEHOLD_ID, name="Test Household", created_at=datetime.now(UTC)
    )
    db.add(household)
    db.commit()
    db.refresh(household)

    membership = HouseholdUser(
        household_id=household.id,
        user_id=test_user.id,
        role_id=role.id,
        is_active=True,
    )
    db.add(membership)
    db.commit()
    return household


@pytest.fixture()
def auth_token(test_user: User) -> str:
    """Generates a valid access JWT for the test user."""
    return create_access_token(subject=test_user.id, token_version=test_user.token_version or 0)


@pytest.fixture()
def cookie_client(
    db: Session, test_user: User, auth_token: str
) -> Generator[TestClient, None, None]:
    """TestClient that authenticates by setting the access cookie (real auth path).

    Use this when you want to exercise the cookie-based dependency, not bypass it.
    """
    from app.core.config import settings

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        c.cookies.set(settings.access_cookie_name, auth_token)
        c.headers.update({"Origin": TEST_ORIGIN})
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def mock_grocy_api() -> MagicMock:
    """
    Returns a MagicMock for GrocyAPI with sensible default return values.
    Used for overriding the get_grocy_api dependency.
    """
    mock = MagicMock(spec=GrocyAPI)
    mock.get_meal_plan_recipe.return_value = {}
    mock.get_product.return_value = {"id": 1, "name": "Test Product"}
    mock.create_recipe_shopping_list.return_value = None
    return mock


# Origin header that satisfies the CSRF middleware (must be in CORS_ORIGINS).
TEST_ORIGIN = "http://localhost:5173"


@pytest.fixture()
def client(db: Session, test_user: User) -> Generator[TestClient, None, None]:
    """
    TestClient with full dependency overrides:
    - get_db → in-memory SQLite session
    - get_current_user → returns test_user (bypasses JWT validation)

    Use for tests of authenticated endpoints.
    """

    def override_get_db():
        yield db

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        c.headers.update({"Origin": TEST_ORIGIN})
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client(db: Session) -> Generator[TestClient, None, None]:
    """
    TestClient with only get_db overridden.
    Use for testing authentication endpoints (register, login),
    which handle their own authorization logic.
    """

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        c.headers.update({"Origin": TEST_ORIGIN})
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def grocy_client(
    db: Session,
    test_user: User,
    mock_grocy_api: MagicMock,
) -> Generator[TestClient, None, None]:
    """
    TestClient for endpoints that require GrocyAPI.
    Overrides get_current_user and get_grocy_api (returns mock).
    """
    from app.core.auth import get_grocy_api

    def override_get_db():
        yield db

    def override_get_current_user():
        return test_user

    def override_get_grocy_api():
        return mock_grocy_api

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_grocy_api] = override_get_grocy_api

    with TestClient(app) as c:
        c.headers.update({"Origin": TEST_ORIGIN})
        yield c

    app.dependency_overrides.clear()
