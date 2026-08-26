import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.seed import seed_demo_data


@pytest.fixture()
def client() -> TestClient:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)
    with testing_session() as db:
        seed_demo_data(db)

    def override_get_db():
        with testing_session() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    test_client.headers.update(
        {
            "X-User-Id": "clinician-demo-001",
            "X-Role": "clinician",
            "X-Clinic-Id": "clinic-demo-001",
        }
    )
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
