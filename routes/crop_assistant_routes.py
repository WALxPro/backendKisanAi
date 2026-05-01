from __future__ import annotations

import json
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

load_dotenv()

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)


class CropChatRequest(BaseModel):
    question: str = Field(min_length=1)
    crop_name: str | None = None
    location: str | None = None
    language: str | None = "en"
    chat_history: list[ChatMessage] = Field(default_factory=list)


def _is_valid_gemini_key(api_key: str | None) -> bool:
    if not api_key:
        return False

    normalized = api_key.strip()
    if not normalized:
        return False

    return normalized.lower() not in {"gemini_api_key", "google_api_key", "your_api_key"}


def _load_llm() -> ChatGoogleGenerativeAI:
    if not _is_valid_gemini_key(GEMINI_API_KEY):
        raise RuntimeError("GEMINI_API_KEY is not configured")

    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.3,
    )


def _build_system_prompt(crop_name: str | None, location: str | None, language: str | None) -> str:
    crop_text = crop_name.strip() if crop_name else "any crop"
    location_text = location.strip() if location else "an unknown location"
    language_text = language.strip() if language else "en"

    return (
        "You are KisanAI Crop Assistant, a practical agriculture expert for farmers. "
        "Answer in simple, clear language. Keep responses short but useful. "
        "Cover crops, diseases, fertilizers, irrigation, weather impact, pest control, and harvesting tips. "
        "Do not claim to be a doctor or government officer. "
        "If the user asks about severe disease, toxic chemicals, or urgent crop loss, advise contacting a local agriculture expert. "
        "If the user asks about weather and no live weather data is provided, give general weather-based farming advice only. "
        "Return ONLY valid JSON with these exact keys: answer, topic, crop_name, urgency, suggested_prompts, safety_note. "
        "answer must be a helpful natural-language reply. "
        "topic must be one word or short phrase like disease, fertilizer, weather, irrigation, harvesting, pest, general. "
        "urgency must be one of low, medium, high, or unknown. "
        "suggested_prompts must be an array of 3 short follow-up questions. "
        "safety_note must be one short practical warning or empty string. "
        f"Known crop context: {crop_text}. Location context: {location_text}. Output language code: {language_text}."
    )


def _history_to_messages(chat_history: list[ChatMessage]) -> list[HumanMessage | AIMessage | SystemMessage]:
    messages: list[HumanMessage | AIMessage | SystemMessage] = []

    for item in chat_history:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            messages.append(AIMessage(content=item.content))
        elif item.role == "system":
            messages.append(SystemMessage(content=item.content))

    return messages


def _parse_json_response(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini response was not a JSON object")
        return parsed
    except Exception:
        return {
            "answer": cleaned,
            "topic": "general",
            "crop_name": "",
            "urgency": "unknown",
            "suggested_prompts": [],
            "safety_note": "",
        }


@router.post("/chat")
async def crop_assistant_chat(payload: CropChatRequest):
    try:
        llm = _load_llm()
        messages = [SystemMessage(content=_build_system_prompt(payload.crop_name, payload.location, payload.language))]
        messages.extend(_history_to_messages(payload.chat_history))
        messages.append(HumanMessage(content=payload.question))

        response = llm.invoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)
        parsed = _parse_json_response(response_text)

        answer = str(parsed.get("answer") or "")
        topic = str(parsed.get("topic") or "general")
        crop_name = str(parsed.get("crop_name") or payload.crop_name or "")
        urgency = str(parsed.get("urgency") or "unknown")
        suggested_prompts = parsed.get("suggested_prompts")
        safety_note = str(parsed.get("safety_note") or "")

        if not isinstance(suggested_prompts, list):
            suggested_prompts = []

        suggested_prompts = [str(item).strip() for item in suggested_prompts if str(item).strip()][:3]

        return {
            "status": "success",
            "message": "Crop assistant reply generated successfully",
            "data": {
                "answer": answer,
                "topic": topic,
                "crop_name": crop_name,
                "urgency": urgency,
                "suggested_prompts": suggested_prompts,
                "safety_note": safety_note,
                "source": "gemini",
            },
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crop assistant chat failed: {str(exc)}") from exc