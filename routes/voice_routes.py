from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel
from pydantic import ValidationError

from database import db
from models.disease_chat_model import DiseaseChatRequest
from utils.disease_chat import send_disease_chat_message


router = APIRouter()

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

whisper_model = WhisperModel(
    WHISPER_MODEL_SIZE,
    device=WHISPER_DEVICE,
    compute_type=WHISPER_COMPUTE_TYPE,
)


async def save_audio_temp(file: UploadFile) -> str:
    suffix = Path(file.filename or "voice.webm").suffix or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name

        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            temp_file.write(chunk)

    return temp_path


def transcribe_audio(file_path: str, language: str = "en") -> str:
    whisper_language = "ur" if language == "ur" else "en"
    initial_prompt = (
        "یہ عام پاکستانی اردو گفتگو ہے۔ سوال زراعت، فصل، گندم، بیماری، کھاد، پانی، کیڑے یا علاج کے بارے میں ہو سکتا ہے۔"
        if whisper_language == "ur"
        else "This is a farmer asking a simple agriculture question about crops, fertilizer, disease, irrigation, pests, or harvesting."
    )

    segments, info = whisper_model.transcribe(
        file_path,
        language=whisper_language,
        task="transcribe",
        beam_size=8,
        best_of=5,
        vad_filter=False,
        condition_on_previous_text=False,
        initial_prompt=initial_prompt,
        no_speech_threshold=0.2,
        log_prob_threshold=-1.0,
    )

    text_parts = []

    for segment in segments:
        text = segment.text.strip()
        print(f"[voice] segment: {text}")
        if text:
            text_parts.append(text)

    final_text = " ".join(text_parts).strip()
    print(f"[voice] detected_language={info.language}, text={final_text}")

    return final_text


@router.post("/voice")
async def voice_chat(
    audio: UploadFile = File(...),

    chat_id: str = Form(...),
    farmer_id: str = Form(...),
    language: str = Form("en"),
    chat_mode: str = Form("general"),
    prediction_id: str | None = Form(None),
):
    if not audio.content_type or not audio.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Please upload a valid audio file.")

    temp_audio_path = None

    try:
        temp_audio_path = await save_audio_temp(audio)

        user_text = await asyncio.to_thread(transcribe_audio, temp_audio_path, language)

        if not user_text:
            raise HTTPException(status_code=400, detail="Could not understand audio.")

        request = DiseaseChatRequest(
            chat_mode=chat_mode,
            prediction_id=prediction_id,
            chat_id=chat_id,
            farmer_id=farmer_id,
            language=language,
            user_message=user_text,
        )

        chatbot_response = await send_disease_chat_message(request=request, db=db)

        return {
            "userText": user_text,
            "reply": chatbot_response.get("ai_response", ""),
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors()) from e

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice chat failed: {str(e)}") from e

    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.remove(temp_audio_path)
            except OSError:
                pass
