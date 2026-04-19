from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlmodel import Session


def utcnow():
    return datetime.now(timezone.utc)


def seed_tenant(session: Session, name: str, slug: str, plan_tier: str = "pro") -> str:
    tenant_id = str(uuid4())
    session.exec(
        text("""
            INSERT INTO tenant (id, name, slug, plan_tier, created_at)
            VALUES (:id, :name, :slug, :plan_tier, :created_at)
        """),
        params={
            "id": tenant_id,
            "name": name,
            "slug": slug,
            "plan_tier": plan_tier,
            "created_at": utcnow(),
        },
    )
    return tenant_id


def seed_product(
    session: Session,
    tenant_id: str,
    external_id: str,
    title: str,
    category: str,
    price: float,
    currency: str = "USD",
    active: bool = True,
) -> str:
    product_id = str(uuid4())
    session.exec(
        text("""
            INSERT INTO product (
                id, tenant_id, external_id, title, description, price, currency,
                category, tags, metadata, active, created_at
            )
            VALUES (
                :id, :tenant_id, :external_id, :title, :description, :price, :currency,
                :category, '[]'::json, '{}'::json, :active, :created_at
            )
        """),
        params={
            "id": product_id,
            "tenant_id": tenant_id,
            "external_id": external_id,
            "title": title,
            "description": f"{title} description",
            "price": price,
            "currency": currency,
            "category": category,
            "active": active,
            "created_at": utcnow(),
        },
    )
    return product_id


def seed_interaction_event(
    session: Session,
    tenant_id: str,
    customer_id: str,
    event_type: str,
    product_id: str | None,
    ts: datetime,
    properties: str = "{}",
) -> str:
    event_id = str(uuid4())
    session.exec(
        text("""
            INSERT INTO interactionevent (
                id, tenant_id, customer_id, event_type, product_id, properties, timestamp
            )
            VALUES (
                :id, :tenant_id, :customer_id, :event_type, :product_id,
                CAST(:properties AS jsonb), :timestamp
            )
        """),
        params={
            "id": event_id,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "event_type": event_type,
            "product_id": product_id,
            "properties": properties,
            "timestamp": ts,
        },
    )
    return event_id


def seed_customer_features(
    session: Session,
    tenant_id: str,
    customer_id: str,
    category_affinity: str = '{"electronics": 9, "accessories": 4}',
) -> str:
    feature_id = str(uuid4())
    session.exec(
        text("""
            INSERT INTO customer_features (
                id,
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
            VALUES (
                :id,
                :tenant_id,
                :customer_id,
                12,
                2,
                3,
                4,
                2,
                20,
                1,
                CAST(:category_affinity AS jsonb),
                10.5,
                699.00,
                233.00,
                420.0,
                3.0,
                :updated_at
            )
        """),
        params={
            "id": feature_id,
            "tenant_id": tenant_id,
            "customer_id": customer_id,
            "category_affinity": category_affinity,
            "updated_at": utcnow(),
        },
    )
    return feature_id


def seed_product_cooccurrence(
    session: Session,
    tenant_id: str,
    product_a_id: str,
    product_b_id: str,
    co_count: int,
    confidence: float,
) -> str:
    row_id = str(uuid4())
    session.exec(
        text("""
            INSERT INTO product_cooccurrence (
                id, tenant_id, product_a_id, product_b_id, co_count, confidence, last_updated
            )
            VALUES (
                :id, :tenant_id, :product_a_id, :product_b_id, :co_count, :confidence, :last_updated
            )
        """),
        params={
            "id": row_id,
            "tenant_id": tenant_id,
            "product_a_id": product_a_id,
            "product_b_id": product_b_id,
            "co_count": co_count,
            "confidence": confidence,
            "last_updated": utcnow(),
        },
    )
    return row_id


def seed_warm_recommendation_scenario(session: Session) -> dict:
    now = utcnow()

    tenant_id = seed_tenant(session, "Tenant A", "tenant-a")
    customer_id = "cust_1"

    phone = seed_product(session, tenant_id, "ext-phone", "Phone", "electronics", 499.0)
    earbuds = seed_product(session, tenant_id, "ext-earbuds", "Earbuds", "electronics", 99.0)
    charger = seed_product(session, tenant_id, "ext-charger", "Charger", "electronics", 29.0)
    case = seed_product(session, tenant_id, "ext-case", "Case", "accessories", 19.0)
    shoes = seed_product(session, tenant_id, "ext-shoes", "Shoes", "fashion", 89.0)

    seed_customer_features(session, tenant_id, customer_id)

    seed_product_cooccurrence(session, tenant_id, phone, earbuds, 5, 0.80)
    seed_product_cooccurrence(session, tenant_id, phone, charger, 4, 0.60)
    seed_product_cooccurrence(session, tenant_id, phone, case, 3, 0.40)

    seed_interaction_event(session, tenant_id, customer_id, "product_view", phone, now - timedelta(days=2))
    seed_interaction_event(session, tenant_id, customer_id, "add_to_cart", phone, now - timedelta(days=1))
    seed_interaction_event(
        session,
        tenant_id,
        customer_id,
        "purchase",
        phone,
        now - timedelta(hours=12),
        properties='{"revenue": 499.0}',
    )

    session.commit()

    return {
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "products": {
            "phone": phone,
            "earbuds": earbuds,
            "charger": charger,
            "case": case,
            "shoes": shoes,
        },
    }


def seed_cold_start_scenario(session: Session) -> dict:
    now = utcnow()

    tenant_id = seed_tenant(session, "Tenant Cold", "tenant-cold")
    customer_id = "cold_customer"

    popular_1 = seed_product(session, tenant_id, "ext-pop-1", "Popular One", "electronics", 100.0)
    popular_2 = seed_product(session, tenant_id, "ext-pop-2", "Popular Two", "electronics", 120.0)

    for _ in range(5):
        seed_interaction_event(session, tenant_id, f"viewer_{uuid4().hex[:8]}", "product_view", popular_1, now)
    for _ in range(3):
        seed_interaction_event(
            session,
            tenant_id,
            f"buyer_{uuid4().hex[:8]}",
            "purchase",
            popular_2,
            now,
            properties='{"revenue": 120.0}',
        )

    session.commit()

    return {
        "tenant_id": tenant_id,
        "customer_id": customer_id,
        "products": {
            "popular_1": popular_1,
            "popular_2": popular_2,
        },
    }


def seed_tenant_isolation_scenario(session: Session) -> dict:
    scenario_a = seed_warm_recommendation_scenario(session)
    scenario_b_tenant = seed_tenant(session, "Tenant B", "tenant-b")
    shared_customer_id = scenario_a["customer_id"]

    other_product = seed_product(
        session,
        scenario_b_tenant,
        "ext-b-only",
        "Tenant B Only Product",
        "electronics",
        777.0,
    )

    seed_customer_features(
        session,
        scenario_b_tenant,
        shared_customer_id,
        category_affinity='{"electronics": 99}',
    )

    session.commit()

    return {
        "tenant_a": scenario_a,
        "tenant_b": {
            "tenant_id": scenario_b_tenant,
            "customer_id": shared_customer_id,
            "product_id": other_product,
        },
    }