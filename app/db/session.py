from sqlalchemy import text
from sqlmodel import Session, create_engine
import os

# Use app_user for regular requests (RLS enforced)
DATABASE_URL = "postgresql://app_user:app_password@localhost:5432/aira"
engine = create_engine(DATABASE_URL)

def get_db_session(tenant_id: str):
    """
    Injects the tenant_id into the Postgres session variable.
    """
    with Session(engine) as session:
        # SET LOCAL ensures this variable only exists for THIS transaction
        session.execute(
            text("SET LOCAL app.current_tenant = :t_id"), 
            {"t_id": tenant_id}
        )
        yield session