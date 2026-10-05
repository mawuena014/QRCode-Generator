from typing import Optional
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from services.qr_generator import (
    InvalidColorError,
    InvalidDrawerError,
    InvalidGradientError,
    InvalidLogoError,
    QRCodeGeneratorError,
    QRCodeService,
)

app = FastAPI(title="QR Code Generator")


def get_qr_service() -> QRCodeService:
    """Dependency provider for QRCodeService."""
    return QRCodeService()


@app.get("/health")
async def health_check() -> dict:
    """Check if the API service is running."""
    return {"status": "healthy", "service": "qr-code-generator"}


@app.post("/generate_qr")
async def generate_qr(
    url: str = Form(
        ...,
        min_length=1,
        description="Target URL or text content to encode in the QR code",
    ),
    logo: Optional[UploadFile] = File(
        default=None,
        description="Optional image file (PNG, JPEG, etc.) to place at the center",
    ),
    logo_size_ratio: float = Form(
        default=0.22,
        ge=0.05,
        le=0.30,
        description="Ratio of the logo dimension relative to the QR code (0.05 to 0.30)",
    ),
    add_logo_background: bool = Form(
        default=True,
        description="Whether to pad and back the center logo with a solid background for scan contrast",
    ),
    box_size: int = Form(
        default=10,
        ge=1,
        le=50,
        description="Pixel dimension of each individual QR code module",
    ),
    border: int = Form(
        default=4,
        ge=1,
        le=20,
        description="Width of the quiet zone border around the QR code",
    ),
    fill_color: str = Form(
        default="black",
        description="Foreground color for QR modules (hex code e.g. #1A56DB or CSS color name)",
    ),
    back_color: str = Form(
        default="white",
        description="Background canvas color (hex code e.g. #FFFFFF or CSS color name)",
    ),
    drawer: str = Form(
        default="square",
        description="Module shape drawer: square, circle, rounded, gapped_square, vertical_bars, horizontal_bars",
    ),
    eye_drawer: Optional[str] = Form(
        default=None,
        description="Corner eye marker shape: square, circle, rounded, gapped_square",
    ),
    gradient_type: str = Form(
        default="none",
        description="Gradient mode across modules: none, radial, horizontal, vertical",
    ),
    gradient_start_color: Optional[str] = Form(
        default=None,
        description="Gradient start color (defaults to fill_color if unspecified)",
    ),
    gradient_end_color: Optional[str] = Form(
        default=None,
        description="Gradient end color (required when gradient_type is not 'none')",
    ),
    transparent_background: bool = Form(
        default=False,
        description="Whether to generate an RGBA PNG with 100% transparent background",
    ),
    service: QRCodeService = Depends(get_qr_service),
) -> StreamingResponse:
    """Generate a QR code from form data with styled modules, eyes, gradients, and logos."""
    try:
        logo_bytes: Optional[bytes] = None
        if logo is not None:
            raw_contents = await logo.read()
            # If the user left the file input untouched, browsers submit an empty filename with 0 bytes
            if not raw_contents and not logo.filename:
                logo_bytes = None
            else:
                logo_bytes = raw_contents

        buffer = service.generate(
            url=url,
            logo_bytes=logo_bytes,
            logo_size_ratio=logo_size_ratio,
            add_logo_background=add_logo_background,
            box_size=box_size,
            border=border,
            fill_color=fill_color,
            back_color=back_color,
            drawer=drawer,
            eye_drawer=eye_drawer,
            gradient_type=gradient_type,
            gradient_start_color=gradient_start_color,
            gradient_end_color=gradient_end_color,
            transparent_background=transparent_background,
        )
        return StreamingResponse(buffer, media_type="image/png")
    except (
        InvalidLogoError,
        InvalidColorError,
        InvalidDrawerError,
        InvalidGradientError,
    ) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except QRCodeGeneratorError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate QR code: {str(exc)}",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
