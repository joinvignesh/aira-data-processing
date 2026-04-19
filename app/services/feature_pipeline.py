# app/services/feature_pipeline.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlmodel import Session


PIPELINE_NAME = "customer_features_v1"


@dataclass
class FeaturePipelineResult:
    tenant_id: str
    checkpoint_before: datetime | None
    checkpoint_after: datetime | None
    affected_customers: int
    upserted_rows: int
    processed_events: int


class CustomerFeaturePipelineService:
    def __init__(self, session: Session):
        self.session = session

    def run_for_tenant(self, tenant_id: str) -> FeaturePipelineResult:
        checkpoint_before = self._get_checkpoint(tenant_id)

        max_event_ts = self._get_max_new_event_timestamp(tenant_id, checkpoint_before)
        if max_event_ts is None:
            return FeaturePipelineResult(
                tenant_id=tenant_id,
                checkpoint_before=checkpoint_before,
                checkpoint_after=checkpoint_before,
                affected_customers=0,
                upserted_rows=0,
                processed_events=0,
            )

        affected_customers = self._materialize_affected_customers(
            tenant_id=tenant_id,
            checkpoint_before=checkpoint_before,
            checkpoint_after=max_event_ts,
        )

        processed_events = self._count_new_events(
            tenant_id=tenant_id,
            checkpoint_before=checkpoint_before,
            checkpoint_after=max_event_ts,
        )

        upserted_rows = self._recompute_and_upsert_features(
            tenant_id=tenant_id,
            checkpoint_after=max_event_ts,
        )

        self._upsert_checkpoint(
            tenant_id=tenant_id,
            checkpoint_value=max_event_ts,
        )

        self.session.commit()

        return FeaturePipelineResult(
            tenant_id=tenant_id,
            checkpoint_before=checkpoint_before,
            checkpoint_after=max_event_ts,
            affected_customers=affected_customers,
            upserted_rows=upserted_rows,
            processed_events=processed_events,
        )

    def _get_checkpoint(self, tenant_id: str) -> datetime | None:
        stmt = text("""
            SELECT last_event_ts
            FROM pipeline_checkpoints
            WHERE tenant_id = :tenant_id
              AND pipeline_name = :pipeline_name
        """)
        row = self.session.exec(
            stmt,
            {
                "tenant_id": tenant_id,
                "pipeline_name": PIPELINE_NAME,
            },
        ).first()
        return row[0] if row else None

    def _get_max_new_event_timestamp(
        self,
        tenant_id: str,
        checkpoint_before: datetime | None,
    ) -> datetime | None:
        stmt = text("""
            SELECT MAX(timestamp) AS max_ts
            FROM events
            WHERE tenant_id = :tenant_id
              AND (:checkpoint_before IS NULL OR timestamp > :checkpoint_before)
        """)
        row = self.session.exec(
            stmt,
            {
                "tenant_id": tenant_id,
                "checkpoint_before": checkpoint_before,
            },
        ).first()
        return row[0] if row and row[0] is not None else None

    def _materialize_affected_customers(
        self,
        tenant_id: str,
        checkpoint_before: datetime | None,
        checkpoint_after: datetime,
    ) -> int:
        self.session.exec(text("DROP TABLE IF EXISTS tmp_affected_customers"))

        self.session.exec(text("""
            CREATE TEMP TABLE tmp_affected_customers AS
            SELECT DISTINCT e.customer_id
            FROM events e
            WHERE e.tenant_id = :tenant_id
              AND (:checkpoint_before IS NULL OR e.timestamp > :checkpoint_before)
              AND e.timestamp <= :checkpoint_after
        """), {
            "tenant_id": tenant_id,
            "checkpoint_before": checkpoint_before,
            "checkpoint_after": checkpoint_after,
        })

        row = self.session.exec(text("""
            SELECT COUNT(*) FROM tmp_affected_customers
        """)).first()

        return int(row[0])

    def _count_new_events(
        self,
        tenant_id: str,
        checkpoint_before: datetime | None,
        checkpoint_after: datetime,
    ) -> int:
        row = self.session.exec(text("""
            SELECT COUNT(*)
            FROM events
            WHERE tenant_id = :tenant_id
              AND (:checkpoint_before IS NULL OR timestamp > :checkpoint_before)
              AND timestamp <= :checkpoint_after
        """), {
            "tenant_id": tenant_id,
            "checkpoint_before": checkpoint_before,
            "checkpoint_after": checkpoint_after,
        }).first()

        return int(row[0])

    def _upsert_basic_features(self, tenant_id: str, checkpoint_after):
        result = self.session.exec(
            text("""
                WITH base_events AS (
                    SELECT
                        e.tenant_id,
                        e.customer_id,
                        e.product_id,
                        e.event_type,
                        e.timestamp,
                        p.category
                    FROM events e
                    LEFT JOIN products p
                      ON p.id = e.product_id
                     AND p.tenant_id = e.tenant_id
                    INNER JOIN tmp_affected_customers ac
                      ON ac.customer_id = e.customer_id
                    WHERE e.tenant_id = :tenant_id
                ),
                aggregates AS (
                    SELECT
                        tenant_id,
                        customer_id,
                        COUNT(*) FILTER (WHERE event_type IN ('page_view', 'product_view')) AS total_views,
                        COUNT(*) FILTER (WHERE event_type = 'add_to_cart') AS total_cart_adds,
                        COUNT(*) FILTER (WHERE event_type = 'purchase') AS total_purchases,
                        COUNT(DISTINCT product_id) FILTER (WHERE product_id IS NOT NULL) AS distinct_products_viewed,
                        COUNT(DISTINCT category) FILTER (WHERE category IS NOT NULL) AS distinct_categories_viewed,
                        CURRENT_DATE - MIN(timestamp::date) AS days_since_first_seen,
                        CURRENT_DATE - MAX(timestamp::date) AS days_since_last_activity
                    FROM base_events
                    GROUP BY tenant_id, customer_id
                )
                INSERT INTO customer_features (
                    tenant_id,
                    customer_id,
                    total_views,
                    total_cart_adds,
                    total_purchases,
                    distinct_products_viewed,
                    distinct_categories_viewed,
                    days_since_first_seen,
                    days_since_last_activity,
                    updated_at
                )
                SELECT
                    tenant_id,
                    customer_id,
                    total_views,
                    total_cart_adds,
                    total_purchases,
                    distinct_products_viewed,
                    distinct_categories_viewed,
                    days_since_first_seen,
                    days_since_last_activity,
                    :checkpoint_after
                FROM aggregates
                ON CONFLICT (tenant_id, customer_id)
                DO UPDATE SET
                    total_views = EXCLUDED.total_views,
                    total_cart_adds = EXCLUDED.total_cart_adds,
                    total_purchases = EXCLUDED.total_purchases,
                    distinct_products_viewed = EXCLUDED.distinct_products_viewed,
                    distinct_categories_viewed = EXCLUDED.distinct_categories_viewed,
                    days_since_first_seen = EXCLUDED.days_since_first_seen,
                    days_since_last_activity = EXCLUDED.days_since_last_activity,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "tenant_id": tenant_id,
                "checkpoint_after": checkpoint_after,
            },
        )
        return result.rowcount if result.rowcount is not None else 0

    def _save_checkpoint(self, tenant_id: str, checkpoint_after):
        self.session.exec(
            text("""
                INSERT INTO pipeline_checkpoints (
                    tenant_id,
                    pipeline_name,
                    last_event_ts,
                    updated_at
                )
                VALUES (
                    :tenant_id,
                    :pipeline_name,
                    :last_event_ts,
                    now()
                )
                ON CONFLICT (tenant_id, pipeline_name)
                DO UPDATE SET
                    last_event_ts = EXCLUDED.last_event_ts,
                    updated_at = EXCLUDED.updated_at
            """),
            {
                "tenant_id": tenant_id,
                "pipeline_name": PIPELINE_NAME,
                "last_event_ts": checkpoint_after,
            },
        )


    def _recompute_and_upsert_features(
        self,
        tenant_id: str,
        checkpoint_after: datetime,
    ) -> int:
        stmt = text("""
            WITH base_events AS (
                SELECT
                    e.tenant_id,
                    e.customer_id,
                    e.product_id,
                    e.event_type,
                    e.timestamp,
                    e.properties,
                    p.category,
                    COALESCE((e.properties ->> 'revenue')::numeric, 0) AS revenue
                FROM events e
                LEFT JOIN products p
                  ON p.id = e.product_id
                 AND p.tenant_id = e.tenant_id
                INNER JOIN tmp_affected_customers ac
                  ON ac.customer_id = e.customer_id
                WHERE e.tenant_id = :tenant_id
            ),
            aggregate_features AS (
                SELECT
                    tenant_id,
                    customer_id,
                    COUNT(*) FILTER (WHERE event_type = 'page_view' OR event_type = 'product_view') AS total_views,
                    COUNT(*) FILTER (WHERE event_type = 'add_to_cart') AS total_cart_adds,
                    COUNT(*) FILTER (WHERE event_type = 'purchase') AS total_purchases,
                    COUNT(DISTINCT product_id) FILTER (WHERE product_id IS NOT NULL) AS distinct_products_viewed,
                    COUNT(DISTINCT category) FILTER (WHERE category IS NOT NULL) AS distinct_categories_viewed,
                    CURRENT_DATE - MIN(timestamp::date) AS days_since_first_seen,
                    CURRENT_DATE - MAX(timestamp::date) AS days_since_last_activity
                FROM base_events
                GROUP BY tenant_id, customer_id
            ),
            category_affinity AS (
                SELECT
                    tenant_id,
                    customer_id,
                    jsonb_object_agg(category, affinity_score) AS category_affinity
                FROM (
                    SELECT
                        tenant_id,
                        customer_id,
                        category,
                        SUM(
                            CASE
                                WHEN timestamp >= now() - interval '7 days' THEN 3
                                WHEN timestamp >= now() - interval '30 days' THEN 1
                                ELSE 0
                            END
                        )::float AS affinity_score
                    FROM base_events
                    WHERE category IS NOT NULL
                      AND event_type IN ('page_view', 'product_view', 'add_to_cart', 'purchase')
                    GROUP BY tenant_id, customer_id, category
                ) s
                GROUP BY tenant_id, customer_id
            ),
            purchase_events AS (
                SELECT
                    tenant_id,
                    customer_id,
                    timestamp,
                    revenue,
                    LAG(timestamp) OVER (
                        PARTITION BY tenant_id, customer_id
                        ORDER BY timestamp
                    ) AS prev_purchase_ts
                FROM base_events
                WHERE event_type = 'purchase'
            ),
            purchase_features AS (
                SELECT
                    tenant_id,
                    customer_id,
                    AVG(EXTRACT(EPOCH FROM (timestamp - prev_purchase_ts)) / 86400.0)
                        FILTER (WHERE prev_purchase_ts IS NOT NULL) AS avg_days_between_purchases,
                    SUM(revenue) AS total_revenue,
                    AVG(NULLIF(revenue, 0)) FILTER (WHERE revenue > 0) AS avg_order_value
                FROM purchase_events
                GROUP BY tenant_id, customer_id
            ),
            sessionized AS (
                SELECT
                    tenant_id,
                    customer_id,
                    timestamp,
                    product_id,
                    CASE
                        WHEN LAG(timestamp) OVER (
                            PARTITION BY tenant_id, customer_id
                            ORDER BY timestamp
                        ) IS NULL THEN 1
                        WHEN timestamp - LAG(timestamp) OVER (
                            PARTITION BY tenant_id, customer_id
                            ORDER BY timestamp
                        ) > interval '30 minutes' THEN 1
                        ELSE 0
                    END AS new_session_flag
                FROM base_events
            ),
            session_buckets AS (
                SELECT
                    tenant_id,
                    customer_id,
                    timestamp,
                    product_id,
                    SUM(new_session_flag) OVER (
                        PARTITION BY tenant_id, customer_id
                        ORDER BY timestamp
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS session_num
                FROM sessionized
            ),
            session_stats AS (
                SELECT
                    tenant_id,
                    customer_id,
                    AVG(EXTRACT(EPOCH FROM (MAX(timestamp) - MIN(timestamp)))) AS avg_session_duration_seconds,
                    AVG(product_views) AS avg_products_viewed_per_session
                FROM (
                    SELECT
                        tenant_id,
                        customer_id,
                        session_num,
                        MIN(timestamp) AS session_start,
                        MAX(timestamp) AS session_end,
                        COUNT(*) FILTER (WHERE product_id IS NOT NULL) AS product_views
                    FROM session_buckets
                    GROUP BY tenant_id, customer_id, session_num
                ) s
                GROUP BY tenant_id, customer_id
            ),
            final_features AS (
                SELECT
                    a.tenant_id,
                    a.customer_id,
                    a.total_views,
                    a.total_cart_adds,
                    a.total_purchases,
                    a.distinct_products_viewed,
                    a.distinct_categories_viewed,
                    a.days_since_first_seen,
                    a.days_since_last_activity,
                    COALESCE(c.category_affinity, '{}'::jsonb) AS category_affinity,
                    p.avg_days_between_purchases,
                    COALESCE(p.total_revenue, 0) AS total_revenue,
                    p.avg_order_value,
                    s.avg_session_duration_seconds,
                    s.avg_products_viewed_per_session,
                    :checkpoint_after AS updated_at
                FROM aggregate_features a
                LEFT JOIN category_affinity c
                  ON c.tenant_id = a.tenant_id
                 AND c.customer_id = a.customer_id
                LEFT JOIN purchase_features p
                  ON p.tenant_id = a.tenant_id
                 AND p.customer_id = a.customer_id
                LEFT JOIN session_stats s
                  ON s.tenant_id = a.tenant_id
                 AND s.customer_id = a.customer_id
            )
            INSERT INTO customer_features (
                tenant_id,
                customer_id,
                total_views,
                total_cart_adds,
                total_purchases,
                distinct_products_viewed,
                distinct_categories_viewed,
                days_since_first_seen,
                days_since_last_activity,
                category_affinity,
                avg_days_between_purchases,
                total_revenue,
                avg_order_value,
                avg_session_duration_seconds,
                avg_products_viewed_per_session,
                updated_at
            )
            SELECT
                tenant_id,
                customer_id,
                total_views,
                total_cart_adds,
                total_purchases,
                distinct_products_viewed,
                distinct_categories_viewed,
                days_since_first_seen,
                days_since_last_activity,
                category_affinity,
                avg_days_between_purchases,
                total_revenue,
                avg_order_value,
                avg_session_duration_seconds,
                avg_products_viewed_per_session,
                updated_at
            FROM final_features
            ON CONFLICT (tenant_id, customer_id)
            DO UPDATE SET
                total_views = EXCLUDED.total_views,
                total_cart_adds = EXCLUDED.total_cart_adds,
                total_purchases = EXCLUDED.total_purchases,
                distinct_products_viewed = EXCLUDED.distinct_products_viewed,
                distinct_categories_viewed = EXCLUDED.distinct_categories_viewed,
                days_since_first_seen = EXCLUDED.days_since_first_seen,
                days_since_last_activity = EXCLUDED.days_since_last_activity,
                category_affinity = EXCLUDED.category_affinity,
                avg_days_between_purchases = EXCLUDED.avg_days_between_purchases,
                total_revenue = EXCLUDED.total_revenue,
                avg_order_value = EXCLUDED.avg_order_value,
                avg_session_duration_seconds = EXCLUDED.avg_session_duration_seconds,
                avg_products_viewed_per_session = EXCLUDED.avg_products_viewed_per_session,
                updated_at = EXCLUDED.updated_at
        """)

        result = self.session.exec(stmt, {
            "tenant_id": tenant_id,
            "checkpoint_after": checkpoint_after,
        })

        return result.rowcount if result.rowcount is not None else 0

    def _upsert_checkpoint(
        self,
        tenant_id: str,
        checkpoint_value: datetime,
    ) -> None:
        self.session.exec(text("""
            INSERT INTO pipeline_checkpoints (
                tenant_id,
                pipeline_name,
                last_event_ts,
                updated_at
            )
            VALUES (
                :tenant_id,
                :pipeline_name,
                :last_event_ts,
                now()
            )
            ON CONFLICT (tenant_id, pipeline_name)
            DO UPDATE SET
                last_event_ts = EXCLUDED.last_event_ts,
                updated_at = EXCLUDED.updated_at
        """), {
            "tenant_id": tenant_id,
            "pipeline_name": PIPELINE_NAME,
            "last_event_ts": checkpoint_value,
        })