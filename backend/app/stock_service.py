"""Transactional inventory operations shared by the HTTP routes."""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import update

from app import metrics, models

def append_stock_event(db, item, kind, amount, note=""):
    db.add(models.Movement(item_id=item.id, item_name=item.name, unit=item.unit,
                           kind=kind, amount=amount, balance=0 if kind == "removed" else item.quantity, note=note))


def apply_stock_change(db, item_id, payload, kind):
    delta = payload.amount if kind == "restock" else -payload.amount
    # One conditional UPDATE locks and changes the row atomically on PostgreSQL.
    # The ledger insertion shares the same transaction; either both persist or neither does.
    item = db.scalars(update(models.Item).where(
        models.Item.id == item_id,
        models.Item.quantity + delta >= 0,
        models.Item.quantity + delta <= Decimal("99999999.99"),
    ).values(quantity=models.Item.quantity + delta).returning(models.Item)).first()
    if item is None:
        db.rollback()
        if db.get(models.Item, item_id) is None:
            raise HTTPException(status_code=404, detail="item not found")
        raise HTTPException(status_code=409, detail="Stock change exceeds available stock or capacity")
    append_stock_event(db, item, kind, delta, getattr(payload, "note", ""))
    db.commit()
    db.refresh(item)
    if kind == "consume":
        metrics.CONSUMED.labels(item.unit).inc(float(payload.amount))
    return item


