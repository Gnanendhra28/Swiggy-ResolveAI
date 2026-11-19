import os
# Force local SQLite database for unit and regression test suite execution
os.environ["DATABASE_URL"] = "sqlite:///./resolveai.db"
os.environ["ENVIRONMENT"] = "testing"

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.app.database.base import Base
from backend.app.database.session import get_db, engine
from backend.app.main import app
from backend.app.services.simulation_service import SimulationService

# In-memory SQLite engine for fast, isolated, reliable tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine_test)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass
    yield
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception:
        pass
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    connection = engine_test.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Ensure seed entities exist for tests
    SimulationService.ensure_synthetic_seed_entities(session)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
