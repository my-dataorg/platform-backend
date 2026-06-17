from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"

    slug: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    short_description: Mapped[str] = mapped_column(Text)
    icon_url: Mapped[str] = mapped_column(String(256), default="")
    category: Mapped[str] = mapped_column(String(64))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    launch_url: Mapped[str] = mapped_column(String(256))
    sort_order: Mapped[int] = mapped_column(default=0)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_slug: Mapped[str] = mapped_column(
        String(64), ForeignKey("products.slug"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(32), default="active")
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
