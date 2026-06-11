from pydantic import BaseModel, Field
from typing import Optional


class DiseasePredictionRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image string")
    farmer_id: str = Field(..., description="Unique farmer id to link the prediction")
    user_email: Optional[str] = Field(default=None, description="Optional user email for backward compatibility")
    image_name: Optional[str] = Field(default=None, description="Optional original image name")

