from fastapi import APIRouter, HTTPException
from models.admin_models import EmailVerify, OTPVerify, Admin, AdminUpdate
from datetime import datetime, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv
from database import db  
import smtplib
import os
import random

load_dotenv()
router = APIRouter()

def send_email(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("EMAIL"), os.getenv("EMAIL_VERIFICATION_PASSWORD"))
        server.send_message(msg)

@router.post("/send-signup-otp")
async def send_otp(data: EmailVerify):
    try:
        email = data.email
        existing_user = await db.admins.find_one({"email": email})
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail={"email": "Email already registered"}
            )
        otp = str(random.randint(100000, 999999))
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        await db.otps.update_one(
            {"email": email},
            {"$set": {"otp": otp, "expires_at": expires_at, "verified": False}},
            upsert=True
        )
        send_email(email, "Your KisanAi OTP", f"Your OTP is: {otp}")
        return {"message": "OTP sent successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={"general": f"Failed to send OTP: {str(e)}"}
        )

@router.post("/verify-otp")
async def verify_otp(data: OTPVerify):
    record = await db.otps.find_one({"email": data.email})
    if not record:
        raise HTTPException(status_code=404, detail="OTP not found")
    if record["otp"] != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if datetime.utcnow() > record["expires_at"]:
        raise HTTPException(status_code=400, detail="OTP expired")
    await db.otps.update_one(
        {"email": data.email},
        {"$set": {"verified": True}}
    )
    return {"message": "OTP verified successfully"}

@router.post("/signup")
async def signup(data: Admin):
    existing_user = await db.admins.find_one({"email": data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    otp_record = await db.otps.find_one({"email": data.email})
    if not otp_record or not otp_record.get("verified", False):
        raise HTTPException(status_code=400, detail="Email not verified")

    new_admin = {
        "name": data.name,
        "email": data.email,
        "profile_picture": str(data.profile_picture) if data.profile_picture else None,
        "isEmailVerified": True
    }

    await db.admins.insert_one(new_admin)
    await db.otps.delete_one({"email": data.email})

    return {"message": "Account created successfully"}

@router.get("/login/{email}")
async def login(email: str):
    user = await db.admins.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["_id"] = str(user["_id"])

    return {
        "message": "Login success",
        "user": user
    }

@router.put("/update/{email}")
async def update_admin(email: str, data: AdminUpdate):
    existing_admin = await db.admins.find_one({"email": email})
    if not existing_admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    update_data = {k: v for k, v in data.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided")

    # ❌ prevent email change
    if "email" in update_data:
        raise HTTPException(status_code=400, detail="Email cannot be updated")

    # 🖼 profile picture
    if "profile_picture" in update_data:
        update_data["profile_picture"] = str(update_data["profile_picture"])

    await db.admins.update_one(
        {"email": email},
        {"$set": update_data}
    )

    updated_admin = await db.admins.find_one({"email": email})
    updated_admin["_id"] = str(updated_admin["_id"])

    return {
        "message": "Admin updated successfully",
        "admin": updated_admin
    }

@router.post("/farmers/block")
async def block_farmer(data: dict):
    """Block a farmer account"""
    try:
        farmer_email = data.get("email")
        
        if not farmer_email:
            raise HTTPException(status_code=400, detail="Farmer email is required")
        
        # Check if farmer exists
        farmer = await db.farmers.find_one({"email": farmer_email})
        if not farmer:
            raise HTTPException(status_code=404, detail="Farmer not found")
        
        # Block the farmer
        result = await db.farmers.update_one(
            {"email": farmer_email},
            {"$set": {
                "isBlocked": True,
                "blockedAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to block farmer")
        
        return {
            "message": f"Farmer {farmer_email} has been blocked successfully",
            "success": True
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error blocking farmer: {str(e)}"
        )

@router.post("/farmers/unblock")
async def unblock_farmer(data: dict):
    """Unblock a farmer account"""
    try:
        farmer_email = data.get("email")
        
        if not farmer_email:
            raise HTTPException(status_code=400, detail="Farmer email is required")
        
        # Check if farmer exists
        farmer = await db.farmers.find_one({"email": farmer_email})
        if not farmer:
            raise HTTPException(status_code=404, detail="Farmer not found")
        
        # Unblock the farmer
        result = await db.farmers.update_one(
            {"email": farmer_email},
            {"$set": {
                "isBlocked": False,
                "unblockedAt": datetime.utcnow(),
                "updatedAt": datetime.utcnow()
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to unblock farmer")
        
        return {
            "message": f"Farmer {farmer_email} has been unblocked successfully",
            "success": True
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error unblocking farmer: {str(e)}"
        )