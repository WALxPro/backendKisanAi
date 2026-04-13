from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class StatusEnum(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class TimelineStep(BaseModel):
    step: str
    done: bool
    date: Optional[datetime] = None

class ComplaintCreate(BaseModel):
    farmer_id: str  # Reference to Farmer model
    title: str
    category: str
    description: str

class Complaint(ComplaintCreate):
    id: str = Field(..., alias="_id")
    status: StatusEnum = StatusEnum.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    timeline: List[TimelineStep] = []

    class Config:
        from_attributes = True