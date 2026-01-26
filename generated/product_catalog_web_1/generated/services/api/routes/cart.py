from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from .products import Product, PRODUCTS  # reuse existing product model + list


router = APIRouter(prefix="/cart", tags=["cart"])


class CartItem(BaseModel):
    product_id: int = Field(..., description="ID from /products")
    quantity: int = Field(..., gt=0, description="Quantity > 0")


class CartRequest(BaseModel):
    items: List[CartItem]


class CartLine(BaseModel):
    product: Product
    quantity: int
    line_total: float


class CartResponse(BaseModel):
    items: List[CartLine]
    total_items: int
    total_price: float
    currency: str


def _get_product_by_id(pid: int) -> Product:
    for p in PRODUCTS:
        if p.id == pid:
            return p
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unknown product_id={pid}",
    )


@router.post("", response_model=CartResponse)
async def price_cart(payload: CartRequest) -> CartResponse:
    """
    Simple cart pricing endpoint.

    - Validates product IDs against PRODUCTS.
    - Computes line totals + grand total.
    - Does **not** persist anything (pure pricing/preview).
    """
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart cannot be empty",
        )

    lines: List[CartLine] = []
    total_items = 0
    total_price = 0.0
    currency = "EUR"

    for item in payload.items:
        product = _get_product_by_id(item.product_id)
        line_total = product.price * item.quantity
        total_items += item.quantity
        total_price += line_total
        currency = product.currency or currency

        lines.append(
            CartLine(
                product=product,
                quantity=item.quantity,
                line_total=line_total,
            )
        )

    return CartResponse(
        items=lines,
        total_items=total_items,
        total_price=round(total_price, 2),
        currency=currency,
    )
