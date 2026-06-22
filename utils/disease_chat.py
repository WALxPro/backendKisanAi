from __future__ import annotations

import json
import os
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

from utils.tools import (
    get_farm_context,
    build_disease_chat_system_prompt,
    build_crop_assistant_system_prompt,
    build_chat_messages,
)
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

MAX_WORDS = 50  # per-message word limit stays (keeps messages short/cheap) — chat count limit removed


def count_words(text: str) -> int:
    return len(text.split())


def validate_message_length(message: str) -> bool:
    return count_words(message) <= MAX_WORDS


def extract_general_answer(response_text: str) -> str:
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except Exception:
        return response_text

    if isinstance(parsed, dict):
        return str(parsed.get("answer") or response_text)

    return response_text

async def start_disease_chat(prediction_id: str, farmer_id: str, db) -> dict:
    prediction = await db.disease_predictions.find_one({"_id": ObjectId(prediction_id)})

    if not prediction:
        raise RuntimeError("Disease prediction not found")

    if prediction.get("farmer_id") and prediction.get("farmer_id") != farmer_id:
        raise RuntimeError("Disease prediction does not belong to this farmer")

    now = datetime.utcnow()
    farm_context = await get_farm_context(db=db, farmer_id=farmer_id)

    chat_record = {
        "chat_mode": "disease",
        "chat_type": "disease",
        "prediction_id": prediction_id,
        "farmer_id": farmer_id,
        "disease_name": prediction.get("predicted_class"),
        "disease_details": prediction.get("disease_details", {}),
        "farmer_name": farm_context.get("farmer_name"),
        "messages": [],
        "chat_count": 0,
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

    return {
        "chat_id": str(chat["_id"]),
        "chat_mode": "disease",
        "chat_count": chat.get("chat_count", 0),
        "messages": chat.get("messages", []),
        "can_continue": True,  # no limit — chat never locks
        "existing_chat": existing_chat,
        "message": "Existing chat loaded" if existing_chat else "Chat session started",
    }

async def start_general_chat(farmer_id: str, db) -> dict:
    now = datetime.utcnow()
    farm_context = await get_farm_context(db=db, farmer_id=farmer_id)

    chat_record = {
        "chat_mode": "general",
        "chat_type": "general",
        "farmer_id": farmer_id,
        "disease_name": None,
        "disease_details": {},
        "farmer_name": farm_context.get("farmer_name"),
        "messages": [],
        "chat_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    query = {"chat_mode": "general", "farmer_id": farmer_id}
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
        raise RuntimeError("Failed to load general chat session")

    return {
        "chat_id": str(chat["_id"]),
        "chat_mode": "general",
        "chat_count": chat.get("chat_count", 0),
        "messages": chat.get("messages", []),
        "can_continue": True,
        "existing_chat": existing_chat,
        "message": "Existing general chat loaded" if existing_chat else "General chat session started",
    }

async def send_disease_chat_message(request, db) -> dict:
    if not validate_message_length(request.user_message):
        raise ValueError("Message exceeds word limit")

    now = datetime.utcnow()

    chat_mode = getattr(request, "chat_mode", None) or getattr(request, "chat_type", None) or "disease"

    chat_query = {
        "_id": ObjectId(request.chat_id),
        "farmer_id": request.farmer_id,
    }

    if chat_mode == "general":
        chat_query["chat_mode"] = "general"
    else:
        chat_query["prediction_id"] = request.prediction_id

    chat = await db.disease_chats.find_one(chat_query)

    if not chat:
        raise RuntimeError("Chat session not found")

    if GEMINI_LLM is None:
        raise RuntimeError("AI assistant is not available. Please configure GEMINI_API_KEY.")

    farm_context = await get_farm_context(db=db, farmer_id=request.farmer_id)
    farm_context["language"] = request.language or "en"

    if chat_mode == "general":
        system_prompt = build_crop_assistant_system_prompt(
            farm_context,
            request.language or "en",
        )
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(build_chat_messages(chat.get("messages", [])))
        messages.append(HumanMessage(content=request.user_message))
    else:
        disease_name = chat.get("disease_name")
        disease_details = chat.get("disease_details", {})
        farm_context["disease_name"] = disease_name

        system_prompt = build_disease_chat_system_prompt(farm_context, disease_details)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=request.user_message),
        ]

    response = GEMINI_LLM.invoke(messages)
    ai_response = response.content if hasattr(response, "content") else str(response)
    if chat_mode == "general":
        ai_response = extract_general_answer(ai_response)

    new_messages = [
        {"role": "user", "content": request.user_message, "created_at": now},
        {"role": "assistant", "content": ai_response, "created_at": datetime.utcnow()},
    ]

    updated_chat = await db.disease_chats.find_one_and_update(
        chat_query,
        {
            "$push": {"messages": {"$each": new_messages}},
            "$inc": {"chat_count": 1},
            "$set": {"updated_at": datetime.utcnow()},
        },
        return_document=True,
    )

    if not updated_chat:
        raise RuntimeError("Failed to update chat session")

    return {
        "chat_id": str(updated_chat["_id"]),
        "chat_mode": chat_mode,
        "chat_count": updated_chat.get("chat_count", 1),
        "user_message": request.user_message,
        "ai_response": ai_response,
        "can_continue": True,  # no limit
        "message": "Response sent.",
    }
