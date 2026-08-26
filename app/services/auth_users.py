"""Signup / login and token issuance."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.auth_user import AuthUser
from app.services.jwt_keys import KID, private_pem

ph = PasswordHasher()

GENDERS = frozenset({"female", "male", "non_binary", "prefer_not_to_say", "other"})
ACCESS_TTL_MIN = 60 * 12  # 12h for local MVP comfort
AUDIENCE = ["platform", "education", "social", "poker-world", "business"]


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str) -> str:
    return username.strip().lower()


def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    gender: str,
    date_of_birth: date,
    contact_number: str,
    whatsapp_available: bool,
    address_line1: str | None = None,
    city: str | None = None,
    country: str | None = None,
    preferred_language: str = "en",
) -> AuthUser:
    username = normalize_username(username)
    email = normalize_email(email)
    if not username or not email or not password:
        raise ValueError("Username, email, and password are required")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters")
    if gender not in GENDERS:
        raise ValueError("Invalid gender")
    if db.scalar(select(AuthUser).where(AuthUser.username == username)):
        raise ValueError("Username already taken")
    if db.scalar(select(AuthUser).where(AuthUser.email == email)):
        raise ValueError("Email already registered")

    user = AuthUser(
        username=username,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        gender=gender,
        date_of_birth=date_of_birth,
        contact_number=contact_number.strip(),
        whatsapp_available=whatsapp_available,
        address_line1=(address_line1 or None),
        city=(city or None),
        country=(country.upper() if country else None),
        preferred_language=preferred_language or "en",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, login: str, password: str) -> AuthUser | None:
    login = login.strip().lower()
    user = db.scalar(
        select(AuthUser).where(or_(AuthUser.username == login, AuthUser.email == login))
    )
    if not user or not verify_password(user.password_hash, password):
        return None
    return user


def issue_access_token(user: AuthUser) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "name": user.display_name,
        "preferred_username": user.username,
        "iss": settings.issuer,
        "aud": AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TTL_MIN)).timestamp()),
    }
    return jwt.encode(payload, private_pem(), algorithm="RS256", headers={"kid": KID})


def tokens_for(user: AuthUser) -> dict:
    return {
        "accessToken": issue_access_token(user),
        "tokenType": "Bearer",
        "expiresIn": ACCESS_TTL_MIN * 60,
        "user": user_public(user),
    }


def user_public(user: AuthUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "name": user.display_name,
        "gender": user.gender,
        "dateOfBirth": user.date_of_birth.isoformat(),
        "contactNumber": user.contact_number,
        "whatsappAvailable": user.whatsapp_available,
        "addressLine1": user.address_line1,
        "city": user.city,
        "country": user.country,
        "preferredLanguage": user.preferred_language,
    }


def seed_demo_users(db: Session) -> None:
    """Ensure local demo accounts exist (admin / admin)."""
    demos = [
        {
            "username": "admin",
            "email": "admin@mydata.local",
            "password": "admin",
            "first_name": "Admin",
            "last_name": "User",
            "gender": "prefer_not_to_say",
            "date_of_birth": date(1990, 1, 1),
            "contact_number": "+10000000000",
            "whatsapp_available": False,
        },
    ]
    for demo in demos:
        exists = db.scalar(
            select(AuthUser).where(
                or_(AuthUser.username == demo["username"], AuthUser.email == demo["email"])
            )
        )
        if exists:
            continue
        create_user(db, **demo)


def get_user(db: Session, user_id: str) -> AuthUser | None:
    return db.get(AuthUser, user_id)


def users_brief(db: Session, user_ids: list[str]) -> list[dict]:
    ids = list(dict.fromkeys(uid for uid in user_ids if uid))[:100]
    if not ids:
        return []
    users = db.scalars(select(AuthUser).where(AuthUser.id.in_(ids))).all()
    return [
        {
            "userId": user.id,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "displayName": user.display_name,
            "email": user.email,
            "username": user.username,
        }
        for user in users
    ]
