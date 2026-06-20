from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
import numpy as np
import tensorflow as tf
from dotenv import load_dotenv
from utils.leaf_detection import assert_leaf, LeafValidationError
from utils.image_preprocessing import preprocess_image_bytes

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "cnn_model" / "cnn_model" / "wheat_cnn_model_2.keras"
CLASS_INDICES_PATH = ROOT / "cnn_model" / "cnn_model" / "wheat_class_indices.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

try:
    with open(CLASS_INDICES_PATH, "r") as f:
        class_indices = json.load(f)
except Exception:
    class_indices = {}

CLASS_NAMES = {v: k for k, v in class_indices.items()}

DISEASE_DETAILS_CACHE: dict[str, dict[str, object]] = {}

try:
    from langchain_google_genai import ChatGoogleGenerativeAI

    GEMINI_LLM = (
        ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY, temperature=0.2)
        if GEMINI_API_KEY
        else None
    )
except Exception:
    GEMINI_LLM = None


def _format_label(label: str) -> str:
    text = label.replace("___", " ").replace("__", " ").replace("_", " ")
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    words = re.sub(r"\s+", " ", text).strip().split(" ")
    deduped_words = []
    for word in words:
        if not deduped_words or deduped_words[-1].lower() != word.lower():
            deduped_words.append(word)
    return " ".join(deduped_words)


def predict_with_rejection(model: tf.keras.Model, image_array: np.ndarray, class_names: list[str], threshold: float = 0.60) -> dict[str, object]:
    probabilities = model.predict(image_array, verbose=0)[0]
    top_index = int(np.argmax(probabilities))
    top_confidence = float(probabilities[top_index])

    epsilon = 1e-10
    entropy = -np.sum(probabilities * np.log(probabilities + epsilon))
    num_classes = len(class_names)
    max_entropy = np.log(num_classes)
    normalized_entropy = entropy / max_entropy

    print(f"[disease] top_confidence: {top_confidence}")
    print(f"[disease] entropy: {entropy:.4f}")
    print(f"[disease] normalized_entropy: {normalized_entropy:.4f}")

    if top_confidence < 0.60 or normalized_entropy > 0.75:
        return {
            "status": "invalid",
            "message": "Invalid image! Please upload a wheat plant image only.",
            "class": None,
            "confidence": None,
        }

    return {
        "status": "valid",
        "message": "Prediction completed successfully.",
        "class": class_names[top_index],
        "confidence": top_confidence,
    }


def _is_valid_gemini_key(api_key: str | None) -> bool:
    if not api_key:
        return False
    normalized = api_key.strip()
    if not normalized:
        return False
    if normalized.lower() in {"gemini_api_key", "google_api_key", "your_api_key"}:
        return False
    return True


def _build_disease_prompt(disease_name: str, language: str = "en") -> str:
    readable_name = _format_label(disease_name)

    # Language instruction
    if language == "ur":
        lang_instruction = (
            "Respond ENTIRELY in Urdu language. "
            "Use simple Urdu words that a village farmer can understand. "
            "For the disease_name field: write the Urdu translation of the disease name "
            "(e.g. 'پتوں کا جھلساؤ' for LeafBlight, 'گندم کا دھماکہ' for WheatBlast, "
            "'کالا نقطہ' for BlackPoint, 'بہت زیادہ پاؤں کی سڑاند' for FusariumFootRot, "
            "'صحت مند پتہ' for HealthyLeaf). "
            "For the crop_name field: write 'گندم'. "
            "All other fields must also be in Urdu. Do not use English words anywhere. "
        )
    else:
        lang_instruction = (
            "Respond in simple English. "
        )

    prompt = (
        "You are an agriculture assistant for small farmers. "
        "The farmer may not be highly literate, so use very easy words and very short sentences. "
        "Avoid technical terms. Be practical and kind. "
        + lang_instruction +
        "Return ONLY valid JSON with these exact keys: "
        "disease_name, crop_name, disease_status, description, symptoms, causes, prevention, treatment, immediate_actions, when_to_seek_expert_help, spread_risk, confidence_note. "
        "description, causes, spread_risk, confidence_note, when_to_seek_expert_help should be short plain text. "
        "symptoms, prevention, treatment, immediate_actions should be arrays with 3 to 5 short bullet-like strings each. "
        "Keep the response practical and concise. "
        "If the plant appears healthy, clearly say it looks healthy and give only basic care tips. "
        f"Detected wheat disease name: {readable_name}."
    )
    return prompt


def _parse_gemini_text(response_text: str) -> dict[str, object]:
    cleaned_text = response_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:]
        cleaned_text = cleaned_text.strip()
    try:
        parsed = json.loads(cleaned_text)
        return parsed
    except json.JSONDecodeError:
        return {
            "disease_name": "",
            "crop_name": "",
            "disease_status": "unknown",
            "description": cleaned_text,
            "symptoms": [],
            "causes": "",
            "prevention": [],
            "treatment": [],
            "immediate_actions": [],
            "when_to_seek_expert_help": "",
            "spread_risk": "",
            "confidence_note": "",
        }


def _as_text_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return []


def _gemini_unavailable_response(disease_name: str) -> dict[str, object]:
    readable_name = _format_label(disease_name)
    return {
        "disease_name": readable_name,
        "crop_name": "Wheat",
        "disease_status": "unknown",
        "description": "Detailed disease explanation is not available right now.",
        "symptoms": [],
        "causes": "",
        "prevention": [],
        "treatment": [],
        "immediate_actions": ["Please try again after configuring a valid Gemini API key."],
        "when_to_seek_expert_help": "If symptoms spread quickly, contact an agriculture expert.",
        "spread_risk": "Unknown",
        "confidence_note": "AI details unavailable.",
        "simple_description": "Detailed disease explanation is not available right now.",
        "what_farmer_should_do_now": "Please try again after configuring a valid Gemini API key.",
        "prevention_tips": "",
        "source": "unavailable",
    }


