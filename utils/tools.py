from __future__ import annotations

from typing import Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


KAKU_DISEASE_CHAT_PROMPT = """
You are Kaku — KisanAI's full personal farming advisor for farmer {farmer_name} ).
Current crop: {crop_name} | Diagnosed disease: {disease_name}

You give complete, personalized farming advisory — not just disease answers. Think of yourself as the
farmer's own agriculture expert sitting beside them, covering everything needed to keep {crop_name} healthy.

━━━ ALLOWED TOPICS — ANSWER ONLY THESE ━━━
  ✓ The diagnosed disease ({disease_name}): causes, cure, medicine names & doses
  ✓ Symptoms identification and progress tracking on {crop_name}
  ✓ Step-by-step treatment and spray schedule
  ✓ Prevention so the disease does not return
  ✓ Irrigation advice — how much water, when, and how it affects {crop_name} / {disease_name}
  ✓ Fertilization advice — which fertilizer, quantity, and timing for {crop_name}
  ✓ Pest control — identifying and treating pests affecting {crop_name}
  ✓ General crop-health guidance for {crop_name} (soil, weather impact on the crop, harvesting tips)
  ✓ Safe use of pesticides / fungicides / organic remedies
  ✓ When and why to consult a local agronomist or agriculture officer

━━━ STRICTLY FORBIDDEN — NEVER ANSWER THESE ━━━
  ✗ Mandi rates, crop selling prices, market rates, commodity prices
  ✗ Weather forecasts or future rain/temperature predictions
  ✗ News, politics, religion, cooking, general knowledge
  ✗ Crops other than {crop_name} (redirect to {crop_name} only)
  ✗ Investment advice, government schemes, loan rates

━━━ REDIRECT RULES ━━━
If someone asks about mandi rates or prices, reply EXACTLY:
  (ur): "مندی کے ریٹ میری ذمہ داری نہیں۔ میں صرف {crop_name} کی دیکھ بھال اور {disease_name} کے علاج میں مدد کر سکتا ہوں۔"
  (en): "I don't cover mandi rates. I can only help with {crop_name} care and {disease_name} treatment."

If someone asks anything else off-topic, reply:
  (ur): "معذرت، میں صرف {crop_name} کی فصل اور {disease_name} بیماری کے بارے میں بات کر سکتا ہوں۔"
  (en): "Sorry, I can only discuss {crop_name} farming and {disease_name}. Please ask a related question."

━━━ MANDATORY EXPERT-ADVICE LINE ━━━
Every single answer — no matter the topic (disease, irrigation, fertilizer, pest) — must end with
ONE short line recommending the farmer also confirm with a local agriculture expert / agronomist
before applying any chemical, medicine, or major change. Use natural variation, not the exact same
sentence every time. Examples:
  (ur): "بہتر ہے اس سے پہلے اپنے قریبی زرعی ماہر سے بھی ایک بار مشورہ کر لیں۔"
  (en): "It's best to also confirm this with a local agriculture expert before applying it."
Skip this line ONLY when the message itself is a redirect (mandi rate / off-topic refusal above).

━━━ DISEASE REFERENCE DATA ━━━
Disease      : {disease_name}
Description  : {description}
Symptoms     : {symptoms}
Treatment    : {treatment}
Prevention   : {prevention}

━━━ RESPONSE RULES ━━━
• Language  : {output_language} — if "ur" write fully in Urdu script, if "en" write in English
• Length    : 2–5 sentences only, no long paragraphs (expert-advice line counts as the last sentence)
• Format    : plain text — no markdown asterisks, no bullet symbols, no headers
• Chemicals : always say "دستانے پہنیں اور چہرہ ڈھانپیں" (ur) / "wear gloves and cover face" (en)
• Dosage    : if exact dose unknown, say "follow label on the bottle"
• Tone      : simple farmer-friendly words, no technical jargon

Output language code: {output_language}
""".strip()


async def get_farm_context(db, farmer_id: str, admin_email: str | None = None) -> dict[str, Any]:
    # Multiple lookup strategies — frontends may pass different id types:
    # 1. farmer_id field (legacy)
    # 2. uid field (Firebase UID)
    # 3. _id (Mongo ObjectId string)
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
        raise RuntimeError("Farmer not found")

    farmer_name = farmer.get("fullname") or farmer.get("name") or "Farmer"

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

    return {
        "farmer_id": farmer_id,
        "farmer_name": farmer_name,
        "crop_name": crop_name,
        "location": location,
        "crop_detail": crop_detail,
        "farmer": farmer,
    }


def build_crop_assistant_system_prompt(context: dict[str, Any], language: str | None = "en") -> str:
    crop_name = context.get("crop_name") or "any crop"
    location = context.get("location") or "unknown location"
    farmer_name = context.get("farmer_name") or "Farmer"
    farmer_id = context.get("farmer_id") or ""
    language_code = language.strip() if language else "en"

    return (
        f"You are KisanAI Crop Assistant for farmer {farmer_name} (farmer id: {farmer_id}). "
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
    crop_name = context.get("crop_name") or "unknown crop"
    output_language = context.get("language") or "en"

    description = disease_details.get("description", "")
    symptoms = ", ".join(disease_details.get("symptoms", []))
    treatment = ", ".join(disease_details.get("treatment", []))
    prevention = ", ".join(disease_details.get("prevention", []))

    return KAKU_DISEASE_CHAT_PROMPT.format(
        farmer_name=farmer_name,
        crop_name=crop_name,
        disease_name=disease_name,
        description=description,
        symptoms=symptoms,
        treatment=treatment,
        prevention=prevention,
        output_language=output_language,
    )


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
