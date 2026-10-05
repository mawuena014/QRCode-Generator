from typing import Optional
from pydantic import BaseModel, Field

# Schema for QR code generation requests with optional center logo styling.
class QRCodeRequest(BaseModel):
    url: str = Field(
        ...,
        min_length=1,
        description="Target URL or text content to encode in the QR code",
    )
    logo_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded image string (raw or data URI) to place at the center",
    )
    logo_size_ratio: float = Field(
        default=0.22,
        ge=0.05,
        le=0.30,
        description="Ratio of the logo dimension relative to the QR code (0.05 to 0.30)",
    )
    add_logo_background: bool = Field(
        default=True,
        description="Whether to pad and back the center logo with a solid background for scan contrast",
    )
    box_size: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Pixel dimension of each individual QR code module",
    )
    border: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Width of the quiet zone border around the QR code",
    )
