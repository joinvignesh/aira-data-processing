# app/models/recommendation_decision.py

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class RecommendationDecision(SQLModel, table=True):
    __tablename__ = "recommendation_decisions"
    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_recommendation_decisions_decision_id"),
        Index(
            "ix_recommendation_decisions_tenant_customer_created_at",
            "tenant_id",
            "customer_id",
            "created_at",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: str = Field(nullable=False, index=True)
    customer_id: str = Field(nullable=False, index=True)
    surface: str = Field(nullable=False, max_length=100)

    decision_id: str = Field(nullable=False, max_length=100)
    model_version: str = Field(nullable=False, max_length=100)

    response_items: list[dict[str, Any]] = Field(
        sa_column=Column(JSONB, nullable=False)
    )

    latency_ms: float = Field(nullable=False)
    created_at: datetime = Field(nullable=False)