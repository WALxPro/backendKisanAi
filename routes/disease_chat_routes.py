from fastapi import APIRouter, HTTPException
from database import db
from datetime import datetime
from bson import ObjectId
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from models.disease_chat_model import DiseaseChatRequest, DiseaseMessage
from routes.disease_prediction_routes import _format_label

load_dotenv()

router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

GEMINI_LLM = (
    ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.2,
    )
    if GEMINI_API_KEY
    else None
)

MAX_CHATS = 3
MAX_WORDS = 50


def count_words(text: str) -> int:
    """Count words in text"""
    return len(text.split())


def validate_message_length(message: str) -> bool:
    """Validate message doesn't exceed word limit"""
    return count_words(message) <= MAX_WORDS


def _build_disease_chat_system_prompt(disease_name: str, disease_details: dict) -> str:
    """Build system prompt for disease chat"""
    readable_name = _format_label(disease_name)
    
    description = disease_details.get("description", "")
    symptoms = ", ".join(disease_details.get("symptoms", []))
    treatment = ", ".join(disease_details.get("treatment", []))
    prevention = ", ".join(disease_details.get("prevention", []))
    
    return (
        f"You are an agriculture expert assistant helping farmers understand plant diseases. "
        f"Your ONLY purpose is to answer questions related to plant diseases and agricultural health. "
        f"The farmer has detected a disease: {readable_name}. "
        f"Provide helpful, simple, and practical advice. Use easy words and short sentences. "
        f"Avoid technical terms. Be kind and supportive. "
        f"Disease Information: {description}. "
        f"Symptoms: {symptoms}. "
        f"Treatment: {treatment}. "
        f"Prevention: {prevention}. "
        f"IMPORTANT: Only answer questions related to this disease or plant diseases in general. "
        f"If the farmer asks questions outside of plant diseases (like general knowledge, politics, sports, weather, personal advice, etc.), "
        f"respond ONLY with: 'I can only provide assistance related to plant diseases. Please ask me questions about {readable_name} or other plant diseases.'"
    )


@router.post("/start-chat/{prediction_id}")
async def start_disease_chat(prediction_id: str, farmer_id: str = None):
    """Start a new disease chat session"""
    try:
        # Verify prediction exists
        prediction = await db.disease_predictions.find_one({"_id": ObjectId(prediction_id)})
        if not prediction:
            raise HTTPException(status_code=404, detail="Disease prediction not found")
        
        disease_name = prediction.get("predicted_class")
        disease_details = prediction.get("disease_details", {})
        
        # Check if chat already exists for this prediction
        existing_chat = await db.disease_chats.find_one({
            "prediction_id": prediction_id,
            "farmer_id": farmer_id
        })
        
        if existing_chat:
            # Return existing chat
            return {
                "chat_id": str(existing_chat["_id"]),
                "chat_count": existing_chat.get("chat_count", 0),
                "remaining_chats": MAX_CHATS - existing_chat.get("chat_count", 0),
                "message": "Chat session already exists",
                "can_continue": existing_chat.get("chat_count", 0) < MAX_CHATS
            }
        
        # Create new chat session
        chat_record = {
            "prediction_id": prediction_id,
            "farmer_id": farmer_id,
            "disease_name": disease_name,
            "disease_details": disease_details,
            "messages": [],
            "chat_count": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.disease_chats.insert_one(chat_record)
        
        return {
            "chat_id": str(result.inserted_id),
            "chat_count": 0,
            "remaining_chats": MAX_CHATS,
            "message": "Chat session started. You can ask up to 3 questions, each with max 50 words.",
            "can_continue": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start chat: {str(e)}")


@router.post("/send-message")
async def send_disease_chat_message(request: DiseaseChatRequest):
    """Send a message to disease chat and get AI response"""
    try:
        # Validate message length
        if not validate_message_length(request.user_message):
            word_count = count_words(request.user_message)
            raise HTTPException(
                status_code=400, 
                detail=f"Message exceeds 50 word limit. Current: {word_count} words"
            )
        
        # Get chat session
        chat = await db.disease_chats.find_one({"_id": ObjectId(request.prediction_id)})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Check chat limit
        chat_count = chat.get("chat_count", 0)
        if chat_count >= MAX_CHATS:
            raise HTTPException(
                status_code=400,
                detail=f"Chat limit reached. You can only chat 3 times about this disease."
            )
        
        # Check if Gemini is available
        if GEMINI_LLM is None:
            raise HTTPException(
                status_code=500,
                detail="AI assistant is not available. Please configure GEMINI_API_KEY."
            )
        
        # Get disease details for context
        disease_name = chat.get("disease_name")
        disease_details = chat.get("disease_details", {})
        
        # Build system message
        system_prompt = _build_disease_chat_system_prompt(disease_name, disease_details)
        
        try:
            # Get AI response
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=request.user_message)
            ]
            
            response = GEMINI_LLM.invoke(messages)
            ai_response = response.content if hasattr(response, "content") else str(response)
            
            # Store messages in database
            new_messages = [
                {
                    "role": "user",
                    "content": request.user_message,
                    "created_at": datetime.utcnow()
                },
                {
                    "role": "assistant",
                    "content": ai_response,
                    "created_at": datetime.utcnow()
                }
            ]
            
            # Update chat with new messages and increment count
            updated_chat = await db.disease_chats.find_one_and_update(
                {"_id": ObjectId(request.prediction_id)},
                {
                    "$push": {"messages": {"$each": new_messages}},
                    "$inc": {"chat_count": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                },
                return_document=True
            )
            
            new_chat_count = updated_chat.get("chat_count", 1)
            remaining_chats = MAX_CHATS - new_chat_count
            
            return {
                "chat_id": str(updated_chat["_id"]),
                "chat_count": new_chat_count,
                "remaining_chats": remaining_chats,
                "user_message": request.user_message,
                "ai_response": ai_response,
                "can_continue": remaining_chats > 0,
                "message": f"Response sent. You have {remaining_chats} chat(s) remaining."
            }
        
        except Exception as gemini_error:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get AI response: {str(gemini_error)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.get("/history/{chat_id}")
async def get_chat_history(chat_id: str):
    """Get chat history for a disease chat session"""
    try:
        chat = await db.disease_chats.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {
            "chat_id": str(chat["_id"]),
            "disease_name": chat.get("disease_name"),
            "chat_count": chat.get("chat_count", 0),
            "remaining_chats": MAX_CHATS - chat.get("chat_count", 0),
            "messages": chat.get("messages", []),
            "created_at": chat.get("created_at"),
            "updated_at": chat.get("updated_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {str(e)}")


@router.get("/status/{chat_id}")
async def get_chat_status(chat_id: str):
    """Get current chat status and remaining chats"""
    try:
        chat = await db.disease_chats.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        chat_count = chat.get("chat_count", 0)
        remaining_chats = MAX_CHATS - chat_count
        
        return {
            "chat_id": str(chat["_id"]),
            "disease_name": chat.get("disease_name"),
            "chat_count": chat_count,
            "remaining_chats": remaining_chats,
            "can_continue": remaining_chats > 0,
            "max_words_per_message": MAX_WORDS
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat status: {str(e)}")
