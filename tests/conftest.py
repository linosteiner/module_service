import os

# Must be set before app.database creates its engine on import. The tests run against an
# in-memory SQLite database; the MySQL-specific parts (schema.sql, TLS) are not exercised.
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session], None, None]:
    # StaticPool: one shared connection, otherwise every session would see its own empty
    # in-memory database.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def module(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/modules", json={"code": "cloud-arch", "name": "Cloud Architecture"}
    )
    assert response.status_code == 201
    return response.json()
