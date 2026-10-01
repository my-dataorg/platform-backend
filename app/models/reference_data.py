"""Platform-owned values used by public registration forms."""

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Country(Base):
    __tablename__ = "registration_countries"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class StateProvince(Base):
    __tablename__ = "registration_states"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    country_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("registration_countries.code"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class GenderOption(Base):
    __tablename__ = "registration_genders"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
