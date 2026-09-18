from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services.auth_users import create_user, search_users

settings.internal_api_token = "test-internal-token"

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
HEADERS = {"X-Internal-Token": "test-internal-token"}


def _make_user(db, username: str, email: str, first: str, last: str):
    return create_user(
        db,
        username=username,
        email=email,
        password="pass12",
        first_name=first,
        last_name=last,
        gender="prefer_not_to_say",
        date_of_birth=date(1990, 1, 1),
        contact_number="+10000000000",
        whatsapp_available=False,
    )


def test_internal_search_finds_username():
    db = TestingSession()
    _make_user(db, "prashantgopishetty", "prashant@example.com", "Prashant", "Gopishetty")
    _make_user(db, "sandhyagopishetty", "sandhya@example.com", "Sandhya", "Gopishetty")
    db.close()

    res = client.get("/internal/users/search?q=sandhya", headers=HEADERS)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "sandhyagopishetty"
    assert items[0]["email"] == "sandhya@example.com"


def test_internal_search_requires_token():
    res = client.get("/internal/users/search?q=sandhya")
    assert res.status_code == 401


def test_search_users_service_matches_partial_username():
    db = TestingSession()
    _make_user(db, "anothersandhya", "another.sandhya@example.com", "Sandhya", "Rao")
    rows = search_users(db, "AnotherSand")
    assert len(rows) == 1
    assert rows[0].username == "anothersandhya"
    db.close()
