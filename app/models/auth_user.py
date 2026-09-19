"""Platform-owned auth users (ADR 0010). Lives in platform DB; products never store passwords."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Index, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class AuthUser(Base):
    __tablename__ = "auth_users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_auth_users_username"),
        UniqueConstraint("email", name="uq_auth_users_email"),
        Index(
            "uq_auth_users_single_superuser",
            "is_superuser",
            unique=True,
            sqlite_where=text("is_superuser = 1"),
            postgresql_where=text("is_superuser IS TRUE"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), index=True)
    email: Mapped[str] = mapped_column(String(200), index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    gender: Mapped[str] = mapped_column(String(32))
    date_of_birth: Mapped[date] = mapped_column(Date)
    contact_number: Mapped[str] = mapped_column(String(40))
    whatsapp_available: Mapped[bool] = mapped_column(Boolean, default=False)
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(16), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.username
