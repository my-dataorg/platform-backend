"""Add product administration and handoff storage."""

from alembic import op
import sqlalchemy as sa

revision = "20260918_product_handoff"
down_revision = None
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    existing_auth = _columns("auth_users")
    if "is_superuser" not in existing_auth:
        op.add_column(
            "auth_users",
            sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    existing_products = _columns("products")
    additions = (
        ("status", sa.String(16), "enabled"),
        ("default_path", sa.String(256), "/"),
        ("embed_enabled", sa.Boolean(), True),
    )
    for name, column_type, default in additions:
        if name not in existing_products:
            op.add_column(
                "products",
                sa.Column(name, column_type, nullable=False, server_default=sa.literal(default)),
            )

    op.create_index(
        "uq_auth_users_single_superuser",
        "auth_users",
        ["is_superuser"],
        unique=True,
        postgresql_where=sa.text("is_superuser IS TRUE"),
        sqlite_where=sa.text("is_superuser = 1"),
    )
    op.create_table(
        "product_audits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_user_id", sa.String(36), nullable=False),
        sa.Column("product_slug", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_product_audits_actor_user_id", "product_audits", ["actor_user_id"])
    op.create_index("ix_product_audits_product_slug", "product_audits", ["product_slug"])
    op.create_table(
        "product_handoffs",
        sa.Column("code_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("product_slug", sa.String(64), nullable=False),
        sa.Column("target_origin", sa.String(256), nullable=False),
        sa.Column("return_path", sa.String(512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_product_handoffs_user_id", "product_handoffs", ["user_id"])
    op.create_index("ix_product_handoffs_product_slug", "product_handoffs", ["product_slug"])
    op.create_index("ix_product_handoffs_expires_at", "product_handoffs", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_product_handoffs_expires_at", table_name="product_handoffs")
    op.drop_index("ix_product_handoffs_product_slug", table_name="product_handoffs")
    op.drop_index("ix_product_handoffs_user_id", table_name="product_handoffs")
    op.drop_table("product_handoffs")
    op.drop_index("ix_product_audits_product_slug", table_name="product_audits")
    op.drop_index("ix_product_audits_actor_user_id", table_name="product_audits")
    op.drop_table("product_audits")
    op.drop_index("uq_auth_users_single_superuser", table_name="auth_users")
    op.drop_column("products", "embed_enabled")
    op.drop_column("products", "default_path")
    op.drop_column("products", "status")
    op.drop_column("auth_users", "is_superuser")
