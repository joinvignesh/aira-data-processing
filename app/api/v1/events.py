from fastapi import APIRouter, Header, HTTPException
from app.models.schemas import EventBatchRequest
from app.services.ingestion import bulk_ingest_events
import uuid

router = APIRouter()

@router.post("/events/batch")
async def ingest_events(
    batch: EventBatchRequest, 
    x_tenant_id: str = Header(...)
):
    try:
        tenant_uuid = uuid.UUID(x_tenant_id)
        count, duration = bulk_ingest_events(tenant_uuid, batch.events)
        
        return {
            "status": "accepted",
            "count": count,
            "processing_time_ms": round(duration, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))