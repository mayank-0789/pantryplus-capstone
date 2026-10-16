from datetime import datetime, timezone, timedelta

from fastapi import Query, Depends, FastAPI, HTTPException, Response, status
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app import metrics, models, schemas
from app.config import settings
from app.db import get_db
from app.stock_service import append_stock_event, apply_stock_change

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
def browse_pantry(category: schemas.Category | None = None, low_stock: bool = False, expiring: bool = False, expired: bool = False, db: Session = Depends(get_db)):
    q = select(models.Item).order_by(models.Item.expires_on.is_(None), models.Item.expires_on, models.Item.name)
    if category:
        q = q.where(models.Item.category == category)
    if low_stock:
        q = q.where(models.Item.quantity <= models.Item.min_quantity)
    if expiring:
        q = q.where(models.Item.quantity > 0, models.Item.expires_on >= datetime.now(timezone.utc).date(),
                    models.Item.expires_on <= datetime.now(timezone.utc).date() + timedelta(days=SOON))
    if expired:
        q = q.where(models.Item.quantity > 0, models.Item.expires_on < datetime.now(timezone.utc).date())
    return db.scalars(q).all()


@app.get("/api/items/stats", response_model=schemas.Stats)
def summarize_pantry(db: Session = Depends(get_db)):
    today = datetime.now(timezone.utc).date()
    by_category = dict(db.execute(select(models.Item.category, func.count()).group_by(models.Item.category)).all())
    low = db.scalar(select(func.count()).where(models.Item.quantity <= models.Item.min_quantity)) or 0
    soon = db.scalar(select(func.count()).where(models.Item.quantity > 0, models.Item.expires_on >= today,
                                                models.Item.expires_on <= today + timedelta(days=SOON))) or 0
    expired = db.scalar(select(func.count()).where(models.Item.quantity > 0, models.Item.expires_on < today)) or 0
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
def create_pantry_item(payload: schemas.ItemIn, db: Session = Depends(get_db)):
    item = models.Item(**payload.model_dump())
    db.add(item)
    db.flush()
    append_stock_event(db, item, "opening", item.quantity)
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


@app.post("/api/items/{item_id}/consume", response_model=schemas.ItemOut)
def consume(item_id: int, payload: schemas.StockChange, db: Session = Depends(get_db)):
    return apply_stock_change(db, item_id, payload, "consume")


@app.post("/api/items/{item_id}/restock", response_model=schemas.ItemOut)
def restock(item_id: int, payload: schemas.StockChange, db: Session = Depends(get_db)):
    return apply_stock_change(db, item_id, payload, "restock")


@app.post("/api/items/{item_id}/waste", response_model=schemas.ItemOut)
def waste(item_id: int, payload: schemas.StockChange, db: Session = Depends(get_db)):
    return apply_stock_change(db, item_id, payload, "waste")


@app.get("/api/activity", response_model=list[schemas.MovementOut])
def list_stock_events(item_id: int | None = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    q = select(models.Movement).order_by(models.Movement.id.desc()).limit(limit)
    if item_id is not None:
        q = q.where(models.Movement.item_id == item_id)
    return db.scalars(q).all()


@app.delete("/api/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.get(models.Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="item not found")
    append_stock_event(db, item, "removed", -item.quantity)
    db.flush()
    db.execute(update(models.Movement).where(models.Movement.item_id == item_id).values(item_id=None))
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
