from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from urllib.parse import unquote, urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuthUser, Product, ProductHandoff
from app.schemas.handoff import HandoffCreate
from app.services.auth_users import tokens_for
from app.services.catalog import user_subscribed_slugs


def _origin(value: str) -> str | None:
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _return_path(value: str) -> bool:
    decoded = value
    for _ in range(4):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    else:
        return False
    parsed = urlsplit(decoded)
    return (
        decoded.startswith("/")
        and not decoded.startswith("//")
        and not parsed.scheme
        and not parsed.netloc
        and not any(ord(char) < 32 or ord(char) == 127 for char in decoded)
        and "\\" not in decoded
        and not any(part == ".." for part in parsed.path.split("/"))
    )


def _validate_target(product: Product, target_origin: str, return_path: str) -> None:
    target = _origin(target_origin)
    launch_origin = _origin(product.launch_url)
    allowed = {
        _origin(origin.strip())
        for origin in settings.product_allowed_origins.split(",")
        if _origin(origin.strip())
    }
    if (
        product.status != "enabled"
        or not product.embed_enabled
        or not target
        or target not in allowed
        or target != launch_origin
        or not _return_path(return_path)
    ):
        raise ValueError("Invalid product handoff target")


def create_handoff(db: Session, user_id: str, body: HandoffCreate) -> tuple[str, int]:
    product = db.get(Product, body.productSlug)
    if not product or body.productSlug not in user_subscribed_slugs(db, user_id):
        raise ValueError("Product handoff is not available")
    _validate_target(product, body.targetOrigin, body.returnPath)

    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.handoff_ttl_seconds)
    db.add(
        ProductHandoff(
            code_hash=sha256(code.encode()).hexdigest(),
            user_id=user_id,
            product_slug=product.slug,
            target_origin=_origin(body.targetOrigin),
            return_path=body.returnPath,
            expires_at=expires_at,
        )
    )
    db.commit()
    return code, settings.handoff_ttl_seconds


def exchange_handoff(
    db: Session, code: str, target_origin: str, return_path: str
) -> dict:
    handoff = db.scalar(
        select(ProductHandoff)
        .where(ProductHandoff.code_hash == sha256(code.encode()).hexdigest())
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    expires_at = handoff.expires_at if handoff else now
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        not handoff
        or handoff.used_at is not None
        or expires_at <= now
        or handoff.target_origin != _origin(target_origin)
        or handoff.return_path != return_path
    ):
        raise ValueError("Invalid or expired handoff code")

    user = db.get(AuthUser, handoff.user_id)
    if not user:
        raise ValueError("Invalid or expired handoff code")
    handoff.used_at = now
    db.commit()
    return tokens_for(user)
