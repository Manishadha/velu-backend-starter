from multi_tenant import greet


def test_greet_pipeline():
    assert greet("Velu") == "Hello, Velu!"
