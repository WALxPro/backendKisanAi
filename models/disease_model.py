from pydantic import BaseModel, Field
from typing import Optional


class DiseasePredictionRequest(BaseModel):
    image_base64: str = Field(..., description="Base64 encoded image string")
    user_email: Optional[str] = Field(default=None, description="Optional user email to link the prediction")
    image_name: Optional[str] = Field(default=None, description="Optional original image name")
