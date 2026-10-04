"""Integration tests for FastAPI endpoints."""

import base64
import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app


def create_test_logo_b64() -> str:
    """Helper generating a valid base64 PNG icon."""
    img = Image.new("RGBA", (32, 32), color=(0, 0, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a TestClient for the FastAPI app."""
    return TestClient(app)


def test_health_check_endpoint(client: TestClient) -> None:
    """Ensure /health returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "qr-code-generator"}


def test_generate_qr_without_logo(client: TestClient) -> None:
    """Ensure standard /generate_qr request succeeds and returns image/png."""
    response = client.post("/generate_qr", json={"url": "https://antigravity.dev"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0


def test_generate_qr_with_valid_logo(client: TestClient) -> None:
    """Ensure /generate_qr with base64 logo succeeds and returns image/png."""
    logo_b64 = create_test_logo_b64()
    response = client.post(
        "/generate_qr",
        json={
            "url": "https://antigravity.dev",
            "logo_base64": logo_b64,
            "logo_size_ratio": 0.20,
            "add_logo_background": True,
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Verify response body can be parsed as a PNG
    img = Image.open(io.BytesIO(response.content))
    assert img.format == "PNG"


def test_generate_qr_with_data_uri_logo(client: TestClient) -> None:
    """Ensure data URI format works cleanly via HTTP endpoint."""
    logo_b64 = create_test_logo_b64()
    data_uri = f"data:image/png;base64,{logo_b64}"
    response = client.post(
        "/generate_qr",
        json={"url": "https://antigravity.dev", "logo_base64": data_uri},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_generate_qr_with_invalid_logo_base64(client: TestClient) -> None:
    """Ensure malformed base64 logo returns 400 Bad Request."""
    response = client.post(
        "/generate_qr",
        json={"url": "https://antigravity.dev", "logo_base64": "invalid_base64!#%"},
    )
    assert response.status_code == 400
    assert "Malformed base64" in response.json()["detail"]


def test_generate_qr_with_non_image_payload(client: TestClient) -> None:
    """Ensure valid base64 that is not an image returns 400 Bad Request."""
    text_b64 = base64.b64encode(b"Not an image at all").decode("utf-8")
    response = client.post(
        "/generate_qr",
        json={"url": "https://antigravity.dev", "logo_base64": text_b64},
    )
    assert response.status_code == 400
    assert "Invalid or corrupted image format" in response.json()["detail"]


def test_generate_qr_validation_bounds(client: TestClient) -> None:
    """Ensure schema validation rejects invalid ratio bounds."""
    # Logo size ratio > 0.30 should be rejected by Pydantic
    response = client.post(
        "/generate_qr",
        json={"url": "https://antigravity.dev", "logo_size_ratio": 0.50},
    )
    assert response.status_code == 422

    # Empty URL should be rejected
    response = client.post("/generate_qr", json={"url": ""})
    assert response.status_code == 422
