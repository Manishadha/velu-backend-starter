# src/inventory_mod.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


def greet(name: str) -> str:
    """Simple greeter used by smoke tests."""
    return f"Hello, {name}!"


@dataclass
class Item:
    sku: str
    name: str
    quantity: int = 0
    reorder_level: int = 0


# Inventory is just a mapping sku -> Item
Inventory = Dict[str, Item]


def create_inventory() -> Inventory:
    """
    Create a new, empty in-memory inventory.

    The service keeps its own ID mapping; here we only care about SKU keys.
    """
    return {}


def add_item(
    inv: Inventory,
    sku: str,
    name: str,
    quantity: int = 0,
    reorder_level: int = 0,
) -> Item:
    """
    Create or overwrite an item for the given SKU in the inventory.

    Supports positional (inv, "SKU1", "Name", quantity=..., reorder_level=...).
    """
    item = Item(
        sku=str(sku),
        name=str(name),
        quantity=int(quantity),
        reorder_level=int(reorder_level),
    )
    inv[item.sku] = item
    return item


def get_item(inv: Inventory, sku: str) -> Optional[Item]:
    """
    Look up an item by SKU. Returns None if not present.
    """
    return inv.get(str(sku))


def set_stock(inv: Inventory, sku: str, quantity: int) -> Item:
    """
    Set the absolute stock quantity for an item.

    If the SKU does not exist yet, create it with:
      - name = sku
      - given quantity
      - reorder_level = 0
    """
    key = str(sku)
    quantity = int(quantity)

    item = inv.get(key)
    if item is None:
        item = Item(sku=key, name=key, quantity=quantity, reorder_level=0)
        inv[key] = item
    else:
        item.quantity = quantity
    return item


def adjust_stock(inv: Inventory, sku: str, delta: int) -> Item:
    """
    Adjust the stock by a delta (may be negative).

    If the SKU does not exist yet, create it with:
      - name = sku
      - quantity = delta
      - reorder_level = 0
    """
    key = str(sku)
    delta = int(delta)

    item = inv.get(key)
    if item is None:
        item = Item(sku=key, name=key, quantity=delta, reorder_level=0)
        inv[key] = item
    else:
        item.quantity = int(item.quantity) + delta
    return item


def low_stock(inv: Inventory) -> List[Item]:
    """
    Return items where quantity <= reorder_level.
    """
    out: List[Item] = []
    for item in inv.values():
        if item.quantity <= item.reorder_level:
            out.append(item)
    return out


def total_quantity(inv: Inventory) -> int:
    """
    Sum of quantities across all items.
    """
    return sum(int(item.quantity) for item in inv.values())
