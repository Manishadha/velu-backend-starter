from tshirt_shop_v2 import greet


def test_greet_pipeline():
    assert greet("Velu") == "Hello, Velu!"
