from fastapi import Header, HTTPException
import firebase_admin.auth

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split("Bearer ")[1]

    try:
        decoded = firebase_admin.auth.verify_id_token(token)
        return decoded  # uid, email
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")