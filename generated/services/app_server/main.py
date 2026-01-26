from fastapi import FastAPI  # noqa: F401
from generated.services.api.app import app as _base


def create_app():
    return _base


app = create_app()
