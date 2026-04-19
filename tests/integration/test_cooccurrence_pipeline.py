from datetime import timedelta

from sqlmodel import Session
from sqlalchemy import text

from app.services.cooccurrence_pipeline import ProductCooccurrencePipelineService
from tests.integration.seeds import (
    seed_tenant,
    seed_product,
    seed_interaction_event,
    utcnow,
)


def test_cooccurrence_pipeline_builds_expected_pairs(db_session: Session):
    tenant_id = seed_tenant(db_session, "Cooccur Tenant", "cooccur-tenant")

    phone = seed_product(db_session, tenant_id, "ext-phone", "Phone", "electronics", 500.0)
    earbuds = seed_product(db_session, tenant_id, "ext-earbuds", "Earbuds", "electronics", 100.0)

    now = utcnow()

    for idx in range(3):
        customer_id = f"cust_{idx+1}"
        seed_interaction_event(
            db_session,
            tenant_id,
            customer_id,
            "purchase",
            phone,
            now - timedelta(days=10),
            properties='{"revenue": 500.0}',
        )
        seed_interaction_event(
            db_session,
            tenant_id,
            customer_id,
            "purchase",
            earbuds,
            now - timedelta(days=5),
            properties='{"revenue": 100.0}',
        )

    db_session.commit()

    service = ProductCooccurrencePipelineService(db_session)
    result = service.run_for_tenant(tenant_id)

    assert result.pair_rows_upserted >= 1

    row = db_session.exec(
        text("""
            SELECT product_a_id, product_b_id, co_count, confidence
            FROM product_cooccurrence
            WHERE tenant_id = :tenant_id
              AND product_a_id = :phone
              AND product_b_id = :earbuds
        """),
        params={
            "tenant_id": tenant_id,
            "phone": phone,
            "earbuds": earbuds,
        },
    ).mappings().first()

    assert row is not None
    assert row["co_count"] >= 3
    assert float(row["confidence"]) > 0