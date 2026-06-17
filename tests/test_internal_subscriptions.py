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


def test_internal_subscribe_requires_token():
    res = client.post(
        "/internal/users/user-1/subscriptions",
        json={"productSlug": "education"},
    )
    assert res.status_code == 401


def test_internal_subscribe_creates():
    res = client.post(
        "/internal/users/user-sub-1/subscriptions",
        json={"productSlug": "education"},
        headers=VALID_HEADERS,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["productSlug"] == "education"
    assert data["status"] == "active"


def test_internal_subscribe_idempotent():
    res1 = client.post(
        "/internal/users/user-sub-2/subscriptions",
        json={"productSlug": "education"},
        headers=VALID_HEADERS,
    )
    res2 = client.post(
        "/internal/users/user-sub-2/subscriptions",
        json={"productSlug": "education"},
        headers=VALID_HEADERS,
    )
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json() == res2.json()


def test_internal_subscribe_unknown_product():
    res = client.post(
        "/internal/users/user-1/subscriptions",
        json={"productSlug": "nonexistent"},
        headers=VALID_HEADERS,
    )
    assert res.status_code == 404
