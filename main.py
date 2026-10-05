from typing import Optional
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from services.qr_generator import (
    InvalidColorError,
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
    service: QRCodeService = Depends(get_qr_service),
) -> StreamingResponse:
    """Generate a QR code from form data with optional center logo and custom colors."""
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
        )
        return StreamingResponse(buffer, media_type="image/png")
    except (InvalidLogoError, InvalidColorError) as exc:
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
