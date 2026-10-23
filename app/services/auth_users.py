"""Signup / login and token issuance."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import httpx
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.auth_user import AuthUser
from app.services.jwt_keys import KID, private_pem

ph = PasswordHasher()

GENDERS = frozenset(
    {
        "agender",
        "bigender",
        "female",
        "genderfluid",
        "genderqueer",
        "intersex",
        "male",
        "non_binary",
        "prefer_not_to_say",
        "other",
        "transgender",
        "two_spirit",
    }
)
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
    state: str | None = None,
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
        state=(state.strip() if state else None),
        preferred_language=preferred_language or "en",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _keycloak_profile(login: str, password: str) -> dict | None:
    """Users who registered in Keycloak can still sign in to platform."""
    realm = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
    try:
        token = httpx.post(
            f"{realm}/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "platform-frontend",
                "username": login,
                "password": password,
            },
            timeout=5.0,
        )
        if token.status_code != 200:
            return None
        access = token.json().get("access_token")
        if not access:
            return None
        info = httpx.get(
            f"{realm}/protocol/openid-connect/userinfo",
            headers={"Authorization": f"Bearer {access}"},
            timeout=5.0,
        )
        if info.status_code != 200:
            return None
        return info.json()
    except httpx.HTTPError:
        return None


def _user_from_keycloak(db: Session, login: str, password: str, profile: dict) -> AuthUser:
    username = normalize_username(str(profile.get("preferred_username") or login))
    email = normalize_email(str(profile.get("email") or f"{username}@users.local"))
    existing = db.scalar(
        select(AuthUser).where(or_(AuthUser.username == username, AuthUser.email == email))
    )
    if existing:
        existing.password_hash = hash_password(password)
        db.commit()
        db.refresh(existing)
        return existing
    return create_user(
        db,
        username=username,
        email=email,
        password=password,
        first_name=str(profile.get("given_name") or username),
        last_name=str(profile.get("family_name") or "User"),
        gender="prefer_not_to_say",
        date_of_birth=date(1990, 1, 1),
        contact_number="+10000000000",
        whatsapp_available=False,
    )


def authenticate(db: Session, login: str, password: str) -> AuthUser | None:
    login = login.strip().lower()
    user = db.scalar(
        select(AuthUser).where(or_(AuthUser.username == login, AuthUser.email == login))
    )
    if user and verify_password(user.password_hash, password):
        return user
    profile = _keycloak_profile(login, password)
    if not profile:
        return None
    return _user_from_keycloak(db, login, password, profile)


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
        "state": user.state,
        "preferredLanguage": user.preferred_language,
    }


def seed_demo_users(db: Session) -> None:
    """Ensure demo accounts exist for local/staging (see platform-backend README)."""
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
        {
            "username": "demo",
            "email": "demo@mydata.local",
            "password": "demo1234",
            "first_name": "Demo",
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


def search_users(db: Session, query: str, *, limit: int = 10) -> list[AuthUser]:
    q = query.strip()
    if len(q) < 2:
        return []
    like = f"%{q}%"
    stmt = (
        select(AuthUser)
        .where(
            or_(
                AuthUser.username.ilike(like),
                AuthUser.email.ilike(like),
                AuthUser.first_name.ilike(like),
                AuthUser.last_name.ilike(like),
            )
        )
        .order_by(AuthUser.username)
        .limit(limit)
    )
    return list(db.scalars(stmt))


def get_users_by_ids(db: Session, user_ids: list[str]) -> list[AuthUser]:
    ids = list(dict.fromkeys(uid for uid in user_ids if uid))
    if not ids:
        return []
    return list(db.scalars(select(AuthUser).where(AuthUser.id.in_(ids))))


def user_search_item(user: AuthUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "name": user.display_name,
        "firstName": user.first_name,
        "lastName": user.last_name,
    }


def user_brief_item(user: AuthUser) -> dict:
    return {
        **user_search_item(user),
        "dateOfBirth": user.date_of_birth,
        "gender": user.gender or "",
    }
