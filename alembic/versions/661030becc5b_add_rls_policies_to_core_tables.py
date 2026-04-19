"""add_rls_policies_to_core_tables

Revision ID: 661030becc5b
Revises: 
Create Date: 2026-04-17 22:03:07.156003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '661030becc5b'
down_revision: Union[str, Sequence[str], None] = '120177e9e390'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Enable RLS on the tables
    op.execute("ALTER TABLE product ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE interactionevent ENABLE ROW LEVEL SECURITY;")

    # 2. Create the Policies
    # This policy says: "Only show rows where tenant_id matches the session variable"
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON product
        USING (tenant_id = nullif(current_setting('app.current_tenant', TRUE), '')::uuid);
    """)
    
    op.execute("""
        CREATE POLICY tenant_isolation_policy ON interactionevent
        USING (tenant_id = nullif(current_setting('app.current_tenant', TRUE), '')::uuid);
    """)


    # 1. Drop the old table if it exists
    op.execute("DROP TABLE IF EXISTS interactionevent;")

    # 2. Create the Table with PARTITION BY RANGE
    op.execute("""
        CREATE TABLE interactionevent (
            id UUID DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            customer_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            product_id UUID,
            properties JSONB,
            timestamp TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (id, timestamp)
        ) PARTITION BY RANGE (timestamp);
    """)

    # 3. Create an initial partition for April 2026
    op.execute("""
        CREATE TABLE interactionevent_2026_04 
        PARTITION OF interactionevent 
        FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
    """)

    # ---------------------------------------------------------------------------
    # 1. Create the Table and index it for historic lookup
    op.create_table(
        "recommendation_decisions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.Text(), nullable=False),
        sa.Column("surface", sa.String(length=100), nullable=False),
        sa.Column("decision_id", sa.String(length=100), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("response_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("decision_id", name="uq_recommendation_decisions_decision_id"),
    )
    op.create_index(
        "ix_recommendation_decisions_tenant_customer_created_at",
        "recommendation_decisions",
        ["tenant_id", "customer_id", "created_at"],
        unique=False,
    )
    
    # Without this, the app_user won't even be allowed to look at the table to check the RLS!
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;")
    

def downgrade():
    # This is for "undoing" your changes
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON product;")
    op.execute("DROP POLICY IF EXISTS tenant_isolation_policy ON interactionevent;")
    op.execute("ALTER TABLE product DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE interactionevent DISABLE ROW LEVEL SECURITY;")
