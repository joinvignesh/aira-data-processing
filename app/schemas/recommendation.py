# app/schemas/recommendation.py

from __future__ import annotations

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=200)
    surface: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=8, ge=1, le=50)
    exclude_product_ids: list[str] = Field(default_factory=list)


class RecommendItemResponse(BaseModel):
    product_id: str
    score: float
    reason: str


class RecommendResponse(BaseModel):
    items: list[RecommendItemResponse]
    model_version: str
    decision_id: str
    latency_ms: float