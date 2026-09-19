from datetime import date

import pytest

from app.models import AuthUser, Product, UserSubscription
from app.schemas.handoff import HandoffCreate
from app.services.auth_users import hash_password
from app.services.handoff import create_handoff, exchange_handoff


def setup_handoff(db):
    user = AuthUser(
        username="user",
        email="user@example.com",
        password_hash=hash_password("secret"),
        first_name="Test",
        last_name="User",
        gender="prefer_not_to_say",
        date_of_birth=date(1990, 1, 1),
        contact_number="555",
    )
    product = Product(
        slug="reports",
        name="Reports",
        short_description="Reports",
        category="business",
        launch_url="http://localhost:3030",
    )
    db.add_all([user, product])
    db.commit()
    db.add(UserSubscription(user_id=user.id, product_slug=product.slug, status="active"))
    db.commit()
    return user


def test_handoff_exchange_is_single_use(db):
    user = setup_handoff(db)
    request = HandoffCreate(
        productSlug="reports",
        targetOrigin="http://localhost:3030",
        returnPath="/reports",
    )

    code, _ = create_handoff(db, user.id, request)
    token = exchange_handoff(db, code, request.targetOrigin, request.returnPath)

    assert token["tokenType"] == "Bearer"
    with pytest.raises(ValueError, match="Invalid or expired"):
        exchange_handoff(db, code, request.targetOrigin, request.returnPath)


def test_handoff_rejects_wrong_target(db):
    user = setup_handoff(db)
    request = HandoffCreate(
        productSlug="reports",
        targetOrigin="http://localhost:3030",
        returnPath="/reports",
    )

    with pytest.raises(ValueError, match="Invalid product handoff target"):
        create_handoff(
            db,
            user.id,
            request.model_copy(update={"targetOrigin": "https://example.com"}),
        )


def test_handoff_rejects_encoded_parent_traversal(db):
    user = setup_handoff(db)
    request = HandoffCreate(
        productSlug="reports",
        targetOrigin="http://localhost:3030",
        returnPath="/reports/%2e%2e/admin",
    )

    with pytest.raises(ValueError, match="Invalid product handoff target"):
        create_handoff(db, user.id, request)


def test_handoff_rejects_double_encoded_parent_traversal(db):
    user = setup_handoff(db)
    request = HandoffCreate(
        productSlug="reports",
        targetOrigin="http://localhost:3030",
        returnPath="/reports/%252e%252e/admin",
    )

    with pytest.raises(ValueError, match="Invalid product handoff target"):
        create_handoff(db, user.id, request)
