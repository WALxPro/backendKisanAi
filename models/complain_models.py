from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class StatusEnum(str, Enum):
    PENDING = "Pending"
    IN_REVIEW = "In Review"
    RESOLVED = "Resolved"
    REJECTED = "Rejected"


class TimelineStep(BaseModel):
    step: str
    date: datetime = Field(default_factory=datetime.utcnow)


class ComplaintCreate(BaseModel):
    farmer_id: str
    title: str
    category: str
    description: str


class ComplaintStatusUpdate(BaseModel):
    status: StatusEnum
    note: Optional[str] = None


    