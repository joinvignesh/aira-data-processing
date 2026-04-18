from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Column, JSON, String
from pydantic import EmailStr

class UserRole(str, Enum):
    admin = "admin"
    power_user = "power_user"
    operator = "operator"
    viewer = "viewer"

class EventType(str, Enum):
    page_view = "page_view"
    product_view = "product_view"
    add_to_cart = "add_to_cart"
    purchase = "purchase"
    click = "click"
    dismiss = "dismiss"

# --- CORE TABLES ---

class Tenant(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    plan_tier: str = "free"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    email: EmailStr = Field(unique=True, index=True)
    password_hash: str
    display_name: str
    role: UserRole = Field(default=UserRole.viewer)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Product(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(foreign_key="tenant.id", index=True)
    external_id: str = Field(index=True)
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "USD"
    category: str = Field(index=True)
    tags: List[str] = Field(default=[], sa_column=Column(JSON))
    meta: Dict = Field(default={}, sa_column=Column("metadata", JSON))
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Event(SQLModel, table=True):
    __tablename__ = "interactionevent"
    """
    Note: In Module 2, we will add the Partitioning logic via Alembic.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    tenant_id: UUID = Field(index=True)
    customer_id: str = Field(index=True)
    event_type: EventType
    product_id: Optional[UUID] = None
    properties: Dict = Field(default={}, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)