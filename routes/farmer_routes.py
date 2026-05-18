from fastapi import APIRouter, HTTPException,Depends
from models.farmer_model import EmailVerify,OTPVerify, Farmer, UpdateFarmer
from passlib.context import CryptContext
from datetime import datetime, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv
from database import db  
import smtplib
import os
import random

from utils.farmer_identity import generate_farmer_id

from dependencies import get_current_user  # ← yeh add karo


load_dotenv()
router = APIRouter()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

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
        existing_user = await db.farmers.find_one({"email": email})
        existing_admin = await db.admins.find_one({"email": email})
        if existing_user or existing_admin:
            raise HTTPException(
                status_code=400,
                detail={"email": "Email already registered"}
            )
        otp = str(random.randint(100000, 999999))
        hashed_otp = pwd_context.hash(otp)

        expires_at = datetime.utcnow() + timedelta(minutes=5)
        await db.otps.update_one(
            {"email": email},
            {"$set": {"otp": hashed_otp, "expires_at": expires_at, "verified": False}},
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

    if datetime.utcnow() > record["expires_at"]:
        await db.otps.delete_one({"email": data.email})
        raise HTTPException(status_code=400, detail="OTP expired")

    if record.get("attempts", 0) >= 5:
        await db.otps.delete_one({"email": data.email})
        raise HTTPException(status_code=400, detail="Too many attempts")

    if not pwd_context.verify(data.otp, record["otp"]):
        await db.otps.update_one(
            {"email": data.email},
            {"$inc": {"attempts": 1}}
        )
        raise HTTPException(status_code=400, detail="Invalid OTP")

    await db.otps.delete_one({"email": data.email})

    return {"message": "OTP verified successfully"}

@router.post("/signup")
async def farmer_signup(data: Farmer):

    existing_user = await db.farmers.find_one({"email": data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

<<<<<<< HEAD
    hashed_password = pwd_context.hash(data.password[:72])
    farmer_id = data.farmer_id or generate_farmer_id()

    new_farmer = {
        "farmer_id": farmer_id,
        "fullname": data.fullname,  
=======
    new_farmer = {
        "fullname": data.fullname,
>>>>>>> e8cd478c136cda89584b1601fa73461b08cd7143
        "email": data.email,
        "phone": data.phone,
        "profilePicture": str(data.profilePicture) if data.profilePicture else None,
        "cropDetail": data.cropDetail.dict() if data.cropDetail else None,
        "type": "farmer",
        "isBlocked": False,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await db.farmers.insert_one(new_farmer)

    return {
<<<<<<< HEAD
        "message": "Farmer account created successfully",
        "id": str(result.inserted_id),
        "farmer_id": farmer_id
=======
        "message": "Farmer created successfully",
        "id": str(result.inserted_id)
>>>>>>> e8cd478c136cda89584b1601fa73461b08cd7143
    }
@router.post("/login")
async def login(user=Depends(get_current_user)):
    email = user["email"]  # token se aata hai, URL se nahi
    farmer = await db.farmers.find_one({"email": email})
    if not farmer:
        raise HTTPException(status_code=404, detail="User not found")
    if farmer.get("isBlocked"):
        raise HTTPException(status_code=403, detail="Account is blocked")
    farmer["_id"] = str(farmer["_id"])
    if "password" in farmer:
        del farmer["password"]
    return {"message": "Login success", "user": farmer}

@router.get("/me")
async def get_me(user=Depends(get_current_user)):

    email = user["email"]

    farmer = await db.farmers.find_one({"email": email})

    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    if farmer.get("isBlocked"):
        raise HTTPException(status_code=403, detail="Account is blocked")

    farmer["_id"] = str(farmer["_id"])

    if "password" in farmer:
        del farmer["password"]

    return {
        "message": "Farmer fetched successfully",
        "farmer": farmer
    }

@router.put("/update")
async def update_farmer(data: UpdateFarmer, user=Depends(get_current_user)):

    email = user["email"]

    update_data = {k: v for k, v in data.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided")

    update_data["updatedAt"] = datetime.utcnow()

    await db.farmers.update_one(
        {"email": email},
        {"$set": update_data}
    )

    farmer = await db.farmers.find_one({"email": email})
    farmer["_id"] = str(farmer["_id"])

    return {"message": "Updated successfully", "farmer": farmer}
@router.get("/all")
async def get_all_farmers():
    farmers_cursor = db.farmers.find()

    farmers = []
    async for farmer in farmers_cursor:
        farmer["_id"] = str(farmer["_id"])

        # Sensitive data remove
        if "password" in farmer:
            del farmer["password"]

        farmers.append(farmer)

    return {
        "message": "All farmers fetched successfully",
        "count": len(farmers),
        "farmers": farmers
    }