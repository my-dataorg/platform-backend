"""Add database-backed registration options."""

from alembic import op
import sqlalchemy as sa


revision = "20260930_registration_options"
down_revision = "20260930_expand_signup_gender"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registration_countries",
        sa.Column("code", sa.String(2), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "registration_states",
        sa.Column("code", sa.String(16), primary_key=True),
        sa.Column(
            "country_code",
            sa.String(2),
            sa.ForeignKey("registration_countries.code"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_registration_states_country_code",
        "registration_states",
        ["country_code"],
    )
    op.create_table(
        "registration_genders",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("auth_users", sa.Column("state", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("auth_users", "state")
    op.drop_table("registration_genders")
    op.drop_index("ix_registration_states_country_code", table_name="registration_states")
    op.drop_table("registration_states")
    op.drop_table("registration_countries")
