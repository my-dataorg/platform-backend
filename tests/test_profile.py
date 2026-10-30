from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base
from app.services.auth_users import create_user

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)
client = TestClient(app)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def use_profile_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def _profile(**overrides):
    body = {
        "firstName": "Prashant",
        "lastName": "Gopishetty",
        "email": "prashant@example.com",
        "gender": "prefer_not_to_say",
        "dateOfBirth": "1990-01-01",
        "contactNumber": "+10000000001",
        "whatsappAvailable": True,
        "addressLine1": None,
        "city": "Austin",
        "country": None,
        "state": None,
        "preferredLanguage": "en",
    }
    body.update(overrides)
    return body


def _user(username="prashant", email="prashant@example.com"):
    db = TestingSession()
    create_user(
        db,
        username=username,
        email=email,
        password="pass12",
        first_name="Prashant",
        last_name="Gopishetty",
        gender="prefer_not_to_say",
        date_of_birth=date(1990, 1, 1),
        contact_number="+10000000000",
        whatsapp_available=False,
    )
    db.close()


def _token(username="prashant"):
    res = client.post("/v1/auth/login", json={"username": username, "password": "pass12"})
    assert res.status_code == 200
    return res.json()["accessToken"]


def test_update_profile_changes_name_and_password():
    _user()
    token = _token()
    res = client.patch(
        "/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json=_profile(newPassword="newpass", currentPassword="pass12"),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["firstName"] == "Prashant"
    assert body["city"] == "Austin"
    assert body["whatsappAvailable"] is True

    old_login = client.post("/v1/auth/login", json={"username": "prashant", "password": "pass12"})
    assert old_login.status_code == 401
    new_login = client.post("/v1/auth/login", json={"username": "prashant", "password": "newpass"})
    assert new_login.status_code == 200


def test_update_profile_rejects_wrong_password_and_duplicate_email():
    _user()
    _user(username="other", email="other@example.com")
    token = _token()

    wrong = client.patch(
        "/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json=_profile(newPassword="newpass", currentPassword="nope"),
    )
    assert wrong.status_code == 400

    taken = client.patch(
        "/v1/users/me/profile",
        headers={"Authorization": f"Bearer {token}"},
        json=_profile(email="other@example.com"),
    )
    assert taken.status_code == 400


def test_update_profile_requires_token():
    res = client.patch("/v1/users/me/profile", json=_profile())
    assert res.status_code == 401
