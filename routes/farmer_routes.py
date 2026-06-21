from fastapi import APIRouter, Depends
from models.farmer_model import EmailVerify, OTPVerify, Farmer, UpdateFarmer
from passlib.context import CryptContext
from utils.response import error_response, success_response
from datetime import datetime, timedelta
from email.message import EmailMessage
from dotenv import load_dotenv
from database import db
import smtplib
import os
import random
from fastapi.encoders import jsonable_encoder
from dependencies import get_current_user


load_dotenv()

router = APIRouter()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def send_email(to_email: str, subject: str, body: str, is_html: bool = False):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = to_email

    if is_html:
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(
            os.getenv("EMAIL"),
            os.getenv("EMAIL_VERIFICATION_PASSWORD")
        )
        server.send_message(msg)


@router.post("/send-signup-otp")
async def send_otp(data: EmailVerify):
    try:
        email = data.email

        existing_user = await db.farmers.find_one({"email": email})
        existing_admin = await db.admins.find_one({"email": email})

        if existing_user or existing_admin:
            return error_response(
                message="Email already registered",
                detail={"email": "Email already registered"},
                status_code=400
            )

        otp = str(random.randint(100000, 999999))
        hashed_otp = pwd_context.hash(otp)
        expires_at = datetime.utcnow() + timedelta(minutes=5)

        await db.otps.update_one(
            {"email": email},
            {
                "$set": {
                    "otp": hashed_otp,
                    "expires_at": expires_at,
                    "verified": False,
                    "attempts": 0
                }
            },
            upsert=True
        )

        html_body = f"""
<html>
  <body style="font-family: Arial, sans-serif;">
    <div style="padding:20px; border:1px solid #ddd; border-radius:10px;">
      <h2 style="color:#2e7d32;">KisanAi OTP Verification</h2>

      <p>Hello,</p>

      <p>Your OTP for verification is:</p>

      <h1 style="letter-spacing:5px; color:#000;">{otp}</h1>

      <p style="color:red;">
        This code will expire in <b>5 minutes</b>.
      </p>

      <p>If you did not request this, ignore this email.</p>

      <br/>
      <p>— <b>KisanAi Team</b></p>
    </div>
  </body>
</html>
"""

        send_email(
            email,
            "KisanAi OTP Verification",
            html_body,
            is_html=True
        )

        return success_response(
            message="OTP sent successfully",
            detail=None,
            status_code=200
        )

    except Exception as e:
        return error_response(
            message="Failed to send OTP",
            detail={"general": str(e)},
            status_code=500
        )


@router.post("/verify-otp")
async def verify_otp(data: OTPVerify):
    try:
        record = await db.otps.find_one({"email": data.email})

        if not record:
            return error_response(
                message="OTP not found",
                detail="OTP not found",
                status_code=404
            )

        if datetime.utcnow() > record["expires_at"]:
            await db.otps.delete_one({"email": data.email})
            return error_response(
                message="OTP expired",
                detail="OTP expired",
                status_code=400
            )

        if record.get("attempts", 0) >= 5:
            await db.otps.delete_one({"email": data.email})
            return error_response(
                message="Too many attempts",
                detail="Too many attempts",
                status_code=400
            )

        if not pwd_context.verify(data.otp, record["otp"]):
            await db.otps.update_one(
                {"email": data.email},
                {"$inc": {"attempts": 1}}
            )

            return error_response(
                message="Invalid OTP",
                detail="Invalid OTP",
                status_code=400
            )

        await db.otps.update_one(
            {"email": data.email},
            {"$set": {"verified": True}}
        )

        return success_response(
            message="OTP verified successfully",
            detail=None,
            status_code=200
        )

    except Exception as e:
        return error_response(
            message="Failed to verify OTP",
            detail={"general": str(e)},
            status_code=500
        )


@router.post("/signup")
async def farmer_signup(data: Farmer):
    try:
        otp_record = await db.otps.find_one({"email": data.email})

        if not otp_record or not otp_record.get("verified"):
            return error_response(
                message="OTP not verified",
                detail="OTP not verified",
                status_code=400
            )

        existing_user = await db.farmers.find_one({"email": data.email})

        if existing_user:
            return error_response(
                message="Email already registered",
                detail="Email already registered",
                status_code=400
            )

        new_farmer = data.dict()
        new_farmer["profilePicture"] = (
            str(data.profilePicture) if data.profilePicture else None
        )

        new_farmer.update({
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
            "ai_scan_limit": 3,
            "ai_scan_used": 0,
        })

        result = await db.farmers.insert_one(new_farmer)

        await db.otps.delete_one({"email": data.email})

        return success_response(
            message="Farmer created successfully",
            detail={"id": str(result.inserted_id)},
            status_code=201
        )

    except Exception as e:
        return error_response(
            message="Failed to create farmer",
            detail={"general": str(e)},
            status_code=500
        )


# @router.get("/auth-user")
# async def get_me(user=Depends(get_current_user)):
#     try:
#         uid = user["uid"]

#         farmer = await db.farmers.find_one({"uid": uid})

#         if not farmer:
#             return error_response(
#                 message="Farmer profile not found",
#                 detail="Farmer profile not found",
#                 status_code=404
#             )

#         if farmer.get("isBlocked"):
#             return error_response(
#                 message="Account is blocked",
#                 detail="Account is blocked",
#                 status_code=403
#             )
        
#         farmer["_id"] = str(farmer["_id"])
#         farmer.pop("password", None)

#         farmer = jsonable_encoder(farmer)

#         return success_response(
#         message="Farmer fetched successfully",
#         detail={"farmer": farmer},
#         status_code=200
# )



#     except Exception as e:
#         return error_response(
#             message="Failed to fetch farmer",
#             detail={"general": str(e)},
#             status_code=500
#         )

@router.get("/auth-user")
async def get_me(email: str):
    farmer = await db.farmers.find_one({"email": email})

    if not farmer:
        return error_response(
            message="Farmer not found",
            detail="Farmer not found",
            status_code=404
        )

    if farmer.get("isBlocked"):
        return error_response(
            message="Account is blocked",
            detail="Account is blocked",
            status_code=403
        )

    farmer["_id"] = str(farmer["_id"])
    farmer.pop("password", None)
    farmer = jsonable_encoder(farmer)

    return success_response(
        message="Farmer fetched successfully",
        detail={"farmer": farmer},
        status_code=200
    )

@router.put("/update")
async def update_farmer(email: str, data: UpdateFarmer):
    farmer = await db.farmers.find_one({"email": email})

    if not farmer:
        return error_response(
            message="Farmer not found",
            detail="Farmer not found",
            status_code=404
        )

    update_data = data.dict(exclude_none=True)

    if not update_data:
        return error_response(
            message="No data provided",
            detail="No data provided",
            status_code=400
        )

    # 🔥 FIX: HttpUrl aur dusre non-BSON types ko safe types mein convert karen
    update_data = jsonable_encoder(update_data)

    update_data["updatedAt"] = datetime.utcnow()

    await db.farmers.update_one(
        {"email": email},
        {"$set": update_data}
    )

    updated = await db.farmers.find_one({"email": email})

    if not updated:
        return error_response(
            message="Update failed",
            detail="Update failed",
            status_code=500
        )

    updated["_id"] = str(updated["_id"])
    updated = jsonable_encoder(updated)

    return success_response(
        message="Updated successfully",
        detail={"farmer": updated},
        status_code=200
    )

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