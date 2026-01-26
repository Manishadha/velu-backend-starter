from __future__ import annotations

from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="inventory_service")

# --- CORS so the React console (Vite) can talk to us -------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ------------------------------------------------------------------


class ItemCreate(BaseModel):
    sku: str
    name: str
    quantity: int = 0
    reorder_level: int = 0


class Item(ItemCreate):
    id: int


class QuantityUpdate(BaseModel):
    delta: int


# --- In-memory store for demo ------------------------------------------------

ITEMS: dict[int, Item] = {}
NEXT_ID: int = 1


def _next_id() -> int:
    global NEXT_ID
    i = NEXT_ID
    NEXT_ID += 1
    return i


# --- Health ------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    total_items = len(ITEMS)
    total_quantity = sum(it.quantity for it in ITEMS.values())
    return {
        "ok": True,
        "service": "inventory",
        "total_items": total_items,
        "total_quantity": total_quantity,
    }


# --- CRUD-ish endpoints ------------------------------------------------------


@app.get("/items", response_model=List[Item])
def list_items() -> list[Item]:
    return list(ITEMS.values())


@app.post("/items", response_model=Item)
def create_item(payload: ItemCreate) -> Item:
    item_id = _next_id()
    item = Item(id=item_id, **payload.dict())
    ITEMS[item_id] = item
    return item


@app.patch("/items/{item_id}", response_model=Item)
def adjust_quantity(item_id: int, payload: QuantityUpdate) -> Item:
    """
    Adjust quantity by payload.delta (can be + or -).
    Body must be JSON: {"delta": 1} or {"delta": -3}.
    """
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="item_not_found")

    delta = payload.delta
    item = ITEMS[item_id]
    new_q = item.quantity + delta

    if new_q < 0:
        raise HTTPException(
            status_code=400,
            detail="quantity_cannot_be_negative",
        )

    item.quantity = new_q
    ITEMS[item_id] = item
    return item


@app.get("/items-low-stock", response_model=List[Item])
def list_low_stock() -> list[Item]:
    """Return items where quantity <= reorder_level."""
    return [it for it in ITEMS.values() if it.reorder_level > 0 and it.quantity <= it.reorder_level]
