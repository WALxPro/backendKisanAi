from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from database import db
from datetime import datetime
import json
import os
from pathlib import Path
import re
import numpy as np
import requests
import tensorflow as tf
import base64
import io
from PIL import Image


router = APIRouter()
def decode_base64_image(base64_str: str):
    image_bytes = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = image.resize((256, 256))
    image = np.array(image) / 255.0
    return np.expand_dims(image, axis=0)

MODEL_PATH = Path(__file__).resolve().parents[1] / "cnn_model" / "cnn_model.h5"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)
CLASS_NAMES = [
    "Corn___Common_Rust",
    "Corn___Gray_Leaf_Spot",
    "Corn___Healthy",
    "Corn___Northern_Leaf_Blight",
    "Potato___Early_Blight",
    "Potato___Healthy",
    "Potato___Late_Blight",
    "Rice___Brown_Spot",
    "Rice___Healthy",
    "Rice___Leaf_Blast",
    "Rice___Neck_Blast",
    "Sugarcane__BacterialBlight",
    "Sugarcane__Healthy",
    "Sugarcane__RedRot",
    "Wheat___Brown_Rust",
    "Wheat___Healthy",
    "Wheat___Yellow_Rust",
]

DISEASE_DETAILS_CACHE: dict[str, dict[str, str]] = {}


def _load_model():
    if not MODEL_PATH.exists():
        raise RuntimeError(f"CNN model not found at {MODEL_PATH}")
    return tf.keras.models.load_model(str(MODEL_PATH), compile=False)


MODEL = _load_model()


def _format_label(label: str) -> str:
    text = label.replace("___", " ").replace("__", " ").replace("_", " ")
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _preprocess_image(image_bytes: bytes) -> np.ndarray:
    image_tensor = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image_tensor = tf.image.resize(image_tensor, (256, 256))
    image_tensor = tf.cast(image_tensor, tf.float32) / 255.0
    return np.expand_dims(image_tensor.numpy(), axis=0)


def _build_disease_prompt(disease_name: str) -> str:
    readable_name = _format_label(disease_name)
    return (
        "You are helping a farmer. Explain the plant disease in simple, practical language. "
        "Return ONLY valid JSON with these keys: disease_name, description, symptoms, causes, prevention, treatment, urgency. "
        "Use short, clear sentences. If the class is healthy, explain that the plant appears healthy and mention general monitoring advice. "
        f"Disease class: {disease_name}. Readable name: {readable_name}."
    )


def _parse_gemini_text(response_text: str) -> dict[str, object]:
    cleaned_text = response_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.strip("`")
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:]
        cleaned_text = cleaned_text.strip()

    return json.loads(cleaned_text)


def _fallback_disease_details(disease_name: str) -> dict[str, object]:
    readable_name = _format_label(disease_name)
    if "Healthy" in disease_name:
        return {
            "disease_name": readable_name,
            "description": "The model detected a healthy plant leaf with no obvious disease symptoms.",
            "symptoms": ["No obvious spots, blight, or rust visible."],
            "causes": ["Normal plant condition"],
            "prevention": ["Keep monitoring leaves regularly", "Maintain proper irrigation and nutrition"],
            "treatment": ["No treatment needed right now", "Continue routine crop care"],
            "urgency": "low",
        }

    return {
        "disease_name": readable_name,
        "description": f"{readable_name} is a crop disease that can reduce plant health and yield if not managed early.",
        "symptoms": ["Visible leaf spots, discoloration, or tissue damage may appear."],
        "causes": ["Fungal, bacterial, or environmental stress depending on the crop."],
        "prevention": ["Remove infected leaves", "Avoid overhead watering", "Keep field hygiene"],
        "treatment": ["Apply a crop-appropriate treatment recommended by an agronomist", "Monitor the plant closely"],
        "urgency": "medium",
    }


def _get_disease_details(disease_name: str) -> dict[str, object]:
    if disease_name in DISEASE_DETAILS_CACHE:
        return DISEASE_DETAILS_CACHE[disease_name]

    fallback_details = _fallback_disease_details(disease_name)

    if not GEMINI_API_KEY:
        DISEASE_DETAILS_CACHE[disease_name] = fallback_details
        return fallback_details

    try:
        response = requests.post(
            GEMINI_ENDPOINT,
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": _build_disease_prompt(disease_name)}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 500,
                },
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        candidates = payload.get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidates")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        parsed = _parse_gemini_text(text)
        result = {**fallback_details, **parsed}
        DISEASE_DETAILS_CACHE[disease_name] = result
        return result
    except Exception:
        DISEASE_DETAILS_CACHE[disease_name] = fallback_details
        return fallback_details


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

        probabilities = MODEL.predict(image_array, verbose=0)[0]
        top_index = int(np.argmax(probabilities))
        top_class = CLASS_NAMES[top_index]
        top_confidence = float(probabilities[top_index])

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