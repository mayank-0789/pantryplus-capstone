from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Category = Literal["produce", "dairy", "grains", "protein", "spices", "frozen", "other"]
Unit = Literal["pcs", "g", "kg", "ml", "l", "pack"]
Quantity = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ItemIn(Input):
    name: str = Field(min_length=1, max_length=80)
    category: Category = "other"
    quantity: Quantity = Decimal("0")
    unit: Unit = "pcs"
    min_quantity: Quantity = Decimal("0")
    expires_on: date | None = None
    location: str = Field(default="", max_length=40)
    notes: str = Field(default="", max_length=2000)


class ItemUpdate(Input):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    category: Category | None = None
    quantity: Quantity | None = None
    unit: Unit | None = None
    min_quantity: Quantity | None = None
    expires_on: date | None = None
    location: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def reject_null_fields(self):
        for key in self.model_fields_set - {"expires_on"}:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null")
        return self


class Consume(Input):
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)


class ItemOut(ItemIn):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Stats(BaseModel):
    total_items: int
    by_category: dict[str, int]
    low_stock: int
    expiring_soon: int
    expired: int
