# app/api/v1/pipelines.py

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import Session

from app.db.dependencies import get_db
from app.services.feature_pipeline import CustomerFeaturePipelineService

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


@router.post("/customer-features/run")
def run_customer_feature_pipeline(
    x_tenant_id: str = Header(...),
    db: Session = Depends(get_db),
):
    service = CustomerFeaturePipelineService(db)
    result = service.run_for_tenant(x_tenant_id)
    return {
        "tenant_id": result.tenant_id,
        "checkpoint_before": result.checkpoint_before,
        "checkpoint_after": result.checkpoint_after,
        "affected_customers": result.affected_customers,
        "upserted_rows": result.upserted_rows,
        "processed_events": result.processed_events,
    }