# app/repositories/recommendation.py

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session


class RecommendationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_customer_features(self, tenant_id: str, customer_id: str):
        row = self.session.exec(
            text("""
                SELECT
                    customer_id,
                    category_affinity,
                    total_views,
                    total_purchases,
                    avg_days_between_purchases,
                    total_revenue,
                    avg_order_value,
                    avg_session_duration_seconds,
                    avg_products_viewed_per_session
                FROM customer_features
                WHERE tenant_id = :tenant_id
                  AND customer_id = :customer_id
            """),
            {
                "tenant_id": tenant_id,
                "customer_id": customer_id,
            },
        ).mappings().first()

        return dict(row) if row else None

    def get_recent_anchor_products(self, tenant_id: str, customer_id: str, limit: int = 5) -> list[str]:
        rows = self.session.exec(
            text("""
                SELECT product_id
                FROM (
                    SELECT
                        product_id,
                        MAX(timestamp) AS last_seen
                    FROM events
                    WHERE tenant_id = :tenant_id
                      AND customer_id = :customer_id
                      AND product_id IS NOT NULL
                      AND event_type IN ('product_view', 'add_to_cart', 'purchase')
                      AND timestamp >= now() - interval '30 days'
                    GROUP BY product_id
                ) t
                ORDER BY last_seen DESC
                LIMIT :limit
            """),
            {
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "limit": limit,
            },
        ).all()

        return [str(r[0]) for r in rows]

    def get_products_by_category_affinity(
        self,
        tenant_id: str,
        category_affinity: dict,
        limit: int = 100,
    ) -> list[dict]:
        if not category_affinity:
            return []

        rows = self.session.exec(
            text("""
                WITH affinity_rows AS (
                    SELECT
                        key AS category,
                        value::float AS affinity_score
                    FROM jsonb_each_text(CAST(:category_affinity AS jsonb))
                )
                SELECT
                    p.id AS product_id,
                    MAX(ar.affinity_score) AS score
                FROM products p
                JOIN affinity_rows ar
                  ON ar.category = p.category
                WHERE p.tenant_id = :tenant_id
                  AND p.active = true
                GROUP BY p.id
                ORDER BY score DESC, p.id
                LIMIT :limit
            """),
            {
                "tenant_id": tenant_id,
                "category_affinity": category_affinity,
                "limit": limit,
            },
        ).mappings().all()

        return [dict(r) for r in rows]

    def get_top_related_products(self, tenant_id: str, product_id: str, limit: int = 50) -> list[dict]:
        rows = self.session.exec(
            text("""
                SELECT
                    product_b_id AS product_id,
                    co_count,
                    confidence
                FROM product_cooccurrence
                WHERE tenant_id = :tenant_id
                  AND product_a_id = :product_id
                ORDER BY confidence DESC, co_count DESC, product_b_id
                LIMIT :limit
            """),
            {
                "tenant_id": tenant_id,
                "product_id": product_id,
                "limit": limit,
            },
        ).mappings().all()

        return [dict(r) for r in rows]

    def get_global_popularity(self, tenant_id: str, limit: int = 50) -> list[dict]:
        rows = self.session.exec(
            text("""
                WITH recent_events AS (
                    SELECT
                        product_id,
                        event_type
                    FROM events
                    WHERE tenant_id = :tenant_id
                      AND product_id IS NOT NULL
                      AND timestamp >= now() - interval '30 days'
                      AND event_type IN ('product_view', 'purchase')
                ),
                popularity AS (
                    SELECT
                        product_id,
                        (
                            COUNT(*) FILTER (WHERE event_type = 'product_view') * 1.0 +
                            COUNT(*) FILTER (WHERE event_type = 'purchase') * 5.0
                        ) AS score
                    FROM recent_events
                    GROUP BY product_id
                )
                SELECT
                    p.id AS product_id,
                    pop.score
                FROM popularity pop
                JOIN products p
                  ON p.id = pop.product_id
                 AND p.tenant_id = :tenant_id
                WHERE p.active = true
                ORDER BY pop.score DESC, p.id
                LIMIT :limit
            """),
            {
                "tenant_id": tenant_id,
                "limit": limit,
            },
        ).mappings().all()

        return [dict(r) for r in rows]

    def log_recommendation_decision(
        self,
        tenant_id: str,
        customer_id: str,
        surface: str,
        decision_id: str,
        model_version: str,
        response_items: list[dict],
        latency_ms: float,
    ) -> None:
        self.session.exec(
            text("""
                INSERT INTO recommendation_decisions (
                    tenant_id,
                    customer_id,
                    surface,
                    decision_id,
                    model_version,
                    response_items,
                    latency_ms,
                    created_at
                )
                VALUES (
                    :tenant_id,
                    :customer_id,
                    :surface,
                    :decision_id,
                    :model_version,
                    CAST(:response_items AS jsonb),
                    :latency_ms,
                    now()
                )
            """),
            {
                "tenant_id": tenant_id,
                "customer_id": customer_id,
                "surface": surface,
                "decision_id": decision_id,
                "model_version": model_version,
                "response_items": response_items,
                "latency_ms": latency_ms,
            },
        )