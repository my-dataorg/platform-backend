from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models import Base, Product
from app.services.catalog import seed_products

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

db = TestingSession()
seed_products(db)
db.close()


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_products_list():
    res = client.get("/v1/products?limit=5")
    data = res.json()
    assert len(data["items"]) == 5
    assert data["totalApprox"] == 12


def test_poker_world_product():
    res = client.get("/v1/products?q=poker")
    items = res.json()["items"]
    poker = next(p for p in items if p["slug"] == "poker-world")
    assert poker["name"] == "Poker World"
    assert poker["launchUrl"] == "http://localhost:3110"
    assert poker["category"] == "lifestyle"


def test_business_product():
    res = client.get("/v1/products?q=ledger")
    items = res.json()["items"]
    biz = next(p for p in items if p["slug"] == "business")
    assert biz["name"] == "Business"
    assert biz["launchUrl"] == "http://localhost:3120"
    assert biz["category"] == "productivity"
    assert "ledger" in biz["tags"]


def test_seed_products_adds_missing_catalog_entries():
    partial_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    PartialSession = sessionmaker(bind=partial_engine)
    Base.metadata.create_all(bind=partial_engine)

    db = PartialSession()
    db.add(
        Product(
            slug="education",
            name="Education",
            short_description="Institutes",
            icon_url="/icons/education.svg",
            category="learning",
            tags=["schools"],
            featured=True,
            launch_url="http://localhost:3010",
            sort_order=0,
        )
    )
    db.commit()

    seed_products(db)
    slugs = set(db.scalars(select(Product.slug)).all())
    db.close()

    assert "poker-world" in slugs
    assert "business" in slugs
    assert len(slugs) == 12
