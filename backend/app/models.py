from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

CATEGORIES = ("produce", "dairy", "grains", "protein", "spices", "frozen", "other")
UNITS = ("pcs", "g", "kg", "ml", "l", "pack")


def now():
    return datetime.now(timezone.utc)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    category: Mapped[str] = mapped_column(String(20), default="other", index=True)
    quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    unit: Mapped[str] = mapped_column(String(8), default="pcs")
    min_quantity: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    location: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
