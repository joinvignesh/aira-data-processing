from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
from datetime import datetime
from uuid import UUID

class EventCreate(BaseModel):
    customer_id: str
    event_type: str
    product_id: Optional[UUID] = None
    properties: Dict = Field(default_factory=dict)
    timestamp: datetime

class EventBatchRequest(BaseModel):
    events: List[EventCreate]

    @field_validator("events")
    @classmethod
    def validate_batch_size(cls, v):
        if len(v) > 1000:
            raise ValueError("Batch size exceeds 1,000 limit")
        return v