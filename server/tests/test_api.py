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


def test_predict_rejects_mismatched_kinds(client):
    image_bytes = io.BytesIO()
    Image.new("RGB", (50, 50), color="green").save(image_bytes, format="JPEG")
    image_bytes.seek(0)

    # 1 file, but 2 kinds
    response = client.post(
        "/api/v1/predict",
        files=[("files", ("test.jpg", image_bytes, "image/jpeg"))],
        data={
            "kinds": ["exterior", "interior"],
            "features": "{}",
            "model": "classifier",
        },
    )
    assert response.status_code == 400
    assert "Number of photos must match" in response.json()["detail"]


def test_predict_rejects_disallowed_mime(client):
    fake_doc = io.BytesIO(b"Hello world")
    response = client.post(
        "/api/v1/predict",
        files=[("files", ("test.pdf", fake_doc, "application/pdf"))],
        data={
            "kinds": ["exterior"],
            "features": "{}",
            "model": "classifier",
        },
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_predict_rejects_corrupted_image(client):
    corrupted = io.BytesIO(b"corrupted-image-data-that-is-not-valid")
    response = client.post(
        "/api/v1/predict",
        files=[("files", ("corrupt.jpg", corrupted, "image/jpeg"))],
        data={
            "kinds": ["exterior"],
            "features": "{}",
            "model": "classifier",
        },
    )
    assert response.status_code == 400
    assert "corrupted or not a valid image" in response.json()["detail"]


def test_predict_rejects_oversized_file(client):
    # 10 MB + 1 byte
    oversized = io.BytesIO(b"0" * (10 * 1024 * 1024 + 1))
    response = client.post(
        "/api/v1/predict",
        files=[("files", ("large.jpg", oversized, "image/jpeg"))],
        data={
            "kinds": ["exterior"],
            "features": "{}",
            "model": "classifier",
        },
    )
    assert response.status_code == 400
    assert "exceeds maximum allowed size" in response.json()["detail"]


def test_predict_rejects_invalid_features_json(client):
    image_bytes = io.BytesIO()
    Image.new("RGB", (50, 50), color="yellow").save(image_bytes, format="JPEG")
    image_bytes.seek(0)

    response = client.post(
        "/api/v1/predict",
        files=[("files", ("test.jpg", image_bytes, "image/jpeg"))],
        data={
            "kinds": ["exterior"],
            "features": "{invalid_json: true}",
            "model": "classifier",
        },
    )
    assert response.status_code == 400
    assert "Features must be a valid JSON object" in response.json()["detail"]


def test_predict_rejects_invalid_model(client):
    image_bytes = io.BytesIO()
    Image.new("RGB", (50, 50), color="orange").save(image_bytes, format="JPEG")
    image_bytes.seek(0)

    response = client.post(
        "/api/v1/predict",
        files=[("files", ("test.jpg", image_bytes, "image/jpeg"))],
        data={
            "kinds": ["exterior"],
            "features": "{}",
            "model": "non_existent_model",
        },
    )
    assert response.status_code == 400
    assert "Invalid model" in response.json()["detail"]
