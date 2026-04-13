from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional

class EmailVerify(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

class Admin(BaseModel):
    name: str
    email: EmailStr
    profile_picture: Optional[HttpUrl] = None


class AdminUpdate(BaseModel):
    name: Optional[str] = None
    profile_picture: Optional[HttpUrl] = None