<<<<<<< HEAD
from __future__ import annotations

import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
=======

from __future__ import annotations
from pymongo.errors import DuplicateKeyError
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
>>>>>>> 53c2c75 (chat issue resolve)
from bson import ObjectId

from utils.tools import get_farm_context, build_disease_chat_system_prompt

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
<<<<<<< HEAD

=======
>>>>>>> 53c2c75 (chat issue resolve)
    GEMINI_LLM = (
        ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, temperature=0.2)
        if GEMINI_API_KEY
        else None
    )
except Exception:
    GEMINI_LLM = None

MAX_CHATS = 3
MAX_WORDS = 50
<<<<<<< HEAD
=======
CHAT_LIMIT_MESSAGE = "Chat limit reached. Try after 2 minutes"
WINDOW_MINUTES = 2
>>>>>>> 53c2c75 (chat issue resolve)


def count_words(text: str) -> int:
    return len(text.split())


def validate_message_length(message: str) -> bool:
    return count_words(message) <= MAX_WORDS


async def start_disease_chat(prediction_id: str, farmer_id: str, db) -> dict:
    prediction = await db.disease_predictions.find_one({"_id": ObjectId(prediction_id)})
<<<<<<< HEAD
=======

>>>>>>> 53c2c75 (chat issue resolve)
    if not prediction:
        raise RuntimeError("Disease prediction not found")

    if prediction.get("farmer_id") and prediction.get("farmer_id") != farmer_id:
        raise RuntimeError("Disease prediction does not belong to this farmer")

<<<<<<< HEAD
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
=======
    now = datetime.utcnow()
    farm_context = await get_farm_context(db=db, farmer_id=farmer_id)

    chat_record = {
        "prediction_id": prediction_id,
        "farmer_id": farmer_id,
        "disease_name": prediction.get("predicted_class"),
        "disease_details": prediction.get("disease_details", {}),
>>>>>>> 53c2c75 (chat issue resolve)
        "farmer_name": farm_context.get("farmer_name"),
        "admin_name": farm_context.get("admin_name"),
        "messages": [],
        "chat_count": 0,
<<<<<<< HEAD
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
=======
        "window_started_at": None,
        "window_expires_at": None,
        "created_at": now,
        "updated_at": now,
    }

    query = {"prediction_id": prediction_id, "farmer_id": farmer_id}
    existing_chat = False

    try:
        result = await db.disease_chats.update_one(
            query,
            {"$setOnInsert": chat_record},
            upsert=True,
        )
        existing_chat = result.matched_count > 0
    except DuplicateKeyError:
        existing_chat = True

    chat = await db.disease_chats.find_one(query)

    if not chat:
        raise RuntimeError("Failed to load chat session")

    chat_count = chat.get("chat_count", 0)
    window_expires_at = chat.get("window_expires_at")

    # ✅ 2 min window expired → reset count → 3 fresh messages
    if chat_count >= MAX_CHATS and (not window_expires_at or now >= window_expires_at):
        await db.disease_chats.update_one(
            {"_id": chat["_id"]},
            {"$set": {
                "chat_count": 0,
                "window_started_at": None,
                "window_expires_at": None,
                "updated_at": now,
            }}
        )
        chat_count = 0
        window_expires_at = None

    remaining_chats = MAX_CHATS - chat_count

    return {
        "chat_id": str(chat["_id"]),
        "chat_count": chat_count,
        "remaining_chats": remaining_chats,
        "messages": chat.get("messages", []),
        "can_continue": remaining_chats > 0,
        "existing_chat": existing_chat,
        "message": "Existing chat loaded" if existing_chat else "Chat session started",
        "window_expires_at": window_expires_at,
>>>>>>> 53c2c75 (chat issue resolve)
    }


async def send_disease_chat_message(request, db) -> dict:
    if not validate_message_length(request.user_message):
        raise ValueError("Message exceeds word limit")

<<<<<<< HEAD
    chat = await db.disease_chats.find_one({"_id": ObjectId(request.prediction_id), "farmer_id": request.farmer_id})
