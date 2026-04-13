from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Literal, Optional


class Blog(BaseModel):
    title: str
    description: str
    category: str
    author: str
    image: HttpUrl
    status: Literal["Published", "Draft"]
    created_at: Optional[datetime] = None


class UpdateBlog(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    author:str=None
    image: Optional[HttpUrl] = None
    status: Optional[Literal["Published", "Draft"]] = None