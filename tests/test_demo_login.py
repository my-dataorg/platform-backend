from app.services.auth_users import authenticate, seed_demo_users, verify_password


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
