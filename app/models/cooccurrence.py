# app/models/cooccurrence.py

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint, Index
from sqlmodel import SQLModel, Field


class ProductCooccurrence(SQLModel, table=True):
    __tablename__ = "product_cooccurrence"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "product_a_id",
            "product_b_id",
            name="uq_product_cooccurrence_tenant_pair",
        ),
        Index(
            "ix_product_cooccurrence_tenant_product_a_confidence",
            "tenant_id",
            "product_a_id",
            "confidence",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    tenant_id: UUID = Field(nullable=False, index=True)
    product_a_id: str = Field(nullable=False, index=True)
    product_b_id: str = Field(nullable=False, index=True)

    co_count: int = Field(nullable=False)
    confidence: float = Field(nullable=False)

    last_updated: datetime = Field(nullable=False)