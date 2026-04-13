from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Literal, Optional


class Tutorial(BaseModel):
    title: str
    description: str
    category: str
    video: Optional[HttpUrl] = None   # ✅ optional
    image: Optional[str] = None       # ✅ ADD THIS (thumbnail)
    status: Literal["Published", "Draft"]
    created_at: Optional[datetime] = None


class UpdateTutorial(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    video: Optional[HttpUrl] = None
    image: Optional[str] = None       # ✅ ADD THIS
    status: Optional[Literal["Published", "Draft"]] = None