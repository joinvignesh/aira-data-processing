# app/api/v1/recommend.py

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.db.dependencies import get_db
from app.repositories.recommendations import RecommendationRepository
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/v1", tags=["recommendations"])


class RecommendRequest(BaseModel):
    customer_id: str
    surface: str
    limit: int = Field(default=8, ge=1, le=50)
    exclude_product_ids: list[str] = Field(default_factory=list)


@router.post("/recommend")
def recommend(
    payload: RecommendRequest,
    x_tenant_id: str = Header(...),
    db: Session = Depends(get_db),
):
    repo = RecommendationRepository(db)
    service = RecommendationService(db, repo)
    result = service.recommend(
        tenant_id=x_tenant_id,
        customer_id=payload.customer_id,
        surface=payload.surface,
        limit=payload.limit,
        exclude_product_ids=payload.exclude_product_ids,
    )
    return {
        "items": [item.__dict__ for item in result.items],
        "model_version": result.model_version,
        "decision_id": result.decision_id,
        "latency_ms": result.latency_ms,
    }