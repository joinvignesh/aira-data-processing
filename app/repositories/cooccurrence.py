# app/repositories/cooccurrence.py

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session


class CooccurrenceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_top_related_products(
        self,
        tenant_id: str,
        product_id: str,
        limit: int = 10,
    ) -> list[dict]:
        rows = self.session.exec(
            text("""
                SELECT
                    product_b_id AS product_id,
                    co_count,
                    confidence,
                    last_updated
                FROM product_cooccurrence
                WHERE tenant_id = :tenant_id
                  AND product_a_id = :product_id
                ORDER BY confidence DESC, co_count DESC, product_b_id
                LIMIT :limit
            """),
            params={
                "tenant_id": tenant_id,
                "product_id": product_id,
                "limit": limit,
            },
        ).mappings().all()

        return [dict(row) for row in rows]