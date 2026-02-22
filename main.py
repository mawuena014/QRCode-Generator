from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import qrcode
import io
from schema import QRCodeRequest

app = FastAPI(title = "QR Code Generator")

@app.get("/health")
async def health_check() -> dict:
    # Check if the API is running
    return {"status": "healthy", "service": "qr-code-generator"}

@app.post("/generate_qr")
async def generate_qr(request: QRCodeRequest) -> StreamingResponse:
    # Generate a QR code from a URL or text
    try:
        # Generate QR code
        img = qrcode.make(request.url)
        
        # Save image to a bytes buffer
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
