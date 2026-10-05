"""QR Code generation and image processing domain service."""

import io
from typing import Optional, Union
from PIL import Image, ImageColor, ImageDraw, UnidentifiedImageError
import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_M
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import (
    HorizontalGradiantColorMask,
    QRColorMask,
    RadialGradiantColorMask,
    SolidFillColorMask,
    VerticalGradiantColorMask,
)
from qrcode.image.styles.moduledrawers.pil import (
    CircleModuleDrawer,
    GappedSquareModuleDrawer,
    HorizontalBarsDrawer,
    QRModuleDrawer,
    RoundedModuleDrawer,
    SquareModuleDrawer,
    VerticalBarsDrawer,
)


class QRCodeGeneratorError(Exception):
    """Base exception for QR code generation failures."""


class InvalidLogoError(QRCodeGeneratorError):
    """Raised when a provided logo image cannot be decoded or validated."""


class InvalidColorError(QRCodeGeneratorError):
    """Raised when an invalid or unresolvable color string is specified."""


class InvalidDrawerError(QRCodeGeneratorError):
    """Raised when an unsupported module or eye drawer name is provided."""


class InvalidGradientError(QRCodeGeneratorError):
    """Raised when an invalid gradient type or color configuration is provided."""


MODULE_DRAWERS: dict[str, type[QRModuleDrawer]] = {
    "square": SquareModuleDrawer,
    "circle": CircleModuleDrawer,
    "rounded": RoundedModuleDrawer,
    "gapped_square": GappedSquareModuleDrawer,
    "vertical_bars": VerticalBarsDrawer,
    "horizontal_bars": HorizontalBarsDrawer,
}

EYE_DRAWERS: dict[str, type[QRModuleDrawer]] = {
    "square": SquareModuleDrawer,
    "circle": CircleModuleDrawer,
    "rounded": RoundedModuleDrawer,
    "gapped_square": GappedSquareModuleDrawer,
}

GRADIENT_TYPES: tuple[str, ...] = ("none", "radial", "horizontal", "vertical")


