from urllib.parse import unquote, urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Product, ProductAudit
from app.schemas.admin_products import ProductCreate, ProductUpdate
from app.services.handoff import _origin, _return_path

VALID_STATUSES = {"enabled", "disabled"}


def _validate_launch(launch_url: str, default_path: str, status: str) -> None:
    allowed = {
        _origin(origin.strip())
        for origin in settings.product_allowed_origins.split(",")
        if _origin(origin.strip())
    }
    origin = _origin(launch_url)
    if not origin:
        raise ValueError("launchUrl must be an HTTP(S) URL")
    if origin not in allowed:
        raise ValueError("launchUrl origin is not allowlisted")
    if status not in VALID_STATUSES:
        raise ValueError("status must be enabled or disabled")
    decoded_path = unquote(default_path)
    path = urlsplit(decoded_path)
    if not _return_path(default_path):
        if any(part == ".." for part in path.path.split("/")):
            raise ValueError("defaultPath cannot traverse parent directories")
        raise ValueError("defaultPath must be a local path")


def _audit(db: Session, actor_id: str, product_slug: str, action: str, fields: dict) -> None:
    db.add(
        ProductAudit(
            actor_user_id=actor_id,
            product_slug=product_slug,
            action=action,
            changed_fields=fields,
        )
    )


def list_admin_products(db: Session) -> list[Product]:
    return list(db.scalars(select(Product).order_by(Product.sort_order, Product.slug)))


def get_admin_product(db: Session, slug: str) -> Product | None:
    return db.get(Product, slug)


def create_admin_product(db: Session, actor_id: str, body: ProductCreate) -> Product:
    if db.get(Product, body.slug):
        raise ValueError("Product slug already exists")
    _validate_launch(body.launchUrl, body.defaultPath, body.status)
    product = Product(
        slug=body.slug,
        name=body.name,
        short_description=body.shortDescription,
        icon_url=body.iconUrl,
        category=body.category,
        tags=body.tags,
        featured=body.featured,
        launch_url=body.launchUrl,
        status=body.status,
        default_path=body.defaultPath,
        embed_enabled=body.embedEnabled,
        sort_order=body.sortOrder,
    )
    db.add(product)
    _audit(db, actor_id, product.slug, "create", body.model_dump())
    db.commit()
    db.refresh(product)
    return product


def update_admin_product(
    db: Session, actor_id: str, product: Product, body: ProductUpdate
) -> Product:
    values = body.model_dump(exclude_unset=True)
    current = {
        "launchUrl": values.get("launchUrl", product.launch_url),
        "defaultPath": values.get("defaultPath", product.default_path),
        "status": values.get("status", product.status),
    }
    _validate_launch(current["launchUrl"], current["defaultPath"], current["status"])
    field_map = {
        "shortDescription": "short_description",
        "iconUrl": "icon_url",
        "launchUrl": "launch_url",
        "defaultPath": "default_path",
        "embedEnabled": "embed_enabled",
        "sortOrder": "sort_order",
    }
    for key, value in values.items():
        setattr(product, field_map.get(key, key), value)
    _audit(db, actor_id, product.slug, "update", values)
    db.commit()
    db.refresh(product)
    return product


def set_product_status(db: Session, actor_id: str, product: Product, status: str) -> Product:
    _validate_launch(product.launch_url, product.default_path, status)
    product.status = status
    _audit(db, actor_id, product.slug, status, {"status": status})
    db.commit()
    db.refresh(product)
    return product


def archive_admin_product(db: Session, actor_id: str, product: Product) -> Product:
    return set_product_status(db, actor_id, product, "disabled")
