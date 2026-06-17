from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Product, UserSubscription
from app.seed import PRODUCTS


def seed_products(db: Session) -> None:
    if db.scalar(select(Product).limit(1)):
        return
    for i, p in enumerate(PRODUCTS):
        db.add(
            Product(
                slug=p["slug"],
                name=p["name"],
                short_description=p["shortDescription"],
                icon_url=p["iconUrl"],
                category=p["category"],
                tags=p["tags"],
                featured=p["featured"],
                launch_url=p["launchUrl"],
                sort_order=i,
            )
        )
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
