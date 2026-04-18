import pytest
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlmodel import Session
from app.db.session import engine
from app.models.domain import Product, Tenant

admin_engine = create_engine("postgresql://app_admin:admin_password@localhost:5432/aira")

def test_tenant_isolation_rls():
    """
    Test that Tenant A cannot see Tenant B's data at the database level.
    """
    # 1. Setup: Create two unique Tenant IDs
    tenant_a_id = uuid4()
    tenant_b_id = uuid4()

    # We use a 'super_user' session to set up the data initially
    with Session(admin_engine) as session:
        # Clear existing test data if necessary
        session.exec(text("DELETE FROM product"))
        
        # Insert a product for Tenant A
        tenant_A = Tenant(id=tenant_a_id, name=f"Tenant A {tenant_a_id}", slug=f"tenant-a-{tenant_a_id}", plan_tier="free")
        session.add(tenant_A)
        
        # Insert a product for Tenant B
        tenant_B = Tenant(id=tenant_b_id, name=f"Tenant B {tenant_b_id}", slug=f"tenant-b-{tenant_b_id}", plan_tier="free")
        session.add(tenant_B)
        
        session.commit() # Commit tenants before adding products to satisfy FK constraints
        
        pA = Product(tenant_id=tenant_a_id, external_id='p1', title='Tenant A Product', price=10.0, category='cat', currency='USD', active=True)
        session.add(pA)
        pB = Product(tenant_id=tenant_b_id, external_id='p2', title='Tenant B Product', price=20.0, category='cat', currency='USD', active=True)
        session.add(pB)
        
        session.commit()

    # 2. The Test: Connect as 'app_user' and set context to Tenant A
    with engine.connect() as conn:
        # IMPORTANT: This mimics what our FastAPI middleware does
        conn.execute(text(f"SET app.current_tenant = '{tenant_a_id}'"))
        
        # Try to select all products
        result = conn.execute(text("SELECT title FROM product")).fetchall()
        
        # 3. Verification
        titles = [row[0] for row in result]
        
        assert "Tenant A Product" in titles
        assert "Tenant B Product" not in titles
        assert len(titles) == 1, "Tenant A should ONLY see their own product"

    print("✅ RLS Isolation Test Passed: Data is successfully siloed.")