from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/products", tags=["products"])


class Product(BaseModel):
    id: int
    name: str
    price: float
    currency: str = "EUR"
    in_stock: bool = True
    image_url: str | None = None
    description: str | None = None


# Simple in-memory catalog
PRODUCTS: List[Product] = [
    Product(
        id=1,
        name="Classic T-Shirt",
        price=19.99,
        currency="EUR",
        in_stock=True,
        image_url="https://placehold.co/400x400?text=T-Shirt",
        description="Soft cotton tee with your brand logo.",
    ),
    Product(
        id=2,
        name="Premium Hoodie",
        price=49.99,
        currency="EUR",
        in_stock=True,
        image_url="https://placehold.co/400x400?text=Hoodie",
        description="Warm hoodie for colder days.",
    ),
    Product(
        id=3,
        name="Sneakers",
        price=79.00,
        currency="EUR",
        in_stock=False,
        image_url="https://placehold.co/400x400?text=Sneakers",
        description="Comfortable sneakers, currently out of stock.",
    ),
]


def _get_product_or_404(product_id: int) -> Product:
    for p in PRODUCTS:
        if p.id == product_id:
            return p
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product {product_id} not found",
    )


@router.get("", response_model=list[Product])
async def list_products() -> list[Product]:
    return PRODUCTS


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: int) -> Product:
    return _get_product_or_404(product_id)
