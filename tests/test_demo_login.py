from sqlalchemy import select

from app.models.auth_user import AuthUser
from app.services.auth_users import (
    authenticate,
    ensure_bootstrap_admin_from_settings,
    hash_password,
    seed_demo_users,
    verify_password,
)
from app.config import settings


def test_demo_user_login_after_seed(db):
    seed_demo_users(db)
    user = authenticate(db, "demo@mydata.local", "demo1234")
    assert user is not None
    assert user.email == "demo@mydata.local"


def test_demo_password_resync(db):
    seed_demo_users(db)
    user = authenticate(db, "demo", "demo1234")
    assert user is not None
    seed_demo_users(db)
    assert authenticate(db, "demo@mydata.local", "demo1234") is not None
    assert verify_password(user.password_hash, "demo1234")


def test_admin_login_after_stale_hash(db):
    seed_demo_users(db)
    user = db.scalar(select(AuthUser).where(AuthUser.username == "admin"))
    assert user is not None
    user.password_hash = hash_password("wrong-password")
    db.commit()
    assert authenticate(db, "admin", "admin") is not None


def test_demo_admin_wins_after_bootstrap(db, monkeypatch):
    monkeypatch.setattr(settings, "bootstrap_admin_username", "owner")
    monkeypatch.setattr(settings, "bootstrap_admin_email", "owner@example.com")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "owner-secret")
    ensure_bootstrap_admin_from_settings(db)
    seed_demo_users(db)
    assert authenticate(db, "admin", "admin") is not None
    assert authenticate(db, "owner", "owner-secret") is not None
