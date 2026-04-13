from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class NotificationCreate(BaseModel):
    title: str
    message: str
    type: Literal["login", "farmer", "complaint", "system", "blog", "tutorial"]

    user_id: Optional[str] = None
    target_role: Literal["admin", "farmer", "all"] = "all"

class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    type: str
    user_id: Optional[str]
    read: bool = False
    created_at: datetime

class NotificationUpdate(BaseModel):
    read: bool = True