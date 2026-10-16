from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["produce", "dairy", "grains", "protein", "spices", "frozen", "other"]
Unit = Literal["pcs", "g", "kg", "ml", "l", "pack"]


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: Category = "other"
    quantity: Decimal = Field(default=Decimal("0"), ge=0)
    unit: Unit = "pcs"
    min_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    expires_on: date | None = None
    location: str = Field(default="", max_length=40)
    notes: str = ""


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    category: Category | None = None
    quantity: Decimal | None = Field(default=None, ge=0)
    unit: Unit | None = None
    min_quantity: Decimal | None = Field(default=None, ge=0)
    expires_on: date | None = None
    location: str | None = Field(default=None, max_length=40)
    notes: str | None = None


class Consume(BaseModel):
    amount: Decimal = Field(gt=0)


class ItemOut(ItemIn):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Stats(BaseModel):
    total_items: int
    by_category: dict[str, int]
    low_stock: int
    expiring_soon: int
    expired: int
