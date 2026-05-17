from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class DiseaseMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    created_at: Optional[datetime] = None


class DiseaseChatRequest(BaseModel):
    prediction_id: str = Field(..., description="Disease prediction ID from /disease/predict")
    farmer_id: str = Field(..., description="Unique farmer ID")
    user_message: str = Field(..., min_length=1, description="User's question about the disease")
    
    @validator('user_message')
    def validate_word_count(cls, v):
        word_count = len(v.split())
        if word_count > 50:
            raise ValueError(f"Message exceeds 50 words limit. Current: {word_count} words")
        return v


class DiseaseChatCreate(BaseModel):
    prediction_id: str
    farmer_id: str
    disease_name: str
    messages: List[DiseaseMessage] = Field(default_factory=list)
    chat_count: int = 0  # Number of times user has chatted (max 3)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DiseaseChatResponse(BaseModel):
    chat_id: str
    chat_count: int
    remaining_chats: int
    message: str
    response: str
    can_continue: bool
