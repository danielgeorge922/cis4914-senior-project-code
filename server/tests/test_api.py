import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOCK_INFERENCE", "true")
    # Reload settings with mock inference enabled
    from app import main
    main.settings = Settings(mock_inference=True)
    with TestClient(app) as test_client:
        yield test_client


def test_predict_endpoint_mock(client):
    # Create a small valid test JPEG in-memory
    image_bytes = io.BytesIO()
    Image.new("RGB", (100, 100), color="orange").save(image_bytes, format="JPEG")
    image_bytes.seek(0)

    response = client.post(
        "/api/v1/predict",
        files=[("files", ("test.jpg", image_bytes, "image/jpeg"))],
        data={
            "kinds": ["fruit"],
            "features": "{}",
            "model": "classifier",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["demo"] is True
    assert len(data["predictions"]) > 0
    assert "name" in data["predictions"][0]
    assert "matchScore" in data["predictions"][0]
