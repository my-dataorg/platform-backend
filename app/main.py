from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_optional_user
from app.config import settings
from app.db.session import SessionLocal, engine, get_db
from app.models import Base, Product
from app.services.catalog import seed_products, subscribe_user, user_subscribed_slugs


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_products(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserProfile(BaseModel):
    id: str
    email: str
    name: str


class ProductOut(BaseModel):
    slug: str
    name: str
    shortDescription: str
    iconUrl: str
    category: str
    tags: list[str]
    featured: bool
    subscribed: bool
    launchUrl: str


class ProductList(BaseModel):
    items: list[ProductOut]
    nextCursor: str | None
    totalApprox: int


def _to_product(p: Product, subscribed: bool) -> ProductOut:
    return ProductOut(
        slug=p.slug,
        name=p.name,
        shortDescription=p.short_description,
        iconUrl=p.icon_url,
        category=p.category,
        tags=p.tags or [],
        featured=p.featured,
        subscribed=subscribed,
        launchUrl=p.launch_url,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/users/me", response_model=UserProfile)
def users_me(user: dict = Depends(get_current_user)):
    return UserProfile(**user)


@app.get("/v1/products", response_model=ProductList)
def list_products(
    q: str | None = None,
    category: str | None = None,
    featured: bool | None = None,
    cursor: str | None = None,
    limit: int = Query(default=24, le=48),
    db: Session = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    stmt = select(Product).order_by(Product.sort_order)
    if category:
        stmt = stmt.where(Product.category == category)
    if featured is not None:
        stmt = stmt.where(Product.featured == featured)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Product.name.ilike(like), Product.short_description.ilike(like))
        )

    all_products = list(db.scalars(stmt))
    start = int(cursor) if cursor else 0
    page = all_products[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(all_products) else None

    subs = user_subscribed_slugs(db, user["id"]) if user else set()
    items = [_to_product(p, p.slug in subs) for p in page]
    return ProductList(items=items, nextCursor=next_cursor, totalApprox=len(all_products))


@app.get("/v1/products/categories")
def list_categories(db: Session = Depends(get_db)):
    products = db.scalars(select(Product)).all()
    counts: dict[str, int] = {}
    for p in products:
        counts[p.category] = counts.get(p.category, 0) + 1
    return {
        "items": [
            {"slug": slug, "name": slug.title(), "count": count}
            for slug, count in sorted(counts.items())
        ]
    }


@app.get("/v1/users/me/subscriptions")
def my_subscriptions(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    slugs = user_subscribed_slugs(db, user["id"])
    return {"items": [{"productSlug": s, "status": "active"} for s in sorted(slugs)]}


@app.post("/v1/users/me/subscriptions")
def subscribe(
    productSlug: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        subscribe_user(db, user["id"], productSlug)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"productSlug": productSlug, "status": "active"}
