"""QR Code generation and image processing domain service."""

import io
from typing import Optional
from PIL import Image, ImageDraw, UnidentifiedImageError
import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_M


class QRCodeGeneratorError(Exception):
    """Base exception for QR code generation failures."""


class InvalidLogoError(QRCodeGeneratorError):
    """Raised when a provided logo image cannot be decoded or validated."""


class QRCodeService:
    """Domain service responsible for rendering QR codes with optional center logos."""

    MAX_RAW_IMAGE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit to prevent DoS

    def generate(
        self,
        url: str,
        logo_bytes: Optional[bytes] = None,
        logo_size_ratio: float = 0.22,
        add_logo_background: bool = True,
        box_size: int = 10,
        border: int = 4,
    ) -> io.BytesIO:
        """Generate a QR code image as a PNG bytes buffer with optional center logo."""
        if not url or not url.strip():
            raise QRCodeGeneratorError("URL/text content cannot be empty.")

        error_correction = ERROR_CORRECT_H if logo_bytes is not None else ERROR_CORRECT_M

        qr = qrcode.QRCode(
            version=None,
            error_correction=error_correction,
            box_size=box_size,
            border=border,
        )
        qr.add_data(url)
        try:
            qr.make(fit=True)
        except Exception as exc:
            raise QRCodeGeneratorError(f"Failed to compile QR matrix: {exc}") from exc

        # Render base QR image and convert to RGBA for compositing
        base_qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_canvas: Image.Image = base_qr_img.convert("RGBA")

        if logo_bytes is not None:
            logo_img = self._validate_and_load_logo(logo_bytes)
            qr_canvas = self._overlay_center_logo(
                qr_canvas=qr_canvas,
                logo_img=logo_img,
                size_ratio=logo_size_ratio,
                add_background=add_logo_background,
            )

        output_buffer = io.BytesIO()
        qr_canvas.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        return output_buffer

    def _validate_and_load_logo(self, image_bytes: bytes) -> Image.Image:
        """Safely validate image integrity and load into an RGBA Pillow Image."""
        if len(image_bytes) == 0:
            raise InvalidLogoError("Uploaded logo file is empty.")

        if len(image_bytes) > self.MAX_RAW_IMAGE_BYTES:
            raise InvalidLogoError(
                f"Logo file exceeds maximum allowed size of {self.MAX_RAW_IMAGE_BYTES} bytes."
            )

        # Integrity verification
        try:
            verify_buffer = io.BytesIO(image_bytes)
            with Image.open(verify_buffer) as test_img:
                test_img.verify()
        except (UnidentifiedImageError, OSError, Exception) as exc:
            raise InvalidLogoError(f"Invalid or corrupted image format: {exc}") from exc

        # Re-open after verify() to get readable image instance
        load_buffer = io.BytesIO(image_bytes)
        try:
            logo = Image.open(load_buffer)
            logo.load()
            return logo.convert("RGBA")
        except Exception as exc:
            raise InvalidLogoError(f"Failed to load image canvas: {exc}") from exc

    def _overlay_center_logo(
        self,
        qr_canvas: Image.Image,
        logo_img: Image.Image,
        size_ratio: float,
        add_background: bool,
    ) -> Image.Image:
        """Scale and composite the logo onto the center of the QR canvas."""
        qr_w, qr_h = qr_canvas.size
        max_logo_dim = int(min(qr_w, qr_h) * size_ratio)

        if max_logo_dim <= 0:
            return qr_canvas

        orig_w, orig_h = logo_img.size
        if orig_w == 0 or orig_h == 0:
            return qr_canvas

        scale = min(max_logo_dim / orig_w, max_logo_dim / orig_h)
        target_w = max(1, int(orig_w * scale))
        target_h = max(1, int(orig_h * scale))

        resized_logo = logo_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        pos_x = (qr_w - target_w) // 2
        pos_y = (qr_h - target_h) // 2

        if add_background:
            padding = max(3, int(min(qr_w, qr_h) * 0.015))
            bg_box = (
                pos_x - padding,
                pos_y - padding,
                pos_x + target_w + padding,
                pos_y + target_h + padding,
            )
            draw = ImageDraw.Draw(qr_canvas)
            corner_radius = max(2, padding // 2)
            draw.rounded_rectangle(bg_box, radius=corner_radius, fill=(255, 255, 255, 255))

        # Alpha composite overlay
        qr_canvas.alpha_composite(resized_logo, dest=(pos_x, pos_y))
        return qr_canvas