def _get_disease_details(disease_name: str, language: str = "en") -> dict[str, object]:
    # Cache key includes language so Urdu/English cached separately
    cache_key = f"{disease_name}_{language}"

    if cache_key in DISEASE_DETAILS_CACHE:
        return DISEASE_DETAILS_CACHE[cache_key]

    if not _is_valid_gemini_key(GEMINI_API_KEY):
        unavailable = _gemini_unavailable_response(disease_name)
        DISEASE_DETAILS_CACHE[cache_key] = unavailable
        return unavailable

    try:
        if GEMINI_LLM is None:
            raise ValueError("Gemini LLM is not configured")

        print(f"[disease] Fetching Gemini description in language: {language}")
        llm_response = GEMINI_LLM.invoke(_build_disease_prompt(disease_name, language))
        text = llm_response.content if hasattr(llm_response, "content") else str(llm_response)
        parsed = _parse_gemini_text(text)

        description = str(parsed.get("description") or parsed.get("simple_description") or "")
        immediate_actions = _as_text_list(parsed.get("immediate_actions") or parsed.get("what_farmer_should_do_now"))
        prevention = _as_text_list(parsed.get("prevention") or parsed.get("prevention_tips"))

        result = {
            "disease_name": parsed.get("disease_name") or _format_label(disease_name),
            "crop_name": parsed.get("crop_name") or "Wheat",
            "disease_status": parsed.get("disease_status") or "infected",
            "description": description,
            "symptoms": _as_text_list(parsed.get("symptoms")),
            "causes": str(parsed.get("causes") or ""),
            "prevention": prevention,
            "treatment": _as_text_list(parsed.get("treatment")),
            "immediate_actions": immediate_actions,
            "when_to_seek_expert_help": str(parsed.get("when_to_seek_expert_help") or ""),
            "spread_risk": str(parsed.get("spread_risk") or ""),
            "confidence_note": str(parsed.get("confidence_note") or ""),
            "simple_description": description,
            "what_farmer_should_do_now": " ".join(immediate_actions),
            "prevention_tips": " ".join(prevention),
            "source": "gemini",
            "language": language,
        }

        DISEASE_DETAILS_CACHE[cache_key] = result
        return result

    except Exception as e:
        print(f"[disease] Gemini description error: {e}")
        unavailable = _gemini_unavailable_response(disease_name)
        DISEASE_DETAILS_CACHE[cache_key] = unavailable
        return unavailable


def _load_model():
    if not MODEL_PATH.exists():
        raise RuntimeError(f"CNN model not found at {MODEL_PATH}")
    return tf.keras.models.load_model(str(MODEL_PATH), compile=False)


MODEL = _load_model()


def _clear_model_state():
    for layer in MODEL.layers:
        if hasattr(layer, 'reset_states'):
            layer.reset_states()


async def handle_prediction(image_bytes: bytes, farmer_id: str, user_email: str | None, image_name: str | None, db, language: str = "en") -> dict:
    """Run prediction, generate disease details, save to DB, and return a response dict."""

    print(f"[disease] Language received: {language}")

    # ── STEP 1: Gemini wheat validation ─────────────────────────────────────
    try:
        assert_leaf(image_bytes)
    except LeafValidationError as e:
        return {
            "message": str(e),
            "prediction": {
                "status": "invalid",
                "message": str(e),
                "class": None,
                "confidence": None,
            },
            "database_updated": False,
        }

    # ── STEP 2: CNN disease classification ──────────────────────────────────
    _clear_model_state()

    image_array = preprocess_image_bytes(
        image_bytes,
        (256, 256),
        debug_label="disease",
        expected_batch_shape=(1, 256, 256, 3),
        normalize=True,
    )
    print(f"[disease] model expected input shape: {MODEL.input_shape}")
    print(f"[disease] tensor fed to model: {image_array.shape}")

    class_names = [CLASS_NAMES[index] for index in sorted(CLASS_NAMES.keys())]
    prediction_result = predict_with_rejection(model=MODEL, image_array=image_array, class_names=class_names)

    if prediction_result["status"] == "invalid":
        return {"message": prediction_result["message"], "prediction": prediction_result, "database_updated": False}

    probabilities = MODEL.predict(image_array, verbose=0)[0]
    top_class = str(prediction_result["class"])
    top_confidence = float(prediction_result["confidence"]) if prediction_result.get("confidence") is not None else 0.0

    ranked_predictions = []
    for index in np.argsort(probabilities)[::-1][:3]:
        index = int(index)
        ranked_predictions.append({
            "class_name": CLASS_NAMES[index],
            "display_name": _format_label(CLASS_NAMES[index]),
            "confidence": float(probabilities[index]),
        })

    prediction_record = {
        "farmer_id": farmer_id,
        "user_email": user_email,
        "image_name": image_name or None,
        "predicted_class": top_class,
        "predicted_label": _format_label(top_class),
        "confidence": top_confidence,
        "top_predictions": ranked_predictions,
        "disease_details": _get_disease_details(top_class, language),  # ← language pass
        "language": language,
        "createdAt": datetime.utcnow(),
    }

    result = await db.disease_predictions.insert_one(prediction_record)
    prediction_record["_id"] = str(result.inserted_id)

    return {"message": "Disease prediction completed successfully", "prediction": prediction_record, "database_updated": True}