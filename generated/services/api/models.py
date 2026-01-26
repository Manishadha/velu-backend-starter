# generated/services/api/models.py

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,  # noqa: F401
)
from .db import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # New fields
    category = Column(String(100), index=True, nullable=True)
    brand = Column(String(100), nullable=True)
    is_featured = Column(Boolean, default=False, nullable=False, index=True)

    price = Column(Float, nullable=False)
    currency = Column(String(8), nullable=False, default="EUR")
    in_stock = Column(Boolean, default=True, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(8), default="EUR", nullable=False)
    customer_name = Column(String(255), nullable=True)
    customer_email = Column(String(255), nullable=True)


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    qty = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="customer")  # "admin" / "customer"
    created_at = Column(DateTime)
