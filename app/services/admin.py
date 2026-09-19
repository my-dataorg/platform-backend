from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthUser
from app.services.auth_users import hash_password, normalize_email, normalize_username

BOOTSTRAP_LOCK_KEY = 728391


def bootstrap_superuser(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
) -> AuthUser:
    username = normalize_username(username)
    email = normalize_email(email)
    if not username or not email or not password:
        raise ValueError("Bootstrap username, email, and password are required")

    connection = db.connection()
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql("SELECT pg_advisory_xact_lock(%s)", (BOOTSTRAP_LOCK_KEY,))

    existing_admin = db.scalar(select(AuthUser).where(AuthUser.is_superuser.is_(True)))
    if existing_admin:
        return existing_admin

    existing_user = db.scalar(
        select(AuthUser).where((AuthUser.username == username) | (AuthUser.email == email))
    )
    if existing_user:
        raise ValueError("Bootstrap user already exists and is not a superuser")

    admin = AuthUser(
        username=username,
        email=email,
        password_hash=hash_password(password),
        first_name="Platform",
        last_name="Administrator",
        gender="prefer_not_to_say",
        date_of_birth=date(1970, 1, 1),
        contact_number="bootstrap",
        is_superuser=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin
