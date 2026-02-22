from pydantic import BaseModel

# Schema for QR code generation requests.
class QRCodeRequest(BaseModel):
    url: str
