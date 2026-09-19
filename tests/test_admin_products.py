from datetime import date

import pytest
from sqlalchemy import select

from app.models import AuthUser, Product, ProductAudit
from app.schemas.admin_products import ProductCreate, ProductUpdate
from app.services.admin import bootstrap_superuser
from app.services.admin_products import (
    archive_admin_product,
    create_admin_product,
    update_admin_product,
)


def test_bootstrap_is_idempotent(db):
    first = bootstrap_superuser(
        db,
        username="operator",
        email="operator@example.com",
        password="secret",
    )
    second = bootstrap_superuser(
        db,
        username="operator",
        email="operator@example.com",
        password="different",
    )

    assert first.id == second.id
    assert db.scalar(select(AuthUser).where(AuthUser.is_superuser.is_(True))).id == first.id


def test_product_updates_are_audited(db):
    admin = AuthUser(
        username="operator",
        email="operator@example.com",
        password_hash="unused",
        first_name="Platform",
        last_name="Admin",
        gender="prefer_not_to_say",
        date_of_birth=date(1970, 1, 1),
        contact_number="bootstrap",
        is_superuser=True,
    )
    db.add(admin)
    db.commit()

    product = create_admin_product(
        db,
        admin.id,
        ProductCreate(
            slug="reports",
            name="Reports",
            shortDescription="Reports",
            category="business",
            launchUrl="http://localhost:3030",
        ),
    )
    update_admin_product(
        db,
        admin.id,
        product,
        ProductUpdate(defaultPath="/reports", status="disabled"),
    )

    audit = db.scalars(select(ProductAudit)).all()
    assert product.status == "disabled"
    assert audit[-1].changed_fields == {"defaultPath": "/reports", "status": "disabled"}


def test_product_validation_rejects_unapproved_launch_url(db):
    with pytest.raises(ValueError, match="not allowlisted"):
        create_admin_product(
            db,
            "operator",
            ProductCreate(
                slug="unsafe",
                name="Unsafe",
                shortDescription="Unsafe",
                category="business",
                launchUrl="https://example.com",
            ),
        )


def test_product_validation_requires_origin_only_launch_url(db):
    with pytest.raises(ValueError, match="HTTP"):
        create_admin_product(
            db,
            "operator",
            ProductCreate(
                slug="pathful",
                name="Pathful",
                shortDescription="Pathful",
                category="business",
                launchUrl="http://localhost:3030/app?mode=embed",
            ),
        )


def test_archive_disables_product(db):
    product = Product(
        slug="reports",
        name="Reports",
        short_description="Reports",
        category="business",
        launch_url="http://localhost:3030",
    )
    db.add(product)
    db.commit()

    archive_admin_product(db, "operator", product)

    assert product.status == "disabled"
