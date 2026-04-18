# app/api/v1/recommend.py

from fastapi import APIRouter, Depends, Header
from sqlmodel import Session

from app.db.dependencies import get_db
from app.schemas.recommendation import RecommendRequest, RecommendResponse
from app.repositories.recommendations import RecommendationRepository
from app.services.recommendation_service import RecommendationService
from app.core.redis_client import get_redis
from app.core.redis_cache import RecommendationCache

router = APIRouter(prefix="/api/v1", tags=["recommendation"])


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    payload: RecommendRequest,
    x_tenant_id: str = Header(...),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
):
    cache = RecommendationCache(redis_client, ttl_seconds=120)
    cache_key = cache.build_key(
        tenant_id=x_tenant_id,
        customer_id=payload.customer_id,
        surface=payload.surface,
        limit=payload.limit,
        exclude_product_ids=payload.exclude_product_ids,
    )

    cached = cache.get(cache_key)
    if cached:
        return cached

    repo = RecommendationRepository(db)
    service = RecommendationService(repo)

    result = service.recommend(
        tenant_id=x_tenant_id,
        customer_id=payload.customer_id,
        surface=payload.surface,
        limit=payload.limit,
        exclude_product_ids=payload.exclude_product_ids,
    )

    db.commit()
    cache.set(cache_key, result)
    return result