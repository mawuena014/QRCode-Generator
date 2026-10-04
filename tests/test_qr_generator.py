"""Unit tests for domain QR code generation and logo overlay service."""

import io
import pytest
from PIL import Image

from services.qr_generator import InvalidLogoError, QRCodeGeneratorError, QRCodeService


def create_synthetic_image_bytes(
    mode: str = "RGBA",
    size: tuple[int, int] = (64, 64),
    color: tuple = (255, 0, 0, 255),
    image_format: str = "PNG",
) -> bytes:
    """Helper to generate raw bytes for a synthetic test image."""
    img = Image.new(mode, size, color=color)
    buffer = io.BytesIO()
    img.save(buffer, format=image_format)
    return buffer.getvalue()


class TestQRCodeService:
    """Unit test cases for QRCodeService."""

    @pytest.fixture
    def service(self) -> QRCodeService:
        return QRCodeService()

    def test_generate_standard_qr_without_logo(self, service: QRCodeService) -> None:
        """Verify standard QR generation without logo outputs a valid PNG image."""
        output = service.generate(url="https://antigravity.dev")

        assert output is not None
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"
        assert img.width > 0
        assert img.height > 0

    def test_generate_qr_with_rgba_logo_bytes(self, service: QRCodeService) -> None:
        """Verify QR generation successfully composites raw RGBA PNG bytes."""
        logo_bytes = create_synthetic_image_bytes(mode="RGBA", size=(50, 50))
        output = service.generate(
            url="https://antigravity.dev",
            logo_bytes=logo_bytes,
            logo_size_ratio=0.25,
            add_logo_background=True,
        )

        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"
        assert img.mode == "RGBA"

    def test_generate_qr_with_rgb_jpeg_logo_bytes(self, service: QRCodeService) -> None:
        """Verify QR generation converts and composites raw RGB JPEG bytes."""
        logo_bytes = create_synthetic_image_bytes(
            mode="RGB",
            size=(40, 40),
            color=(0, 255, 0),
            image_format="JPEG",
        )
        output = service.generate(
            url="https://antigravity.dev",
            logo_bytes=logo_bytes,
            add_logo_background=False,
        )

        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"

    def test_empty_logo_bytes_raises_invalid_logo_error(self, service: QRCodeService) -> None:
        """Verify 0-byte payload raises InvalidLogoError."""
        with pytest.raises(InvalidLogoError, match="Uploaded logo file is empty"):
            service.generate(url="https://antigravity.dev", logo_bytes=b"")

    def test_corrupted_image_bytes_raises_invalid_logo_error(self, service: QRCodeService) -> None:
        """Verify non-image bytes raise InvalidLogoError."""
        with pytest.raises(InvalidLogoError, match="Invalid or corrupted image format"):
            service.generate(url="https://antigravity.dev", logo_bytes=b"not an image file")

    def test_oversized_payload_raises_invalid_logo_error(
        self, monkeypatch: pytest.MonkeyPatch, service: QRCodeService
    ) -> None:
        """Verify payload exceeding MAX_RAW_IMAGE_BYTES raises InvalidLogoError."""
        monkeypatch.setattr(service, "MAX_RAW_IMAGE_BYTES", 10)
        logo_bytes = create_synthetic_image_bytes()
        with pytest.raises(InvalidLogoError, match="Logo file exceeds maximum allowed size"):
            service.generate(url="https://antigravity.dev", logo_bytes=logo_bytes)

    def test_empty_url_raises_error(self, service: QRCodeService) -> None:
        """Verify empty url string raises QRCodeGeneratorError."""
        with pytest.raises(QRCodeGeneratorError, match="URL/text content cannot be empty"):
            service.generate(url="")
