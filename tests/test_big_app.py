from big_app import greet


def test_greet_pipeline():
    assert greet("Velu") == "Hello, Velu!"
