# generated/services/api/db.py

from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.orm import declarative_base, sessionmaker  # type: ignore

# Default: local SQLite for easy demo.
# For production, set DATABASE_URL to your Postgres URL, e.g.:
#   postgresql+psycopg2://user:password@localhost:5432/myshop
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./product_v1.db")

# SQLite needs this connect_args; Postgres/MySQL do not.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
