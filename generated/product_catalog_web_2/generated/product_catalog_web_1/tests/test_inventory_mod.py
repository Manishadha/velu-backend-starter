# tests/test_inventory_mod.py
from inventory_mod import (
    greet,
    create_inventory,
    add_item,
    get_item,
    adjust_stock,
    set_stock,
    low_stock,
    total_quantity,
)


def test_greet_pipeline():
    # keep the original greet test so pipeline-style expectations still hold
    assert greet("Velu") == "Hello, Velu!"


def test_add_and_get_item():
    inv = create_inventory()
    add_item(inv, sku="SKU1", name="Keyboard", quantity=5, reorder_level=2)

    item = get_item(inv, "SKU1")
    assert item is not None
    assert item.sku == "SKU1"
    assert item.name == "Keyboard"
    assert item.quantity == 5
    assert item.reorder_level == 2


def test_adjust_stock_existing_item():
    inv = create_inventory()
    add_item(inv, sku="SKU1", name="Keyboard", quantity=5, reorder_level=2)

    updated = adjust_stock(inv, "SKU1", +3)
    assert updated.quantity == 8

    updated = adjust_stock(inv, "SKU1", -2)
    assert updated.quantity == 6

    # inventory dict is kept in sync
    assert inv["SKU1"].quantity == 6


def test_adjust_stock_creates_item_if_missing():
    inv = create_inventory()
    updated = adjust_stock(inv, "NEW", +10)

    assert updated.sku == "NEW"
    assert updated.quantity == 10
    assert "NEW" in inv


def test_set_stock_creates_item_if_missing_and_overwrites():
    inv = create_inventory()
    set_stock(inv, "SKU1", 5)
    assert inv["SKU1"].quantity == 5

    set_stock(inv, "SKU1", 2)
    assert inv["SKU1"].quantity == 2


def test_low_stock_filters_items():
    inv = create_inventory()
    add_item(inv, "A", "Item A", quantity=1, reorder_level=2)  # low
    add_item(inv, "B", "Item B", quantity=5, reorder_level=2)  # ok
    add_item(inv, "C", "Item C", quantity=2, reorder_level=2)  # low

    lows = {item.sku for item in low_stock(inv)}
    assert lows == {"A", "C"}


def test_total_quantity():
    inv = create_inventory()
    add_item(inv, "A", "Item A", quantity=1)
    add_item(inv, "B", "Item B", quantity=4)
    add_item(inv, "C", "Item C", quantity=10)

    assert total_quantity(inv) == 15
