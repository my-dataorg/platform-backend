import os
from datetime import date

os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services.auth_users import create_user
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


def test_internal_users_brief_requires_token():
    res = client.post("/internal/users/brief", json={"userIds": ["u1"]})
    assert res.status_code == 401


def test_internal_users_brief_returns_names():
    db = TestingSession()
    user = create_user(
        db,
        username="teacher1",
        email="teacher1@mydata.local",
        password="pass",
        first_name="Priya",
        last_name="Sharma",
        gender="female",
        date_of_birth=date(1990, 1, 1),
        contact_number="+10000000001",
        whatsapp_available=False,
    )
    db.close()

    res = client.post(
        "/internal/users/brief",
        json={"userIds": [user.id]},
        headers=VALID_HEADERS,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["firstName"] == "Priya"
    assert items[0]["lastName"] == "Sharma"
    assert items[0]["displayName"] == "Priya Sharma"
    assert items[0]["email"] == "teacher1@mydata.local"
