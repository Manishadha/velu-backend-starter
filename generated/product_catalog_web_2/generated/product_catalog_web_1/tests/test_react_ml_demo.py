from react_ml_demo import greet


def test_greet_pipeline():
    assert greet("Velu") == "Hello, Velu!"
