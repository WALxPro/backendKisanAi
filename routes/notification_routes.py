from fastapi import APIRouter, HTTPException
from datetime import datetime
from bson import ObjectId

from models.notification_model import (
    NotificationCreate,
    NotificationUpdate
)
from database import db

router = APIRouter()

notifications_collection = db["notifications"]


@router.post("/create")
async def create_notification(notification: NotificationCreate):
    try:
        data = notification.dict()

        data["read"] = False
        data["created_at"] = datetime.utcnow()

        result = await notifications_collection.insert_one(data)

        return {
            "message": "Notification created",
            "id": str(result.inserted_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/{user_id}/{role}")
async def get_notifications(user_id: str, role: str):
    try:
        query = {
            "$and": [
                {
                    "$or": [
                        {"user_id": user_id},
                        {"user_id": None}
                    ]
                },
                {
                    "$or": [
                        {"target_role": role},
                        {"target_role": "all"}
                    ]
                }
            ]
        }

        notifications = await notifications_collection.find(query) \
            .sort("created_at", -1) \
            .to_list(length=100)

        for n in notifications:
            n["_id"] = str(n["_id"])

        return notifications

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.put("/read/{notification_id}")
async def mark_as_read(notification_id: str):
    try:
        result = await notifications_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"read": True}}
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")

        return {"message": "Marked as read"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/{notification_id}")
async def delete_notification(notification_id: str):
    try:
        result = await notifications_collection.delete_one(
            {"_id": ObjectId(notification_id)}
        )

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Not found")

        return {"message": "Deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))