from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from schema import QRCodeRequest
from services.qr_generator import InvalidLogoError, QRCodeGeneratorError, QRCodeService

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
    request: QRCodeRequest,
    service: QRCodeService = Depends(get_qr_service),
) -> StreamingResponse:
    """Generate a QR code from text or URL with optional central logo customization."""
    try:
        buffer = service.generate(request)
        return StreamingResponse(buffer, media_type="image/png")
    except InvalidLogoError as exc:
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
