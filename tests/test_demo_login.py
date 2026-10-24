from sqlalchemy import select

from app.models.auth_user import AuthUser
from app.services.auth_users import (
    authenticate,
    hash_password,
    seed_demo_users,
    verify_password,
)


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
