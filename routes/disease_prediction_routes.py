from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from database import db
from datetime import datetime
import json
import os
from pathlib import Path
import re
import numpy as np
import tensorflow as tf
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

router = APIRouter()

MODEL_PATH = Path(__file__).resolve().parents[1] / "cnn_model" / "cnn_model_2.h5"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
CLASS_INDICES_PATH = Path(__file__).resolve().parents[1] / "cnn_model" / "class_indices.json"

with open(CLASS_INDICES_PATH, "r") as f:
    class_indices = json.load(f)

# Reverse mapping
CLASS_NAMES = {v: k for k, v in class_indices.items()}

DISEASE_DETAILS_CACHE: dict[str, dict[str, object]] = {}
GEMINI_LLM = (
    ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.2,
    )
    if GEMINI_API_KEY
    else None
)


def _load_model():
    if not MODEL_PATH.exists():
        raise RuntimeError(f"CNN model not found at {MODEL_PATH}")
    return tf.keras.models.load_model(str(MODEL_PATH), compile=False)


MODEL = _load_model()


def _format_label(label: str) -> str:
    text = label.replace("___", " ").replace("__", " ").replace("_", " ")
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    words = re.sub(r"\s+", " ", text).strip().split(" ")

    # Some labels come as "Rice Rice Neck Blast"; collapse repeated adjacent words.
    deduped_words = []
    for word in words:
        if not deduped_words or deduped_words[-1].lower() != word.lower():
            deduped_words.append(word)

    return " ".join(deduped_words)


def _preprocess_image(image_bytes: bytes) -> np.ndarray:
    image_tensor = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image_tensor = tf.image.resize(image_tensor, (256, 256))
    image_tensor = tf.cast(image_tensor, tf.float32) / 255.0
    return np.expand_dims(image_tensor.numpy(), axis=0)


def predict_with_rejection(
    model: tf.keras.Model,
    image_array: np.ndarray,
    class_names: list[str],
    threshold: float = 0.70,
) -> dict[str, object]:
    probabilities = model.predict(image_array, verbose=0)[0]
    top_index = int(np.argmax(probabilities))
    top_confidence = float(probabilities[top_index])

    if top_confidence < threshold:
        return {
            "status": "invalid",
            "message": "Invalid image! Please upload a crop image of corn, wheat, rice, sugarcane, or potato only.",
            "class": None,
            "confidence": None,
        }

    return {
        "status": "valid",
        "message": "Prediction completed successfully.",
        "class": class_names[top_index],
        "confidence": top_confidence,
    }


def _build_disease_prompt(disease_name: str) -> str:
    readable_name = _format_label(disease_name)
    return (
        "You are an agriculture assistant for small farmers. "
        "The farmer may not be highly literate, so use very easy words and very short sentences. "
        "Avoid technical terms. Be practical and kind. "
        "Return ONLY valid JSON with these exact keys: "
        "disease_name, crop_name, disease_status, description, symptoms, causes, prevention, treatment, immediate_actions, when_to_seek_expert_help, spread_risk, confidence_note. "
        "description, causes, spread_risk, confidence_note, when_to_seek_expert_help should be short plain text. "
        "symptoms, prevention, treatment, immediate_actions should be arrays with 3 to 5 short bullet-like strings each. "
        "Keep the response practical and concise. "
        "If the plant appears healthy, clearly say it looks healthy and give only basic care tips. "
        f"Detected disease name: {readable_name}."
    )


def _parse_gemini_text(response_text: str) -> dict[str, object]:
    cleaned_text = response_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:]
        cleaned_text = cleaned_text.strip()

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        # If Gemini returns plain text, still provide a usable structure.
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


def _is_valid_gemini_key(api_key: str | None) -> bool:
    if not api_key:
        return False

    normalized = api_key.strip()
    if not normalized:
        return False

    # Guard against placeholder values in .env like GEMINI_API_KEY=GEMINI_API_KEY
    if normalized.lower() in {"gemini_api_key", "google_api_key", "your_api_key"}:
        return False

    return True


def _gemini_unavailable_response(disease_name: str) -> dict[str, object]:
    readable_name = _format_label(disease_name)
    return {
        "disease_name": readable_name,
        "crop_name": readable_name.split(" ")[0] if readable_name else "",
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
        # Backward-compatible fields.
        "simple_description": "Detailed disease explanation is not available right now.",
        "what_farmer_should_do_now": "Please try again after configuring a valid Gemini API key.",
        "prevention_tips": "",
        "source": "unavailable",
    }


def _get_disease_details(disease_name: str) -> dict[str, object]:
    if disease_name in DISEASE_DETAILS_CACHE:
        return DISEASE_DETAILS_CACHE[disease_name]

    if not _is_valid_gemini_key(GEMINI_API_KEY):
        unavailable = _gemini_unavailable_response(disease_name)
        DISEASE_DETAILS_CACHE[disease_name] = unavailable
        return unavailable

    try:
        if GEMINI_LLM is None:
            raise ValueError("Gemini LLM is not configured")

        llm_response = GEMINI_LLM.invoke(_build_disease_prompt(disease_name))
        text = llm_response.content if hasattr(llm_response, "content") else str(llm_response)
        parsed = _parse_gemini_text(text)
        description = str(parsed.get("description") or parsed.get("simple_description") or "")
        immediate_actions = _as_text_list(
            parsed.get("immediate_actions") or parsed.get("what_farmer_should_do_now")
        )
        prevention = _as_text_list(parsed.get("prevention") or parsed.get("prevention_tips"))
        result = {
            "disease_name": parsed.get("disease_name") or _format_label(disease_name),
            "crop_name": parsed.get("crop_name") or _format_label(disease_name).split(" ")[0],
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
            # Backward-compatible fields.
            "simple_description": description,
            "what_farmer_should_do_now": " ".join(immediate_actions),
            "prevention_tips": " ".join(prevention),
            "source": "gemini",
        }
        DISEASE_DETAILS_CACHE[disease_name] = result
        return result
    except Exception:
        unavailable = _gemini_unavailable_response(disease_name)
        DISEASE_DETAILS_CACHE[disease_name] = unavailable
        return unavailable


@router.post("/predict")
async def predict_disease(
    image: UploadFile = File(...),
    user_email: str | None = Form(default=None),
    image_name: str | None = Form(default=None),
):
    try:
        if image.content_type and not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Uploaded file must be an image")

        image_bytes = await image.read()
        image_array = _preprocess_image(image_bytes)

        class_names = [CLASS_NAMES[index] for index in sorted(CLASS_NAMES.keys())]
        prediction_result = predict_with_rejection(
            model=MODEL,
            image_array=image_array,
            class_names=class_names,
        )

        if prediction_result["status"] == "invalid":
            return {
                "message": prediction_result["message"],
                "prediction": prediction_result,
                "database_updated": False,
            }

        probabilities = MODEL.predict(image_array, verbose=0)[0]
        top_class = str(prediction_result["class"])
        top_confidence = float(prediction_result["confidence"])

        ranked_predictions = []
        for index in np.argsort(probabilities)[::-1][:3]:
            index = int(index)
            ranked_predictions.append(
                {
                    "class_name": CLASS_NAMES[index],
                    "display_name": _format_label(CLASS_NAMES[index]),
                    "confidence": float(probabilities[index]),
                }
            )

        prediction_record = {
            "user_email": user_email,
            "image_name": image_name or image.filename,
            "predicted_class": top_class,
            "predicted_label": _format_label(top_class),
            "confidence": top_confidence,
            "top_predictions": ranked_predictions,
            "disease_details": _get_disease_details(top_class),
            "createdAt": datetime.utcnow(),
        }

        result = await db.disease_predictions.insert_one(prediction_record)
        prediction_record["_id"] = str(result.inserted_id)

        return {
            "message": "Disease prediction completed successfully",
            "prediction": prediction_record,
            "database_updated": True,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(exc)}") from exc