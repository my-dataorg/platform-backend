"""Allow the full signup profile values used by the form."""

from alembic import op
import sqlalchemy as sa


revision = "20260930_expand_signup_gender"
down_revision = "20260918_product_handoff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "auth_users",
        "gender",
        existing_type=sa.String(length=2),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.alter_column(
        "auth_users",
        "country",
        existing_type=sa.String(length=2),
        type_=sa.String(length=100),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "auth_users",
        "country",
        existing_type=sa.String(length=100),
        type_=sa.String(length=2),
        existing_nullable=True,
    )
    op.alter_column(
        "auth_users",
        "gender",
        existing_type=sa.String(length=32),
        type_=sa.String(length=2),
        existing_nullable=False,
    )
