from sqlalchemy import text


def test_migrations_apply_cleanly(engine):
    expected_tables = {
        "tenant",
        "user",
        "product",
        "interactionevent",
        "customer_features",
        "pipeline_checkpoints",
        "recommendation_decisions",
    }

    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
        """)).fetchall()

    found_tables = {row[0] for row in rows}

    for table_name in expected_tables:
        assert table_name in found_tables