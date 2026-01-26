from shop_fastapi_next import greet


def test_greet_pipeline():
    assert greet("Velu") == "Hello, Velu!"
