from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_optional_user
from app.config import settings
from app.db.session import SessionLocal, engine, get_db
from app.internal_auth import require_internal_token
from app.models import Base, Product
from app.services.auth_users import (
    authenticate,
    create_user,
    get_user,
    get_users_by_ids,
    search_users,
    seed_demo_users,
    tokens_for,
    user_public,
    user_search_item,
)
from app.services.catalog import seed_products, subscribe_user, user_subscribed_slugs
from app.consumers.poker_world import start_poker_world_consumer, stop_poker_world_consumer
from app.events import close_nats
from app.services.jwt_keys import ensure_keys, jwks
from app.schemas.handoff import HandoffCreate, HandoffExchange, HandoffCreated
from app.services.handoff import create_handoff, exchange_handoff
from app.services.notifications import create_notification, list_notifications, mark_read
from app.routers.admin_products import router as admin_products_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_bootstrap_config()
    ensure_keys()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_products(db)
        seed_demo_users(db)
    finally:
        db.close()
    await start_poker_world_consumer()
    yield
    await stop_poker_world_consumer()
    await close_nats()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.include_router(admin_products_router)


@app.exception_handler(HTTPException)
async def http_problem(_: Request, error: HTTPException):
    return JSONResponse(
        status_code=error.status_code,
        media_type="application/problem+json",
        content={
            "type": f"https://mydata.platform/errors/http-{error.status_code}",
            "title": "Request failed",
            "status": error.status_code,
            "detail": error.detail,
        },
        headers=error.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_problem(_: Request, error: RequestValidationError):
    return JSONResponse(
        status_code=400,
        media_type="application/problem+json",
        content={
            "type": "https://mydata.platform/errors/validation",
            "title": "Validation Error",
            "status": 400,
            "detail": "Request validation failed",
            "errors": jsonable_encoder(error.errors()),
        },
    )


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


class UserSearchItem(BaseModel):
    id: str
    username: str
    email: str
    name: str
    firstName: str
    lastName: str


class UserSearchList(BaseModel):
    items: list[UserSearchItem]


class SignupIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    email: str
    password: str = Field(min_length=4, max_length=128)
    firstName: str = Field(min_length=1, max_length=100)
    lastName: str = Field(min_length=1, max_length=100)
    gender: str
    dateOfBirth: date
    contactNumber: str = Field(min_length=5, max_length=40)
    whatsappAvailable: bool = False
    addressLine1: str | None = None
    city: str | None = None
    country: str | None = None
    preferredLanguage: str = "en"


class LoginIn(BaseModel):
    username: str = Field(min_length=1, description="Username or email")
    password: str = Field(min_length=1)


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
    status: str
    defaultPath: str
    embedEnabled: bool


class ProductList(BaseModel):
    items: list[ProductOut]
    nextCursor: str | None
    totalApprox: int


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    body: str
    link: str
    read: bool
    createdAt: str


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unreadCount: int


class NotificationCreate(BaseModel):
    userId: str
    type: str
    title: str
    body: str = ""
    link: str = ""


class NotificationReadUpdate(BaseModel):
    read: bool = True


class InternalSubscriptionCreate(BaseModel):
    productSlug: str


@app.post("/v1/products/handoff", response_model=HandoffCreated)
def product_handoff(
    body: HandoffCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    try:
        code, expires_in = create_handoff(db, user["id"], body)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return HandoffCreated(code=code, expiresIn=expires_in)


@app.post("/v1/products/handoff/exchange")
def exchange_product_handoff(
    body: HandoffExchange,
    db: Session = Depends(get_db),
):
    try:
        return exchange_handoff(db, body.code, body.targetOrigin, body.returnPath)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


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
        status=p.status,
        defaultPath=p.default_path,
        embedEnabled=p.embed_enabled,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/auth/jwks")
def auth_jwks():
    return jwks()


@app.post("/v1/auth/signup")
def auth_signup(body: SignupIn, db: Session = Depends(get_db)):
    try:
        user = create_user(
            db,
            username=body.username,
            email=body.email,
            password=body.password,
            first_name=body.firstName,
            last_name=body.lastName,
            gender=body.gender,
            date_of_birth=body.dateOfBirth,
            contact_number=body.contactNumber,
            whatsapp_available=body.whatsappAvailable,
            address_line1=body.addressLine1,
            city=body.city,
            country=body.country,
            preferred_language=body.preferredLanguage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return tokens_for(user)


@app.post("/v1/auth/login")
def auth_login(body: LoginIn, db: Session = Depends(get_db)):
    user = authenticate(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return tokens_for(user)


@app.get("/v1/users/me", response_model=UserProfile)
def users_me(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_user(db, user["id"]) if user.get("id") else None
    if row:
        return UserProfile(id=row.id, email=row.email, name=row.display_name)
    return UserProfile(**user)


@app.get("/v1/users/me/profile")
def users_me_profile(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_user(db, user["id"])
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return user_public(row)


@app.get("/v1/users/search", response_model=UserSearchList)
def users_search(
    q: str = Query(default="", min_length=0),
    limit: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    rows = search_users(db, q, limit=limit)
    return UserSearchList(items=[UserSearchItem(**user_search_item(u)) for u in rows])


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
    stmt = select(Product).where(Product.status == "enabled").order_by(Product.sort_order)
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
    products = db.scalars(select(Product).where(Product.status == "enabled")).all()
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


@app.get("/v1/users/me/notifications", response_model=NotificationList)
def my_notifications(
    unreadOnly: bool = False,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    items, unread = list_notifications(db, user["id"], unread_only=unreadOnly)
    return NotificationList(
        items=[
            NotificationOut(
                id=n.id,
                type=n.type,
                title=n.title,
                body=n.body,
                link=n.link,
                read=n.read,
                createdAt=n.created_at.isoformat(),
            )
            for n in items
        ],
        unreadCount=unread,
    )


@app.patch("/v1/users/me/notifications/{notification_id}", response_model=NotificationOut)
def update_notification(
    notification_id: str,
    body: NotificationReadUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not body.read:
        raise HTTPException(status_code=400, detail="Only marking read is supported")
    row = mark_read(db, user["id"], notification_id)
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationOut(
        id=row.id,
        type=row.type,
        title=row.title,
        body=row.body,
        link=row.link,
        read=row.read,
        createdAt=row.created_at.isoformat(),
    )


@app.post("/internal/notifications", response_model=NotificationOut, status_code=201)
def internal_create_notification(
    body: NotificationCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_token),
):
    row = create_notification(
        db,
        user_id=body.userId,
        type=body.type,
        title=body.title,
        body=body.body,
        link=body.link,
    )
    return NotificationOut(
        id=row.id,
        type=row.type,
        title=row.title,
        body=row.body,
        link=row.link,
        read=row.read,
        createdAt=row.created_at.isoformat(),
    )


@app.get("/internal/users/search", response_model=UserSearchList)
def internal_users_search(
    q: str = Query(default="", min_length=0),
    limit: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_token),
):
    rows = search_users(db, q, limit=limit)
    return UserSearchList(items=[UserSearchItem(**user_search_item(u)) for u in rows])


@app.get("/internal/users/briefs", response_model=UserSearchList)
def internal_users_briefs(
    ids: str = Query(default=""),
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_token),
):
    user_ids = [part.strip() for part in ids.split(",") if part.strip()]
    rows = get_users_by_ids(db, user_ids)
    return UserSearchList(items=[UserSearchItem(**user_search_item(u)) for u in rows])


@app.get("/internal/users/{user_id}/subscriptions")
def internal_list_user_subscriptions(
    user_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_token),
):
    slugs = user_subscribed_slugs(db, user_id)
    return {"items": [{"productSlug": s, "status": "active"} for s in sorted(slugs)]}


@app.post("/internal/users/{user_id}/subscriptions")
def internal_subscribe_user(
    user_id: str,
    body: InternalSubscriptionCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_token),
):
    try:
        sub = subscribe_user(db, user_id, body.productSlug)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"productSlug": sub.product_slug, "status": sub.status}
