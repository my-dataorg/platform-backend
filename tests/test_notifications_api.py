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
from app.services.notifications import create_notification

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
create_notification(
    db,
    user_id="user-notify-1",
    type="education.invitation",
    title="Hello",
    body="Body",
    link="/invitations",
)
db.close()


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_notifications_require_auth():
    res = client.get("/v1/users/me/notifications")
    assert res.status_code == 401


def test_mark_read_requires_auth():
    res = client.patch("/v1/users/me/notifications/nope", json={"read": True})
    assert res.status_code == 401
