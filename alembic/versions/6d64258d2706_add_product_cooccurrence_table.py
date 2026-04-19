"""add product cooccurrence table

Revision ID: 6d64258d2706
Revises: 661030becc5b
Create Date: 2026-04-19 08:56:49.139141
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "6d64258d2706"
down_revision: Union[str, Sequence[str], None] = "661030becc5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_cooccurrence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("co_count", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "product_a_id",
            "product_b_id",
            name="uq_product_cooccurrence_tenant_pair",
        ),
    )

    op.create_index(
        "ix_product_cooccurrence_lookup",
        "product_cooccurrence",
        ["tenant_id", "product_a_id", "confidence", "co_count"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_product_cooccurrence_lookup", table_name="product_cooccurrence")
    op.drop_table("product_cooccurrence")