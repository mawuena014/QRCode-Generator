"""Integration tests for FastAPI endpoints with multipart/form-data upload."""

import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from main import app


def create_test_image_bytes(
    mode: str = "RGBA",
    size: tuple[int, int] = (32, 32),
    color: tuple = (0, 0, 255, 255),
    image_format: str = "PNG",
) -> bytes:
    """Helper generating synthetic image bytes."""
    img = Image.new(mode, size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=image_format)
    return buf.getvalue()


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
    """Ensure standard form request without file upload returns image/png."""
    response = client.post("/generate_qr", data={"url": "https://antigravity.dev"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0


def test_generate_qr_with_png_file_upload(client: TestClient) -> None:
    """Ensure /generate_qr with multipart PNG file upload succeeds."""
    png_bytes = create_test_image_bytes(mode="RGBA", image_format="PNG")
    response = client.post(
        "/generate_qr",
        data={
            "url": "https://antigravity.dev",
            "logo_size_ratio": "0.20",
            "add_logo_background": "true",
        },
        files={"logo": ("logo.png", png_bytes, "image/png")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

    # Verify output stream is a valid PNG
    img = Image.open(io.BytesIO(response.content))
    assert img.format == "PNG"


def test_generate_qr_with_jpeg_file_upload(client: TestClient) -> None:
    """Ensure /generate_qr with multipart JPEG file upload succeeds."""
    jpeg_bytes = create_test_image_bytes(
        mode="RGB",
        color=(255, 255, 0),
        image_format="JPEG",
    )
    response = client.post(
        "/generate_qr",
        data={"url": "https://antigravity.dev"},
        files={"logo": ("icon.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_generate_qr_with_unselected_file_input(client: TestClient) -> None:
    """Ensure browser submitting empty unselected file field does not fail."""
    response = client.post(
        "/generate_qr",
        data={"url": "https://antigravity.dev"},
        files={"logo": ("", b"", "application/octet-stream")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


def test_generate_qr_with_corrupt_file(client: TestClient) -> None:
    """Ensure corrupted image file upload returns 400 Bad Request."""
    response = client.post(
        "/generate_qr",
        data={"url": "https://antigravity.dev"},
        files={"logo": ("corrupt.png", b"this is not image data", "image/png")},
    )
    assert response.status_code == 400
    assert "Invalid or corrupted image format" in response.json()["detail"]


def test_generate_qr_form_validation_bounds(client: TestClient) -> None:
    """Ensure form parameter bounds are defensively validated."""
    # Logo size ratio > 0.30 should be rejected
    response = client.post(
        "/generate_qr",
        data={"url": "https://antigravity.dev", "logo_size_ratio": "0.45"},
    )
    assert response.status_code == 422

    # Empty URL should be rejected
    response = client.post(
        "/generate_qr",
        data={"url": ""},
    )
    assert response.status_code == 422
