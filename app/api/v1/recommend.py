# app/api/v1/recommend.py

from sqlalchemy import text
from fastapi import APIRouter, Depends, Header
from sqlmodel import Session

from app.db.dependencies import get_db
from app.schemas.recommendation import RecommendRequest, RecommendResponse
from app.repositories.recommendations import RecommendationRepository
from app.services.recommendation_service import RecommendationService
from app.core.redis_client import get_redis
from app.core.redis_cache import RecommendationCache
from app.db.session import engine

from fastapi import BackgroundTasks

router = APIRouter(prefix="/api/v1", tags=["recommendation"])

# 1. Define this function OUTSIDE of the route
def log_decision_bg_task(log_payload: dict):
    """
    Background task that manages its own database session.
    """
    with Session(engine) as session:
        repo = RecommendationRepository(session)
        # We unpack the dictionary here
        repo.log_recommendation_decision(**log_payload)

@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    payload: RecommendRequest,
    background_tasks: BackgroundTasks,
    x_tenant_id: str = Header(...),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis),
):
    # Set the tenant ID for RLS before doing anything else
    db.execute(text("SET LOCAL app.current_tenant = :t_id"), {"t_id": x_tenant_id})
    
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

    # Extract the log data
    log_data = result.pop("_log_payload")
    
    # 2. Extract logging logic from service and run in background
    # This allows the API to return the response while DB is still writing
    background_tasks.add_task(log_decision_bg_task, log_data)

    #db.commit()
    cache.set(cache_key, result)
    return result