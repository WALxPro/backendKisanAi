from fastapi import APIRouter, HTTPException
from models.farmer_model import EmailVerify,OTPVerify, Farmer, UpdateFarmer
from passlib.context import CryptContext
from datetime import datetime, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv
from database import db  
import smtplib
import os
import random




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
        # existing_otp = await db.otps.find_one({"email": email})
        # if existing_otp and datetime.utcnow() < existing_otp.get("resend_after", datetime.utcnow()):
        #     raise HTTPException(
        #         status_code=429,
        #         detail="Wait before requesting another OTP"
            
        #     )
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

    hashed_password = pwd_context.hash(data.password[:72])

    new_farmer = {
        "fullname": data.fullname,  
        "email": data.email,
        "phone": data.phone,
        "password": hashed_password,
        "profilePicture": str(data.profilePicture) if data.profilePicture else None,
        "cropDetail": data.cropDetail.dict() if data.cropDetail else None,
        "type": "farmer",
        "isBlocked": False, 
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }

    result = await db.farmers.insert_one(new_farmer)

    await db.otps.delete_one({"email": data.email})

    return {
        "message": "Farmer account created successfully",
        "id": str(result.inserted_id)
    }
@router.get("/login/{email}")
async def login(email: str):
    print("Received email:", email)
    user = await db.farmers.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return {
        "message": "Login success",
        "user": user
    }

@router.get("/get-by-email/{email}")
async def get_farmer_by_email(email: str):
    """
    Fetch farmer data using email.
    Returns full farmer profile if found.
    """
    farmer = await db.farmers.find_one({"email": email})
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    if farmer.get("isBlocked"):
        raise HTTPException(status_code=403, detail="Account is blocked")

    # Convert ObjectId to string for JSON serialization
    farmer["_id"] = str(farmer["_id"])

    # Optional: remove sensitive info like password
    if "password" in farmer:
        del farmer["password"]

    return {
        "message": "Farmer data fetched successfully",
        "farmer": farmer
    }


@router.put("/update/{email}")
async def update_farmer(email: str, data: UpdateFarmer):
    existing_farmer = await db.farmers.find_one({"email": email})
    if not existing_farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    update_data = {k: v for k, v in data.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    if "profilePicture" in update_data:
        update_data["profilePicture"] = str(update_data["profilePicture"])


    update_data["updatedAt"] = datetime.utcnow()

    result = await db.farmers.update_one(
        {"email": email},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="No changes made")

    updated_farmer = await db.farmers.find_one({"email": email})
    updated_farmer["_id"] = str(updated_farmer["_id"])

    if "password" in updated_farmer:
        del updated_farmer["password"]

    return {
        "message": "Farmer updated successfully",
        "farmer": updated_farmer
    }

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