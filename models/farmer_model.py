from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional
from datetime import datetime

class EmailVerify(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class Farmer(BaseModel):
<<<<<<< HEAD
    farmer_id: Optional[str] = None
=======
    uid: str
>>>>>>> 53c2c75 (chat issue resolve)
    fullname: str
    phone: str
    email: EmailStr
    city: str
    isBlocked: bool = False
    profilePicture: Optional[HttpUrl] = None
    type: str = "farmer"

    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    # AI scan system
    ai_scan_limit: int = 3
    ai_scan_used: int = 0

class UpdateFarmer(BaseModel):
    fullname: Optional[str] = None
    phone: Optional[str] = None
    profilePicture: Optional[HttpUrl] = None
    isBlocked: Optional[bool] = None
    
    ai_scan_limit: Optional[int] = None
    ai_scan_used: Optional[int] = None