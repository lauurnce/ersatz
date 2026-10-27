"""FastAPI application."""

from fastapi import FastAPI
from pydantic import BaseModel

from ersatz import __version__

app = FastAPI(title="Ersatz API", version=__version__)


class Health(BaseModel):
    status: str
    version: str


@app.get("/health")
def health() -> Health:
    """Report that the service is up. Makes no provider or model call."""
    return Health(status="ok", version=__version__)