class QRCodeService:
    """Domain service responsible for rendering QR codes with visual styles and logos."""

    MAX_RAW_IMAGE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit to prevent DoS

    def generate(
        self,
        url: str,
        logo_bytes: Optional[bytes] = None,
        logo_size_ratio: float = 0.22,
        add_logo_background: bool = True,
        box_size: int = 10,
        border: int = 4,
        fill_color: str = "black",
        back_color: str = "white",
        drawer: str = "square",
        eye_drawer: Optional[str] = None,
        gradient_type: str = "none",
        gradient_start_color: Optional[str] = None,
        gradient_end_color: Optional[str] = None,
        transparent_background: bool = False,
    ) -> io.BytesIO:
        """Generate a QR code image as a PNG bytes buffer with optional styling and logo."""
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

        module_drawer_cls = self._resolve_drawer(drawer)
        eye_drawer_cls = self._resolve_eye_drawer(eye_drawer)
        color_mask = self._build_color_mask(
            fill_color=fill_color,
            back_color=back_color,
            gradient_type=gradient_type,
            gradient_start_color=gradient_start_color,
            gradient_end_color=gradient_end_color,
            transparent_background=transparent_background,
        )

        # Standard fast path optimization for default square unstyled codes
        norm_gradient = gradient_type.strip().lower()
        if (
            drawer == "square"
            and eye_drawer is None
            and norm_gradient == "none"
            and not transparent_background
        ):
            fill_rgb, back_rgb = self._validate_colors(fill_color, back_color)
            base_qr_img = qr.make_image(fill_color=fill_rgb, back_color=back_rgb)
            qr_canvas: Image.Image = base_qr_img.convert("RGBA")
        else:
            image_kwargs: dict[str, Union[type, QRModuleDrawer, QRColorMask]] = {
                "image_factory": StyledPilImage,
                "module_drawer": module_drawer_cls(),
                "color_mask": color_mask,
            }
            if eye_drawer_cls is not None:
                image_kwargs["eye_drawer"] = eye_drawer_cls()

            styled_img = qr.make_image(**image_kwargs)
            qr_canvas = styled_img._img.convert("RGBA")

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

    def _parse_color(self, color_str: str, param_name: str) -> tuple[int, int, int]:
        """Parse a color string into an RGB 3-tuple."""
        if not color_str or not color_str.strip():
            raise InvalidColorError(f"{param_name} cannot be empty.")
        try:
            rgb = ImageColor.getrgb(color_str.strip())
            return rgb[:3]
        except Exception as exc:
            raise InvalidColorError(
                f"Invalid {param_name} '{color_str}': must be a valid hex string or CSS color name."
            ) from exc

    def _resolve_drawer(self, drawer_name: str) -> type[QRModuleDrawer]:
        """Resolve a friendly drawer name to a QRModuleDrawer class."""
        normalized = drawer_name.strip().lower()
        if normalized not in MODULE_DRAWERS:
            allowed = ", ".join(sorted(MODULE_DRAWERS.keys()))
            raise InvalidDrawerError(
                f"Unsupported module drawer '{drawer_name}'. Allowed options: {allowed}."
            )
        return MODULE_DRAWERS[normalized]

    def _resolve_eye_drawer(self, eye_drawer_name: Optional[str]) -> Optional[type[QRModuleDrawer]]:
        """Resolve an eye drawer name to a QRModuleDrawer class."""
        if not eye_drawer_name or not eye_drawer_name.strip():
            return None
        normalized = eye_drawer_name.strip().lower()
        if normalized not in EYE_DRAWERS:
            allowed = ", ".join(sorted(EYE_DRAWERS.keys()))
            raise InvalidDrawerError(
                f"Unsupported eye drawer '{eye_drawer_name}'. Allowed options: {allowed}."
            )
        return EYE_DRAWERS[normalized]

    def _build_color_mask(
        self,
        fill_color: str,
        back_color: str,
        gradient_type: str,
        gradient_start_color: Optional[str],
        gradient_end_color: Optional[str],
        transparent_background: bool,
    ) -> QRColorMask:
        """Construct the appropriate QRColorMask based on gradient and transparency settings."""
        norm_gradient = gradient_type.strip().lower()
        if norm_gradient not in GRADIENT_TYPES:
            allowed = ", ".join(sorted(GRADIENT_TYPES))
            raise InvalidGradientError(
                f"Unsupported gradient_type '{gradient_type}'. Allowed options: {allowed}."
            )

        back_rgb = self._parse_color(back_color, "back_color")
        back_tuple = (*back_rgb, 0) if transparent_background else back_rgb

        if norm_gradient == "none":
            fill_rgb = self._parse_color(fill_color, "fill_color")
            if not transparent_background and fill_rgb == back_rgb:
                raise InvalidColorError(
                    f"fill_color and back_color cannot be identical ({fill_color}). "
                    "Sufficient contrast is required for scanning."
                )
            front_tuple = (*fill_rgb, 255) if transparent_background else fill_rgb
            mask: QRColorMask = SolidFillColorMask(back_color=back_tuple, front_color=front_tuple)
        else:
            start_str = (
                gradient_start_color
                if gradient_start_color and gradient_start_color.strip()
                else fill_color
            )
            if not gradient_end_color or not gradient_end_color.strip():
                raise InvalidGradientError(
                    "gradient_end_color must be specified when gradient_type is not 'none'."
                )
            start_rgb = self._parse_color(start_str, "gradient_start_color")
            end_rgb = self._parse_color(gradient_end_color, "gradient_end_color")

            if not transparent_background and start_rgb == back_rgb and end_rgb == back_rgb:
                raise InvalidColorError(
                    "Gradient colors cannot match back_color. Sufficient contrast is required for scanning."
                )

            start_tuple = (*start_rgb, 255) if transparent_background else start_rgb
            end_tuple = (*end_rgb, 255) if transparent_background else end_rgb

            if norm_gradient == "radial":
                mask = RadialGradiantColorMask(
                    back_color=back_tuple,
                    center_color=start_tuple,
                    edge_color=end_tuple,
                )
            elif norm_gradient == "horizontal":
                mask = HorizontalGradiantColorMask(
                    back_color=back_tuple,
                    left_color=start_tuple,
                    right_color=end_tuple,
                )
            elif norm_gradient == "vertical":
                mask = VerticalGradiantColorMask(
                    back_color=back_tuple,
                    top_color=start_tuple,
                    bottom_color=end_tuple,
                )

        if transparent_background:
            mask.has_transparency = True

        return mask

    def _validate_colors(
        self, fill_color: str, back_color: str
    ) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """Validate and resolve foreground and background color strings."""
        fill_rgb = self._parse_color(fill_color, "fill_color")
        back_rgb = self._parse_color(back_color, "back_color")

        if fill_rgb == back_rgb:
            raise InvalidColorError(
                f"fill_color and back_color cannot be identical ({fill_color}). "
                "Sufficient contrast is required for scanning."
            )

        return fill_rgb, back_rgb

    def _validate_and_load_logo(self, image_bytes: bytes) -> Image.Image:
        """Safely validate image integrity and load into an RGBA Pillow Image."""
        if len(image_bytes) == 0:
            raise InvalidLogoError("Uploaded logo file is empty.")

        if len(image_bytes) > self.MAX_RAW_IMAGE_BYTES:
            raise InvalidLogoError(
                f"Logo file exceeds maximum allowed size of {self.MAX_RAW_IMAGE_BYTES} bytes."
            )

        try:
            verify_buffer = io.BytesIO(image_bytes)
            with Image.open(verify_buffer) as test_img:
                test_img.verify()
        except (UnidentifiedImageError, OSError, Exception) as exc:
            raise InvalidLogoError(f"Invalid or corrupted image format: {exc}") from exc

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

        qr_canvas.alpha_composite(resized_logo, dest=(pos_x, pos_y))
        return qr_canvas
