# app/services/cooccurrence_pipeline.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from sqlalchemy import text
from sqlmodel import Session


@dataclass
class CooccurrencePipelineResult:
    tenant_id: str
    pair_rows_upserted: int
    computed_at: datetime


class ProductCooccurrencePipelineService:
    def __init__(self, session: Session):
        self.session = session

    def run_for_tenant(self, tenant_id: str) -> CooccurrencePipelineResult:
        computed_at = datetime.utcnow()

        self.session.exec(
            text("DELETE FROM product_cooccurrence WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id},
        )

        upserted = self._compute_and_upsert(tenant_id=tenant_id, computed_at=computed_at)

        self.session.commit()

        return CooccurrencePipelineResult(
            tenant_id=tenant_id,
            pair_rows_upserted=upserted,
            computed_at=computed_at,
        )

    def _compute_and_upsert(self, tenant_id: str, computed_at: datetime) -> int:
        result = self.session.exec(
            text("""
                WITH purchase_events AS (
                    SELECT
                        e.tenant_id,
                        e.customer_id,
                        e.product_id,
                        e.timestamp
                    FROM events e
                    WHERE e.tenant_id = :tenant_id
                    AND e.event_type = 'purchase'
                    AND e.product_id IS NOT NULL
                ),

                product_support AS (
                    SELECT
                        tenant_id,
                        product_id,
                        COUNT(DISTINCT customer_id) AS customer_support
                    FROM purchase_events
                    GROUP BY tenant_id, product_id
                ),

                candidate_pairs AS (
                    SELECT
                        a.tenant_id,
                        a.customer_id,
                        a.product_id AS product_a_id,
                        b.product_id AS product_b_id
                    FROM purchase_events a
                    JOIN purchase_events b
                    ON a.tenant_id = b.tenant_id
                    AND a.customer_id = b.customer_id
                    AND a.product_id <> b.product_id
                    AND b.timestamp >= a.timestamp
                    AND b.timestamp <= a.timestamp + interval '30 days'
                ),

                distinct_customer_pairs AS (
                    SELECT DISTINCT
                        tenant_id,
                        customer_id,
                        product_a_id,
                        product_b_id
                    FROM candidate_pairs
                ),

                pair_counts AS (
                    SELECT
                        tenant_id,
                        product_a_id,
                        product_b_id,
                        COUNT(DISTINCT customer_id) AS co_count
                    FROM distinct_customer_pairs
                    GROUP BY tenant_id, product_a_id, product_b_id
                    HAVING COUNT(DISTINCT customer_id) >= 3
                ),

                scored_pairs AS (
                    SELECT
                        pc.tenant_id,
                        pc.product_a_id,
                        pc.product_b_id,
                        pc.co_count,
                        CASE
                            WHEN ps.customer_support = 0 THEN 0
                            ELSE pc.co_count::float / ps.customer_support::float
                        END AS confidence,
                        :computed_at AS last_updated
                    FROM pair_counts pc
                    JOIN product_support ps
                    ON ps.tenant_id = pc.tenant_id
                    AND ps.product_id = pc.product_a_id
                )

                INSERT INTO product_cooccurrence (
                    tenant_id,
                    product_a_id,
                    product_b_id,
                    co_count,
                    confidence,
                    last_updated
                )
                SELECT
                    tenant_id,
                    product_a_id,
                    product_b_id,
                    co_count,
                    confidence,
                    last_updated
                FROM scored_pairs
                ON CONFLICT (tenant_id, product_a_id, product_b_id)
                DO UPDATE SET
                    co_count = EXCLUDED.co_count,
                    confidence = EXCLUDED.confidence,
                    last_updated = EXCLUDED.last_updated
            """),
            {
                "tenant_id": tenant_id,
                "computed_at": computed_at,
            },
        )
        return result.rowcount if result.rowcount is not None else 0



