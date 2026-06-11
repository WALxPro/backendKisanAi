from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Literal, Optional


class Ad(BaseModel):
    title: str
    description: str
    status: Literal["Active", "Inactive"]
    image: HttpUrl
    created_at: Optional[datetime] = None

class UpdateAd(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    image: Optional[HttpUrl] = None
    status: Optional[str] = None