from __future__ import annotations

from typing import Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

<<<<<<< HEAD

async def get_farm_context(db, farmer_id: str, admin_email: str | None = None) -> dict[str, Any]:
    farmer = await db.farmers.find_one({"farmer_id": farmer_id})
    if not farmer:
=======
KAKU_DISEASE_CHAT_PROMPT = """
You are KisanAI disease chat assistant for farmer {farmer_name}.
This farmer is managed through admin {admin_name}.
The farmer's crop is {crop_name}. The detected disease is {disease_name}.

Language rule:
- If output_language is "ur", reply in Urdu.
- If output_language is "en" or missing, reply in English.

Behavior rules:
- Answer only plant disease and crop-health questions.
- Use simple, practical words.
- Avoid technical terms.
- Keep replies short and helpful.
- If the question is outside plant disease guidance, respond with a short redirect to crop health topics.

Disease information:
Description: {description}
Symptoms: {symptoms}
Treatment: {treatment}
Prevention: {prevention}

Output language: {output_language}
""".strip()  # FIX: keep all Kaku disease-chat behavior in one central prompt string.


async def get_farm_context(db, farmer_id: str, admin_email: str | None = None) -> dict[str, Any]:
    # Try multiple lookup strategies because frontends may pass different id types:
    # 1. `farmer_id` field (legacy)
    # 2. `uid` field (Firebase UID)
    # 3. `_id` (Mongo ObjectId string)
    farmer = await db.farmers.find_one({"farmer_id": farmer_id})
    if not farmer:
        farmer = await db.farmers.find_one({"uid": farmer_id})
    if not farmer:
        try:
            from bson import ObjectId

            farmer = await db.farmers.find_one({"_id": ObjectId(farmer_id)})
        except Exception:
            farmer = None

    if not farmer:
>>>>>>> 53c2c75 (chat issue resolve)
        raise RuntimeError("Farmer not found")

    admin = None
    if admin_email:
        admin = await db.admins.find_one({"email": admin_email})
    if admin is None:
        admin = await db.admins.find_one({})

    farmer_name = farmer.get("fullname") or farmer.get("name") or "Farmer"
<<<<<<< HEAD
    crop_detail = farmer.get("cropDetail") or {}
    crop_name = crop_detail.get("cropName") or crop_detail.get("crop_name") or "any crop"
    location = crop_detail.get("city") or crop_detail.get("location") or "unknown location"
=======
    # Prefer top-level crop fields if frontend sends them, otherwise fall back to legacy `cropDetail`
    crop_detail = farmer.get("crop_detail") or farmer.get("cropDetail") or {}
    crop_name = (
        farmer.get("crop_name")
        or farmer.get("cropName")
        or crop_detail.get("cropName")
        or crop_detail.get("crop_name")
        or "any crop"
    )
    location = (
        farmer.get("location")
        or farmer.get("city")
        or crop_detail.get("city")
        or crop_detail.get("location")
        or "unknown location"
    )
>>>>>>> 53c2c75 (chat issue resolve)

    admin_name = (admin or {}).get("name") or "Admin"
    admin_profile_picture = (admin or {}).get("profile_picture") or None

    return {
        "farmer_id": farmer_id,
        "farmer_name": farmer_name,
        "crop_name": crop_name,
        "location": location,
        "admin_name": admin_name,
        "admin_profile_picture": admin_profile_picture,
        "crop_detail": crop_detail,
        "farmer": farmer,
        "admin": admin,
    }


def build_crop_assistant_system_prompt(context: dict[str, Any], language: str | None = "en") -> str:
    crop_name = context.get("crop_name") or "any crop"
    location = context.get("location") or "unknown location"
    farmer_name = context.get("farmer_name") or "Farmer"
    admin_name = context.get("admin_name") or "Admin"
    farmer_id = context.get("farmer_id") or ""
    language_code = language.strip() if language else "en"

    return (
        f"You are KisanAI Crop Assistant for farmer {farmer_name} (farmer id: {farmer_id}). "
        f"The farmer is being supported by admin {admin_name}. "
        "Answer in simple, clear language. Keep responses short but useful. "
        "Use practical farming advice only. Avoid technical terms. "
        "Cover crops, diseases, fertilizers, irrigation, weather impact, pest control, and harvesting tips. "
        "If the user asks about severe disease, toxic chemicals, or urgent crop loss, advise contacting a local agriculture expert. "
        "If live weather data is not provided, give general weather-based farming advice only. "
        "Return ONLY valid JSON with these exact keys: answer, topic, crop_name, urgency, suggested_prompts, safety_note. "
        "answer must be a helpful natural-language reply. "
        "topic must be one word or short phrase like disease, fertilizer, weather, irrigation, harvesting, pest, general. "
        "urgency must be one of low, medium, high, or unknown. "
        "suggested_prompts must be an array of 3 short follow-up questions. "
        "safety_note must be one short practical warning or empty string. "
        f"Known crop context: {crop_name}. Location context: {location}. Output language code: {language_code}."
    )


def build_disease_chat_system_prompt(context: dict[str, Any], disease_details: dict[str, Any]) -> str:
    disease_name = context.get("disease_name") or "the detected disease"
    farmer_name = context.get("farmer_name") or "Farmer"
    admin_name = context.get("admin_name") or "Admin"
    crop_name = context.get("crop_name") or "unknown crop"
<<<<<<< HEAD
=======
    output_language = context.get("language") or "en"  # FIX: default Kaku replies to English when no language is provided.
>>>>>>> 53c2c75 (chat issue resolve)
    description = disease_details.get("description", "")
    symptoms = ", ".join(disease_details.get("symptoms", []))
    treatment = ", ".join(disease_details.get("treatment", []))
    prevention = ", ".join(disease_details.get("prevention", []))

<<<<<<< HEAD
    return (
        f"You are KisanAI disease chat assistant for farmer {farmer_name}. "
        f"This farmer is managed through admin {admin_name}. "
        f"The farmer's crop is {crop_name}. The detected disease is {disease_name}. "
        "Answer only plant disease and crop-health questions. Use simple, practical words. "
        "Avoid technical terms. Keep replies short and helpful. "
        f"Disease information: {description}. Symptoms: {symptoms}. Treatment: {treatment}. Prevention: {prevention}. "
        "If the question is outside plant disease guidance, respond with a short redirect to crop health topics."
    )
=======
    return KAKU_DISEASE_CHAT_PROMPT.format(
        farmer_name=farmer_name,
        admin_name=admin_name,
        crop_name=crop_name,
        disease_name=disease_name,
        description=description,
        symptoms=symptoms,
        treatment=treatment,
        prevention=prevention,
        output_language=output_language,
    )  # FIX: changing KAKU_DISEASE_CHAT_PROMPT now changes Kaku behavior globally.
>>>>>>> 53c2c75 (chat issue resolve)


def build_chat_messages(chat_history: list[dict]) -> list[HumanMessage | AIMessage | SystemMessage]:
    messages: list[HumanMessage | AIMessage | SystemMessage] = []
    for item in chat_history:
        role = item.get("role")
        content = item.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))
    return messages
