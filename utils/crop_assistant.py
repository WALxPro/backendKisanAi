from __future__ import annotations

import json
import os
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage

from utils.tools import build_chat_messages, build_crop_assistant_system_prompt, get_farm_context

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")


def _is_valid_gemini_key(api_key: str | None) -> bool:
    if not api_key:
        return False
    normalized = api_key.strip()
    if not normalized:
        return False
    return normalized.lower() not in {"gemini_api_key", "google_api_key", "your_api_key"}


def _load_llm():
    if not _is_valid_gemini_key(GEMINI_API_KEY):
        raise RuntimeError("GEMINI_API_KEY is not configured")
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, temperature=0.3)


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


async def handle_crop_chat(payload, db) -> dict:
    llm = _load_llm()
    farm_context = await get_farm_context(
        db=db,
        farmer_id=payload.farmer_id,
    )
    system_prompt = build_crop_assistant_system_prompt(farm_context, payload.language)
    messages = [SystemMessage(content=system_prompt)]
    messages.extend(build_chat_messages([item.model_dump() if hasattr(item, "model_dump") else item for item in payload.chat_history]))
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
