"""The health route answers without keys or network access."""

from fastapi.testclient import TestClient

from api.main import app
from ersatz import __version__


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}
