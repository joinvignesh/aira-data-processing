# app/db/dependencies.py

from sqlmodel import Session
from app.db.session import engine

def get_db():
    with Session(engine) as session:
        yield session