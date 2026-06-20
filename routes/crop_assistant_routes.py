from __future__ import annotations

from fastapi import APIRouter, HTTPException
from database import db
from utils.crop_assistant import handle_crop_chat
from pydantic import BaseModel, Field
from typing import Literal


router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(min_length=1)


class CropChatRequest(BaseModel):
    farmer_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    crop_name: str | None = None
    location: str | None = None
    language: str | None = "en"
    chat_history: list[ChatMessage] = Field(default_factory=list)


@router.post("/chat")
async def crop_assistant_chat(payload: CropChatRequest):
    try:
        return await handle_crop_chat(payload, db=db)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Crop assistant chat failed: {str(exc)}") from exc
