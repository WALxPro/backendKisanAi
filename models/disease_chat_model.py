from pydantic import BaseModel, Field, model_validator, validator
from typing import Optional, List , Literal
from datetime import datetime


class DiseaseMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    created_at: Optional[datetime] = None


class DiseaseChatRequest(BaseModel):
    chat_mode: Literal["disease", "general"] = "disease"
    chat_type: Optional[Literal["disease", "general"]] = None

    prediction_id: Optional[str] = None
    chat_id: str = Field(
    ...,
    description="Chat session ID (works for both disease and general chats)"
)  # FIX: keep chat session id separate from prediction id.
    farmer_id: str = Field(..., description="Firebase UID for the farmer")  # FIX: accept UID sent by mobile for ownership validation.
    language: str = Field(default="en", description="Kaku reply language, defaults to English")  # FIX: default Kaku answer language to English if mobile sends nothing.
    user_message: str = Field(..., min_length=1, description="User's question about the disease")
    
    @validator('user_message')
    def validate_word_count(cls, v):
        word_count = len(v.split())
        if word_count > 50:
            raise ValueError(f"Message exceeds 50 words limit. Current: {word_count} words")
        return v

    @model_validator(mode="before")
    @classmethod
    def normalize_chat_mode(cls, values):
        if isinstance(values, dict):
            chat_type = values.get("chat_type")
            if chat_type and not values.get("chat_mode"):
                values["chat_mode"] = chat_type
        return values

    @model_validator(mode="after")
    def validate_prediction_id(self):
        chat_mode = self.chat_mode
        prediction_id = self.prediction_id

        if chat_mode == "disease" and not prediction_id:
            raise ValueError("prediction_id required for disease chat")

        if chat_mode == "general" and prediction_id:
            raise ValueError("prediction_id must not be provided for general chat")

        self.chat_type = chat_mode
        return self
class DiseaseChatCreate(BaseModel):
    prediction_id: str
    farmer_id: Optional[str] = None
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
