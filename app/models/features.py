# app/models/features.py

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Numeric, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class CustomerFeatures(SQLModel, table=True):
    __tablename__ = "customer_features"
    __table_args__ = (
        UniqueConstraint("tenant_id", "customer_id", name="uq_customer_features_tenant_customer"),
        Index("ix_customer_features_tenant_updated_at", "tenant_id", "updated_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    tenant_id: UUID = Field(nullable=False, index=True)
    customer_id: str = Field(nullable=False, index=True)

    total_views: int = Field(default=0, nullable=False)
    total_cart_adds: int = Field(default=0, nullable=False)
    total_purchases: int = Field(default=0, nullable=False)

    distinct_products_viewed: int = Field(default=0, nullable=False)
    distinct_categories_viewed: int = Field(default=0, nullable=False)

    days_since_first_seen: Optional[int] = Field(default=None)
    days_since_last_activity: Optional[int] = Field(default=None)

    category_affinity: Dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="{}"),
    )

    avg_days_between_purchases: Optional[float] = Field(default=None)

    total_revenue: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(12, 2), nullable=False, server_default="0"),
    )

    avg_order_value: Optional[Decimal] = Field(
        default=None,
        sa_column=Column(Numeric(12, 2), nullable=True),
    )

    avg_session_duration_seconds: Optional[float] = Field(default=None)
    avg_products_viewed_per_session: Optional[float] = Field(default=None)

    updated_at: datetime = Field(nullable=False)


class PipelineCheckpoint(SQLModel, table=True):
    __tablename__ = "pipeline_checkpoints"
    __table_args__ = (
        UniqueConstraint("tenant_id", "pipeline_name", name="uq_pipeline_checkpoints_tenant_pipeline"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    tenant_id: UUID = Field(nullable=False, index=True)
    pipeline_name: str = Field(nullable=False, max_length=100)

    last_event_ts: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(nullable=False)