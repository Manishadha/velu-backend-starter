from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from ..db import get_db  # type: ignore
from ..models import Product, Order, OrderItem  # type: ignore

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


# ---------- Schemas ----------


class OrderItemIn(BaseModel):
    product_id: int = Field(..., ge=1)
    qty: int = Field(..., ge=1)


class OrderCreate(BaseModel):
    items: List[OrderItemIn]
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_email: Optional[str] = Field(None, max_length=255)


class OrderItemOut(BaseModel):
    product_id: int
    qty: int
    unit_price: float
    line_total: float

    class Config:
        from_attributes = True  # pydantic v2 replacement for orm_mode


class OrderOut(BaseModel):
    id: int
    total_amount: float
    currency: str
    items: List[OrderItemOut]

    class Config:
        from_attributes = True


# ---------- Helpers ----------


def _load_products_map(db: Session, product_ids: List[int]) -> dict[int, Product]:
    if not product_ids:
        return {}

    stmt = select(Product).where(Product.id.in_(product_ids))
    rows = db.execute(stmt).scalars().all()
    return {p.id: p for p in rows}


# ---------- Endpoints ----------


@router.post(
    "/",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must contain at least one item.",
        )

    # Load products, validate they all exist and are in stock
    product_ids = [item.product_id for item in payload.items]
    products_map = _load_products_map(db, product_ids)

    if len(products_map) != len(set(product_ids)):
        missing = sorted(set(product_ids) - set(products_map.keys()))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown product IDs: {missing}",
        )

    total = 0.0
    currency = "EUR"

    # Compute totals
    for item in payload.items:
        product = products_map[item.product_id]
        if not product.in_stock:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product.name}' is out of stock.",
            )
        total += float(product.price) * item.qty
        currency = product.currency or currency

    # Create order row
    order = Order(
        total_amount=total,
        currency=currency,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
    )
    db.add(order)
    db.flush()  # get order.id without committing yet

    # Create items
    for item in payload.items:
        product = products_map[item.product_id]
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                qty=item.qty,
                unit_price=float(product.price),
            )
        )

    db.commit()
    db.refresh(order)

    # Build response
    items_out: List[OrderItemOut] = []
    for item in payload.items:
        product = products_map[item.product_id]
        line_total = float(product.price) * item.qty
        items_out.append(
            OrderItemOut(
                product_id=product.id,
                qty=item.qty,
                unit_price=float(product.price),
                line_total=line_total,
            )
        )

    return OrderOut(
        id=order.id,
        total_amount=order.total_amount,
        currency=order.currency,
        items=items_out,
    )


@router.get("/", response_model=List[OrderOut])
def list_orders(db: Session = Depends(get_db)):
    stmt = select(Order).order_by(Order.created_at.desc())
    orders = db.execute(stmt).scalars().all()

    if not orders:
        return []

    # Load items
    stmt_items = select(OrderItem).where(OrderItem.order_id.in_([o.id for o in orders]))
    items = db.execute(stmt_items).scalars().all()

    # Group items by order_id
    items_by_order: dict[int, List[OrderItem]] = {}
    for item in items:
        items_by_order.setdefault(item.order_id, []).append(item)

    results: List[OrderOut] = []
    for o in orders:
        order_items_out: List[OrderItemOut] = []
        for item in items_by_order.get(o.id, []):
            order_items_out.append(
                OrderItemOut(
                    product_id=item.product_id,
                    qty=item.qty,
                    unit_price=float(item.unit_price),
                    line_total=float(item.unit_price) * item.qty,
                )
            )

        results.append(
            OrderOut(
                id=o.id,
                total_amount=float(o.total_amount),
                currency=o.currency,
                items=order_items_out,
            )
        )

    return results
