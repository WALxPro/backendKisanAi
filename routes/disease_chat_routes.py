from fastapi import APIRouter, HTTPException, Query
from database import db
from bson import ObjectId
from models.disease_chat_model import DiseaseChatRequest
from utils.disease_chat import start_disease_chat, send_disease_chat_message

router = APIRouter()


@router.post("/start-chat/{prediction_id}")
async def start_disease_chat_route(prediction_id: str, farmer_id: str = Query(...)):
    try:
        return await start_disease_chat(prediction_id=prediction_id, farmer_id=farmer_id, db=db)
    except HTTPException:
        raise
    except Exception as e:
        if str(e) == CHAT_LIMIT_MESSAGE:
            raise HTTPException(status_code=429, detail=CHAT_LIMIT_MESSAGE)
        raise HTTPException(status_code=500, detail=f"Failed to start chat: {str(e)}")


@router.post("/send-message")
async def send_disease_chat_message_route(request: DiseaseChatRequest):
    try:
        return await send_disease_chat_message(request=request, db=db)
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}") from e


@router.get("/history/{chat_id}")
async def get_chat_history(chat_id: str, farmer_id: str = Query(...)):
    try:
        chat = await db.disease_chats.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if chat.get("farmer_id") != farmer_id:
            raise HTTPException(status_code=403, detail="Chat session does not belong to this farmer")

        return {
            "chat_id": str(chat["_id"]),
            "disease_name": chat.get("disease_name"),
            "chat_count": chat.get("chat_count", 0),
            "remaining_chats": 3 - chat.get("chat_count", 0),
            "messages": chat.get("messages", []),
            "created_at": chat.get("created_at"),
            "updated_at": chat.get("updated_at"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")


@router.get("/status/{chat_id}")
async def get_chat_status(chat_id: str, farmer_id: str = Query(...)):
    try:
        chat = await db.disease_chats.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
        if chat.get("farmer_id") != farmer_id:
            raise HTTPException(status_code=403, detail="Chat session does not belong to this farmer")

        chat_count = chat.get("chat_count", 0)
        remaining_chats = 3 - chat_count

        return {
            "chat_id": str(chat["_id"]),
            "disease_name": chat.get("disease_name"),
            "chat_count": chat_count,
            "remaining_chats": remaining_chats,
            "can_continue": remaining_chats > 0,
            "max_words_per_message": 50,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat status: {str(e)}")

