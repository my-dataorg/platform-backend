from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Product, UserSubscription
from app.seed import PRODUCTS


def seed_products(db: Session) -> None:
    existing = set(db.scalars(select(Product.slug)).all())
    added = False
    launch_overrides = {
        "education": settings.education_launch_url,
        "poker-world": settings.poker_world_launch_url,
        "business": settings.business_launch_url,
    }
    for i, p in enumerate(PRODUCTS):
        if p["slug"] in existing:
            product = db.get(Product, p["slug"])
            launch_url = launch_overrides.get(p["slug"])
            if product and launch_url and product.launch_url != launch_url:
                product.launch_url = launch_url
                added = True
            continue
        db.add(
            Product(
                slug=p["slug"],
                name=p["name"],
                short_description=p["shortDescription"],
                icon_url=p["iconUrl"],
                category=p["category"],
                tags=p["tags"],
                featured=p["featured"],
                launch_url=launch_overrides.get(p["slug"], p["launchUrl"]),
                status="enabled",
                default_path="/",
                embed_enabled=True,
                sort_order=i,
            )
        )
        added = True
    if added:
        db.commit()


def user_subscribed_slugs(db: Session, user_id: str) -> set[str]:
    rows = db.scalars(
        select(UserSubscription.product_slug).where(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active",
        )
    )
    return set(rows.all())


def subscribe_user(db: Session, user_id: str, product_slug: str) -> UserSubscription:
    product = db.get(Product, product_slug)
    if not product:
        raise ValueError("Product not found")
    existing = db.get(UserSubscription, {"user_id": user_id, "product_slug": product_slug})
    if existing:
        return existing
    sub = UserSubscription(user_id=user_id, product_slug=product_slug, status="active")
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub
