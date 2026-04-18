# app/api/v1/cooccurrence.py

from fastapi import APIRouter, Depends, Header, Query
from sqlmodel import Session

from app.db.dependencies import get_db
from app.repositories.cooccurrence import CooccurrenceRepository
from app.services.cooccurrence_service import CooccurrenceService

router = APIRouter(prefix="/api/v1/cooccurrence", tags=["cooccurrence"])


@router.get("/{product_id}")
def get_related_products(
    product_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    x_tenant_id: str = Header(...),
    db: Session = Depends(get_db),
):
    repo = CooccurrenceRepository(db)
    service = CooccurrenceService(repo)

    items = service.get_related_products(
        tenant_id=x_tenant_id,
        product_id=product_id,
        limit=limit,
    )

    return {
        "product_id": product_id,
        "items": items,
    }