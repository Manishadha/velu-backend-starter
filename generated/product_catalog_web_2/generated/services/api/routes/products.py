from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter(prefix="/products", tags=["products"])


class Product(BaseModel):
    id: int
    name: str
    price: float
    currency: str = "EUR"
    category: str
    in_stock: bool = True
    image_url: str | None = None
    description: str | None = None


PRODUCTS: List[Product] = [
    Product(
        id=1,
        name="Classic T-Shirt",
        price=19.99,
        currency="EUR",
        category="Clothing",
        in_stock=True,
        image_url="https://placehold.co/400x400?text=T-Shirt",
        description="Soft cotton tee with your brand logo.",
    ),
    Product(
        id=2,
        name="Premium Hoodie",
        price=49.99,
        currency="EUR",
        category="Clothing",
        in_stock=True,
        image_url="https://placehold.co/400x400?text=Hoodie",
        description="Warm hoodie for colder days.",
    ),
    Product(
        id=3,
        name="Sneakers",
        price=79.00,
        currency="EUR",
        category="Shoes",
        in_stock=False,
        image_url="https://placehold.co/400x400?text=Sneakers",
        description="Comfortable sneakers, currently out of stock.",
    ),
    Product(
        id=4,
        name="Leather Backpack",
        price=99.00,
        currency="EUR",
        category="Accessories",
        in_stock=True,
        image_url="https://placehold.co/400x400?text=Backpack",
        description="Everyday backpack with space for laptop and essentials.",
    ),
    Product(
        id=5,
        name="Baseball Cap",
        price=15.00,
        currency="EUR",
        category="Accessories",
        in_stock=True,
        image_url="https://placehold.co/400x400?text=Cap",
        description="Adjustable cap with embroidered logo.",
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
async def list_products(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
) -> list[Product]:
    items = PRODUCTS

    if category:
        c = category.strip().lower()
        items = [p for p in items if p.category.strip().lower() == c]

    if q:
        needle = q.strip().lower()
        items = [
            p
            for p in items
            if needle in p.name.lower()
            or (p.description and needle in p.description.lower())
            or needle in p.category.lower()
        ]

    return items


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: int) -> Product:
    return _get_product_or_404(product_id)