=======
    now = datetime.utcnow()

    chat = await db.disease_chats.find_one({
        "_id": ObjectId(request.chat_id),
        "prediction_id": request.prediction_id,
        "farmer_id": request.farmer_id,
    })

>>>>>>> 53c2c75 (chat issue resolve)
    if not chat:
        raise RuntimeError("Chat session not found")

    chat_count = chat.get("chat_count", 0)
<<<<<<< HEAD
    if chat_count >= MAX_CHATS:
        raise RuntimeError("Chat limit reached")
=======
    window_expires_at = chat.get("window_expires_at")
    window_started_at = chat.get("window_started_at") or now

    # ✅ Window expired or never started → reset
    if not window_expires_at or now >= window_expires_at:
        window_started_at = now
        window_expires_at = now + timedelta(minutes=WINDOW_MINUTES)
        chat_count = 0

        await db.disease_chats.update_one(
            {"_id": chat["_id"]},
            {"$set": {
                "chat_count": 0,
                "window_started_at": window_started_at,
                "window_expires_at": window_expires_at,
                "updated_at": now,
            }}
        )

    if chat_count >= MAX_CHATS:
        raise RuntimeError(CHAT_LIMIT_MESSAGE)
>>>>>>> 53c2c75 (chat issue resolve)

    if GEMINI_LLM is None:
        raise RuntimeError("AI assistant is not available. Please configure GEMINI_API_KEY.")

    disease_name = chat.get("disease_name")
    disease_details = chat.get("disease_details", {})
<<<<<<< HEAD
    farm_context = await get_farm_context(db=db, farmer_id=request.farmer_id)
    farm_context["disease_name"] = disease_name
    system_prompt = build_disease_chat_system_prompt(farm_context, disease_details)

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=request.user_message)]
=======

    farm_context = await get_farm_context(db=db, farmer_id=request.farmer_id)
    farm_context["disease_name"] = disease_name
    farm_context["language"] = request.language or "en"

    system_prompt = build_disease_chat_system_prompt(farm_context, disease_details)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=request.user_message),
    ]

>>>>>>> 53c2c75 (chat issue resolve)
    response = GEMINI_LLM.invoke(messages)
    ai_response = response.content if hasattr(response, "content") else str(response)

    new_messages = [
<<<<<<< HEAD
        {"role": "user", "content": request.user_message, "created_at": datetime.utcnow()},
=======
        {"role": "user", "content": request.user_message, "created_at": now},
>>>>>>> 53c2c75 (chat issue resolve)
        {"role": "assistant", "content": ai_response, "created_at": datetime.utcnow()},
    ]

    updated_chat = await db.disease_chats.find_one_and_update(
<<<<<<< HEAD
        {"_id": ObjectId(request.prediction_id)},
        {"$push": {"messages": {"$each": new_messages}}, "$inc": {"chat_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
        return_document=True,
    )

=======
        {
            "_id": ObjectId(request.chat_id),
            "prediction_id": request.prediction_id,
            "farmer_id": request.farmer_id,
            "chat_count": {"$lt": MAX_CHATS},
        },
        {
            "$push": {"messages": {"$each": new_messages}},
            "$inc": {"chat_count": 1},
            "$set": {"updated_at": datetime.utcnow()},
        },
        return_document=True,
    )

    if not updated_chat:
        raise RuntimeError(CHAT_LIMIT_MESSAGE)

>>>>>>> 53c2c75 (chat issue resolve)
    new_chat_count = updated_chat.get("chat_count", 1)
    remaining_chats = MAX_CHATS - new_chat_count

    return {
        "chat_id": str(updated_chat["_id"]),
        "chat_count": new_chat_count,
        "remaining_chats": remaining_chats,
        "user_message": request.user_message,
        "ai_response": ai_response,
        "can_continue": remaining_chats > 0,
<<<<<<< HEAD
        "message": f"Response sent. You have {remaining_chats} chat(s) remaining.",
    }
=======
        "window_expires_at": updated_chat.get("window_expires_at"),
        "message": f"Response sent. You have {remaining_chats} chat(s) remaining.",
    }
>>>>>>> 53c2c75 (chat issue resolve)
