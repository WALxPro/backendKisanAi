from __future__ import annotations

import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from bson import ObjectId

from utils.tools import get_farm_context, build_disease_chat_system_prompt

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    GEMINI_LLM = (
        ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, temperature=0.2)
        if GEMINI_API_KEY
        else None
    )
except Exception:
    GEMINI_LLM = None

MAX_CHATS = 3
MAX_WORDS = 50


def count_words(text: str) -> int:
    return len(text.split())


def validate_message_length(message: str) -> bool:
    return count_words(message) <= MAX_WORDS


async def start_disease_chat(prediction_id: str, farmer_id: str, db) -> dict:
    prediction = await db.disease_predictions.find_one({"_id": ObjectId(prediction_id)})
    if not prediction:
        raise RuntimeError("Disease prediction not found")

    if prediction.get("farmer_id") and prediction.get("farmer_id") != farmer_id:
        raise RuntimeError("Disease prediction does not belong to this farmer")

    disease_name = prediction.get("predicted_class")
    disease_details = prediction.get("disease_details", {})
    farm_context = await get_farm_context(db=db, farmer_id=farmer_id)

    existing_chat = await db.disease_chats.find_one({"prediction_id": prediction_id, "farmer_id": farmer_id})
    if existing_chat:
        return {
            "chat_id": str(existing_chat["_id"]),
            "chat_count": existing_chat.get("chat_count", 0),
            "remaining_chats": MAX_CHATS - existing_chat.get("chat_count", 0),
            "message": "Chat session already exists",
            "can_continue": existing_chat.get("chat_count", 0) < MAX_CHATS,
        }

    chat_record = {
        "prediction_id": prediction_id,
        "farmer_id": farmer_id,
        "disease_name": disease_name,
        "disease_details": disease_details,
        "farmer_name": farm_context.get("farmer_name"),
        "admin_name": farm_context.get("admin_name"),
        "messages": [],
        "chat_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await db.disease_chats.insert_one(chat_record)

    return {
        "chat_id": str(result.inserted_id),
        "chat_count": 0,
        "remaining_chats": MAX_CHATS,
        "message": "Chat session started. You can ask up to 3 questions, each with max 50 words.",
        "can_continue": True,
    }


async def send_disease_chat_message(request, db) -> dict:
    if not validate_message_length(request.user_message):
        raise ValueError("Message exceeds word limit")

    chat = await db.disease_chats.find_one({"_id": ObjectId(request.prediction_id), "farmer_id": request.farmer_id})
    if not chat:
        raise RuntimeError("Chat session not found")

    chat_count = chat.get("chat_count", 0)
    if chat_count >= MAX_CHATS:
        raise RuntimeError("Chat limit reached")

    if GEMINI_LLM is None:
        raise RuntimeError("AI assistant is not available. Please configure GEMINI_API_KEY.")

    disease_name = chat.get("disease_name")
    disease_details = chat.get("disease_details", {})
    farm_context = await get_farm_context(db=db, farmer_id=request.farmer_id)
    farm_context["disease_name"] = disease_name
    system_prompt = build_disease_chat_system_prompt(farm_context, disease_details)

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=request.user_message)]
    response = GEMINI_LLM.invoke(messages)
    ai_response = response.content if hasattr(response, "content") else str(response)

    new_messages = [
        {"role": "user", "content": request.user_message, "created_at": datetime.utcnow()},
        {"role": "assistant", "content": ai_response, "created_at": datetime.utcnow()},
    ]

    updated_chat = await db.disease_chats.find_one_and_update(
        {"_id": ObjectId(request.prediction_id)},
        {"$push": {"messages": {"$each": new_messages}}, "$inc": {"chat_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
        return_document=True,
    )

    new_chat_count = updated_chat.get("chat_count", 1)
    remaining_chats = MAX_CHATS - new_chat_count

    return {
        "chat_id": str(updated_chat["_id"]),
        "chat_count": new_chat_count,
        "remaining_chats": remaining_chats,
        "user_message": request.user_message,
        "ai_response": ai_response,
        "can_continue": remaining_chats > 0,
        "message": f"Response sent. You have {remaining_chats} chat(s) remaining.",
    }
