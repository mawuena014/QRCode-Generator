"""QR Code generation and image processing domain service."""

import base64
import binascii
import io
import re
from typing import Optional, Tuple
from PIL import Image, ImageDraw, UnidentifiedImageError
import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_M

from schema import QRCodeRequest


class QRCodeGeneratorError(Exception):
    """Base exception for QR code generation failures."""


class InvalidLogoError(QRCodeGeneratorError):
    """Raised when an provided logo image cannot be decoded or validated."""


class QRCodeService:
    """Domain service responsible for rendering QR codes with optional center logos."""

    MAX_RAW_IMAGE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit to prevent DoS
    DATA_URI_PATTERN: re.Pattern = re.compile(r"^data:image\/[a-zA-Z0-9.+_-]+;base64,")

    def generate(self, request: QRCodeRequest) -> io.BytesIO:
        """Generate a QR code image as a PNG bytes buffer according to request parameters."""
        error_correction = ERROR_CORRECT_H if request.logo_base64 else ERROR_CORRECT_M

        qr = qrcode.QRCode(
            version=None,  # Auto-size version according to data and error correction
            error_correction=error_correction,
            box_size=request.box_size,
            border=request.border,
        )
        qr.add_data(request.url)
        try:
            qr.make(fit=True)
        except Exception as exc:
            raise QRCodeGeneratorError(f"Failed to compile QR matrix: {exc}") from exc

        # Render base QR image and convert to RGBA for compositing
        base_qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_canvas: Image.Image = base_qr_img.convert("RGBA")

        if request.logo_base64:
            logo_img = self._decode_and_validate_logo(request.logo_base64)
            qr_canvas = self._overlay_center_logo(
                qr_canvas=qr_canvas,
                logo_img=logo_img,
                size_ratio=request.logo_size_ratio,
                add_background=request.add_logo_background,
            )

        output_buffer = io.BytesIO()
        qr_canvas.save(output_buffer, format="PNG")
        output_buffer.seek(0)
        return output_buffer

    def _decode_and_validate_logo(self, raw_base64_str: str) -> Image.Image:
        """Safely decode, sanitize, and validate an input base64 image string."""
        cleaned_str = raw_base64_str.strip()
        cleaned_str = self.DATA_URI_PATTERN.sub("", cleaned_str)

        try:
            image_bytes = base64.b64decode(cleaned_str, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise InvalidLogoError(f"Malformed base64 logo string: {exc}") from exc

        if len(image_bytes) == 0:
            raise InvalidLogoError("Decoded logo payload is empty.")

        if len(image_bytes) > self.MAX_RAW_IMAGE_BYTES:
            raise InvalidLogoError(
                f"Logo payload exceeds maximum allowed size of {self.MAX_RAW_IMAGE_BYTES} bytes."
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
