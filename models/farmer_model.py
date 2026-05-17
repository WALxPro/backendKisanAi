from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional
from datetime import datetime

class EmailVerify(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str


class CropDetail(BaseModel):
    cropName: str
    season: str
    irrigationType: str
    city: str


class Farmer(BaseModel):
    farmer_id: Optional[str] = None
    fullname: str
    phone: str
    email: EmailStr
    password: str
    isBlocked: bool = False   # 👈 FIXED
    profilePicture: Optional[HttpUrl] = None
    cropDetail: Optional[CropDetail] = None
    type: str = "farmer"
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

class UpdateFarmer(BaseModel):
    fullname: Optional[str] = None
    phone: Optional[str] = None
    profilePicture: Optional[HttpUrl] = None
    isBlocked : Optional[bool] = None

