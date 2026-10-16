from datetime import date, timedelta
from decimal import Decimal

from fastapi import Query, Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app import metrics, models, schemas
from app.config import settings
from app.db import get_db

app = FastAPI(title="Pantry Plus API", version=settings.app_version)
metrics.install(app)

SOON = 7


@app.get("/")
def root():
    return {"service": "pantry-api", "version": settings.app_version, "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc.__class__.__name__}")
    return {"status": "ready"}


@app.get("/api/items", response_model=list[schemas.ItemOut])
def list_items(category: str | None = None, low_stock: bool = False, expiring: bool = False, db: Session = Depends(get_db)):
    q = select(models.Item).order_by(models.Item.expires_on.is_(None), models.Item.expires_on, models.Item.name)
    if category:
        q = q.where(models.Item.category == category)
    if low_stock:
        q = q.where(models.Item.quantity <= models.Item.min_quantity)
    if expiring:
        q = q.where(models.Item.expires_on.is_not(None), models.Item.expires_on <= date.today() + timedelta(days=SOON))
    return db.scalars(q).all()


@app.get("/api/items/stats", response_model=schemas.Stats)
def stats(db: Session = Depends(get_db)):
    today = date.today()
    by_category = dict(db.execute(select(models.Item.category, func.count()).group_by(models.Item.category)).all())
    low = db.scalar(select(func.count()).where(models.Item.quantity <= models.Item.min_quantity)) or 0
    soon = db.scalar(select(func.count()).where(models.Item.expires_on.is_not(None), models.Item.expires_on >= today,
                                                models.Item.expires_on <= today + timedelta(days=SOON))) or 0
    expired = db.scalar(select(func.count()).where(models.Item.expires_on.is_not(None), models.Item.expires_on < today)) or 0
    return schemas.Stats(
        total_items=sum(by_category.values()),
        by_category={c: by_category.get(c, 0) for c in models.CATEGORIES},
        low_stock=low,
        expiring_soon=soon,
        expired=expired,
    )


@app.get("/api/items/{item_id}", response_model=schemas.ItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    return item


@app.post("/api/items", response_model=schemas.ItemOut, status_code=status.HTTP_201_CREATED)
def add_item(payload: schemas.ItemIn, db: Session = Depends(get_db)):
    item = models.Item(**payload.model_dump())
    db.add(item)
    db.flush()
    record_movement(db, item, "opening", item.quantity)
    db.commit()
    db.refresh(item)
    metrics.ITEMS_ADDED.inc()
    return item


@app.put("/api/items/{item_id}", response_model=schemas.ItemOut)
def update_item(item_id: int, payload: schemas.ItemUpdate, db: Session = Depends(get_db)):
    item = db.get(models.Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def record_movement(db, item, kind, amount, note=""):
    db.add(models.Movement(item_id=item.id, item_name=item.name, unit=item.unit,
                           kind=kind, amount=amount, balance=0 if kind == "removed" else item.quantity, note=note))


def change_stock(db, item_id, payload, kind):
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
    record_movement(db, item, kind, delta, getattr(payload, "note", ""))
    db.commit()
    db.refresh(item)
    if kind == "consume":
        metrics.CONSUMED.labels(item.unit).inc(float(payload.amount))
    return item


@app.post("/api/items/{item_id}/consume", response_model=schemas.ItemOut)
def consume(item_id: int, payload: schemas.StockChange, db: Session = Depends(get_db)):
    return change_stock(db, item_id, payload, "consume")


@app.post("/api/items/{item_id}/restock", response_model=schemas.ItemOut)
def restock(item_id: int, payload: schemas.StockChange, db: Session = Depends(get_db)):
    return change_stock(db, item_id, payload, "restock")


@app.post("/api/items/{item_id}/waste", response_model=schemas.ItemOut)
def waste(item_id: int, payload: schemas.StockChange, db: Session = Depends(get_db)):
    return change_stock(db, item_id, payload, "waste")


@app.get("/api/activity", response_model=list[schemas.MovementOut])
def activity(item_id: int | None = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    q = select(models.Movement).order_by(models.Movement.id.desc()).limit(limit)
    if item_id is not None:
        q = q.where(models.Movement.item_id == item_id)
    return db.scalars(q).all()


@app.delete("/api/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    record_movement(db, item, "removed", -item.quantity)
    db.flush()
    db.execute(update(models.Movement).where(models.Movement.item_id == item_id).values(item_id=None))
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
