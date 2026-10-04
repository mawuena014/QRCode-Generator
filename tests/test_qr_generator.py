"""Unit tests for domain QR code generation and logo overlay service."""

import base64
import io
import pytest
from PIL import Image

from schema import QRCodeRequest
from services.qr_generator import InvalidLogoError, QRCodeService


def create_synthetic_image_b64(
    mode: str = "RGBA",
    size: tuple[int, int] = (64, 64),
    color: tuple = (255, 0, 0, 255),
    image_format: str = "PNG",
) -> str:
    """Helper to generate a base64 encoded synthetic test image."""
    img = Image.new(mode, size, color=color)
    buffer = io.BytesIO()
    img.save(buffer, format=image_format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class TestQRCodeService:
    """Unit test cases for QRCodeService."""

    @pytest.fixture
    def service(self) -> QRCodeService:
        return QRCodeService()

    def test_generate_standard_qr_without_logo(self, service: QRCodeService) -> None:
        """Verify standard QR generation without logo outputs a valid PNG image."""
        request = QRCodeRequest(url="https://antigravity.dev")
        output = service.generate(request)

        assert output is not None
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"
        assert img.width > 0
        assert img.height > 0

    def test_generate_qr_with_rgba_logo(self, service: QRCodeService) -> None:
        """Verify QR generation successfully composites an RGBA PNG logo."""
        logo_b64 = create_synthetic_image_b64(mode="RGBA", size=(50, 50))
        request = QRCodeRequest(
            url="https://antigravity.dev",
            logo_base64=logo_b64,
            logo_size_ratio=0.25,
            add_logo_background=True,
        )
        output = service.generate(request)

        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"
        assert img.mode == "RGBA"

    def test_generate_qr_with_rgb_jpeg_logo(self, service: QRCodeService) -> None:
        """Verify QR generation converts and composites an RGB JPEG logo."""
        logo_b64 = create_synthetic_image_b64(
            mode="RGB",
            size=(40, 40),
            color=(0, 255, 0),
            image_format="JPEG",
        )
        request = QRCodeRequest(
            url="https://antigravity.dev",
            logo_base64=logo_b64,
            add_logo_background=False,
        )
        output = service.generate(request)

        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"

    def test_generate_qr_with_data_uri_prefix(self, service: QRCodeService) -> None:
        """Verify that data:image/png;base64 prefixes are cleanly parsed."""
        raw_b64 = create_synthetic_image_b64()
        data_uri = f"data:image/png;base64,{raw_b64}"
        request = QRCodeRequest(url="https://antigravity.dev", logo_base64=data_uri)
        output = service.generate(request)

        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"

    def test_invalid_base64_raises_invalid_logo_error(self, service: QRCodeService) -> None:
        """Verify malformed base64 strings raise InvalidLogoError."""
        request = QRCodeRequest(
            url="https://antigravity.dev",
            logo_base64="not-valid-base64!@@#",
        )
        with pytest.raises(InvalidLogoError, match="Malformed base64 logo string"):
            service.generate(request)

    def test_non_image_payload_raises_invalid_logo_error(self, service: QRCodeService) -> None:
        """Verify non-image base64 text payload raises InvalidLogoError."""
        text_b64 = base64.b64encode(b"This is just plain text, not an image").decode("utf-8")
        request = QRCodeRequest(url="https://antigravity.dev", logo_base64=text_b64)
        with pytest.raises(InvalidLogoError, match="Invalid or corrupted image format"):
            service.generate(request)

    def test_empty_payload_raises_invalid_logo_error(self, service: QRCodeService) -> None:
        """Verify empty decoded payload raises InvalidLogoError."""
        request = QRCodeRequest(url="https://antigravity.dev", logo_base64="")
        with pytest.raises(InvalidLogoError, match="Decoded logo payload is empty"):
            service.generate(request)

    def test_oversized_payload_raises_invalid_logo_error(
        self, monkeypatch: pytest.MonkeyPatch, service: QRCodeService
    ) -> None:
        """Verify payload exceeding MAX_RAW_IMAGE_BYTES raises InvalidLogoError."""
        monkeypatch.setattr(service, "MAX_RAW_IMAGE_BYTES", 10)
        img_b64 = create_synthetic_image_b64()
        request = QRCodeRequest(url="https://antigravity.dev", logo_base64=img_b64)
        with pytest.raises(InvalidLogoError, match="Logo payload exceeds maximum allowed size"):
            service.generate(request)
