"""Unit tests for domain QR code generation and logo overlay service."""

import io
import pytest
from PIL import Image

from services.qr_generator import (
    DrawerType,
    EyeDrawerType,
    GradientType,
    InvalidColorError,
    InvalidDrawerError,
    InvalidGradientError,
    InvalidLogoError,
    QRCodeGeneratorError,
    QRCodeService,
)


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

    def test_generate_qr_with_custom_hex_colors(self, service: QRCodeService) -> None:
        """Verify QR generation succeeds with valid hex colors."""
        output = service.generate(
            url="https://antigravity.dev",
            fill_color="#1A56DB",
            back_color="#F3F4F6",
        )
        assert output is not None
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"

    def test_generate_qr_with_named_css_colors(self, service: QRCodeService) -> None:
        """Verify QR generation succeeds with named CSS colors."""
        output = service.generate(
            url="https://antigravity.dev",
            fill_color="navy",
            back_color="ghostwhite",
        )
        assert output is not None
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"

    def test_invalid_fill_color_raises_invalid_color_error(
        self, service: QRCodeService
    ) -> None:
        """Verify unresolvable fill color raises InvalidColorError."""
        with pytest.raises(InvalidColorError, match="Invalid fill_color"):
            service.generate(url="https://antigravity.dev", fill_color="not_a_color")

    def test_invalid_back_color_raises_invalid_color_error(
        self, service: QRCodeService
    ) -> None:
        """Verify unresolvable back color raises InvalidColorError."""
        with pytest.raises(InvalidColorError, match="Invalid back_color"):
            service.generate(url="https://antigravity.dev", back_color="xyz123")

    def test_empty_color_string_raises_invalid_color_error(
        self, service: QRCodeService
    ) -> None:
        """Verify empty color string raises InvalidColorError."""
        with pytest.raises(InvalidColorError, match="cannot be empty"):
            service.generate(url="https://antigravity.dev", fill_color="   ")

    def test_matching_colors_raises_invalid_color_error(
        self, service: QRCodeService
    ) -> None:
        """Verify identical fill and back colors raise contrast InvalidColorError."""
        with pytest.raises(InvalidColorError, match="cannot be identical"):
            service.generate(
                url="https://antigravity.dev",
                fill_color="#000000",
                back_color="black",
            )

    @pytest.mark.parametrize(
        "drawer_name",
        ["circle", "rounded", "gapped_square", "vertical_bars", "horizontal_bars"],
    )
    def test_generate_with_styled_module_drawers(
        self, service: QRCodeService, drawer_name: str
    ) -> None:
        """Verify each supported module drawer generates a valid PNG."""
        output = service.generate(
            url="https://antigravity.dev",
            drawer=drawer_name,
        )
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"
        assert img.width > 0

    @pytest.mark.parametrize("eye_drawer_name", ["circle", "rounded", "gapped_square"])
    def test_generate_with_styled_eye_drawers(
        self, service: QRCodeService, eye_drawer_name: str
    ) -> None:
        """Verify custom eye drawers composite properly."""
        output = service.generate(
            url="https://antigravity.dev",
            drawer="circle",
            eye_drawer=eye_drawer_name,
        )
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"

    def test_invalid_drawer_raises_invalid_drawer_error(
        self, service: QRCodeService
    ) -> None:
        """Verify unknown module drawer raises InvalidDrawerError."""
        with pytest.raises(InvalidDrawerError, match="Unsupported module drawer"):
            service.generate(url="https://antigravity.dev", drawer="hexagon")

    def test_invalid_eye_drawer_raises_invalid_drawer_error(
        self, service: QRCodeService
    ) -> None:
        """Verify unknown eye drawer raises InvalidDrawerError."""
        with pytest.raises(InvalidDrawerError, match="Unsupported eye drawer"):
            service.generate(url="https://antigravity.dev", eye_drawer="diamond")

    @pytest.mark.parametrize("gradient_type", ["radial", "horizontal", "vertical"])
    def test_generate_with_gradients(
        self, service: QRCodeService, gradient_type: str
    ) -> None:
        """Verify linear and radial gradients generate valid images."""
        output = service.generate(
            url="https://antigravity.dev",
            gradient_type=gradient_type,
            gradient_start_color="#7B1FA2",
            gradient_end_color="#00BCD4",
        )
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"

    def test_gradient_missing_end_color_raises_error(
        self, service: QRCodeService
    ) -> None:
        """Verify gradient without end color raises InvalidGradientError."""
        with pytest.raises(InvalidGradientError, match="gradient_end_color must be specified"):
            service.generate(
                url="https://antigravity.dev",
                gradient_type="radial",
                gradient_start_color="#FF0000",
            )

    def test_invalid_gradient_type_raises_error(
        self, service: QRCodeService
    ) -> None:
        """Verify unknown gradient type raises InvalidGradientError."""
        with pytest.raises(InvalidGradientError, match="Unsupported gradient_type"):
            service.generate(
                url="https://antigravity.dev",
                gradient_type="diagonal",
                gradient_start_color="#FF0000",
                gradient_end_color="#0000FF",
            )

    def test_generate_transparent_background(self, service: QRCodeService) -> None:
        """Verify transparent background produces an RGBA PNG with 0-alpha corner."""
        output = service.generate(
            url="https://antigravity.dev",
            drawer="circle",
            fill_color="#1A56DB",
            transparent_background=True,
        )
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"
        assert img.mode == "RGBA"
        # Corner quiet zone pixel must have alpha 0
        corner_pixel = img.getpixel((0, 0))
        assert corner_pixel[3] == 0

    def test_generate_combined_styles_with_logo(self, service: QRCodeService) -> None:
        """Verify combination of rounded drawer, radial gradient, transparency, and logo."""
        logo_bytes = create_synthetic_image_bytes(mode="RGBA", size=(50, 50))
        output = service.generate(
            url="https://antigravity.dev",
            drawer="rounded",
            eye_drawer="circle",
            gradient_type="radial",
            gradient_start_color="#9C27B0",
            gradient_end_color="#E91E63",
            transparent_background=True,
            logo_bytes=logo_bytes,
            add_logo_background=True,
        )
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"
        assert img.mode == "RGBA"
        # Corner remains transparent
        assert img.getpixel((0, 0))[3] == 0

    def test_generate_with_enum_instances(self, service: QRCodeService) -> None:
        """Verify passing DrawerType, EyeDrawerType, and GradientType Enum instances works."""
        output = service.generate(
            url="https://antigravity.dev",
            drawer=DrawerType.CIRCLE,
            eye_drawer=EyeDrawerType.ROUNDED,
            gradient_type=GradientType.RADIAL,
            gradient_start_color="#123456",
            gradient_end_color="#abcdef",
        )
        assert output is not None
        output.seek(0)
        img = Image.open(output)
        assert img.format == "PNG"

