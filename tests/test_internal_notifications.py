import os

os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services.catalog import seed_products

settings.internal_api_token = "test-internal-token"

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

db = TestingSession()
seed_products(db)
db.close()


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

VALID_HEADERS = {"X-Internal-Token": "test-internal-token"}


def test_internal_notification_requires_token():
    res = client.post(
        "/internal/notifications",
        json={
            "userId": "user-1",
            "type": "education.invitation",
            "title": "Test",
            "body": "Body",
            "link": "/invitations",
        },
    )
    assert res.status_code == 401


def test_internal_notification_rejects_invalid_token():
    res = client.post(
        "/internal/notifications",
        json={
            "userId": "user-1",
            "type": "education.invitation",
            "title": "Test",
        },
        headers={"X-Internal-Token": "wrong"},
    )
    assert res.status_code == 401


def test_internal_notification_creates():
    res = client.post(
        "/internal/notifications",
        json={
            "userId": "user-1",
            "type": "education.invitation",
            "title": "Invitation to E2E Academy",
            "body": "You were invited as Teacher.",
            "link": "http://localhost:3000/invitations",
        },
        headers=VALID_HEADERS,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Invitation to E2E Academy"
    assert data["read"] is False
    assert data["id"]
